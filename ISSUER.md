# **Issuer Service**

## **1. Overview**

The **Issuer Service** issues **Verifiable Credentials (VCs)** to dataspace participants, enabling dynamic credential management and solving DID mismatch issues from pre-signed credentials.

It supports:

* **Local mode:** self-hosted issuer stack for development
* **External mode:** remote issuer endpoint for production

---

## **2. Architecture**

| Component              | Port        | Purpose                                       |
| ---------------------- | ----------- | --------------------------------------------- |
| **issuer-postgres**    | 5433        | Stores membership attestations                |
| **issuer-vault**       | 8201        | Securely stores private signing key           |
| **issuer-did (NGINX)** | 9876        | Hosts `/.well-known/did.json`                 |
| **issuer-service**     | 10010–10015 | Main Issuer APIs (STS, Issuance, Admin, etc.) |

All components run in **`compose.issuer.yaml`** (isolated from participant stack but sharing the same Docker network).

---

## **3. Configuration**

### **Local Mode (Development)**

```bash
ISSUER_MODE=local
ISSUER_DID=did:web:localhost%3A9876
ISSUER_PUBLIC_HOST=localhost
ISSUER_PUBLIC_PORT=9876
```

**Pros:** Full control, offline support, easy debugging
**Cons:** More containers, longer startup

### **External Mode (Production)**

```bash
ISSUER_MODE=external
ISSUER_DID=did:web:issuer.yourdomain.com
ISSUER_EXTERNAL_STS_URL=https://issuer.yourdomain.com/api/sts
ISSUER_EXTERNAL_ISSUANCE_URL=https://issuer.yourdomain.com/api/issuance
```

**Pros:** Centralized, scalable, managed infra
**Cons:** Requires network access, limited control

---

## **4. Quick Start**

### Prerequisites

Ensure you have already:
- Built participant services: `task build`
- Started participant services: `task up`
- Seeded participant data: `task seed`

### Issuer Setup

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env → set ISSUER_MODE=local

# 2. Generate issuer keys and DID document
task generate-issuer-keys

# 3. Build issuer service Docker image
task build-issuer

# 4. Configure issuer (Vault setup, config generation)
task configure-issuer

# 5. Start issuer services (postgres, vault, nginx, issuer-service)
task issuer-up

# 6. Seed issuer attestation database
task seed-issuer

# 7. Request credential from issuer (requires participant IdentityHub running)
task request-credential TYPE=MembershipCredential

# 8. Verify issuer setup
task verify-issuer
```

> [!IMPORTANT]
> The `request-credential` command requires the participant's IdentityHub to be running. If you get a connection error, ensure participant services are started with `task up`.

---

## **5. Key Scripts and Tasks**

| Task                                  | Description                                       |
| ------------------------------------- | ------------------------------------------------- |
| `task generate-issuer-keys`           | Generates Ed25519 key pair, DID doc, NGINX config |
| `task build-issuer`                   | Builds Docker image for issuer service            |
| `task configure-issuer`               | Generates config, initializes Vault               |
| `task issuer-up / issuer-down`        | Start/stop full issuer stack                      |
| `task seed-issuer`                    | Inserts participant into attestation DB           |
| `task request-credential TYPE=<type>` | Requests VC from issuer                           |
| `task verify-issuer`                  | Health + DID resolution check                     |
| `task up-all / down-all / seed-all`   | Combined participant + issuer ops                 |

---

## **6. Credential Issuance Flow**

```mermaid
sequenceDiagram
    participant Participant
    participant IdentityHub
    participant IssuerService

    Participant->>IdentityHub: Request credential
    IdentityHub->>IssuerService: Forward credential request
    IssuerService->>IdentityHub: Validate + issue signed VC
    IdentityHub->>Participant: Store + return credential
```

---

## **7. DID & Key Generation**

Run:

```bash
task generate-issuer-keys
```

Creates:

```
assets/issuer/private.pem
assets/issuer/public.pem
assets/issuer/did.json
config/issuer-nginx.conf
```

Keys are `.gitignored`, and private keys are stored in Vault at runtime.
DID Web URLs comply with:

* `did:web:domain → https://domain/.well-known/did.json`
* `did:web:domain%3Aport → https://domain:port/.well-known/did.json`

---

## **8. Environment & Files**

| File                                 | Purpose              |
| ------------------------------------ | -------------------- |
| `.env.example`                       | Environment template |
| `compose.issuer.yaml`                | Issuer Docker stack  |
| `config/issuer-service.env.template` | Config template      |
| `scripts/generate-issuer-keys.sh`    | Key/DID generation   |
| `scripts/configure-issuer.sh`        | Vault + config setup |
| `scripts/seed-issuer.sh`             | Attestation seeding  |
| `scripts/request-credential.sh`      | Credential issuance  |
| `scripts/issuer-init-db.sql`         | DB schema setup      |

**Generated (.gitignored):**
`.env`, `config/issuer-service.env`, `assets/issuer/private.pem`, `assets/issuer/did.json`, etc.

---

## **9. Production Configuration**

```bash
ISSUER_DID=did:web:issuer.yourdomain.com
ISSUER_PUBLIC_HOST=issuer.yourdomain.com
ISSUER_PUBLIC_PORT=443
```

**Checklist:**

* [ ] Fresh keys generated
* [ ] Strong Vault and DB credentials
* [ ] HTTPS enabled
* [ ] Restricted DB/Vault access
* [ ] Backup keys securely
* [ ] Monitor logs and health checks

---

## **10. Troubleshooting**

| Issue                       | Cause                                | Fix                                             |
| --------------------------- | ------------------------------------ | ----------------------------------------------- |
| ❌ Keys not found            | Missing key files                    | `task generate-issuer-keys`                     |
| ❌ Vault not healthy         | Vault not ready                      | `task issuer-logs-service SERVICE=issuer-vault` |
| ❌ DID not resolving         | NGINX down                           | `task issuer-status`, check `issuer-did`        |
| ❌ 401 Unauthorized          | Missing attestation or wrong API key | `task seed-issuer`, verify `.env`               |
| ❌ 404 Not Found             | Participant not seeded               | `task seed && task seed-issuer`                 |
| ❌ Connection refused (curl) | Participant services not running     | `task up` to start participant services         |

---

## **11. Migration Example**

**Development:**

```bash
ISSUER_DID=did:web:localhost%3A9876
ISSUER_PUBLIC_HOST=localhost
ISSUER_PUBLIC_PORT=9876
```

**Production:**

```bash
ISSUER_DID=did:web:issuer.production.com
ISSUER_PUBLIC_HOST=issuer.production.com
ISSUER_PUBLIC_PORT=443
```
