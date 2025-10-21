#!/bin/bash

#
# Load Environment Configuration
#
# This script loads the .env file and validates required variables.
# It uses hybrid validation: strict for critical vars, defaults for optional ones.
#
# Usage:
#   source scripts/load-env.sh
#   OR
#   . scripts/load-env.sh
#

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Check if .env exists, if not copy from .env.example
if [ ! -f "$ROOT_DIR/.env" ]; then
  echo "⚠️  .env file not found"

  if [ -f "$ROOT_DIR/.env.example" ]; then
    echo "📋 Creating .env from .env.example..."
    cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
    echo "✓ .env created"
    echo ""
    echo "⚠️  Please review and customize .env before proceeding!"
    echo "   Critical settings to review:"
    echo "   - PARTICIPANT_DID (your participant identity)"
    echo "   - ISSUER_MODE (local or external)"
    echo "   - API keys and tokens (change for production!)"
    echo ""
    exit 1
  else
    echo "❌ Error: Neither .env nor .env.example found"
    exit 1
  fi
fi

# Source .env to load all variables
set -a
source "$ROOT_DIR/.env"
set +a

# ============================================
# CRITICAL VARIABLES - Must be set
# ============================================

CRITICAL_VARS=(
  "PARTICIPANT_DID"
  "VAULT_TOKEN"
  "DB_USER"
  "DB_PASSWORD"
  "DB_NAME"
  "MANAGEMENT_API_KEY"
  "SUPERUSER_API_KEY"
)

MISSING_VARS=()

for var in "${CRITICAL_VARS[@]}"; do
  if [ -z "${!var}" ]; then
    MISSING_VARS+=("$var")
  fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
  echo "❌ Error: Required variables not set in .env:"
  for var in "${MISSING_VARS[@]}"; do
    echo "   - $var"
  done
  echo ""
  echo "Please set these variables in .env and try again."
  exit 1
fi

# ============================================
# OPTIONAL VARIABLES - Set defaults if missing
# ============================================

# Debug ports
: ${IDENTITYHUB_DEBUG_PORT:=1044}
: ${CONTROLPLANE_DEBUG_PORT:=1045}
: ${DATAPLANE_DEBUG_PORT:=1046}
: ${ISSUER_DEBUG_PORT:=1047}

# Service ports (use standard defaults if not set)
: ${IDENTITYHUB_PORT:=7080}
: ${IDENTITYHUB_CREDENTIALS_PORT:=7081}
: ${IDENTITYHUB_IDENTITY_PORT:=7082}
: ${IDENTITYHUB_DID_PORT:=7083}
: ${IDENTITYHUB_STS_PORT:=7086}

: ${CONTROLPLANE_PORT:=8080}
: ${CONTROLPLANE_MGMT_PORT:=8081}
: ${CONTROLPLANE_DSP_PORT:=8082}
: ${CONTROLPLANE_CONTROL_PORT:=8083}
: ${CONTROLPLANE_CATALOG_PORT:=8084}

: ${DATAPLANE_PUBLIC_PORT:=11001}
: ${DATAPLANE_CONTROL_PORT:=11002}
: ${DATAPLANE_PORT:=11003}

: ${POSTGRES_PORT:=5432}
: ${VAULT_PORT:=8200}

# Infrastructure ports (issuer)
: ${ISSUER_PUBLIC_PORT:=9876}
: ${ISSUER_HTTP_PORT:=10010}
: ${ISSUER_STS_PORT:=10011}
: ${ISSUER_ISSUANCE_PORT:=10012}
: ${ISSUER_ADMIN_PORT:=10013}
: ${ISSUER_VERSION_PORT:=10014}
: ${ISSUER_IDENTITY_PORT:=10015}

# Key file paths
: ${PARTICIPANT_PUBLIC_KEY_FILE:=assets/keys/consumer_public.pem}
: ${PARTICIPANT_PRIVATE_KEY_FILE:=assets/keys/consumer_private.pem}
: ${PARTICIPANT_KEY_ALIAS:=key-1}

: ${ISSUER_PUBLIC_KEY_FILE:=assets/issuer/public.pem}
: ${ISSUER_PRIVATE_KEY_FILE:=assets/issuer/private.pem}
: ${ISSUER_SIGNING_KEY_ALIAS:=issuer-signing-key}

# Issuer mode
: ${ISSUER_MODE:=local}

# Issuer database (only for local mode)
: ${ISSUER_DB_NAME:=issuer}
: ${ISSUER_DB_USER:=issuer}
: ${ISSUER_DB_PASSWORD:=issuer_password}

# Issuer vault (only for local mode)
: ${ISSUER_VAULT_TOKEN:=issuer-vault-token}

# Computed URLs (from host machine)
: ${VAULT_HOST_URL:=http://localhost:${VAULT_PORT}}
: ${IDENTITYHUB_HOST_URL:=http://localhost:${IDENTITYHUB_IDENTITY_PORT}}
: ${CONTROLPLANE_MGMT_HOST_URL:=http://localhost:${CONTROLPLANE_MGMT_PORT}}

# Internal URLs (from Docker containers)
: ${VAULT_CONTAINER_URL:=http://vault:8200}
: ${POSTGRES_CONTAINER_URL:=jdbc:postgresql://postgres:5432}
: ${IDENTITYHUB_CONTAINER_URL:=http://identityhub:7082}
: ${CONTROLPLANE_CONTAINER_URL:=http://controlplane:8082}

# Export all defaults so they're available to calling scripts
export IDENTITYHUB_DEBUG_PORT CONTROLPLANE_DEBUG_PORT DATAPLANE_DEBUG_PORT ISSUER_DEBUG_PORT
export IDENTITYHUB_PORT IDENTITYHUB_CREDENTIALS_PORT IDENTITYHUB_IDENTITY_PORT IDENTITYHUB_DID_PORT IDENTITYHUB_STS_PORT
export CONTROLPLANE_PORT CONTROLPLANE_MGMT_PORT CONTROLPLANE_DSP_PORT CONTROLPLANE_CONTROL_PORT CONTROLPLANE_CATALOG_PORT
export DATAPLANE_PUBLIC_PORT DATAPLANE_CONTROL_PORT DATAPLANE_PORT
export POSTGRES_PORT VAULT_PORT
export ISSUER_PUBLIC_PORT ISSUER_HTTP_PORT ISSUER_STS_PORT ISSUER_ISSUANCE_PORT ISSUER_ADMIN_PORT ISSUER_VERSION_PORT ISSUER_IDENTITY_PORT
export PARTICIPANT_PUBLIC_KEY_FILE PARTICIPANT_PRIVATE_KEY_FILE PARTICIPANT_KEY_ALIAS
export ISSUER_PUBLIC_KEY_FILE ISSUER_PRIVATE_KEY_FILE ISSUER_SIGNING_KEY_ALIAS
export ISSUER_MODE ISSUER_DB_NAME ISSUER_DB_USER ISSUER_DB_PASSWORD ISSUER_VAULT_TOKEN
export VAULT_HOST_URL IDENTITYHUB_HOST_URL CONTROLPLANE_MGMT_HOST_URL
export VAULT_CONTAINER_URL POSTGRES_CONTAINER_URL IDENTITYHUB_CONTAINER_URL CONTROLPLANE_CONTAINER_URL

# Validation complete
echo "✓ Environment configuration loaded successfully"
echo "  Participant DID: $PARTICIPANT_DID"
echo "  Issuer Mode: $ISSUER_MODE"
