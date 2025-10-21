#!/bin/bash

#
# Request Credential from Issuer
#
# This script requests a verifiable credential from the issuer service
# for the configured participant.
#

set -e

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

# Parse arguments
CREDENTIAL_TYPE="${1:-MembershipCredential}"

echo "============================================="
echo "Credential Request"
echo "============================================="
echo ""
echo "Credential Type: $CREDENTIAL_TYPE"
echo "Holder: $PARTICIPANT_DID"
echo "Issuer: $ISSUER_DID"
echo ""

# Base64-encode the participant DID for the URL
ENCODED_PARTICIPANT_DID=$(echo -n "$PARTICIPANT_DID" | base64 | tr -d '\n')

# Construct the identity hub URL
IDENTITY_HUB_URL="http://localhost:${IDENTITYHUB_IDENTITY_PORT}"

echo "📤 Sending credential request..."
echo ""

# Request credential
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
  "$IDENTITY_HUB_URL/api/identity/v1alpha/participants/$ENCODED_PARTICIPANT_DID/credentials/request" \
  -H "x-api-key: $SUPERUSER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "issuerDid": "'"$ISSUER_DID"'",
    "holderPid": "'"$PARTICIPANT_DID"'",
    "credentials": [{
      "format": "VC1_0_JWT",
      "credentialType": "'"$CREDENTIAL_TYPE"'"
    }]
  }')

# Extract HTTP code and body
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

echo "HTTP Status: $HTTP_CODE"
echo ""

if [ "$HTTP_CODE" -ge 200 ] && [ "$HTTP_CODE" -lt 300 ]; then
  echo "✓ Response:"
  echo "$BODY" | jq .

  if echo "$BODY" | jq -e '.id' >/dev/null 2>&1; then
    echo ""
    echo "============================================="
    echo "✓ Credential request successful!"
    echo "============================================="
    REQUEST_ID=$(echo "$BODY" | jq -r '.id')
    echo ""
    echo "Request ID: $REQUEST_ID"
    echo ""
    echo "The credential should now be available in the participant's identity hub."
    echo ""
    echo "To verify, list credentials:"
    echo "  curl -s \"$IDENTITY_HUB_URL/api/identity/v1alpha/participants/$ENCODED_PARTICIPANT_DID/credentials\" \\"
    echo "    -H \"x-api-key: $SUPERUSER_API_KEY\" | jq ."
    echo ""
  else
    echo ""
    echo "⚠️  Request accepted but no ID returned"
  fi
else
  echo "❌ Credential request failed!"
  echo ""
  echo "Error response:"
  echo "$BODY" | jq . 2>/dev/null || echo "$BODY"
  echo ""

  # Provide helpful diagnostics
  echo "Troubleshooting:"
  echo "  1. Check issuer service is running: task issuer-status"
  echo "  2. Verify participant attestation: task verify-issuer"
  echo "  3. Check issuer logs: docker compose -f compose.issuer.yaml logs issuer-service"
  echo ""
  exit 1
fi
