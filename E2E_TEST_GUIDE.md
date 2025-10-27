# End-to-End Test Guide for MVD Single-Connector Setup

## Overview

This guide provides a complete walkthrough for testing a Minimum Viable Dataspace (MVD) deployment where a single Provider participant acts as both data provider and consumer. This scenario is useful for Docker Compose deployments or simplified testing environments.

The end-to-end test covers:
1. **Contract Negotiation** - Establishing agreement to access data
2. **Transfer Process** - Initiating data transfer with agreed terms
3. **Data Access** - Retrieving actual data through the dataplane

---

## Prerequisites: Detailed Explanation

Before executing the end-to-end test, your dataspace deployment must be properly configured. This section explains each prerequisite in detail.

### Prerequisite 1: Assets Are Seeded

#### What Are Assets?

In EDC, an **Asset** represents a data resource that can be shared in the dataspace. It contains:
- **Metadata**: Descriptive information (name, description, content type, etc.)
- **Data Address**: Technical information about where the actual data resides (backend API URL, authentication, etc.)

Assets are registered in the provider's control plane and appear in catalogs that consumers can query.

#### Why Are Assets Needed?

Without registered assets:
- The catalog will be empty when queried
- There will be nothing to negotiate access for
- The dataplane won't know what data to serve

#### Asset Structure

An asset consists of two main parts:

**1. Asset Metadata** (what consumers see in the catalog):
```json
{
  "@id": "asset-1",
  "properties": {
    "name": "Sample Dataset",
    "description": "Test data for E2E validation",
    "contenttype": "application/json",
    "version": "1.0"
  }
}
```

**2. Data Address** (how the dataplane accesses the data):
```json
{
  "@type": "DataAddress",
  "type": "HttpData",
  "baseUrl": "http://backend-service:8080/api/data",
  "proxyPath": "true",
  "proxyMethod": "true",
  "proxyQueryParams": "true"
}
```

#### How to Create Assets

Assets are created via the Management API:

```http
POST http://<controlplane>:<mgmt-port>/api/management/v3/assets
Content-Type: application/json
X-Api-Key: <management-api-key>

{
  "@context": {
    "edc": "https://w3id.org/edc/v0.0.1/ns/"
  },
  "@id": "asset-1",
  "@type": "Asset",
  "properties": {
    "name": "Sample Dataset",
    "description": "Test data for E2E validation",
    "contenttype": "application/json"
  },
  "dataAddress": {
    "@type": "DataAddress",
    "type": "HttpData",
    "baseUrl": "http://backend-service:8080/api/data"
  }
}
```

#### How to Verify Assets Exist

Query the assets endpoint:

```http
POST http://<controlplane>:<mgmt-port>/api/management/v3/assets/request
Content-Type: application/json
X-Api-Key: <management-api-key>

{
  "@context": {
    "edc": "https://w3id.org/edc/v0.0.1/ns/"
  },
  "@type": "QuerySpec",
  "limit": 50
}
```

You should receive a list of registered assets. If empty, proceed to create assets.

---

### Prerequisite 2: Policies and Contract Definitions Exist

#### What Are Policies?

**Policies** define the rules and constraints for accessing assets. In MVD, policies use the ODRL (Open Digital Rights Language) vocabulary and typically enforce:
- **Membership requirements**: Participant must have a MembershipCredential
- **Access level constraints**: Participant must have DataProcessorCredential with specific access levels

#### Policy Types

1. **Access Policy**: Controls who can see the asset in the catalog
2. **Contract Policy**: Controls who can negotiate a contract for the asset
3. **Usage Policy**: Defines terms of use once access is granted

In MVD, access and contract policies are often the same, focusing on credential validation.

#### Example Policy Structure

```json
{
  "@id": "policy-1",
  "@type": "PolicyDefinition",
  "policy": {
    "@type": "Policy",
    "permission": [{
      "action": "use",
      "constraint": [
        {
          "leftOperand": "MembershipCredential",
          "operator": "eq",
          "rightOperand": "active"
        },
        {
          "leftOperand": "DataAccess.level",
          "operator": "eq",
          "rightOperand": "processing"
        }
      ]
    }]
  }
}
```

This policy requires:
- A valid MembershipCredential
- A DataProcessorCredential with `credentialSubject.level = "processing"`

#### What Are Contract Definitions?

**Contract Definitions** bind assets to policies, creating offers that appear in the catalog. They specify:
- Which **assets** are offered
- Which **access policy** controls catalog visibility
- Which **contract policy** governs negotiations

#### Contract Definition Structure

```json
{
  "@id": "contract-def-1",
  "@type": "ContractDefinition",
  "accessPolicyId": "policy-1",
  "contractPolicyId": "policy-1",
  "assetsSelector": [{
    "operandLeft": "@id",
    "operator": "=",
    "operandRight": "asset-1"
  }]
}
```

#### Why Are Policies and Contract Definitions Needed?

Without them:
- Assets won't appear in the catalog (no contract definition)
- Negotiations will fail (no contract policy to evaluate)
- The dataspace access control is undefined

#### How to Create Policies

```http
POST http://<controlplane>:<mgmt-port>/api/management/v3/policydefinitions
Content-Type: application/json
X-Api-Key: <management-api-key>

{
  "@context": {
    "edc": "https://w3id.org/edc/v0.0.1/ns/"
  },
  "@id": "membership-policy",
  "@type": "PolicyDefinition",
  "policy": {
    "@type": "Policy",
    "permission": [{
      "action": "use",
      "constraint": [{
        "leftOperand": "MembershipCredential",
        "operator": "eq",
        "rightOperand": "active"
      }]
    }]
  }
}
```

#### How to Create Contract Definitions

```http
POST http://<controlplane>:<mgmt-port>/api/management/v3/contractdefinitions
Content-Type: application/json
X-Api-Key: <management-api-key>

{
  "@context": {
    "edc": "https://w3id.org/edc/v0.0.1/ns/"
  },
  "@id": "contract-def-1",
  "@type": "ContractDefinition",
  "accessPolicyId": "membership-policy",
  "contractPolicyId": "membership-policy",
  "assetsSelector": [{
    "operandLeft": "@id",
    "operator": "=",
    "operandRight": "asset-1"
  }]
}
```

#### How to Verify Policies and Contract Definitions

Query policies:
```http
POST http://<controlplane>:<mgmt-port>/api/management/v3/policydefinitions/request
```

Query contract definitions:
```http
POST http://<controlplane>:<mgmt-port>/api/management/v3/contractdefinitions/request
```

---

### Prerequisite 3: Verifiable Credentials Are Issued

#### What Are Verifiable Credentials?

**Verifiable Credentials (VCs)** are digitally signed attestations that prove claims about a participant. In MVD, they enable decentralized access control without a central authority.

MVD uses two types of credentials:

**1. MembershipCredential**
- **Purpose**: Proves the participant is a member of the dataspace
- **Required for**: All DSP protocol operations (catalog requests, negotiations, transfers)
- **Issued by**: The dataspace issuer service
- **Credential Subject**: Contains participant identity

**2. DataProcessorCredential**
- **Purpose**: Proves the participant has specific data processing capabilities/permissions
- **Required for**: Accessing assets with `DataAccess.level` constraints
- **Contains**: Access level in `credentialSubject` (e.g., "processing", "sensitive")

#### Example MembershipCredential

```json
{
  "@context": ["https://www.w3.org/2018/credentials/v1"],
  "type": ["VerifiableCredential", "MembershipCredential"],
  "issuer": "did:web:issuer-service%3A10016:issuer",
  "issuanceDate": "2024-01-01T00:00:00Z",
  "credentialSubject": {
    "id": "did:web:provider-identityhub%3A7083:provider",
    "holderIdentifier": "provider-participant"
  },
  "proof": {
    "type": "JsonWebSignature2020",
    "created": "2024-01-01T00:00:00Z",
    "proofPurpose": "assertionMethod",
    "verificationMethod": "did:web:issuer-service%3A10016:issuer#key-1",
    "jws": "eyJhbGc..."
  }
}
```

#### Example DataProcessorCredential

```json
{
  "@context": ["https://www.w3.org/2018/credentials/v1"],
  "type": ["VerifiableCredential", "DataProcessorCredential"],
  "issuer": "did:web:issuer-service%3A10016:issuer",
  "issuanceDate": "2024-01-01T00:00:00Z",
  "credentialSubject": {
    "id": "did:web:provider-identityhub%3A7083:provider",
    "level": "processing"
  },
  "proof": {
    "type": "JsonWebSignature2020",
    "created": "2024-01-01T00:00:00Z",
    "proofPurpose": "assertionMethod",
    "verificationMethod": "did:web:issuer-service%3A10016:issuer#key-1",
    "jws": "eyJhbGc..."
  }
}
```

#### Why Are Credentials Needed?

Without proper credentials:
- **Catalog requests fail**: MembershipCredential required for DSP authentication
- **Negotiations fail**: Policy evaluation checks for required credentials
- **Transfers fail**: Contract agreement validation requires credential proof

#### How Credentials Are Issued

Credentials are issued through the MVD issuer service API:

```http
POST http://<issuer-service>/api/identity/v1alpha/participants/{participant-id}/credentials/request
Content-Type: application/json
X-Api-Key: <issuer-api-key>

{
  "issuerDid": "did:web:issuer-service%3A10016:issuer",
  "holderPid": "credential-request-1",
  "credentials": [
    {
      "format": "VC1_0_JWT",
      "credentialType": "MembershipCredential"
    },
    {
      "format": "VC1_0_JWT",
      "credentialType": "DataProcessorCredential",
      "credentialSubject": {
        "level": "processing"
      }
    }
  ]
}
```

#### How Credentials Are Stored

Issued credentials are stored in the participant's **IdentityHub**, which acts as a credential wallet. The connector retrieves credentials from IdentityHub when needed for DSP operations.

#### How to Verify Credentials Exist

Query the IdentityHub's credential store:

```http
POST http://<identityhub>:<port>/api/identity/v1alpha/participants/{participant-id}/credentials/query
Content-Type: application/json
X-Api-Key: <identityhub-api-key>

{
  "@context": {
    "edc": "https://w3id.org/edc/v0.0.1/ns/"
  },
  "@type": "QuerySpec"
}
```

You should see both MembershipCredential and DataProcessorCredential in the response.

#### Credential Flow in DSP Operations

1. **Consumer initiates catalog request** → Control plane queries IdentityHub for credentials
2. **Control plane creates VP (Verifiable Presentation)** → Signs the presentation with participant's key
3. **Sends DSP request with VP** → Provider receives and validates the presentation
4. **Provider validates credentials** → Checks issuer signature, expiration, credential type
5. **Provider evaluates policy** → Checks if credentials satisfy policy constraints
6. **Response sent** → Catalog/negotiation/transfer proceeds if validation succeeds

---

### Prerequisite 4: Backend Data API Is Available

#### What Is the Backend Data API?

The **backend data API** is the actual data source that your EDC connector exposes through the dataspace. It's a separate service (not part of EDC) that hosts the real data.

#### Architecture Overview

```
Consumer Request → Dataplane (EDC) → Backend API → Data Response
                     ↓ Validates EDR token
                     ↓ Proxies request
                     ↓ Returns data to consumer
```

The EDC dataplane acts as a **secure proxy**:
1. Receives requests with EDR tokens
2. Validates the token (checks contract agreement, expiration)
3. Forwards the request to the backend API
4. Returns the response to the consumer

#### Why Is Backend API Needed?

Without a backend API:
- The dataplane has nothing to proxy to
- Data transfer will fail with connection errors
- EDR tokens can be issued, but data access returns 502/504

#### Backend API Requirements

Your backend API must:
1. **Be reachable from the dataplane container** (network connectivity)
2. **Respond on the URL specified in the asset's DataAddress**
3. **Return data in the expected format** (JSON, CSV, binary, etc.)
4. **Not require authentication** (or use auth that dataplane can forward)

#### Example Backend API

Simple Flask example:

```python
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/data', methods=['GET'])
def get_data():
    return jsonify({
        "message": "Hello from backend!",
        "timestamp": "2024-01-01T12:00:00Z",
        "data": [1, 2, 3, 4, 5]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
```

#### Matching Backend API to Asset DataAddress

The asset's `dataAddress.baseUrl` must match your backend API:

**Asset DataAddress**:
```json
{
  "baseUrl": "http://backend-service:8080/api/data"
}
```

**Backend API must respond at**:
```
http://backend-service:8080/api/data
```

#### Docker Compose Networking

In Docker Compose, ensure:
1. Backend service is defined in the same `docker-compose.yml` or connected network
2. Service name matches the hostname in `baseUrl`
3. Internal ports are exposed (external exposure not required)

Example Docker Compose snippet:

```yaml
services:
  backend-api:
    image: my-backend-api:latest
    container_name: backend-service
    ports:
      - "8080:8080"
    networks:
      - dataspace-network

  provider-dataplane:
    image: dataplane:latest
    # ... other config ...
    networks:
      - dataspace-network
```

#### How to Verify Backend API

From within the dataplane container or network:

```bash
curl http://backend-service:8080/api/data
```

Should return your expected data.

---

## Complete End-to-End Test Procedure

Once all prerequisites are satisfied, execute the following steps.

### Phase 1: Catalog Discovery

#### Step 1.1: Request Catalog from Provider

```http
POST http://<provider-controlplane>:<mgmt-port>/api/management/v3/catalog/request
Content-Type: application/json
X-Api-Key: <management-api-key>

{
  "@context": {
    "edc": "https://w3id.org/edc/v0.0.1/ns/"
  },
  "@type": "CatalogRequest",
  "counterPartyAddress": "http://<provider-controlplane>:<dsp-port>/api/v1/dsp",
  "counterPartyId": "<provider-participant-id>",
  "protocol": "dataspace-protocol-http",
  "querySpec": {
    "filterExpression": []
  }
}
```

**Parameters**:
- `<provider-controlplane>`: Container hostname or localhost
- `<mgmt-port>`: Management API port (typically 8181 or 9191)
- `<dsp-port>`: DSP protocol port (typically 8282 or 8383)
- `<provider-participant-id>`: Participant DID (e.g., `did:web:provider-identityhub%3A7083:provider`)

#### Step 1.2: Parse Catalog Response

**Expected Response Structure**:
```json
{
  "@id": "catalog-id",
  "@type": "dcat:Catalog",
  "dcat:dataset": [
    {
      "@id": "asset-1",
      "@type": "dcat:Dataset",
      "odrl:hasPolicy": {
        "@id": "contract-offer-id-1",
        "@type": "odrl:Offer",
        "odrl:permission": {
          "odrl:action": "use",
          "odrl:constraint": [
            {
              "odrl:leftOperand": "MembershipCredential",
              "odrl:operator": "eq",
              "odrl:rightOperand": "active"
            }
          ]
        }
      },
      "dcat:distribution": [...],
      "name": "Sample Dataset",
      "contenttype": "application/json"
    }
  ],
  "participantId": "<provider-participant-id>"
}
```

**Extract These Values**:
- `dcat:dataset[].@id` → **Asset ID** (e.g., "asset-1")
- `dcat:dataset[].odrl:hasPolicy.@id` → **Policy ID** (e.g., "contract-offer-id-1")

---

### Phase 2: Contract Negotiation

#### Step 2.1: Initiate Contract Negotiation

```http
POST http://<provider-controlplane>:<mgmt-port>/api/management/v3/contractnegotiations
Content-Type: application/json
X-Api-Key: <management-api-key>

{
  "@context": {
    "edc": "https://w3id.org/edc/v0.0.1/ns/"
  },
  "@type": "ContractRequest",
  "counterPartyAddress": "http://<provider-controlplane>:<dsp-port>/api/v1/dsp",
  "counterPartyId": "<provider-participant-id>",
  "protocol": "dataspace-protocol-http",
  "policy": {
    "@type": "Offer",
    "@id": "<policy-id-from-catalog>",
    "target": "<asset-id-from-catalog>"
  }
}
```

**Response**:
```json
{
  "@type": "IdResponse",
  "@id": "<negotiation-id>",
  "createdAt": 1234567890,
  "@context": {...}
}
```

**Extract**: `@id` → **Negotiation ID**

#### Step 2.2: Poll Negotiation Status

```http
GET http://<provider-controlplane>:<mgmt-port>/api/management/v3/contractnegotiations/<negotiation-id>
X-Api-Key: <management-api-key>
```

**Poll every 1-2 seconds until `state` is `FINALIZED`**.

**State Progression**:
```
REQUESTING → REQUESTED → AGREEING → AGREED → FINALIZING → FINALIZED
```

**Final Response**:
```json
{
  "@type": "ContractNegotiation",
  "@id": "<negotiation-id>",
  "type": "CONSUMER",
  "protocol": "dataspace-protocol-http",
  "state": "FINALIZED",
  "counterPartyId": "<provider-participant-id>",
  "contractAgreementId": "<agreement-id>",
  "createdAt": 1234567890
}
```

**Extract**: `contractAgreementId` → **Agreement ID**

#### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Negotiation stuck in REQUESTING | Provider not reachable | Check `counterPartyAddress` and network connectivity |
| State becomes TERMINATED | Policy evaluation failed | Verify credentials exist and match policy constraints |
| 401/403 errors | Missing or invalid credentials | Check IdentityHub has required VCs |

---

### Phase 3: Transfer Process

#### Step 3.1: Initiate Transfer

```http
POST http://<provider-controlplane>:<mgmt-port>/api/management/v3/transferprocesses
Content-Type: application/json
X-Api-Key: <management-api-key>

{
  "@context": {
    "edc": "https://w3id.org/edc/v0.0.1/ns/"
  },
  "@type": "TransferRequest",
  "counterPartyAddress": "http://<provider-controlplane>:<dsp-port>/api/v1/dsp",
  "counterPartyId": "<provider-participant-id>",
  "contractId": "<agreement-id-from-negotiation>",
  "assetId": "<asset-id-from-catalog>",
  "protocol": "dataspace-protocol-http",
  "dataDestination": {
    "@type": "DataAddress",
    "type": "HttpProxy"
  }
}
```

**Transfer Types**:
- **HttpProxy**: Consumer pulls data from dataplane using EDR (recommended)
- **HttpData**: Provider pushes data to consumer endpoint (requires `receiverHttpEndpoint`)

**Response**:
```json
{
  "@type": "IdResponse",
  "@id": "<transfer-process-id>",
  "createdAt": 1234567890
}
```

**Extract**: `@id` → **Transfer Process ID**

#### Step 3.2: Poll Transfer Status

```http
GET http://<provider-controlplane>:<mgmt-port>/api/management/v3/transferprocesses/<transfer-process-id>
X-Api-Key: <management-api-key>
```

**Poll every 1-2 seconds until `state` is `STARTED`**.

**State Progression**:
```
REQUESTING → REQUESTED → STARTING → STARTED
```

**Final Response**:
```json
{
  "@type": "TransferProcess",
  "@id": "<transfer-process-id>",
  "state": "STARTED",
  "type": "CONSUMER",
  "contractId": "<agreement-id>",
  "assetId": "<asset-id>",
  "dataDestination": {...},
  "createdAt": 1234567890
}
```

---

### Phase 4: Data Access via EDR

#### Step 4.1: Retrieve EDR (Endpoint Data Reference)

**Option A: V1 API (Simpler)**:
```http
GET http://<provider-controlplane>:<mgmt-port>/api/management/v1/edrs?transferProcessId=<transfer-process-id>
X-Api-Key: <management-api-key>
```

**Option B: V3 API (Standard)**:
```http
POST http://<provider-controlplane>:<mgmt-port>/api/management/v3/edrs/request
Content-Type: application/json
X-Api-Key: <management-api-key>

{
  "@context": {
    "edc": "https://w3id.org/edc/v0.0.1/ns/"
  },
  "@type": "QuerySpec",
  "filterExpression": [
    {
      "operandLeft": "transferProcessId",
      "operator": "=",
      "operandRight": "<transfer-process-id>"
    }
  ]
}
```

**Response**:
```json
{
  "@type": "edc:DataAddress",
  "@id": "<edr-id>",
  "edc:agreementId": "<agreement-id>",
  "edc:assetId": "<asset-id>",
  "edc:providerId": "<provider-participant-id>",
  "edc:transferProcessId": "<transfer-process-id>",
  "edc:endpoint": "http://<dataplane-public-endpoint>/api/public",
  "edc:authKey": "Authorization",
  "edc:authCode": "eyJhbGciOiJFZERTQSJ9...",
  "edc:expirationDate": "2024-01-02T00:00:00Z"
}
```

**Extract**:
- `edc:endpoint` → **Dataplane Public API URL**
- `edc:authCode` → **Bearer Token**
- `edc:authKey` → **Header Name** (typically "Authorization")

#### Step 4.2: Access Data Through Dataplane

```http
GET <edc:endpoint>
Authorization: <edc:authCode>
```

**Example**:
```bash
curl -X GET \
  http://localhost:8185/api/public \
  -H "Authorization: eyJhbGciOiJFZERTQSJ9..."
```

**Expected Response**: The actual data from your backend API

**Example Success Response**:
```json
{
  "message": "Hello from backend!",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": [1, 2, 3, 4, 5]
}
```

#### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| 401 Unauthorized | Token invalid or expired | Re-fetch EDR, check token validity |
| 403 Forbidden | Contract agreement validation failed | Verify agreement is still valid |
| 404 Not Found | Wrong endpoint or path | Check `edc:endpoint` matches dataplane public API |
| 502 Bad Gateway | Backend API unreachable | Verify backend service is running and reachable |
| 504 Gateway Timeout | Backend API slow/unresponsive | Check backend service logs |

---

## Testing Checklist

Use this checklist to systematically verify your setup:

- [ ] **Assets**
  - [ ] At least one asset created
  - [ ] Asset has valid `dataAddress` with correct `baseUrl`
  - [ ] Asset appears in management API query

- [ ] **Policies**
  - [ ] Policy definition created
  - [ ] Policy constraints match available credentials
  - [ ] Policy appears in management API query

- [ ] **Contract Definitions**
  - [ ] Contract definition created
  - [ ] Links asset to access/contract policies
  - [ ] Contract definition appears in management API query

- [ ] **Credentials**
  - [ ] MembershipCredential issued to participant
  - [ ] DataProcessorCredential issued (if needed by policy)
  - [ ] Credentials stored in IdentityHub
  - [ ] Credentials are not expired

- [ ] **Backend API**
  - [ ] Service running and reachable
  - [ ] Responds at URL specified in asset DataAddress
  - [ ] Returns expected data format

- [ ] **Networking**
  - [ ] Control plane management API reachable
  - [ ] Control plane DSP endpoint reachable
  - [ ] Dataplane public API reachable
  - [ ] Backend API reachable from dataplane

- [ ] **DID Resolution**
  - [ ] Participant DID document accessible
  - [ ] Issuer DID document accessible
  - [ ] DID documents contain correct keys and service endpoints

---

## Automation Example: Shell Script

```bash
#!/bin/bash

# Configuration
MGMT_URL="http://localhost:8181/api/management"
DSP_URL="http://localhost:8282/api/v1/dsp"
PARTICIPANT_ID="did:web:provider-identityhub%3A7083:provider"
API_KEY="password"

echo "=== Phase 1: Catalog ==="
CATALOG=$(curl -s -X POST "$MGMT_URL/v3/catalog/request" \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: $API_KEY" \
  -d "{
    \"@context\": {\"edc\": \"https://w3id.org/edc/v0.0.1/ns/\"},
    \"@type\": \"CatalogRequest\",
    \"counterPartyAddress\": \"$DSP_URL\",
    \"counterPartyId\": \"$PARTICIPANT_ID\",
    \"protocol\": \"dataspace-protocol-http\"
  }")

ASSET_ID=$(echo "$CATALOG" | jq -r '."dcat:dataset"[0]."@id"')
POLICY_ID=$(echo "$CATALOG" | jq -r '."dcat:dataset"[0]."odrl:hasPolicy"."@id"')
echo "Asset ID: $ASSET_ID"
echo "Policy ID: $POLICY_ID"

echo "=== Phase 2: Negotiation ==="
NEG_RESPONSE=$(curl -s -X POST "$MGMT_URL/v3/contractnegotiations" \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: $API_KEY" \
  -d "{
    \"@context\": {\"edc\": \"https://w3id.org/edc/v0.0.1/ns/\"},
    \"@type\": \"ContractRequest\",
    \"counterPartyAddress\": \"$DSP_URL\",
    \"counterPartyId\": \"$PARTICIPANT_ID\",
    \"protocol\": \"dataspace-protocol-http\",
    \"policy\": {
      \"@type\": \"Offer\",
      \"@id\": \"$POLICY_ID\",
      \"target\": \"$ASSET_ID\"
    }
  }")

NEG_ID=$(echo "$NEG_RESPONSE" | jq -r '."@id"')
echo "Negotiation ID: $NEG_ID"

# Poll for FINALIZED
while true; do
  NEG_STATE=$(curl -s -X GET "$MGMT_URL/v3/contractnegotiations/$NEG_ID" \
    -H "X-Api-Key: $API_KEY" | jq -r '.state')
  echo "Negotiation state: $NEG_STATE"

  if [ "$NEG_STATE" == "FINALIZED" ]; then
    break
  elif [ "$NEG_STATE" == "TERMINATED" ]; then
    echo "Negotiation failed!"
    exit 1
  fi

  sleep 2
done

AGREEMENT_ID=$(curl -s -X GET "$MGMT_URL/v3/contractnegotiations/$NEG_ID" \
  -H "X-Api-Key: $API_KEY" | jq -r '.contractAgreementId')
echo "Agreement ID: $AGREEMENT_ID"

echo "=== Phase 3: Transfer ==="
TRANSFER_RESPONSE=$(curl -s -X POST "$MGMT_URL/v3/transferprocesses" \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: $API_KEY" \
  -d "{
    \"@context\": {\"edc\": \"https://w3id.org/edc/v0.0.1/ns/\"},
    \"@type\": \"TransferRequest\",
    \"counterPartyAddress\": \"$DSP_URL\",
    \"counterPartyId\": \"$PARTICIPANT_ID\",
    \"contractId\": \"$AGREEMENT_ID\",
    \"assetId\": \"$ASSET_ID\",
    \"protocol\": \"dataspace-protocol-http\",
    \"dataDestination\": {
      \"@type\": \"DataAddress\",
      \"type\": \"HttpProxy\"
    }
  }")

TRANSFER_ID=$(echo "$TRANSFER_RESPONSE" | jq -r '."@id"')
echo "Transfer ID: $TRANSFER_ID"

# Poll for STARTED
while true; do
  TRANSFER_STATE=$(curl -s -X GET "$MGMT_URL/v3/transferprocesses/$TRANSFER_ID" \
    -H "X-Api-Key: $API_KEY" | jq -r '.state')
  echo "Transfer state: $TRANSFER_STATE"

  if [ "$TRANSFER_STATE" == "STARTED" ]; then
    break
  elif [ "$TRANSFER_STATE" == "TERMINATED" ]; then
    echo "Transfer failed!"
    exit 1
  fi

  sleep 2
done

echo "=== Phase 4: Data Access ==="
EDR=$(curl -s -X GET "$MGMT_URL/v1/edrs?transferProcessId=$TRANSFER_ID" \
  -H "X-Api-Key: $API_KEY")

ENDPOINT=$(echo "$EDR" | jq -r '.[0]."edc:endpoint"')
AUTH_CODE=$(echo "$EDR" | jq -r '.[0]."edc:authCode"')

echo "Endpoint: $ENDPOINT"
echo "Fetching data..."

DATA=$(curl -s -X GET "$ENDPOINT" \
  -H "Authorization: $AUTH_CODE")

echo "Data received:"
echo "$DATA" | jq .

echo "=== Test Complete ==="
```

---

## Troubleshooting Guide

### Catalog is Empty

**Symptoms**: Catalog request returns empty `dcat:dataset` array

**Possible Causes**:
1. No assets created
2. No contract definitions created
3. Access policy too restrictive (participant doesn't have required credentials)

**Solutions**:
- Verify assets exist: Query `/api/management/v3/assets/request`
- Verify contract definitions exist: Query `/api/management/v3/contractdefinitions/request`
- Check access policy constraints match participant's credentials
- Review control plane logs for policy evaluation errors

### Negotiation Fails (TERMINATED state)

**Symptoms**: Contract negotiation reaches TERMINATED state instead of FINALIZED

**Possible Causes**:
1. Contract policy evaluation failed (missing credentials)
2. Participant DID resolution failed
3. Invalid contract offer ID

**Solutions**:
- Check participant has required credentials in IdentityHub
- Verify DID documents are accessible (try resolving `did:web:...` manually)
- Ensure policy ID from catalog is used exactly in negotiation request
- Review control plane logs for detailed error messages

### Transfer Fails (TERMINATED state)

**Symptoms**: Transfer process reaches TERMINATED state

**Possible Causes**:
1. Invalid contract agreement ID
2. Dataplane not reachable
3. Backend API not configured

**Solutions**:
- Verify agreement ID exists and is FINALIZED
- Check dataplane service is running and network-accessible
- Verify asset DataAddress points to valid backend service
- Review dataplane logs for connection errors

### EDR Retrieval Returns Empty

**Symptoms**: EDR query returns empty array or null

**Possible Causes**:
1. Transfer process not yet STARTED
2. Wrong transfer process ID
3. EDR expiration (unlikely immediately after transfer)

**Solutions**:
- Wait for transfer state to be STARTED before querying EDR
- Double-check transfer process ID matches
- Query all EDRs without filter to see if any exist

### Data Access Returns 401/403

**Symptoms**: Request to dataplane public API returns unauthorized/forbidden

**Possible Causes**:
1. EDR token expired
2. Token not included in request or wrong header name
3. Contract agreement no longer valid

**Solutions**:
- Verify `Authorization` header contains `edc:authCode` value
- Check `edc:expirationDate` in EDR response
- Ensure no extra spaces or quotes around token
- Try fetching fresh EDR

### Data Access Returns 502/504

**Symptoms**: Request to dataplane returns gateway errors

**Possible Causes**:
1. Backend API not running
2. Backend API URL wrong in asset DataAddress
3. Network connectivity issue between dataplane and backend

**Solutions**:
- Verify backend service is running: `docker ps` or check service logs
- Test backend directly from dataplane container: `docker exec <dataplane-container> curl http://backend:8080/api/data`
- Check asset DataAddress `baseUrl` matches actual backend endpoint
- Review dataplane logs for connection errors

---

## Additional Resources

### MVD-Specific Resources

- **Seed Scripts**: Reference `seed.sh` (IntelliJ) or `seed-k8s.sh` (Kubernetes) for seeding examples
- **Postman Collection**: Use `deployment/postman/MVD.postman_collection.json` as a reference
- **End-to-End Tests**: Review `tests/end2end` module for programmatic test examples

### EDC Documentation

- Management API Specification: https://eclipse-edc.github.io/docs/
- DSP Protocol: https://docs.internationaldataspaces.org/ids-knowledgebase/v/dataspace-protocol

### Docker Compose Networking

- Compose Networking Guide: https://docs.docker.com/compose/networking/
- Container DNS Resolution: https://docs.docker.com/config/containers/container-networking/

---

## Summary

This guide covered:

1. **Prerequisites**:
   - Assets: Data resources with metadata and backend addresses
   - Policies: Access control rules using ODRL
   - Contract Definitions: Bindings between assets and policies
   - Credentials: MembershipCredential and DataProcessorCredential
   - Backend API: Actual data source reachable from dataplane

2. **End-to-End Flow**:
   - Catalog discovery → Extract asset and policy IDs
   - Contract negotiation → Obtain agreement ID
   - Transfer initiation → Wait for STARTED state
   - EDR retrieval → Get dataplane endpoint and token
   - Data access → Fetch data through dataplane proxy

3. **Verification Steps**: How to confirm each prerequisite is satisfied

4. **Troubleshooting**: Common issues and solutions

For a single-connector setup where the provider acts as both consumer and provider, ensure all networking uses the correct hostnames and that credentials/policies are configured to allow self-service access.
