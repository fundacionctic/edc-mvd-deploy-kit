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

# Configuration
API_KEY="c3VwZXItdXNlcg==.c3VwZXItc2VjcmV0LWtleQo="
PARTICIPANT_DID="did:web:identityhub%3A7083"
IDENTITY_HUB_URL="http://localhost:7082"
CONTROLPLANE_MGMT_URL="http://localhost:8081"

# Check if services are running
echo "Checking if services are running..."
if ! curl -sf http://localhost:7080/api/check/health > /dev/null; then
    echo "ERROR: IdentityHub is not healthy. Please start services with 'task up'"
    exit 1
fi

if ! curl -sf http://localhost:8080/api/check/health > /dev/null; then
    echo "ERROR: Controlplane is not healthy. Please start services with 'task up'"
    exit 1
fi

echo "✓ Services are running"
echo ""

# Create participant context in IdentityHub
echo "Creating participant context in IdentityHub..."
PEM_PUBLIC=$(sed -E ':a;N;$!ba;s/\r{0,1}\n/\\n/g' assets/keys/consumer_public.pem)
DATA_PARTICIPANT=$(jq -n --arg pem "$PEM_PUBLIC" '{
  "roles":[],
  "serviceEndpoints":[
    {
      "type": "CredentialService",
      "serviceEndpoint": "http://identityhub:7081/api/credentials/v1/participants/ZGlkOndlYjppZGVudGl0eWh1YiUzQTcwODM=",
      "id": "credentialservice-1"
    },
    {
      "type": "ProtocolEndpoint",
      "serviceEndpoint": "http://controlplane:8082/api/dsp",
      "id": "dsp-endpoint"
    }
  ],
  "active": true,
  "participantId": "'"$PARTICIPANT_DID"'",
  "did": "'"$PARTICIPANT_DID"'",
  "key":{
    "keyId": "'"$PARTICIPANT_DID"'#key-1",
    "privateKeyAlias": "key-1",
    "publicKeyPem":"\($pem)"
  }
}')

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
SECRETS_DATA=$(jq -n --arg secret "$clientSecret" '{
  "@context" : {
    "edc" : "https://w3id.org/edc/v0.0.1/ns/"
  },
  "@type" : "https://w3id.org/edc/v0.0.1/ns/Secret",
  "@id" : "'"$PARTICIPANT_DID"'-sts-client-secret",
  "https://w3id.org/edc/v0.0.1/ns/value": "\($secret)"
}')

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$CONTROLPLANE_MGMT_URL/api/management/v3/secrets" \
  -H "x-api-key: password" \
  -H "Content-Type: application/json" \
  -d "$SECRETS_DATA")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
if [ "$HTTP_CODE" != "200" ] && [ "$HTTP_CODE" != "204" ]; then
  echo "ERROR: Failed to add client secret to vault (HTTP $HTTP_CODE)"
  echo "$RESPONSE"
  exit 1
fi

echo "✓ Client secret added to vault"
echo ""

# Create test asset
echo "Creating test asset..."
ASSET_DATA='{
  "@context": {
    "@vocab": "https://w3id.org/edc/v0.0.1/ns/"
  },
  "@id": "test-asset-1",
  "properties": {
    "name": "Test Asset 1",
    "description": "A test asset for demonstrating MVD",
    "contenttype": "application/json"
  },
  "dataAddress": {
    "@type": "DataAddress",
    "type": "HttpData",
    "baseUrl": "http://dataplane:11001/api/public/test-data"
  }
}'

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
POLICY_DATA='{
  "@context": {
    "@vocab": "https://w3id.org/edc/v0.0.1/ns/",
    "odrl": "http://www.w3.org/ns/odrl/2/"
  },
  "@id": "membership-policy",
  "@type": "PolicyDefinition",
  "policy": {
    "@type": "Set",
    "obligation": [],
    "prohibition": [],
    "permission": [
      {
        "action": "use",
        "constraint": {
          "leftOperand": "Membership.active",
          "operator": "eq",
          "rightOperand": "true"
        }
      }
    ]
  }
}'

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
CONTRACT_DATA='{
  "@context": {
    "@vocab": "https://w3id.org/edc/v0.0.1/ns/"
  },
  "@id": "test-contract-def",
  "@type": "ContractDefinition",
  "accessPolicyId": "membership-policy",
  "contractPolicyId": "membership-policy",
  "assetsSelector": [
    {
      "operandLeft": "https://w3id.org/edc/v0.0.1/ns/id",
      "operator": "=",
      "operandRight": "test-asset-1"
    }
  ]
}'

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
