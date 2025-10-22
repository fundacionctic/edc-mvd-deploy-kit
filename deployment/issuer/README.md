# Issuer Service Deployment Guide

This directory contains configuration files and documentation for deploying the Issuer Service in the Eclipse EDC Minimum Viable Dataspace.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Configuration](#configuration)
5. [Deployment Steps](#deployment-steps)
6. [Seeding Process](#seeding-process)
7. [Verification](#verification)
8. [Troubleshooting](#troubleshooting)
9. [API Reference](#api-reference)
10. [Production Considerations](#production-considerations)

---

## Overview

The Issuer Service is responsible for:
- Issuing Verifiable Credentials to dataspace participants
- Managing attestation sources (evidence backing credential claims)
- Providing credential definitions (templates for credential types)
- Signing credentials using cryptographic keys
- Exposing DID documents for verification

---

## Prerequisites

### Required Software

- **Docker** 20.10+ and **Docker Compose** 2.x
- **Python** 3.8+ (for seeding scripts)
- **Task** (Task runner) - Optional but recommended
- **curl** (for health checks)
- **envsubst** (for configuration templating)
  - macOS: `brew install gettext`
  - Ubuntu: `apt-get install gettext-base`

### Docker Network

The Issuer services must join the `mvd-network`:

```bash
docker network create mvd-network
```

---

## Quick Start

### Option 1: Using Task Runner (Recommended)

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your configuration

# 2. Complete deployment (config generation + start + seed)
task issuer:deploy

# 3. Verify deployment
task issuer:verify
```

### Option 2: Manual Deployment

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your configuration

# 2. Generate configuration
task issuer:generate-config
# or: source .env && envsubst < config/issuer-service.env.template > config/issuer-service.env

# 3. Start services
task issuer:up
# or: docker compose -f docker-compose.issuer.yaml up -d

# 4. Seed the service
task issuer:seed
# or: source .env && python3 scripts/issuer/seed_issuer.py

# 5. Verify deployment
task issuer:verify
# or: python3 scripts/issuer/verify_deployment.py
```

---

## Configuration

### Environment Variables

The following environment variables must be configured in `.env`:

#### Issuer Identity

```bash
# DID (Decentralized Identifier)
ISSUER_DID=did:web:host.docker.internal%3A9876

# Public hostname for DID resolution
ISSUER_PUBLIC_HOST=host.docker.internal
```

#### Ports

```bash
ISSUER_HTTP_PORT=10010           # Main API
ISSUER_STS_PORT=10011            # STS
ISSUER_ISSUANCE_PORT=10012       # Issuance
ISSUER_ADMIN_PORT=10013          # Admin (CRITICAL for seeding!)
ISSUER_VERSION_PORT=10014        # Version
ISSUER_IDENTITY_PORT=10015       # Identity
ISSUER_DID_API_PORT=10016        # DID API
ISSUER_DEBUG_PORT=1044           # Debug
ISSUER_DID_PORT=9876             # DID Server (NGINX)
```

#### Database

```bash
ISSUER_DB_NAME=issuer
ISSUER_DB_USER=issuer
ISSUER_DB_PASSWORD=issuer        # ⚠️ CHANGE FOR PRODUCTION!
```

#### Authentication

```bash
# Superuser key for admin endpoints
# Format: base64(username).base64(password)
# Default: super-user / super-secret-key
ISSUER_SUPERUSER_KEY=c3VwZXItdXNlcg==.c3VwZXItc2VjcmV0LWtleQo=  # ⚠️ CHANGE FOR PRODUCTION!

# Identity API key
ISSUER_IDENTITY_API_KEY=password  # ⚠️ CHANGE FOR PRODUCTION!
```

#### Vault

```bash
ISSUER_VAULT_TOKEN=root           # ⚠️ CHANGE FOR PRODUCTION!
```

#### Keys

```bash
ISSUER_SIGNING_KEY_ALIAS=statuslist-signing-key
ISSUER_PUBLIC_KEY_FILE=assets/keys/issuer_public.pem
ISSUER_PRIVATE_KEY_FILE=assets/keys/issuer_private.pem
```

### Configuration Files

#### 1. `did.docker.json`

DID document served by NGINX at `http://localhost:9876/.well-known/did.json`

**Important:** The `publicKeyJwk` must match your actual signing key!

```json
{
  "id": "did:web:host.docker.internal%3A9876",
  "verificationMethod": [{
    "id": "did:web:host.docker.internal%3A9876#key-1",
    "type": "JsonWebKey2020",
    "controller": "did:web:host.docker.internal%3A9876",
    "publicKeyJwk": {
      "kty": "OKP",
      "crv": "Ed25519",
      "x": "Hsq2QXPbbsU7j6JwXstbpxGSgliI04g_fU3z2nwkuVc"
    }
  }],
  "authentication": ["key-1"],
  "@context": ["https://www.w3.org/ns/did/v1"]
}
```

#### 2. `nginx.conf`

NGINX configuration for serving the DID document.

#### 3. `init-issuer-db.sql`

PostgreSQL initialization script that:
- Creates `issuer` user and database
- Creates attestation tables:
  - `membership_attestations` - Stores membership data
  - `data_processor_attestations` - Stores data processing capabilities
- Seeds initial participant data (Consumer and Provider)

---

## Deployment Steps

### Step 1: Environment Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and configure Issuer-specific variables
3. Validate configuration:
   ```bash
   task issuer:validate-env
   ```

### Step 2: Generate Configuration

Generate the Issuer service configuration from the template:

```bash
task issuer:generate-config
```

This creates `config/issuer-service.env` from `config/issuer-service.env.template` using `envsubst`.

### Step 3: Start Services

Start all Issuer services (PostgreSQL, Vault, Issuer Service, DID Server):

```bash
task issuer:up
```

Or manually:

```bash
docker network create mvd-network || true
docker compose -f docker-compose.issuer.yaml up -d --wait
```

### Step 4: Verify Health

Check that all services are healthy:

```bash
task issuer:health
```

Or manually:

```bash
# Check Issuer service
curl http://localhost:10010/api/check/health

# Check DID server
curl http://localhost:9876/.well-known/did.json
```

### Step 5: Seed the Service

Run the seeding scripts to create participants, attestations, and credential definitions:

```bash
task issuer:seed
```

Or manually:

```bash
source .env
python3 scripts/issuer/seed_issuer.py
```

### Step 6: Verification

Verify that everything is deployed correctly:

```bash
task issuer:verify
```

---

## Seeding Process

The seeding process creates the foundational data required for the Issuer Service to issue credentials.

### Seeding Sequence

```
1. Wait for Issuer Service health
2. Check DID server accessibility
3. Create participant holders (Consumer, Provider)
4. Create attestation definitions
   - membership-attestation-db (queries membership_attestations table)
   - data-processor-attestation-db (queries data_processor_attestations table)
5. Create credential definitions
   - MembershipCredential (REQUIRED for MVD)
   - DataProcessorCredential (REQUIRED for MVD)
```

### Credential Types

#### MembershipCredential

**Purpose:** Proves dataspace membership

**Policy Evaluation:** Checks `membership.since` claim with date validation

**Required Claims:**
- `credentialSubject.membershipType` (e.g., "FullMember")
- `credentialSubject.membershipStartDate` (ISO 8601 timestamp)
- `credentialSubject.id` (participant DID)

**Attestation:** Database query against `membership_attestations` table

#### DataProcessorCredential

**Purpose:** Attests to data processing capabilities

**Policy Evaluation:** Checks `level` claim (e.g., "processing", "sensitive")

**Required Claims:**
- `credentialSubject.contractVersion` (e.g., "1.0.0")
- `credentialSubject.level` (e.g., "processing" or "sensitive")
- `credentialSubject.id` (participant DID)

**Attestation:** Database query against `data_processor_attestations` table

### Python Scripts

All seeding scripts are located in `scripts/issuer/`:

- **`config.py`** - Configuration management
- **`create_participants.py`** - Create participant holders
- **`create_attestations.py`** - Create attestation definitions
- **`create_credentials.py`** - Create credential definitions
- **`verify_deployment.py`** - Verify deployment health
- **`seed_issuer.py`** - Main orchestration script

**Requirements:**
- Python 3.8+
- Only built-in packages (no external dependencies)
- Environment variables for all configuration
- Comprehensive logging

---

## Verification

### Automated Verification

Run the complete verification suite:

```bash
task issuer:verify
```

This checks:
1. Issuer Service health endpoint
2. DID document accessibility
3. Participant holders registered
4. Attestation definitions created
5. Credential definitions created

### Manual Verification

#### 1. Check Service Status

```bash
task issuer:status
```

#### 2. Check Health Endpoints

```bash
# Issuer service health
curl http://localhost:10010/api/check/health

# DID document
curl http://localhost:9876/.well-known/did.json
```

#### 3. Query Seeded Data

**Headers for authenticated requests:**
```bash
ISSUER_CONTEXT="did:web:host.docker.internal%3A9876"
API_KEY="c3VwZXItdXNlcg==.c3VwZXItc2VjcmV0LWtleQo="
```

**List participants:**
```bash
curl -H "X-Api-Key: ${API_KEY}" \
  "http://localhost:10013/api/admin/v1alpha/participants/${ISSUER_CONTEXT}/holders"
```

**List attestations:**
```bash
curl -H "X-Api-Key: ${API_KEY}" \
  "http://localhost:10013/api/admin/v1alpha/participants/${ISSUER_CONTEXT}/attestations"
```

**List credential definitions:**
```bash
curl -H "X-Api-Key: ${API_KEY}" \
  "http://localhost:10013/api/admin/v1alpha/participants/${ISSUER_CONTEXT}/credentialdefinitions"
```

#### 4. Check Database

```bash
task issuer:db
```

Then run:
```sql
-- List membership attestations
SELECT * FROM membership_attestations;

-- List data processor attestations
SELECT * FROM data_processor_attestations;
```

---

## Troubleshooting

### Common Issues

#### 1. Service Health Check Fails

**Symptoms:**
- `curl http://localhost:10010/api/check/health` returns connection refused
- Docker container is not running

**Solutions:**
```bash
# Check container status
task issuer:status

# Check logs
task issuer:logs-service SERVICE=issuer-service

# Restart services
task issuer:restart
```

#### 2. Database Connection Refused

**Symptoms:**
- Issuer service logs show database connection errors
- PostgreSQL container is not healthy

**Solutions:**
```bash
# Check PostgreSQL status
docker compose -f docker-compose.issuer.yaml ps issuer-postgres

# Check PostgreSQL logs
task issuer:logs-service SERVICE=issuer-postgres

# Verify database connectivity from issuer
docker compose -f docker-compose.issuer.yaml exec issuer-service ping issuer-postgres
```

#### 3. Admin API Returns 401 Unauthorized

**Symptoms:**
- Seeding scripts fail with 401 errors
- Manual API calls return unauthorized

**Solutions:**
- Verify `X-Api-Key` header matches `ISSUER_SUPERUSER_KEY` in `.env`
- Default key: `c3VwZXItdXNlcg==.c3VwZXItc2VjcmV0LWtleQo=`
- Check key format: `base64(username).base64(password)`

#### 4. Attestation Queries Fail

**Symptoms:**
- Credential issuance fails
- Database attestations return no data

**Solutions:**
```bash
# Check database directly
task issuer:db
# Then: SELECT * FROM membership_attestations;

# Verify holder_id matches participant DID exactly
# Including URL encoding (: becomes %3A)

# Verify table name in attestation definition matches schema
```

#### 5. DID Resolution Fails

**Symptoms:**
- `curl http://localhost:9876/.well-known/did.json` fails
- NGINX container not running

**Solutions:**
```bash
# Check NGINX container
docker compose -f docker-compose.issuer.yaml ps issuer-did-server

# Check NGINX logs
task issuer:logs-service SERVICE=issuer-did-server

# Verify port mapping
# Should be: 9876:80
```

### Logs and Debugging

#### View All Logs

```bash
task issuer:logs
```

#### View Specific Service Logs

```bash
# Issuer service
task issuer:logs-service SERVICE=issuer-service

# PostgreSQL
task issuer:logs-service SERVICE=issuer-postgres

# Vault
task issuer:logs-service SERVICE=issuer-vault

# DID server
task issuer:logs-service SERVICE=issuer-did-server
```

#### Debug Mode

The Issuer service exposes a Java debug port (1044) for remote debugging.

---

## API Reference

### Base URLs

- **Main API:** `http://localhost:10010/api`
- **Admin API:** `http://localhost:10013/api/admin`
- **DID Document:** `http://localhost:9876/.well-known/did.json`

### Authentication

All admin API requests require the `X-Api-Key` header:

```
X-Api-Key: c3VwZXItdXNlcg==.c3VwZXItc2VjcmV0LWtleQo=
```

### Endpoints

#### Health Check

```http
GET /api/check/health
```

#### Create Participant Holder

```http
POST /api/admin/v1alpha/participants/{issuer-context-id}/holders
Content-Type: application/json
X-Api-Key: {api-key}

{
  "did": "did:web:host.docker.internal%3A7083:consumer",
  "holderId": "did:web:host.docker.internal%3A7083:consumer",
  "name": "Consumer Corp"
}
```

#### Create Attestation Definition

```http
POST /api/admin/v1alpha/participants/{issuer-context-id}/attestations
Content-Type: application/json
X-Api-Key: {api-key}

{
  "id": "membership-attestation-db",
  "attestationType": "database",
  "configuration": {
    "tableName": "membership_attestations",
    "dataSourceName": "membership",
    "idColumn": "holder_id"
  }
}
```

#### Create Credential Definition

```http
POST /api/admin/v1alpha/participants/{issuer-context-id}/credentialdefinitions
Content-Type: application/json
X-Api-Key: {api-key}

{
  "id": "membership-credential-def",
  "credentialType": "MembershipCredential",
  "attestations": ["membership-attestation-db"],
  "jsonSchema": "{}",
  "jsonSchemaUrl": "https://example.com/schema/membership.json",
  "mappings": [
    {
      "input": "membership_type",
      "output": "credentialSubject.membershipType",
      "required": true
    },
    {
      "input": "membership_start_date",
      "output": "credentialSubject.membershipStartDate",
      "required": true
    },
    {
      "input": "holder_id",
      "output": "credentialSubject.id",
      "required": true
    }
  ],
  "rules": [],
  "format": "VC1_0_JWT"
}
```

---

## Production Considerations

### Security

**⚠️ CRITICAL: Change all default credentials before production deployment!**

1. **Admin API Key** (`ISSUER_SUPERUSER_KEY`):
   ```bash
   # Generate new credentials
   NEW_USER=$(echo -n "your-admin-username" | base64)
   NEW_PASS=$(echo -n "your-secure-password" | base64)
   ISSUER_SUPERUSER_KEY="${NEW_USER}.${NEW_PASS}"
   ```

2. **Database Passwords**:
   - Update `ISSUER_DB_PASSWORD`
   - Update `POSTGRES_PASSWORD` in Docker Compose
   - Update SQL init script user creation

3. **Vault Token**:
   - Never use `root` token in production
   - Configure Vault with proper authentication backend
   - Use Vault's token lifecycle management

4. **Additional Security Measures**:
   - Enable HTTPS (`EDC_IAM_DID_WEB_USE_HTTPS=true`)
   - Remove debug port (1044) from production
   - Implement network segmentation
   - Use TLS for database connections
   - Enable audit logging
   - Implement rate limiting on API endpoints

### Networking

**Development (Docker Compose):**
- Use `host.docker.internal` for local deployments
- DID: `did:web:host.docker.internal%3A9876`
- Requires: `EDC_IAM_DID_WEB_USE_HTTPS=false`

**Production (Internet):**
- Use public domain names
- DID: `did:web:issuer.yourdomain.com`
- Requires: `EDC_IAM_DID_WEB_USE_HTTPS=true`
- Configure proper DNS and SSL certificates
- Use reverse proxy (Traefik, Nginx) for SSL termination

### Monitoring

Recommended monitoring:
- Health check endpoints (Prometheus, Datadog, etc.)
- Credential issuance metrics
- Failed attestation queries
- API response times
- Authentication failures

### Backups

```bash
# Backup database
task issuer:backup

# Restore database
task issuer:restore BACKUP=./backups/issuer-backup-YYYYMMDD-HHMMSS.sql
```

---

## Useful Commands

```bash
# Start services
task issuer:up

# Stop services
task issuer:down

# Restart services
task issuer:restart

# View logs
task issuer:logs

# View status
task issuer:status

# Seed service
task issuer:seed

# Verify deployment
task issuer:verify

# Check health
task issuer:health

# Open shell in container
task issuer:shell

# Connect to database
task issuer:db

# Backup database
task issuer:backup

# Clean (remove all data)
task issuer:clean
```
