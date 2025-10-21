#!/bin/bash

#
# Configure Issuer Service
#
# This script:
# 1. Generates config files from templates
# 2. Configures the issuer private key in Vault
# 3. Verifies the setup
#

set -e

echo "============================================="
echo "Issuer Service Configuration"
echo "============================================="
echo ""

: "${DOCKER_NETWORK_NAME:=mvd-network}"

# Vault connectivity
: "${VAULT_HOST:=localhost}"
: "${VAULT_PORT:=8201}" # Issuer vault external port
: "${VAULT_URL:=http://${VAULT_HOST}:${VAULT_PORT}}"

# Startup and health-check timings
: "${INITIAL_VAULT_WAIT_SECONDS:=5}"          # initial wait after starting vault
: "${VAULT_HEALTH_MAX_RETRIES:=30}"           # max number of health-check attempts
: "${VAULT_HEALTH_RETRY_INTERVAL_SECONDS:=2}" # seconds between health checks

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Check if .env exists
if [ ! -f "$ROOT_DIR/.env" ]; then
  echo "❌ Error: .env file not found"
  echo "   Please create .env from .env.example first"
  exit 1
fi

# Source .env to get configuration
set -a
source "$ROOT_DIR/.env"
set +a

# Validate issuer mode
if [ "$ISSUER_MODE" != "local" ] && [ "$ISSUER_MODE" != "external" ]; then
  echo "❌ Error: ISSUER_MODE must be 'local' or 'external'"
  echo "   Current value: $ISSUER_MODE"
  exit 1
fi

if [ "$ISSUER_MODE" == "external" ]; then
  echo "ℹ️  ISSUER_MODE=external - skipping local issuer configuration"
  echo ""
  echo "External issuer URLs:"
  echo "  STS:      $ISSUER_EXTERNAL_STS_URL"
  echo "  Issuance: $ISSUER_EXTERNAL_ISSUANCE_URL"
  echo "  Admin:    $ISSUER_EXTERNAL_ADMIN_URL"
  echo "  Identity: $ISSUER_EXTERNAL_IDENTITY_URL"
  echo ""
  exit 0
fi

echo "📋 Configuration mode: LOCAL"
echo ""

# Check if keys exist
if [ ! -f "$ROOT_DIR/$ISSUER_PRIVATE_KEY_FILE" ]; then
  echo "❌ Error: Issuer private key not found: $ISSUER_PRIVATE_KEY_FILE"
  echo ""
  echo "Please generate issuer keys first:"
  echo "  task generate-issuer-keys"
  exit 1
fi

if [ ! -f "$ROOT_DIR/$ISSUER_PUBLIC_KEY_FILE" ]; then
  echo "❌ Error: Issuer public key not found: $ISSUER_PUBLIC_KEY_FILE"
  echo ""
  echo "Please generate issuer keys first:"
  echo "  task generate-issuer-keys"
  exit 1
fi

echo "✓ Issuer keys found"
echo ""

# Step 1: Generate config file from template
echo "📄 Step 1: Generating issuer service config..."

# Use envsubst to replace variables in template
envsubst <"$ROOT_DIR/config/issuer-service.env.template" >"$ROOT_DIR/config/issuer-service.env"

echo "✓ Config generated: config/issuer-service.env"
echo ""

# Step 2: Wait for issuer vault to be ready
echo "🔐 Step 2: Configuring issuer private key in Vault..."

# Ensure network exists
echo "   Ensuring Docker network exists..."
docker network create "$DOCKER_NETWORK_NAME" 2>/dev/null || true

# Check if issuer vault is running
if ! docker compose -f "$ROOT_DIR/compose.issuer.yaml" ps issuer-vault | grep -qE "(running|Up)"; then
  echo "⚠️  Issuer vault not running"
  echo "   Starting issuer vault..."
  docker compose -f "$ROOT_DIR/compose.issuer.yaml" up -d issuer-vault

  echo "   Waiting for vault to be ready..."
  sleep "$INITIAL_VAULT_WAIT_SECONDS"

  # Wait for vault to be healthy
  MAX_RETRIES="$VAULT_HEALTH_MAX_RETRIES"
  RETRY_COUNT=0
  while [ "$RETRY_COUNT" -lt "$MAX_RETRIES" ]; do
    if docker compose -f "$ROOT_DIR/compose.issuer.yaml" ps issuer-vault | grep -q "healthy"; then
      break
    fi
    echo "   Waiting for vault (attempt $((RETRY_COUNT + 1))/$MAX_RETRIES)..."
    sleep "$VAULT_HEALTH_RETRY_INTERVAL_SECONDS"
    RETRY_COUNT=$((RETRY_COUNT + 1))
  done

  if [ "$RETRY_COUNT" -eq "$MAX_RETRIES" ]; then
    echo "❌ Error: Vault failed to become healthy"
    exit 1
  fi
fi

echo "✓ Issuer vault is ready"
echo ""

# Read the issuer private key
ISSUER_PRIVATE_KEY=$(cat "$ROOT_DIR/$ISSUER_PRIVATE_KEY_FILE")

# Create JSON payload using jq
JSON_PAYLOAD=$(jq -n \
  --arg key "$ISSUER_PRIVATE_KEY" \
  '{data: {content: $key}}')

# Add to vault
RESPONSE=$(curl -s -X POST \
  -H "X-Vault-Token: $ISSUER_VAULT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$JSON_PAYLOAD" \
  "$VAULT_URL/v1/secret/data/$ISSUER_SIGNING_KEY_ALIAS")

if echo "$RESPONSE" | jq -e '.errors' >/dev/null 2>&1; then
  echo "❌ Error storing key in Vault:"
  echo "$RESPONSE" | jq '.errors'
  exit 1
fi

echo "✓ Issuer private key configured in Vault"
echo ""

# Verify
echo "🔍 Step 3: Verifying configuration..."

STORED_KEY=$(curl -s -H "X-Vault-Token: $ISSUER_VAULT_TOKEN" \
  "$VAULT_URL/v1/secret/data/$ISSUER_SIGNING_KEY_ALIAS" | jq -r '.data.data.content')

if [ -z "$STORED_KEY" ] || [ "$STORED_KEY" == "null" ]; then
  echo "❌ Error: Failed to verify key in Vault"
  exit 1
fi

echo "✓ Key successfully stored and retrieved from Vault"
echo ""

# Display summary
echo "============================================="
echo "✓ Issuer configuration complete!"
echo "============================================="
echo ""
echo "Generated files:"
echo "  Config: config/issuer-service.env"
echo ""
echo "Vault configuration:"
echo "  URL: $VAULT_URL"
echo "  Key alias: $ISSUER_SIGNING_KEY_ALIAS"
echo ""
echo "Next steps:"
echo "  1. Start issuer stack: task issuer-up"
echo "  2. Verify services: task issuer-status"
echo "  3. Test DID resolution: curl http://${ISSUER_PUBLIC_HOST}:${ISSUER_PUBLIC_PORT}/.well-known/did.json"
echo ""
