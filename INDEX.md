# Documentation Index

Welcome to the MVD Single-Instance Docker Compose Deployment! This index will help you find the right documentation for your needs.

## 🚀 Getting Started (Choose Your Path)

### I want to get running ASAP (5 minutes)
→ **[QUICKSTART.md](QUICKSTART.md)** - Fastest path to a running system

### I want a comprehensive guide
→ **[README.md](README.md)** - Complete user guide with all features

### I want to verify my deployment
→ **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - Step-by-step verification

### I want to understand the architecture
→ **[ARCHITECTURE.md](ARCHITECTURE.md)** - Detailed architecture documentation

### I want a high-level overview
→ **[SUMMARY.md](SUMMARY.md)** - What was created and why

## 📚 Documentation by Purpose

### For First-Time Users
1. [SUMMARY.md](SUMMARY.md) - Understand what this deployment provides
2. [QUICKSTART.md](QUICKSTART.md) - Get it running in 5 minutes
3. [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) - Verify everything works

### For Developers
1. [README.md](README.md) - Complete reference
2. [ARCHITECTURE.md](ARCHITECTURE.md) - System design and data flows
3. [Taskfile.yml](Taskfile.yml) - Available automation tasks

### For Production Deployment
1. [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) - Production readiness checklist
2. [ARCHITECTURE.md](ARCHITECTURE.md) - Security and scaling considerations
3. [README.md](README.md) - Production considerations section

### For Troubleshooting
1. [README.md](README.md#troubleshooting) - Common issues and solutions
2. [ARCHITECTURE.md](ARCHITECTURE.md#troubleshooting-guide) - Detailed troubleshooting
3. [QUICKSTART.md](QUICKSTART.md#troubleshooting) - Quick fixes

### For Interoperability
1. [README.md](README.md#interoperability-with-other-participants) - Connecting to other participants
2. [ARCHITECTURE.md](ARCHITECTURE.md#interoperability) - Protocol compatibility
3. [SUMMARY.md](SUMMARY.md#interoperability) - Supported scenarios

## 📁 File Reference

### Configuration Files
- **[compose.yaml](compose.yaml)** - Docker Compose service definitions
- **[Taskfile.yml](Taskfile.yml)** - Task automation definitions
- **[config/identityhub.env](config/identityhub.env)** - IdentityHub configuration
- **[config/controlplane.env](config/controlplane.env)** - Controlplane configuration
- **[config/dataplane.env](config/dataplane.env)** - Dataplane configuration
- **[.env.example](.env.example)** - Example environment variables

### Scripts
- **[scripts/seed.sh](scripts/seed.sh)** - Initialize dataspace with participant and test data
- **[scripts/init-db.sql](scripts/init-db.sql)** - PostgreSQL database initialization
- **[scripts/create-test-asset.sh](scripts/create-test-asset.sh)** - Create test assets

### Assets
- **[assets/credentials/](assets/credentials/)** - Pre-seeded Verifiable Credentials
- **[assets/keys/](assets/keys/)** - Cryptographic key pairs
- **[assets/participants/participants.json](assets/participants/participants.json)** - Participant list

### Documentation
- **[README.md](README.md)** - 394 lines - Complete user guide
- **[QUICKSTART.md](QUICKSTART.md)** - 217 lines - Quick start guide
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - 523 lines - Architecture documentation
- **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - 173 lines - Deployment verification
- **[SUMMARY.md](SUMMARY.md)** - 246 lines - High-level overview
- **[BRANCH_CHECK_GUIDE.md](BRANCH_CHECK_GUIDE.md)** - Branch verification feature guide
- **[LICENSE](LICENSE)** - Apache 2.0 License

## 🎯 Quick Access by Topic

### Setup & Installation
- [Prerequisites](QUICKSTART.md#prerequisites-check)
- [Building Images](README.md#1-build-docker-images)
- [Starting Services](README.md#2-start-services)
- [Seeding Data](README.md#3-seed-the-dataspace)

### Configuration
- [Branch Management](README.md#branch-management)
- [Branch Check Guide](BRANCH_CHECK_GUIDE.md)
- [Service Endpoints](README.md#service-endpoints)
- [Environment Variables](ARCHITECTURE.md#environment-variables)
- [Default Credentials](SUMMARY.md#default-credentials)
- [Port Mappings](compose.yaml)

### Operations
- [Available Tasks](README.md#available-tasks)
- [Health Checks](DEPLOYMENT_CHECKLIST.md#verification-tests)
- [Backup & Restore](README.md#data-persistence)
- [Debugging](ARCHITECTURE.md#debugging)

### Development
- [Development Workflow](ARCHITECTURE.md#development-workflow)
- [Remote Debugging](README.md#debugging)
- [Database Access](README.md#data-persistence)
- [Log Viewing](README.md#debugging)

### Architecture
- [System Components](ARCHITECTURE.md#system-components)
- [Data Flow Diagrams](ARCHITECTURE.md#data-flow-diagrams)
- [Security Architecture](ARCHITECTURE.md#security-architecture)
- [Network Architecture](ARCHITECTURE.md#network-architecture)

### API Reference
- [Management API](README.md#example-api-calls)
- [Catalog API](README.md#example-api-calls)
- [DID Document](README.md#example-api-calls)
- [Service Endpoints](README.md#service-endpoints)

## 🔍 Search by Question

### "How do I..."

**...get started?**
→ [QUICKSTART.md](QUICKSTART.md)

**...build the images?**
→ `task build` ([README.md](README.md#1-build-docker-images))

**...start the services?**
→ `task up` ([README.md](README.md#2-start-services))

**...seed the dataspace?**
→ `task seed` ([README.md](README.md#3-seed-the-dataspace))

**...check if it's working?**
→ `task health` ([DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md#verification-tests))

**...view the logs?**
→ `task logs` ([README.md](README.md#debugging))

**...connect to the database?**
→ `task db` ([README.md](README.md#data-persistence))

**...backup the data?**
→ `task backup` ([README.md](README.md#data-persistence))

**...connect to another participant?**
→ [README.md](README.md#interoperability-with-other-participants)

**...create an asset?**
→ [README.md](README.md#example-api-calls)

**...debug a service?**
→ [ARCHITECTURE.md](ARCHITECTURE.md#debugging)

**...change the configuration?**
→ Edit files in [config/](config/)

**...change the MVD branch?**
→ [BRANCH_CHECK_GUIDE.md](BRANCH_CHECK_GUIDE.md#changing-the-expected-branch)

**...prepare for production?**
→ [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md#production-readiness-checklist)

### "What is..."

**...the IdentityHub?**
→ [ARCHITECTURE.md](ARCHITECTURE.md#1-identityhub)

**...the Controlplane?**
→ [ARCHITECTURE.md](ARCHITECTURE.md#2-controlplane)

**...the Dataplane?**
→ [ARCHITECTURE.md](ARCHITECTURE.md#3-dataplane)

**...a DID?**
→ [ARCHITECTURE.md](ARCHITECTURE.md#did-based-identity)

**...a Verifiable Credential?**
→ [ARCHITECTURE.md](ARCHITECTURE.md#credential-types)

**...the DSP protocol?**
→ [ARCHITECTURE.md](ARCHITECTURE.md#data-flow-diagrams)

**...the difference from MVD?**
→ [SUMMARY.md](SUMMARY.md#differences-from-original-mvd)

### "Why..."

**...do I need this?**
→ [SUMMARY.md](SUMMARY.md#what-was-created)

**...use Docker Compose instead of Kubernetes?**
→ [SUMMARY.md](SUMMARY.md#differences-from-original-mvd)

**...are there so many services?**
→ [ARCHITECTURE.md](ARCHITECTURE.md#system-components)

**...do I need to seed the dataspace?**
→ [README.md](README.md#3-seed-the-dataspace)

## 📊 Documentation Statistics

- **Total Documentation**: ~1,850 lines across 5 markdown files
- **Configuration Files**: 4 (compose.yaml + 3 env files)
- **Scripts**: 3 automation scripts
- **Task Definitions**: 15+ automated tasks
- **API Endpoints**: 15+ exposed endpoints

## 🆘 Need Help?

1. **Quick issue?** Check [QUICKSTART.md Troubleshooting](QUICKSTART.md#troubleshooting)
2. **Deployment problem?** See [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
3. **Architecture question?** Read [ARCHITECTURE.md](ARCHITECTURE.md)
4. **Still stuck?** Review [README.md Troubleshooting](README.md#troubleshooting)

## 🎓 Learning Path

### Beginner Path
1. Read [SUMMARY.md](SUMMARY.md) (10 minutes)
2. Follow [QUICKSTART.md](QUICKSTART.md) (5 minutes)
3. Explore [README.md](README.md) (30 minutes)

### Advanced Path
1. Study [ARCHITECTURE.md](ARCHITECTURE.md) (1 hour)
2. Review [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) (20 minutes)
3. Experiment with [Taskfile.yml](Taskfile.yml) tasks (30 minutes)

### Production Path
1. Complete Beginner Path
2. Study [ARCHITECTURE.md Security](ARCHITECTURE.md#security-architecture) (30 minutes)
3. Work through [Production Checklist](DEPLOYMENT_CHECKLIST.md#production-readiness-checklist) (2 hours)
4. Implement production changes (varies)

## 📞 Support & Resources

- **This Deployment Issues**: Create an issue in this repository
- **MVD Core**: [eclipse-edc/MinimumViableDataspace](https://github.com/eclipse-edc/MinimumViableDataspace)
- **EDC Framework**: [eclipse-edc/Connector](https://github.com/eclipse-edc/Connector)
- **EDC Documentation**: [eclipse-edc.github.io/docs](https://eclipse-edc.github.io/docs/)

---

**Last Updated**: 2025-10-20
**Version**: 1.0.0
