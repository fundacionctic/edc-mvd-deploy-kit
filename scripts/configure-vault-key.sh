#!/bin/bash

set -e

# Default configuration (can be overridden by environment)
: "${VAULT_SECRET_PATH_PREFIX:=secret/data}"
: "${VAULT_VERIFY_KEY:=true}"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load environment configuration
set -a
source "$ROOT_DIR/.env"
set +a

# Derived configuration
VAULT_URL="$VAULT_HOST_URL"
KEY_FILE="$ROOT_DIR/$PARTICIPANT_PRIVATE_KEY_FILE"
KEY_ID="$PARTICIPANT_KEY_ALIAS"
VAULT_SECRET_PATH="$VAULT_SECRET_PATH_PREFIX/$KEY_ID"

echo "Configuring private key '$KEY_ID' in Vault..."
echo "  Vault URL: $VAULT_URL"
echo "  Key file: $KEY_FILE"
echo ""

# Read the private key
PRIVATE_KEY=$(cat "$KEY_FILE")

# Create JSON payload using jq
JSON_PAYLOAD=$(jq -n \
  --arg key "$PRIVATE_KEY" \
  '{data: {content: $key}}')

# Add to vault
echo "Storing key in Vault at path: v1/$VAULT_SECRET_PATH"
RESPONSE=$(curl -s -X POST \
  -H "X-Vault-Token: $VAULT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$JSON_PAYLOAD" \
  "$VAULT_URL/v1/$VAULT_SECRET_PATH")

# Check for errors
if echo "$RESPONSE" | jq -e '.errors' >/dev/null 2>&1; then
  echo "❌ Error storing key in Vault:"
  echo "$RESPONSE" | jq '.errors'
  exit 1
fi

echo "✓ Private key configured in Vault"
echo ""

# Verify
if [ "$VAULT_VERIFY_KEY" = "true" ]; then
  echo "Verifying key storage..."
  STORED_KEY=$(curl -s -H "X-Vault-Token: $VAULT_TOKEN" \
    "$VAULT_URL/v1/$VAULT_SECRET_PATH" | jq -r '.data.data.content')

  if [ -z "$STORED_KEY" ] || [ "$STORED_KEY" = "null" ]; then
    echo "❌ Error: Failed to retrieve key from Vault"
    exit 1
  fi

  echo "Key format preview:"
  echo "$STORED_KEY" | head -n 2
  echo "..."
  echo "$STORED_KEY" | tail -n 1

  echo ""
  echo "✓ Key verified in Vault"
else
  echo "⚠️  Skipping verification (VAULT_VERIFY_KEY=false)"
fi
