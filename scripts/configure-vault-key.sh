#!/bin/bash

set -e

VAULT_URL="http://localhost:8200"
VAULT_TOKEN="root-token"
KEY_FILE="assets/keys/consumer_private.pem"
KEY_ID="key-1"

echo "Configuring private key '$KEY_ID' in Vault..."

# Read the private key
PRIVATE_KEY=$(cat "$KEY_FILE")

# Create JSON payload using jq
JSON_PAYLOAD=$(jq -n \
  --arg key "$PRIVATE_KEY" \
  '{data: {content: $key}}')

# Add to vault
RESPONSE=$(curl -s -X POST \
  -H "X-Vault-Token: $VAULT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$JSON_PAYLOAD" \
  "$VAULT_URL/v1/secret/data/$KEY_ID")

echo "$RESPONSE" | jq .

echo ""
echo "✓ Private key configured in Vault"

# Verify
echo ""
echo "Verifying key format..."
STORED_KEY=$(curl -s -H "X-Vault-Token: $VAULT_TOKEN" \
  "$VAULT_URL/v1/secret/data/$KEY_ID" | jq -r '.data.data.content')

echo "$STORED_KEY" | head -2
echo "..."
echo "$STORED_KEY" | tail -1

echo ""
echo "✓ Key format verified"
