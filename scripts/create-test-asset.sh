#!/bin/bash

#
# Simple script to create a test asset via the Management API
#

MGMT_URL="http://localhost:8081"
API_KEY="password"

echo "Creating test asset via Management API..."

curl -X POST "$MGMT_URL/api/management/v3/assets" \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "@context": {
      "@vocab": "https://w3id.org/edc/v0.0.1/ns/"
    },
    "@id": "test-asset-'$(date +%s)'",
    "properties": {
      "name": "Test Asset",
      "description": "A simple test asset",
      "contenttype": "application/json"
    },
    "dataAddress": {
      "@type": "DataAddress",
      "type": "HttpData",
      "baseUrl": "http://example.com/data"
    }
  }'

echo ""
echo "Asset created successfully!"
