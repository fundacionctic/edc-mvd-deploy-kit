# Changelog

All notable changes to this project will be documented in this file.

## [1.1.0] - 2025-10-20

### Added

- **Branch Verification System**: Added automatic branch checking for build operations
  - New `MVD_BRANCH` variable in Taskfile.yml (default: `release/0.14.0`)
  - Internal `_check-branch` task that verifies MVD source is on the correct branch
  - Interactive prompt when branch mismatch is detected
  - Option to continue or abort on mismatch

- **New Task: `task info`**: Display MVD source directory and branch information
  - Shows configured branch
  - Shows current branch
  - Displays status (match/mismatch)
  - Shows recent commits

- **Documentation**:
  - [BRANCH_CHECK_GUIDE.md](BRANCH_CHECK_GUIDE.md) - Comprehensive guide for branch verification feature
  - Updated [README.md](README.md) with branch management section
  - Updated [QUICKSTART.md](QUICKSTART.md) with branch verification steps
  - Updated [INDEX.md](INDEX.md) with branch check references
  - Updated [.env.example](.env.example) with `MVD_BRANCH` variable

### Changed

- Modified `task build` to include branch check dependency
- Modified `task rebuild` to include branch check dependency
- Modified `task dev` to include branch check dependency
- Enhanced task table in README with branch information

### Technical Details

The branch check works as follows:
1. Before building, the `_check-branch` internal task runs
2. It executes `git rev-parse --abbrev-ref HEAD` in the MVD source directory
3. Compares the result with the `MVD_BRANCH` variable
4. On mismatch: displays warning and prompts user
5. On match: displays success message and continues

Users can:
- Override the branch: `MVD_BRANCH=main task build`
- Edit Taskfile.yml to change the default branch
- Accept the prompt to continue anyway

## [1.0.0] - 2025-10-20

### Initial Release

- Complete Docker Compose deployment for MVD single-instance
- Five core services: IdentityHub, Controlplane, Dataplane, PostgreSQL, Vault
- Task-based automation with 15+ tasks
- Comprehensive documentation (7 files, ~2,400 lines)
- Pre-configured Verifiable Credentials and DIDs
- Automated seeding scripts
- Production-ready architecture (with hardening required)
- Full interoperability with EDC-based dataspaces

### Components

- Docker Compose configuration with health checks
- Environment configurations for all services
- PostgreSQL initialization script
- Dataspace seeding script
- Asset creation helper script
- Complete documentation suite

### Documentation

- README.md - Complete user guide
- QUICKSTART.md - 5-minute setup guide
- ARCHITECTURE.md - Detailed architecture
- DEPLOYMENT_CHECKLIST.md - Verification guide
- SUMMARY.md - High-level overview
- INDEX.md - Documentation index
- LICENSE - Apache 2.0

---

## Version Guidelines

- **Major version (X.0.0)**: Breaking changes, major refactoring
- **Minor version (1.X.0)**: New features, enhancements
- **Patch version (1.0.X)**: Bug fixes, documentation updates
