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

# Configuration
MGMT_URL="http://localhost:8081"
DSP_URL="http://controlplane:8082/api/dsp"
API_KEY="password"
PARTICIPANT_DID="did:web:identityhub%3A7083"

# Ensure private key is in vault
echo "🔑 Step 0: Configure private key in Vault"
echo "--------------------------------------------"
if [ ! -f "scripts/configure-vault-key.sh" ]; then
  echo "❌ Error: configure-vault-key.sh not found"
  exit 1
fi

./scripts/configure-vault-key.sh >/dev/null 2>&1
echo "✓ Private key configured"
echo ""

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
    CREDS=$(curl -s "http://localhost:7082/api/identity/v1alpha/participants/$PARTICIPANT_DID/credentials" \
      -H "x-api-key: c3VwZXItdXNlcg==.c3VwZXItc2VjcmV0LWtleQo=" 2>/dev/null || echo "[]")

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
      echo "Waiting for negotiation to finalize..."
      sleep 3

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
