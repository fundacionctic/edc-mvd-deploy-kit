# Deployment Checklist

Use this checklist to verify your MVD deployment is correctly configured and operational.

## Pre-Deployment Checks

- [ ] Docker is installed and running (`docker --version`)
- [ ] Docker Compose is installed (`docker compose version`)
- [ ] Task is installed (`task --version`)
- [ ] Git is installed (`git --version`)
- [ ] jq is installed (`jq --version`)
- [ ] Network connectivity to GitHub (`ping github.com`)
- [ ] No port conflicts on: 5432, 7080-7086, 8080-8084, 8200, 11001-11003

## Source Setup Phase

- [ ] Run `task setup` (or it will run automatically on first build)
- [ ] MVD repository cloned successfully
- [ ] Correct branch checked out (`task info` shows `release/0.14.0`)
- [ ] Source directory exists at `./edc-mvds`

## Build Phase

- [ ] Run `task build` (automatically sets up source if needed)
- [ ] Source repository setup completed successfully
- [ ] Verify Docker images are created:
  - [ ] `controlplane:latest`
  - [ ] `dataplane:latest`
  - [ ] `identity-hub:latest`
- [ ] No build errors in output

## Deployment Phase

- [ ] Run `task up`
- [ ] All containers are running (`docker compose ps`)
- [ ] PostgreSQL is healthy (check `task status`)
- [ ] Vault is healthy (check `task status`)
- [ ] IdentityHub is healthy (check `task status`)
- [ ] Controlplane is healthy (check `task status`)
- [ ] Dataplane is healthy (check `task status`)

## Seeding Phase

- [ ] Wait 30 seconds after `task up`
- [ ] Run `task seed`
- [ ] Participant context created successfully
- [ ] Client secret added to vault
- [ ] Test asset created
- [ ] Access policy created
- [ ] Contract definition created

## Verification Tests

### 1. Health Checks

- [ ] `task health` shows all services healthy
- [ ] `curl http://localhost:7080/api/check/health` returns success
- [ ] `curl http://localhost:8080/api/check/health` returns success
- [ ] `curl http://localhost:11003/api/check/health` returns success

### 2. DID Resolution

- [ ] `curl http://localhost:7083/.well-known/did.json` returns DID document
- [ ] DID document contains public key
- [ ] DID matches `did:web:identityhub%3A7083`

### 3. Management API

- [ ] List assets: `curl -H "x-api-key: password" http://localhost:8081/api/management/v3/assets`
- [ ] Returns JSON with test asset
- [ ] No authentication errors

### 4. Catalog API

- [ ] Query catalog: `curl -H "x-api-key: password" http://localhost:8084/api/catalog`
- [ ] Returns catalog data
- [ ] Contains test asset

### 5. Database Connectivity

- [ ] `task db` connects successfully
- [ ] `\dt` shows EDC tables
- [ ] `SELECT * FROM edc_asset;` returns test asset

### 6. Vault Connectivity

- [ ] `task vault` shows Vault status
- [ ] Vault is unsealed and active

## Post-Deployment Checks

### Configuration

- [ ] Review `config/identityhub.env` for correct settings
- [ ] Review `config/controlplane.env` for correct settings
- [ ] Review `config/dataplane.env` for correct settings
- [ ] Participant DID is correct in all configs

### Security

- [ ] Change default API key (`password`) for production
- [ ] Change Vault token for production
- [ ] Review exposed ports and limit as needed
- [ ] Ensure credentials in `assets/credentials/` are appropriate

### Logging

- [ ] `task logs` shows logs from all services
- [ ] No error messages in logs
- [ ] Services are communicating correctly

## Troubleshooting

If any check fails, refer to the troubleshooting section in [README.md](README.md#troubleshooting).

### Common Issues

**Services not starting**
```bash
task down
task up
task logs
```

**Seed fails**
```bash
# Wait longer for services to initialize
sleep 30
task seed
```

**Port conflicts**
```bash
# Check what's using the ports
sudo lsof -i :8080  # or other ports
# Stop conflicting service or change ports in compose.yaml
```

**Database connection issues**
```bash
task down
rm -rf data/postgres/*
task up
sleep 30
task seed
```

## Production Readiness Checklist

**⚠️ Additional steps required for production deployment:**

- [ ] Configure HTTPS/TLS for all endpoints
- [ ] Use managed PostgreSQL service
- [ ] Configure Vault in production mode with persistent storage
- [ ] Implement proper secret rotation
- [ ] Set up monitoring and alerting
- [ ] Configure automated backups
- [ ] Implement disaster recovery plan
- [ ] Use strong, unique API keys
- [ ] Ensure DIDs are publicly resolvable
- [ ] Configure proper network security (firewalls, VPNs)
- [ ] Set resource limits (CPU, memory)
- [ ] Implement log aggregation
- [ ] Set up certificate management
- [ ] Configure rate limiting
- [ ] Implement audit logging

## Sign-Off

**Deployment Date**: _________________

**Deployed By**: _________________

**Environment**: [ ] Development [ ] Staging [ ] Production

**Notes**:
_______________________________________________________
_______________________________________________________
_______________________________________________________

**Status**: [ ] All checks passed [ ] Issues noted above

