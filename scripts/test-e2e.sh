#!/bin/bash

#
# End-to-End Self-Negotiation Test Script
#
# This script demonstrates contract negotiation where a connector
# negotiates with itself via the DSP protocol.
#

set -e

echo "============================================="
echo "MVD End-to-End Self-Negotiation Test"
echo "============================================="
echo ""

# Default configuration (can be overridden by environment)
: "${E2E_SKIP_VAULT_CONFIG:=false}"
: "${E2E_NEGOTIATION_WAIT_SECONDS:=3}"
: "${E2E_SHOW_VERBOSE_OUTPUT:=false}"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load environment configuration
set -a
source "$ROOT_DIR/.env"
set +a

# Configuration
MGMT_URL="$CONTROLPLANE_MGMT_HOST_URL"
DSP_URL="$CONTROLPLANE_CONTAINER_URL/api/dsp"
API_KEY="$MANAGEMENT_API_KEY"
VAULT_CONFIG_SCRIPT="$SCRIPT_DIR/configure-vault-key.sh"

# Ensure private key is in vault
if [ "$E2E_SKIP_VAULT_CONFIG" != "true" ]; then
  echo "🔑 Step 0: Configure private key in Vault"
  echo "--------------------------------------------"
  if [ ! -f "$VAULT_CONFIG_SCRIPT" ]; then
    echo "❌ Error: Vault configuration script not found: $VAULT_CONFIG_SCRIPT"
    exit 1
  fi

  if [ "$E2E_SHOW_VERBOSE_OUTPUT" = "true" ]; then
    "$VAULT_CONFIG_SCRIPT"
  else
    "$VAULT_CONFIG_SCRIPT" >/dev/null 2>&1
  fi
  echo "✓ Private key configured"
  echo ""
else
  echo "⚠️  Skipping vault configuration (E2E_SKIP_VAULT_CONFIG=true)"
  echo ""
fi

# Step 1: List assets
echo "📋 Step 1: List available assets"
echo "--------------------------------------------"
ASSETS=$(curl -s -X POST "$MGMT_URL/api/management/v3/assets/request" \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
    "@type": "QuerySpec"
  }')

echo "$ASSETS" | jq -r '.[] | "  - \(.["@id"]): \(.properties.name)"'
ASSET_ID=$(echo "$ASSETS" | jq -r '.[0]["@id"]')
echo ""
echo "✓ Found asset: $ASSET_ID"
echo ""

# Step 2: Request catalog from self
echo "📋 Step 2: Request catalog from self (DSP)"
echo "--------------------------------------------"
CATALOG=$(curl -s -X POST "$MGMT_URL/api/management/v3/catalog/request" \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
    "@type": "CatalogRequest",
    "counterPartyAddress": "'"$DSP_URL"'",
    "counterPartyId": "'"$PARTICIPANT_DID"'",
    "protocol": "dataspace-protocol-http"
  }')

# Check for errors
if echo "$CATALOG" | jq -e '.[0].message' >/dev/null 2>&1; then
  ERROR_MSG=$(echo "$CATALOG" | jq -r '.[0].message')
  echo "⚠️  Catalog request failed:"
  echo "   $ERROR_MSG"
  echo ""

  if echo "$ERROR_MSG" | grep -q "Unauthorized"; then
    echo "📝 Diagnosis: Credentials Issue"
    echo "--------------------------------------------"
    echo "The connector needs proper VerifiableCredentials to authenticate."
    echo "Your setup has credentials for a different DID namespace."
    echo ""
    echo "Current participant DID: $PARTICIPANT_DID"
    echo ""
    echo "Checking existing credentials..."
    CREDS=$(curl -s "http://localhost:${IDENTITYHUB_IDENTITY_PORT}/api/identity/v1alpha/participants/$PARTICIPANT_DID/credentials" \
      -H "x-api-key: $SUPERUSER_API_KEY" 2>/dev/null || echo "[]")

    CRED_COUNT=$(echo "$CREDS" | jq 'length')
    if [ "$CRED_COUNT" -eq 0 ]; then
      echo "❌ No credentials found for this participant"
      echo ""
      echo "💡 Solution: The participant needs MembershipCredential"
      echo "   This requires the full MVD setup with issuer service."
    else
      echo "✓ Found $CRED_COUNT credentials"
      echo "$CREDS" | jq -r '.[] | "  - " + .verifiableCredential.credential.type[1]'
    fi
  fi
  echo ""
else
  # Success! Parse catalog
  DATASET_COUNT=$(echo "$CATALOG" | jq -r '."dcat:dataset" | length')
  echo "✓ Catalog received with $DATASET_COUNT datasets"

  if [ "$DATASET_COUNT" -gt 0 ]; then
    echo ""
    echo "Datasets:"
    echo "$CATALOG" | jq -r '."dcat:dataset"[] | "  - \(.["@id"]): \(.description // "No description")"'

    # Extract offer for negotiation
    OFFER_ID=$(echo "$CATALOG" | jq -r '."dcat:dataset"[0]."odrl:hasPolicy"["@id"]')
    echo ""
    echo "✓ Offer ID for negotiation: $OFFER_ID"
    echo ""

    # Step 3: Initiate contract negotiation
    echo "📋 Step 3: Initiate contract negotiation"
    echo "--------------------------------------------"
    NEGOTIATION=$(curl -s -X POST "$MGMT_URL/api/management/v3/contractnegotiations" \
      -H "x-api-key: $API_KEY" \
      -H "Content-Type: application/json" \
      -d '{
            "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
            "@type": "ContractRequest",
            "counterPartyAddress": "'"$DSP_URL"'",
            "counterPartyId": "'"$PARTICIPANT_DID"'",
            "protocol": "dataspace-protocol-http",
            "policy": {
              "@type": "Offer",
              "@id": "'"$OFFER_ID"'",
              "assigner": "'"$PARTICIPANT_DID"'",
              "target": "'"$ASSET_ID"'"
            }
          }')

    NEG_ID=$(echo "$NEGOTIATION" | jq -r '.["@id"] // empty')
    if [ -n "$NEG_ID" ]; then
      echo "✓ Negotiation initiated: $NEG_ID"
      echo ""
      echo "Waiting for negotiation to finalize ($E2E_NEGOTIATION_WAIT_SECONDS seconds)..."
      sleep "$E2E_NEGOTIATION_WAIT_SECONDS"

      # Step 4: Check negotiation status
      echo ""
      echo "📋 Step 4: Query negotiation status"
      echo "--------------------------------------------"
      NEG_STATUS=$(curl -s -X GET "$MGMT_URL/api/management/v3/contractnegotiations/$NEG_ID" \
        -H "x-api-key: $API_KEY")

      STATE=$(echo "$NEG_STATUS" | jq -r '.state')
      echo "Negotiation state: $STATE"

      if [ "$STATE" == "FINALIZED" ]; then
        CONTRACT_ID=$(echo "$NEG_STATUS" | jq -r '.contractAgreementId')
        echo "✓ Contract agreement ID: $CONTRACT_ID"
        echo ""
        echo "🎉 Self-negotiation successful!"
      else
        echo "⏳ Negotiation in progress (state: $STATE)"
        echo "   Run: curl -X GET $MGMT_URL/api/management/v3/contractnegotiations/$NEG_ID -H 'x-api-key: $API_KEY'"
      fi
    else
      echo "❌ Negotiation failed:"
      echo "$NEGOTIATION" | jq .
    fi
  fi
fi

echo ""
echo "============================================="
echo "Test completed"
echo "============================================="
