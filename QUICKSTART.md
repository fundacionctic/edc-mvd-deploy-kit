# Quick Start Guide

Get your MVD instance up and running in 5 minutes!

## Prerequisites Check

```bash
# Verify Docker is installed
docker --version

# Verify Docker Compose is installed
docker compose version

# Verify Task is installed
task --version

# Verify jq is installed
jq --version
```

If any tool is missing, see the [Installation](#installation) section below.

## 5-Minute Setup

### Step 1: Build Images (2-3 minutes)

```bash
task build
```

Expected output:
- Setting up MVD source repository...
- ✓ MVD source setup complete!
- Docker images built successfully!

**Note**: The build task automatically clones/updates the MVD repository from GitHub.

### Step 2: Start Services (30 seconds)

```bash
task up
```

Expected output: Services started!

### Step 3: Seed Dataspace (30 seconds)

```bash
task seed
```

Expected output: Dataspace seeded successfully!

### Step 4: Verify (10 seconds)

```bash
# Check services are healthy
task health

# View your DID document
curl http://localhost:7083/.well-known/did.json
```

## You're Ready! 🎉

Your MVD instance is now running. Here's what you can do:

### View Your Catalog

```bash
curl http://localhost:8084/api/catalog -H 'x-api-key: password' | jq
```

### List Your Assets

```bash
curl http://localhost:8081/api/management/v3/assets -H 'x-api-key: password' | jq
```

### View Service Status

```bash
task status
```

### View Logs

```bash
task logs
```

## Common Commands

| What You Want | Command |
|---------------|---------|
| Setup/update source | `task setup` |
| Check source status | `task info` |
| Start everything | `task up` |
| Stop everything | `task down` |
| Restart everything | `task restart` |
| See what's running | `task status` |
| View logs | `task logs` |
| Check health | `task health` |
| Rebuild from scratch | `task clean && task build && task up && task seed` |

## Next Steps

- Read the [README.md](README.md) for detailed documentation
- Explore the [Management API](http://localhost:8081/api/management) (API Key: `password`)
- Create assets and policies
- Connect to other dataspace participants

## Installation

### Install Task

**macOS:**
```bash
brew install go-task
```

**Linux:**
```bash
sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b ~/.local/bin
```

**Windows:**
```powershell
choco install go-task
```

### Install jq

**macOS:**
```bash
brew install jq
```

**Linux:**
```bash
sudo apt-get install jq  # Debian/Ubuntu
sudo yum install jq      # RHEL/CentOS
```

**Windows:**
```powershell
choco install jq
```

## Troubleshooting

### Repository clone fails

```bash
# Check network connectivity
ping github.com

# Check Git is installed
git --version

# Try manual setup
task setup
```

### Services won't start

```bash
# Check Docker is running
docker ps

# View logs for errors
task logs

# Try a clean restart
task down
task up
```

### Seed fails

```bash
# Wait 30 seconds for services to be fully ready
sleep 30

# Check services are healthy
task health

# Try seeding again
task seed
```

### Port conflicts

If you get port binding errors, another service is using the ports. Either:
1. Stop the conflicting service
2. Edit `compose.yaml` to use different ports

## Getting Help

- Check [README.md](README.md) for detailed documentation
- View logs: `task logs`
- Check service health: `task health`
- View container status: `docker compose ps`

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│                   MVD QUICK REFERENCE                        │
├─────────────────────────────────────────────────────────────┤
│ LIFECYCLE                                                    │
│   task up          Start all services                        │
│   task down        Stop all services                         │
│   task restart     Restart all services                      │
│   task rebuild     Rebuild and restart                       │
│                                                              │
│ MONITORING                                                   │
│   task status      Show service status                       │
│   task logs        View all logs                            │
│   task health      Check service health                      │
│                                                              │
│ MANAGEMENT                                                   │
│   task seed        Initialize dataspace                      │
│   task backup      Backup database                          │
│   task clean       Remove all data                          │
│                                                              │
│ ENDPOINTS (all use API Key: password)                       │
│   Management API:  http://localhost:8081/api/management     │
│   DSP Protocol:    http://localhost:8082/api/dsp            │
│   Catalog API:     http://localhost:8084/api/catalog        │
│   DID Document:    http://localhost:7083/.well-known/did.json│
│                                                              │
│ DATABASES                                                    │
│   task db          Connect to PostgreSQL                     │
│   task vault       Check Vault status                        │
└─────────────────────────────────────────────────────────────┘
```
