#!/bin/bash

# ============================================================
# PROVIDER DATABASE DEBUG SCRIPT
# ============================================================
# Pretty-prints all provider database contents for debugging
# Usage: ./debug_databases.sh <postgres_container_name>

set -e

POSTGRES_CONTAINER=${1:-"mvd-provider-postgres"}

echo "============================================================"
echo "PROVIDER DATABASE DEBUG REPORT"
echo "============================================================"
echo ""

# Function to query database safely with vertical output
query_db_vertical() {
    local db=$1
    local query=$2
    PGPASSWORD=postgres psql -h "$POSTGRES_CONTAINER" -U postgres -d "$db" -x -c "$query" 2>/dev/null
}

# Function to get table count
get_table_count() {
    local db=$1
    local table=$2
    PGPASSWORD=postgres psql -h "$POSTGRES_CONTAINER" -U postgres -d "$db" -t -c "SELECT COUNT(*) FROM $table;" 2>/dev/null | tr -d ' ' || echo "0"
}

# Function to get tables for a database
get_tables() {
    local db=$1
    PGPASSWORD=postgres psql -h "$POSTGRES_CONTAINER" -U postgres -d "$db" -t -c "
        SELECT tablename FROM pg_tables 
        WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
        ORDER BY tablename;" 2>/dev/null | tr -d ' ' | grep -v "^$" || echo ""
}

# Function to get column names for a table
get_columns() {
    local db=$1
    local table=$2
    PGPASSWORD=postgres psql -h "$POSTGRES_CONTAINER" -U postgres -d "$db" -t -c "
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = '$table' AND table_schema = 'public'
        ORDER BY ordinal_position;" 2>/dev/null | tr -d ' ' | grep -v "^$" || echo ""
}

# Function to show table data in vertical format
show_table_data() {
    local db=$1
    local table=$2
    local limit=$3
    
    echo "📋 Data (showing each field on separate line):"
    
    # Get all rows and display each field on a separate line
    PGPASSWORD=postgres psql -h "$POSTGRES_CONTAINER" -U postgres -d "$db" -t -c "
        SELECT row_number() OVER () as row_num, * FROM $table LIMIT $limit;" 2>/dev/null | while IFS='|' read -r line; do
        if [ -n "$line" ]; then
            # Get column names
            columns=$(get_columns "$db" "$table")
            
            # Split the line by | and display each field
            echo "  ┌─ Row $(echo "$line" | cut -d'|' -f1 | tr -d ' ') ─"
            field_num=2
            for column in $columns; do
                if [ -n "$column" ]; then
                    value=$(echo "$line" | cut -d'|' -f$field_num | sed 's/^ *//;s/ *$//')
                    echo "  │ $column: $value"
                    field_num=$((field_num + 1))
                fi
            done
            echo "  └─────────────────────────────────────────"
            echo ""
        fi
    done 2>/dev/null || echo "❌ Could not retrieve data in vertical format"
}

# Function to debug a single database
debug_database() {
    local db=$1
    local display_name=$2
    
    echo "📊 $display_name ($db)"
    echo "------------------------------------------------------------"
    
    if ! PGPASSWORD=postgres psql -h "$POSTGRES_CONTAINER" -U postgres -d "$db" -c "SELECT 1;" >/dev/null 2>&1; then
        echo "❌ Database not accessible"
        echo ""
        return
    fi
    
    # Show table overview in vertical format
    echo "📋 Tables Overview:"
    PGPASSWORD=postgres psql -h "$POSTGRES_CONTAINER" -U postgres -d "$db" -t -c "
        SELECT schemaname, tablename, 
               pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
        FROM pg_tables 
        WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
        ORDER BY schemaname, tablename;" 2>/dev/null | while IFS='|' read -r schema table size; do
        if [ -n "$table" ]; then
            echo "  • Schema: $(echo "$schema" | tr -d ' ')"
            echo "    Table:  $(echo "$table" | tr -d ' ')"
            echo "    Size:   $(echo "$size" | tr -d ' ')"
            echo ""
        fi
    done || echo "❌ Could not retrieve table information"
    
    echo ""
    
    # Show detailed contents
    tables=$(get_tables "$db")
    
    if [ -z "$tables" ]; then
        echo "📋 No tables found"
        echo ""
        return
    fi
    
    for table in $tables; do
        if [ -n "$table" ]; then
            echo "📄 Table: $table"
            echo "----------------------------------------"
            
            count=$(get_table_count "$db" "$table")
            echo "📊 Row count: $count"
            echo ""
            
            if [ "$count" -gt 0 ] && [ "$count" -le 10 ]; then
                show_table_data "$db" "$table" 10
            elif [ "$count" -gt 10 ]; then
                echo "📋 Sample data (first 3 rows, each field on separate line):"
                show_table_data "$db" "$table" 3
            else
                echo "📋 Table is empty"
            fi
            echo ""
        fi
    done
}

# Debug all databases
debug_database "provider_controlplane" "CONTROL PLANE DATABASE"
debug_database "provider_dataplane" "DATA PLANE DATABASE" 
debug_database "provider_identity" "IDENTITY HUB DATABASE"

echo "============================================================"
echo "DEBUG REPORT COMPLETE"
echo "============================================================"