#!/bin/bash

#
# Seed Issuer Attestation Database
#
# Same logic as original, but magic numbers (and a few magic strings)
# are extracted into tunable env vars. Defaults preserve original behavior.
#

set -e

echo "============================================="
echo "Issuer Attestation Database Seeding"
echo "============================================="
echo ""

# Docker Compose / services
: "${COMPOSE_FILE:=compose.issuer.yaml}"
: "${POSTGRES_SERVICE:=issuer-postgres}"
: "${SERVICE_RUNNING_REGEX:=(running|Up)}"

# Database identifiers
: "${ATTESTATION_TABLE:=membership_attestations}"
: "${COL_MEMBERSHIP_TYPE:=membership_type}"
: "${COL_HOLDER_ID:=holder_id}"
: "${COL_START_DATE:=membership_start_date}"

# Business semantics
: "${MEMBERSHIP_TYPE_FULL:=1}" # 1 = Full Member (original magic number)

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Check if .env exists
if [ ! -f "$ROOT_DIR/.env" ]; then
  echo "❌ Error: .env file not found"
  exit 1
fi

# Source .env
set -a
source "$ROOT_DIR/.env"
set +a

# Check issuer mode
if [ "$ISSUER_MODE" != "local" ]; then
  echo "ℹ️  ISSUER_MODE=$ISSUER_MODE - skipping local issuer seeding"
  echo ""
  echo "For external issuer, add attestations manually or via issuer's admin API"
  exit 0
fi

# Check if issuer postgres is running
if ! docker compose -f "$ROOT_DIR/$COMPOSE_FILE" ps "$POSTGRES_SERVICE" | grep -qE "$SERVICE_RUNNING_REGEX"; then
  echo "❌ Error: Issuer PostgreSQL is not running"
  echo "   Please start issuer stack first: task issuer-up"
  exit 1
fi

echo "📋 Adding participant to issuer attestation database..."
echo "   Participant DID: $PARTICIPANT_DID"
echo ""

# Add participant attestation to database
# membership_type: 1 = Full Member (now variable: MEMBERSHIP_TYPE_FULL)
docker compose -f "$ROOT_DIR/$COMPOSE_FILE" exec -T "$POSTGRES_SERVICE" psql -U "$ISSUER_DB_USER" -d "$ISSUER_DB_NAME" <<EOSQL
INSERT INTO ${ATTESTATION_TABLE} (${COL_MEMBERSHIP_TYPE}, ${COL_HOLDER_ID}, ${COL_START_DATE})
VALUES (${MEMBERSHIP_TYPE_FULL}, '${PARTICIPANT_DID}', NOW())
ON CONFLICT (${COL_HOLDER_ID}) DO UPDATE
SET ${COL_MEMBERSHIP_TYPE} = ${MEMBERSHIP_TYPE_FULL}, ${COL_START_DATE} = NOW();
EOSQL

if [ $? -eq 0 ]; then
  echo "✓ Participant attestation added/updated"
else
  echo "❌ Error: Failed to add attestation"
  exit 1
fi

echo ""

# Verify attestation was added
echo "🔍 Verifying attestation..."
ATTESTATION=$(docker compose -f "$ROOT_DIR/$COMPOSE_FILE" exec -T "$POSTGRES_SERVICE" \
  psql -U "$ISSUER_DB_USER" -d "$ISSUER_DB_NAME" -t -c \
  "SELECT ${COL_HOLDER_ID} FROM ${ATTESTATION_TABLE} WHERE ${COL_HOLDER_ID} = '${PARTICIPANT_DID}';")

if echo "$ATTESTATION" | grep -q "$PARTICIPANT_DID"; then
  echo "✓ Attestation verified"
else
  echo "❌ Error: Attestation not found in database"
  exit 1
fi

echo ""
echo "============================================="
echo "✓ Issuer seeding complete!"
echo "============================================="
echo ""
echo "The participant can now request credentials from the issuer:"
echo "  task request-credential"
echo ""
