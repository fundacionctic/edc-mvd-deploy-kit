# Source Repository Management Guide

## Overview

This deployment automatically manages the EDC Minimum Viable Dataspace source repository. The Taskfile includes:
- **Automatic cloning/updating** of the MVD repository from GitHub
- **Branch verification** to ensure you're building from the correct version
- **Easy configuration** of repository URL and branch

This prevents version mismatches and ensures you always have the correct source code.

## How It Works

### Configuration

The repository settings are configured as variables in `Taskfile.yml`:

```yaml
vars:
  MVD_SOURCE_DIR: "{{.ROOT_DIR}}/edc-minimum-viable-dataspace"
  MVD_BRANCH: release/0.14.0  # Change this to your desired branch
  MVD_REPO_URL: https://github.com/eclipse-edc/MinimumViableDataspace
```

The source directory is now located within the project root and is automatically gitignored.

### How It Works

The system consists of two main tasks:

**1. `setup-source` (Internal Task)**:
- Checks if the MVD source directory exists
- If not, clones the repository from GitHub
- If it exists, updates it to the latest commit
- Checks out the configured branch
- Verifies the repository URL matches expectations

**2. `check-branch` (Internal Task)**:
- Verifies the current branch matches `MVD_BRANCH`
- Displays warnings if there's a mismatch
- Prompts for confirmation to continue

### Affected Tasks

Automatic setup runs before these tasks:
- `task build` - Build Docker images (runs `setup-source`)
- `task rebuild` - Rebuild and restart (runs `setup-source`)
- `task dev` - Development mode (runs `setup-source`)
- `task setup` - Manual setup/update (calls `setup-source`)

## Usage Examples

### First Time Setup

```bash
task setup
```

Output example:
```
Setting up MVD source repository...
  Repository: https://github.com/eclipse-edc/MinimumViableDataspace
  Target directory: ./edc-minimum-viable-dataspace
  Branch: release/0.14.0

Cloning repository...
✓ Repository cloned successfully

✓ MVD source setup complete!
  Location: ./edc-minimum-viable-dataspace
  Branch: release/0.14.0
  Current commit: dff9149 - Prepare release 0.14.0
```

### Check Current Status

```bash
task info
```

Output example:
```
MVD Source Configuration:
  Repository: https://github.com/eclipse-edc/MinimumViableDataspace
  Directory: ./edc-minimum-viable-dataspace
  Expected Branch: release/0.14.0

Current Status:
  Current Branch: release/0.14.0
  Status: ✓ On correct branch

Recent commits:
dff9149 Prepare release 0.14.0
3d4a6f7 build(deps): bump actions/checkout from 4 to 5 (#519)
9e98545 build(deps): bump io.rest-assured:rest-assured from 5.5.1 to 5.5.6 (#517)
```

### Building (Automatic Setup)

The build task automatically ensures the source is cloned and up-to-date:

```bash
task build
```

Output:
```
Setting up MVD source repository...
  Repository: https://github.com/eclipse-edc/MinimumViableDataspace
  Target directory: ./edc-minimum-viable-dataspace
  Branch: release/0.14.0

Directory exists, checking if it's a git repository...
✓ Git repository found
Fetching latest changes...
Checking out branch: release/0.14.0
Pulling latest changes...

✓ MVD source setup complete!
  Location: ./edc-minimum-viable-dataspace
  Branch: release/0.14.0
  Current commit: dff9149 - Prepare release 0.14.0

Building MVD components...
```

### Manual Branch Changes

If you manually change branches in the source directory, the setup task will detect and update it:

```bash
# Manually switch branch
cd ./edc-minimum-viable-dataspace
git checkout main
cd ..

# Next build will switch back to configured branch
task build
```

Output:
```
Setting up MVD source repository...
Checking out branch: release/0.14.0
Pulling latest changes...
✓ MVD source setup complete!
```

## Changing the Expected Branch

### Method 1: Edit Taskfile.yml (Permanent)

```bash
# Edit the file
nano Taskfile.yml

# Change the MVD_BRANCH variable
vars:
  MVD_BRANCH: main  # or any other branch
```

### Method 2: Override via Environment Variable (Temporary)

```bash
# For a single command
MVD_BRANCH=main task build

# For the current shell session
export MVD_BRANCH=main
task build
```

## Common Scenarios

### Scenario 1: Working with Multiple Branches

If you frequently switch between branches, you can:

1. **Use task info before building**:
   ```bash
   task info
   task build
   ```

2. **Override the branch variable**:
   ```bash
   MVD_BRANCH=main task build
   ```

3. **Accept the prompt**:
   - Just press `y` when prompted if you know you want to build from a different branch

### Scenario 2: Using Development (main) Branch

For bleeding-edge features:

```bash
# Update Taskfile.yml to use main branch
nano Taskfile.yml
# Change MVD_BRANCH to: main

# Build will automatically switch to main
task build
```

### Scenario 3: Using a Specific Release

For a stable release (this is the default):

```bash
# Verify configuration in Taskfile.yml shows: release/0.14.0
task info

# Build (automatically uses correct branch)
task build
```

### Scenario 4: Testing a Feature Branch

For testing specific features:

```bash
# Update Taskfile.yml
nano Taskfile.yml
# Change MVD_BRANCH to: feature/my-feature

# Build will automatically switch to feature branch
task build
```

## Error Handling

### Error: Repository Clone Failed

```
ERROR: Failed to clone repository
```

**Solution**: Check network connectivity and repository URL:
```bash
# Verify you can reach GitHub
ping github.com

# Try manual clone
git clone https://github.com/eclipse-edc/MinimumViableDataspace

# Check Taskfile.yml has correct URL
grep MVD_REPO_URL Taskfile.yml
```

### Error: Git Command Not Found

If git is not installed or not in PATH:

**macOS**: `brew install git`
**Linux**: `sudo apt-get install git` or `sudo yum install git`
**Windows**: Install Git from https://git-scm.com/

## Best Practices

1. **Always check branch before building**:
   ```bash
   task info
   task build
   ```

2. **Document branch changes**: If you change `MVD_BRANCH` in Taskfile.yml, document why in a comment:
   ```yaml
   # Using main branch for testing feature XYZ
   MVD_BRANCH: main
   ```

3. **Use releases for production**: Always use release branches (e.g., `release/0.14.0`) for production deployments:
   ```yaml
   MVD_BRANCH: release/0.14.0
   ```

4. **Test thoroughly after branch changes**: When switching branches, rebuild and test:
   ```bash
   task clean
   task build
   task up
   task seed
   task health
   ```

## Disabling Branch Check

If you need to temporarily disable the branch check:

### Option 1: Comment out the dependency

Edit `Taskfile.yml`:
```yaml
build:
  desc: Build Docker images for all components
  # deps: [_check-branch]  # Commented out
  dir: '{{.MVD_SOURCE_DIR}}'
  cmds:
    - echo "Building MVD components..."
```

### Option 2: Remove the internal task call

Not recommended, but you can delete or comment out the entire `_check-branch` task.

### Option 3: Always accept the prompt

Use `yes` command (Linux/macOS):
```bash
yes y | task build
```

## Integration with CI/CD

In CI/CD pipelines, you may want to:

1. **Set the branch explicitly**:
   ```yaml
   # .gitlab-ci.yml or similar
   variables:
     MVD_BRANCH: release/0.14.0

   script:
     - task build
   ```

2. **Auto-accept prompts**:
   ```bash
   yes y | task build
   ```

3. **Fail on mismatch** (modify the check to exit immediately):
   Edit the `_check-branch` task to remove the prompt and always exit on mismatch.

## Troubleshooting

### Issue: Setup keeps failing

**Check**:
1. Network connectivity: `ping github.com`
2. Git is installed: `git --version`
3. Directory permissions: `ls -la ./edc-minimum-viable-dataspace`
4. Repository URL in Taskfile.yml is correct

### Issue: Cannot switch branches

**Common causes**:
- Uncommitted changes: `git status` shows modified files
- Detached HEAD state: `git checkout <branch>`

**Solutions**:
```bash
# Stash changes
git stash
git checkout release/0.14.0

# Or commit changes
git add .
git commit -m "WIP"
git checkout release/0.14.0
```

## FAQ

**Q: Why do I need a branch check?**
A: To prevent building from the wrong version, which can lead to version mismatches and unexpected behavior.

**Q: Can I use a commit hash instead of a branch?**
A: The current implementation only checks branches. You could modify `_check-branch` to also accept commit hashes.

**Q: Does this check affect non-build tasks?**
A: No, only `build`, `rebuild`, and `dev` tasks run the check.

**Q: What if I want to use multiple MVD versions?**
A: You can have multiple MVD source directories and switch the `MVD_SOURCE_DIR` variable, or use different Taskfile configurations.

**Q: Can I make the check stricter (no prompt)?**
A: Yes, edit the `_check-branch` task and remove the prompt section, leaving only the `exit 1` on mismatch.

## See Also

- [README.md](README.md) - Complete deployment guide
- [Taskfile.yml](Taskfile.yml) - Full task definitions
- [.env.example](.env.example) - Environment variable template
