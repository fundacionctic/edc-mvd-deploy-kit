# Branch Check Feature Guide

## Overview

The Taskfile includes an automatic branch verification system that ensures the MVD source repository is on the correct branch before building Docker images. This prevents accidentally building from the wrong version of the codebase.

## How It Works

### Configuration

The expected branch is configured as a variable in `Taskfile.yml`:

```yaml
vars:
  MVD_SOURCE_DIR: ../edc-minimum-viable-dataspace
  MVD_BRANCH: release/0.14.0  # Change this to your desired branch
```

### Internal Check Task

The `_check-branch` task is an internal task that:
1. Changes to the MVD source directory
2. Runs `git rev-parse --abbrev-ref HEAD` to get the current branch
3. Compares the current branch with `MVD_BRANCH`
4. If they don't match:
   - Displays a warning message
   - Shows the command to switch branches
   - Prompts the user to continue or abort
5. If they match:
   - Displays a success message
   - Continues with the build

### Affected Tasks

The branch check automatically runs before these tasks:
- `task build` - Build Docker images
- `task rebuild` - Rebuild and restart
- `task dev` - Development mode

## Usage Examples

### Check Current Branch Status

```bash
task info
```

Output example:
```
MVD Source Configuration:
  Directory: ../edc-minimum-viable-dataspace
  Expected Branch: release/0.14.0

Current Status:
  Current Branch: release/0.14.0
  Status: ✓ On correct branch

Recent commits:
dff9149 Prepare release 0.14.0
3d4a6f7 build(deps): bump actions/checkout from 4 to 5 (#519)
9e98545 build(deps): bump io.rest-assured:rest-assured from 5.5.1 to 5.5.6 (#517)
```

### Building with Correct Branch

When on the correct branch:

```bash
task build
```

Output:
```
✓ MVD source is on correct branch: release/0.14.0
Building MVD components...
```

### Building with Wrong Branch

When on a different branch (e.g., `main`):

```bash
task build
```

Output:
```
WARNING: MVD source is on branch 'main', expected 'release/0.14.0'
         Source directory: ../edc-minimum-viable-dataspace

To switch to the correct branch, run:
  cd ../edc-minimum-viable-dataspace && git checkout release/0.14.0

Continue anyway? [y/N]
```

Options:
- Press `y` or `Y` to continue building from the current branch
- Press `n`, `N`, or Enter to abort

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
# Switch MVD source to main
cd ../edc-minimum-viable-dataspace
git checkout main
git pull
cd -

# Update Taskfile or use environment variable
MVD_BRANCH=main task build
```

### Scenario 3: Using a Specific Release

For a stable release:

```bash
# Switch MVD source to release branch
cd ../edc-minimum-viable-dataspace
git checkout release/0.14.0
cd -

# Build (should pass check automatically)
task build
```

### Scenario 4: Testing a Feature Branch

For testing specific features:

```bash
# Switch MVD source to feature branch
cd ../edc-minimum-viable-dataspace
git checkout feature/my-feature
cd -

# Build with override
MVD_BRANCH=feature/my-feature task build

# Or accept the prompt
task build  # Press 'y' when prompted
```

## Error Handling

### Error: Not a Git Repository

```
ERROR: Failed to determine git branch in ../edc-minimum-viable-dataspace
       Is this a git repository?
```

**Solution**: Ensure the MVD source directory exists and is a git repository:
```bash
ls -la ../edc-minimum-viable-dataspace/.git
cd ../edc-minimum-viable-dataspace
git status
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

### Issue: Branch check always fails

**Check**:
1. Correct directory: `cd ../edc-minimum-viable-dataspace && pwd`
2. Git repository: `cd ../edc-minimum-viable-dataspace && git status`
3. Current branch: `cd ../edc-minimum-viable-dataspace && git branch`

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
