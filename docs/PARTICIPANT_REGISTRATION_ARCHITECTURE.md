# Participant Registration Architecture & Future Refactoring Plan

## Table of Contents

- [Executive Summary](#executive-summary)
- [Current Architecture](#current-architecture)
- [Problem Statement](#problem-statement)
- [Workaround Solution](#workaround-solution)
- [Proposed Refactoring](#proposed-refactoring)
- [Implementation Roadmap](#implementation-roadmap)
- [Migration Strategy](#migration-strategy)

---

## Executive Summary

The EDC Minimum Viable Dataspace (MVD) deployment toolkit currently implements a **static participant whitelist model** where authorized participants are registered during the Issuer Service's initial deployment. This architecture creates a scalability bottleneck for growing dataspaces.

**Current State:**

- Participants are hardcoded during issuer deployment via SQL seed data
- Adding new participants requires database manipulation or issuer redeployment
- Configuration is embedded in deployment scripts rather than externalized

**Immediate Workaround:**

- A new task `issuer:add-participant` enables dynamic participant registration
- Uses direct database insertion to add participants post-deployment
- Maintains the security model while enabling runtime extensibility

**Future Vision:**

- Environment-variable driven multi-participant configuration (`PARTICIPANT_{N}_*` pattern)
- Dynamic participant registration via API
- Backward-compatible migration path for existing deployments

---

## Current Architecture

### Participant Registration Flow

The current system uses a **3-phase registration process**:

#### Phase 1: Issuer Deployment & Seeding

1. **Generate SQL seed file** (`generate_init_sql.py`)

   - Creates `init-issuer-db.sql` from template
   - Embeds single `PROVIDER_DID` from `.env`

2. **Start PostgreSQL container with SQL seed**

   - Creates attestation tables
   - Inserts **one** participant's attestations

3. **Run issuer seeding** (`seed_issuer.py`)
   - Register issuer as participant in its Identity Hub
   - Create participant holders (`create_participants.py`)
     - Calls `POST /api/admin/.../holders`
     - Hardcoded list: `[{"did": provider_did, ...}]`
   - Create attestation definitions
   - Create credential definitions

---

#### Phase 2: Provider Deployment

1. Deploy provider's Identity Hub, Control Plane, etc.
2. Register provider in its own Identity Hub
3. Store STS client secret in Vault

---

#### Phase 3: Credential Request

Provider → Provider Identity Hub → Issuer Service

1. Request credentials (`MembershipCredential`, etc.)
2. Issuer validates holder is registered
3. Issuer queries attestation database (**whitelist check**)
4. Issues credentials if authorized

### Key Components

#### 1. SQL Seed Template

**File:** `deployment/issuer/init-issuer-db.sql.template`

Contains database schema and **single participant INSERT**:

```sql
INSERT INTO membership_attestations (membership_type, holder_id, membership_start_date)
VALUES (2, '${PROVIDER_DID}', '2023-01-01T00:00:00Z');

INSERT INTO data_processor_attestations (holder_id, contract_version, processing_level, attestation_date)
VALUES ('${PROVIDER_DID}', '1.0.0', 'processing', '2023-01-01T00:00:00Z');
```

**Limitation:** Only one `${PROVIDER_DID}` variable, no loop support.

#### 2. SQL Generation Script

**File:** `scripts/issuer/generate_init_sql.py`

Generates `init-issuer-db.sql` by:

1. Loading config from environment variables
2. Generating single provider DID: `did:web:{ISSUER_PUBLIC_HOST}%3A{PROVIDER_IH_DID_PORT}:provider`
3. Substituting `${PROVIDER_DID}` in template

**Limitation:** Single provider assumption, no multi-participant support.

#### 3. Participant Creation Script

**File:** `scripts/issuer/create_participants.py`

Registers holders via Identity Hub API:

```python
def create_all_participants(cfg: Config) -> bool:
    participants = [
        {"did": cfg.provider_did, "name": "Provider Corp"},
    ]
    # Only ONE participant hardcoded
```

**Limitation:** Hardcoded list, must modify code to add participants.

#### 4. Configuration Module

**File:** `scripts/issuer/config.py`

Generates participant DIDs from environment:

```python
self.provider_did = self._generate_participant_did(
    self.issuer_public_host,  # From PROVIDER_PUBLIC_HOST
    self.provider_ih_did_port, # From PROVIDER_IH_DID_PORT (default: 7003)
    "provider"                 # HARDCODED name
)
```

**Limitation:** Single provider, hardcoded participant name.

### Attestation Database Schema

```sql
-- Membership whitelist
CREATE TABLE membership_attestations (
    id VARCHAR PRIMARY KEY,
    membership_type INTEGER,      -- 2=Provider, 3=Consumer
    holder_id VARCHAR UNIQUE,     -- Participant DID
    membership_start_date TIMESTAMP
);

-- Processing level whitelist
CREATE TABLE data_processor_attestations (
    id VARCHAR PRIMARY KEY,
    holder_id VARCHAR UNIQUE,     -- Participant DID
    contract_version VARCHAR,
    processing_level VARCHAR,     -- 'processing' or 'sensitive'
    attestation_date TIMESTAMP
);
```

**Security Model:** Issuer acts as Certificate Authority. Only participants with database attestations can request credentials.

---

## Problem Statement

### Scenario: Multi-Instance Deployment

You have:

- **Instance A (dsctic03):** Issuer + Provider
- **Instance B (dsctic02):** Provider only

#### What Happens:

1. **dsctic03 deploys issuer** with `PROVIDER_PUBLIC_HOST=host.docker.internal`

   - Registers: `did:web:dsctic03.cticpoc.com%3A9083:provider` (issuer's perspective)

2. **dsctic02 deploys provider** with `PROVIDER_PUBLIC_HOST=dsctic02.cticpoc.com`

   - Actual DID: `did:web:dsctic02.cticpoc.com%3A9083:provider`

3. **dsctic02 requests credentials** from dsctic03 issuer
   - Issuer checks whitelist for `did:web:dsctic02...`
   - **Not found** → `401 Unauthorized`

#### Root Cause:

The issuer's SQL seed file generates the provider DID using **the issuer's hostname** (`host.docker.internal` → resolves to `dsctic03`), not the actual provider's hostname.

### Architectural Issues

| Issue                             | Impact                                      | Workaround Complexity          |
| --------------------------------- | ------------------------------------------- | ------------------------------ |
| **Single participant assumption** | Can't register multiple providers/consumers | High - requires code changes   |
| **Hardcoded configuration**       | No externalized participant lists           | High - scattered across files  |
| **Static deployment model**       | Can't add participants post-deployment      | Medium - database manipulation |
| **DID generation coupling**       | Provider DID tied to issuer's hostname      | High - requires re-seeding     |

---

## Workaround Solution

### Overview

We've implemented a **runtime participant registration mechanism** that bypasses the static deployment limitation while maintaining security:

| Component   | Details                                                                                             |
| ----------- | --------------------------------------------------------------------------------------------------- |
| **Task**    | `issuer:add-participant`                                                                            |
| **Input**   | Participant DID, membership type, etc.                                                              |
| **Actions** | 1. Insert holder record<br>2. Insert membership attestation<br>3. Insert data processor attestation |
| **Output**  | Participant authorized for credentials                                                              |

### Usage

#### Via Taskfile

```bash
# Add a new participant to the running issuer
task issuer:add-participant \
  PARTICIPANT_DID="did:web:dsctic02.cticpoc.com%3A9083:provider" \
  PARTICIPANT_NAME="Provider Corp (dsctic02)" \
  MEMBERSHIP_TYPE=2 \
  PROCESSING_LEVEL=processing
```

#### Via Python Script

```bash
python3 scripts/issuer/add_participant.py \
  --did "did:web:dsctic02.cticpoc.com%3A9083:provider" \
  --name "Provider Corp (dsctic02)" \
  --membership-type 2 \
  --processing-level processing
```

### Implementation

**File:** `scripts/issuer/add_participant.py`

The script performs direct database insertions:

1. **Holders table:** Registers participant as credential holder
2. **Membership attestations:** Authorizes membership credentials
3. **Data processor attestations:** Authorizes processing credentials

**Security:** Requires superuser access to issuer database (same privilege level as deployment).

### Advantages

✅ **No issuer restart required** - Add participants to running system
✅ **Maintains security model** - Admin-controlled whitelist
✅ **Idempotent** - Safe to run multiple times (ON CONFLICT DO NOTHING)
✅ **Audit trail** - All operations logged
✅ **Production-ready** - Follows same patterns as deployment

### Limitations

⚠️ **Database dependency** - Requires direct PostgreSQL access
⚠️ **No API** - Not exposed as REST endpoint
⚠️ **Manual DID construction** - Must provide exact DID format
⚠️ **No validation** - Doesn't verify DID document accessibility

---

## Proposed Refactoring

### Design Goals

1. **Environment-driven configuration** - Follow existing `PROVIDER_ASSET_{N}_*` pattern
2. **Backward compatibility** - Existing single-provider configs work unchanged
3. **Minimal code changes** - Leverage existing infrastructure
4. **Runtime extensibility** - Support post-deployment participant addition
5. **Security preservation** - Maintain admin-controlled authorization

### New Configuration Pattern

```bash
# .env file - Multi-participant support

# Participant 1 (backward compatible)
PARTICIPANT_1_NAME=provider
PARTICIPANT_1_PUBLIC_HOST=dsctic02.cticpoc.com
PARTICIPANT_1_DID_PORT=9083
PARTICIPANT_1_MEMBERSHIP_TYPE=2              # 2=Provider, 3=Consumer
PARTICIPANT_1_PROCESSING_LEVEL=processing    # processing|sensitive
PARTICIPANT_1_CONTRACT_VERSION=1.0.0
PARTICIPANT_1_DISPLAY_NAME=Provider Corp (dsctic02)

# Participant 2
PARTICIPANT_2_NAME=consumer-corp
PARTICIPANT_2_PUBLIC_HOST=dsctic04.cticpoc.com
PARTICIPANT_2_DID_PORT=9083
PARTICIPANT_2_MEMBERSHIP_TYPE=3
PARTICIPANT_2_PROCESSING_LEVEL=sensitive
PARTICIPANT_2_CONTRACT_VERSION=1.0.0
PARTICIPANT_2_DISPLAY_NAME=Consumer Corporation

# Participant 3
PARTICIPANT_3_NAME=provider-2
PARTICIPANT_3_PUBLIC_HOST=dsctic05.cticpoc.com
PARTICIPANT_3_DID_PORT=9083
PARTICIPANT_3_MEMBERSHIP_TYPE=2
PARTICIPANT_3_PROCESSING_LEVEL=processing
PARTICIPANT_3_CONTRACT_VERSION=1.0.0
```

### Backward Compatibility

Existing configurations automatically map:

```bash
# Old style (still works)
PROVIDER_PUBLIC_HOST=host.docker.internal
PROVIDER_IH_DID_PORT=7003

# Internally treated as:
PARTICIPANT_1_NAME=provider
PARTICIPANT_1_PUBLIC_HOST=${PROVIDER_PUBLIC_HOST}
PARTICIPANT_1_DID_PORT=${PROVIDER_IH_DID_PORT}
```

### Refactoring Components

#### Component 1: Multi-Participant Config Loader

**File:** `scripts/issuer/config.py`

Add method similar to asset loading:

```python
def _load_participants_from_env(self) -> list[dict]:
    """
    Scan environment for PARTICIPANT_{N}_* variables.
    Returns list of participant configurations.
    """
    participants = []
    participant_numbers = set()

    # Scan for PARTICIPANT_{N}_NAME
    for env_var in os.environ.keys():
        if env_var.startswith("PARTICIPANT_") and env_var.endswith("_NAME"):
            num = extract_number(env_var)
            participant_numbers.add(num)

    # Load each participant
    for num in sorted(participant_numbers):
        participant = load_participant_config(num)
        participants.append(participant)

    # Backward compatibility fallback
    if not participants:
        participants.append(load_legacy_provider_config())

    return participants
```

#### Component 2: Dynamic SQL Generation

**File:** `scripts/issuer/generate_init_sql.py`

Generate INSERT blocks for all participants:

```python
def generate_init_sql(config) -> str:
    participant_inserts = []

    for p in config.participants:
        insert = f"""
        -- Participant: {p['display_name']}
        INSERT INTO membership_attestations (...)
        VALUES ({p['membership_type']}, '{p['did']}', ...);

        INSERT INTO data_processor_attestations (...)
        VALUES ('{p['did']}', '{p['contract_version']}', ...);
        """
        participant_inserts.append(insert)

    return template.replace("-- MARKER", "\n".join(participant_inserts))
```

#### Component 3: SQL Template Update

**File:** `deployment/issuer/init-issuer-db.sql.template`

Replace hardcoded INSERT with marker:

```sql
-- ============================================================
-- SEED DATA: PARTICIPANT ATTESTATIONS
-- ============================================================

-- BEGIN_PARTICIPANT_INSERTS
-- Generated by generate_init_sql.py
-- END_PARTICIPANT_INSERTS
```

#### Component 4: Multi-Participant Holder Creation

**File:** `scripts/issuer/create_participants.py`

Use config-driven list:

```python
def create_all_participants(cfg: Config) -> bool:
    participants = [
        {"did": p["did"], "name": p["display_name"]}
        for p in cfg.participants
    ]
    # Process all participants dynamically
```

### Implementation Effort

| Component       | Files Changed | Lines Added | Lines Removed | Effort  |
| --------------- | ------------- | ----------- | ------------- | ------- |
| Config Loader   | 1             | ~80         | ~0            | 3 hours |
| SQL Generation  | 1             | ~30         | ~5            | 2 hours |
| SQL Template    | 1             | ~10         | ~75           | 1 hour  |
| Holder Creation | 1             | ~5          | ~3            | 1 hour  |
| Testing         | -             | -           | -             | 4 hours |
| Documentation   | -             | -           | -             | 2 hours |

**Total Effort:** ~13 hours (2 developer-days)

---

## Implementation Roadmap

### Phase 0: Current State (Completed)

✅ Identified architectural limitation
✅ Implemented workaround script (`add_participant.py`)
✅ Created Taskfile task (`issuer:add-participant`)
✅ Documented architecture and refactoring plan

### Phase 1: Foundation (Week 1)

- [ ] Implement multi-participant config loader
- [ ] Add unit tests for participant loading
- [ ] Validate backward compatibility with existing configs
- [ ] Update `.env.example` with multi-participant examples

### Phase 2: SQL Generation (Week 1)

- [ ] Refactor `generate_init_sql.py` for multi-participant
- [ ] Update SQL template with markers
- [ ] Test SQL generation with 1, 2, 5, 10 participants
- [ ] Validate ON CONFLICT behavior

### Phase 3: Deployment Integration (Week 2)

- [ ] Update `create_participants.py` to use dynamic list
- [ ] Test end-to-end deployment with multiple participants
- [ ] Verify credential issuance for all participants
- [ ] Performance test with 50+ participants

### Phase 4: Documentation & Migration (Week 2)

- [ ] Create migration guide for existing deployments
- [ ] Update main README with new patterns
- [ ] Document DID generation edge cases
- [ ] Create troubleshooting guide

### Phase 5: Production Rollout (Week 3)

- [ ] Deploy to staging environment
- [ ] Migrate existing single-provider deployments
- [ ] Monitor for issues
- [ ] Gather operator feedback

---

## Migration Strategy

### For New Deployments

Use new multi-participant pattern from day 1:

```bash
# Configure in .env
PARTICIPANT_1_NAME=provider1
PARTICIPANT_1_PUBLIC_HOST=provider1.example.com
PARTICIPANT_1_DID_PORT=9083

PARTICIPANT_2_NAME=consumer1
PARTICIPANT_2_PUBLIC_HOST=consumer1.example.com
PARTICIPANT_2_DID_PORT=9083

# Deploy
task issuer:deploy
```

### For Existing Deployments

#### Option A: Continue with Workaround (No Refactoring)

```bash
# Add new participants as needed
task issuer:add-participant \
  PARTICIPANT_DID="did:web:newhost.com%3A9083:provider" \
  PARTICIPANT_NAME="New Provider"
```

**Pros:** No code changes, immediate solution
**Cons:** Manual process, no deployment-time automation

#### Option B: Migrate to Refactored Version

```bash
# 1. Backup current database
docker exec mvd-issuer-postgres pg_dump -U issuer issuer > backup.sql

# 2. Update .env with PARTICIPANT_{N}_* variables
# (Map existing participants to new format)

# 3. Redeploy issuer with new code
task issuer:down
git pull  # Get refactored code
task issuer:deploy

# 4. Verify all participants registered
task issuer:verify-participants
```

**Pros:** Clean architecture, automated deployment
**Cons:** Requires issuer restart, code migration

### Migration Checklist

- [ ] Document all existing participants (DIDs, types, levels)
- [ ] Create PARTICIPANT*{N}*\* env vars for each
- [ ] Test in staging environment first
- [ ] Backup production database before migration
- [ ] Plan maintenance window for issuer restart
- [ ] Verify credential issuance post-migration
- [ ] Update runbooks and documentation

---

## Appendix

### DID Format Reference

**Pattern:** `did:web:{URL_ENCODED_HOST_PORT}:{participant_name}`

**Examples:**

```
# Standard port (9083)
did:web:dsctic02.cticpoc.com%3A9083:provider

# Standard HTTPS port (443) - port omitted
did:web:provider.example.com:provider

# Non-standard port (7003)
did:web:localhost%3A7003:provider

# Docker internal
did:web:host.docker.internal%3A9083:provider
```

**URL Encoding:**

- `:` becomes `%3A`
- Use Python: `urllib.parse.quote(f"{host}:{port}", safe="")`

### Attestation Type Reference

**Membership Types:**

- `2` - Provider (can offer data)
- `3` - Consumer (can consume data)

**Processing Levels:**

- `processing` - Standard data processing
- `sensitive` - High-security processing (additional compliance)

**Contract Versions:**

- `1.0.0` - Current version
- Use semantic versioning for tracking

### Database Table Relationships

```
participant_context (Identity Hub)
    ↓
holders (Issuer Service)
    ↓
membership_attestations ← Whitelist for MembershipCredential
data_processor_attestations ← Whitelist for DataProcessorCredential
```

### Useful Commands

```bash
# List all participants
docker exec mvd-issuer-postgres psql -U issuer -d issuer \
  -c "SELECT holder_id, holder_name FROM holders ORDER BY holder_id;"

# Check attestations for a participant
docker exec mvd-issuer-postgres psql -U issuer -d issuer \
  -c "SELECT * FROM membership_attestations WHERE holder_id = 'did:web:...';"

# Count total participants
docker exec mvd-issuer-postgres psql -U issuer -d issuer \
  -c "SELECT COUNT(*) FROM holders;"

# Backup attestation tables
docker exec mvd-issuer-postgres pg_dump -U issuer issuer \
  -t membership_attestations -t data_processor_attestations > attestations_backup.sql
```
