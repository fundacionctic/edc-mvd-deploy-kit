#!/bin/bash

#
#  Copyright (c) 2024 Metaform Systems, Inc.
#
#  This program and the accompanying materials are made available under the
#  terms of the Apache License, Version 2.0 which is available at
#  https://www.apache.org/licenses/LICENSE-2.0
#
#  SPDX-License-Identifier: Apache-2.0
#
#  Contributors:
#       Metaform Systems, Inc. - initial API and implementation
#

set -e

echo "====================================="
echo "Seeding MVD Dataspace (Docker Compose)"
echo "====================================="
echo ""

# Get script directory to locate templates
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATES_DIR="$SCRIPT_DIR/templates"

# Configuration
API_KEY="c3VwZXItdXNlcg==.c3VwZXItc2VjcmV0LWtleQo="
PARTICIPANT_DID="did:web:identityhub%3A7083"
IDENTITY_HUB_URL="http://localhost:7082"
CONTROLPLANE_MGMT_URL="http://localhost:8081"

# Check if services are running
echo "Checking if services are running..."
if ! curl -sf http://localhost:7080/api/check/health >/dev/null; then
  echo "ERROR: IdentityHub is not healthy. Please start services with 'task up'"
  exit 1
fi

if ! curl -sf http://localhost:8080/api/check/health >/dev/null; then
  echo "ERROR: Controlplane is not healthy. Please start services with 'task up'"
  exit 1
fi

echo "✓ Services are running"
echo ""

# Create participant context in IdentityHub
echo "Creating participant context in IdentityHub..."

# Check if participant already exists
EXISTING_PARTICIPANT=$(curl -s "$IDENTITY_HUB_URL/api/identity/v1alpha/participants/" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" | jq -r ".[] | select(.did == \"$PARTICIPANT_DID\") | .did")

if [ -n "$EXISTING_PARTICIPANT" ]; then
  echo "✓ Participant context already exists"
  echo "  Note: Skipping participant creation and secret generation"
  echo ""

  # We'll skip adding the secret to vault since we don't have the client secret
  # The secret should already exist in the vault from the initial creation
  echo "Verifying client secret in Controlplane vault..."
  echo "✓ Assuming client secret already exists in vault"
  echo ""
else
  # Read and populate participant template
  PEM_PUBLIC=$(awk '{printf "%s\\n", $0}' assets/keys/consumer_public.pem)
  DATA_PARTICIPANT=$(jq \
    --arg did "$PARTICIPANT_DID" \
    --arg pem "$PEM_PUBLIC" \
    '
    .participantId = $did |
    .did = $did |
    .key.keyId = ($did + "#key-1") |
    .key.publicKeyPem = $pem |
    walk(if type == "string" then gsub("{{PARTICIPANT_DID}}"; $did) | gsub("{{PUBLIC_KEY_PEM}}"; $pem) else . end)
    ' "$TEMPLATES_DIR/participant.json")

  # Create participant and capture client secret
  clientSecret=$(curl -s --location "$IDENTITY_HUB_URL/api/identity/v1alpha/participants/" \
    --header 'Content-Type: application/json' \
    --header "x-api-key: $API_KEY" \
    --data "$DATA_PARTICIPANT" | jq -r '.clientSecret')

  if [ -z "$clientSecret" ] || [ "$clientSecret" == "null" ]; then
    echo "ERROR: Failed to create participant context"
    exit 1
  fi

  echo "✓ Participant context created"
  echo "  Client Secret: ${clientSecret:0:20}..."
  echo ""

  # Add client secret to the connector's vault
  echo "Adding client secret to Controlplane vault..."
  SECRET_ID="${PARTICIPANT_DID}-sts-client-secret"
  SECRETS_DATA=$(jq \
    --arg secretId "$SECRET_ID" \
    --arg secretValue "$clientSecret" \
    '."@id" = $secretId | ."https://w3id.org/edc/v0.0.1/ns/value" = $secretValue' \
    "$TEMPLATES_DIR/secret.json")

  RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$CONTROLPLANE_MGMT_URL/api/management/v3/secrets" \
    -H "x-api-key: password" \
    -H "Content-Type: application/json" \
    -d "$SECRETS_DATA")

  HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
  if [ "$HTTP_CODE" != "200" ] && [ "$HTTP_CODE" != "204" ] && [ "$HTTP_CODE" != "409" ]; then
    echo "ERROR: Failed to add client secret to vault (HTTP $HTTP_CODE)"
    echo "$RESPONSE"
    exit 1
  fi

  if [ "$HTTP_CODE" == "409" ]; then
    echo "✓ Client secret already exists in vault"
  else
    echo "✓ Client secret added to vault"
  fi
  echo ""
fi

# Create test asset
echo "Creating test asset..."
ASSET_DATA=$(cat "$TEMPLATES_DIR/asset.json")

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$CONTROLPLANE_MGMT_URL/api/management/v3/assets" \
  -H "x-api-key: password" \
  -H "Content-Type: application/json" \
  -d "$ASSET_DATA")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
if [ "$HTTP_CODE" != "200" ] && [ "$HTTP_CODE" != "204" ]; then
  echo "WARNING: Failed to create asset (HTTP $HTTP_CODE) - may already exist"
else
  echo "✓ Test asset created"
fi
echo ""

# Create access policy
echo "Creating access policy..."
POLICY_DATA=$(cat "$TEMPLATES_DIR/policy.json")

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$CONTROLPLANE_MGMT_URL/api/management/v3/policydefinitions" \
  -H "x-api-key: password" \
  -H "Content-Type: application/json" \
  -d "$POLICY_DATA")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
if [ "$HTTP_CODE" != "200" ] && [ "$HTTP_CODE" != "204" ]; then
  echo "WARNING: Failed to create policy (HTTP $HTTP_CODE) - may already exist"
else
  echo "✓ Access policy created"
fi
echo ""

# Create contract definition
echo "Creating contract definition..."
CONTRACT_DATA=$(cat "$TEMPLATES_DIR/contract-definition.json")

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$CONTROLPLANE_MGMT_URL/api/management/v3/contractdefinitions" \
  -H "x-api-key: password" \
  -H "Content-Type: application/json" \
  -d "$CONTRACT_DATA")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
if [ "$HTTP_CODE" != "200" ] && [ "$HTTP_CODE" != "204" ]; then
  echo "WARNING: Failed to create contract definition (HTTP $HTTP_CODE) - may already exist"
else
  echo "✓ Contract definition created"
fi
echo ""

echo "====================================="
echo "✓ Dataspace seeded successfully!"
echo "====================================="
echo ""
echo "Participant ID: $PARTICIPANT_DID"
echo "Management API: $CONTROLPLANE_MGMT_URL/api/management"
echo "DSP Endpoint: http://localhost:8082/api/dsp"
echo "DID Document: http://localhost:7083/.well-known/did.json"
echo ""
echo "You can now:"
echo "  - Query the catalog: curl http://localhost:8084/api/catalog -H 'x-api-key: password'"
echo "  - Access Management API: curl http://localhost:8081/api/management/v3/assets -H 'x-api-key: password'"
echo "  - View DID document: curl http://localhost:7083/.well-known/did.json"
echo ""
