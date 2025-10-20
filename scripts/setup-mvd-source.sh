#!/usr/bin/env bash

set -e

MVD_SOURCE_DIR="${1}"
MVD_REF="${2}"  # Can be a branch name or commit ID
MVD_REPO_URL="${3:-https://github.com/eclipse-edc/MinimumViableDataspace}"

if [ -z "$MVD_SOURCE_DIR" ] || [ -z "$MVD_REF" ]; then
  echo "Usage: $0 <mvd_source_dir> <branch_or_commit> [repo_url]"
  echo ""
  echo "Examples:"
  echo "  $0 ./edc-mvd main"
  echo "  $0 ./edc-mvd 69e4b0b"
  echo "  $0 ./edc-mvd release/0.14.0"
  exit 1
fi

echo "Setting up MVD source repository..."
echo "  Repository: $MVD_REPO_URL"
echo "  Target directory: $MVD_SOURCE_DIR"
echo "  Target ref: $MVD_REF"
echo ""

# Check if directory exists
if [ -d "$MVD_SOURCE_DIR" ]; then
  echo "Directory exists, checking if it's a git repository..."

  if [ -d "$MVD_SOURCE_DIR/.git" ]; then
    echo "✓ Git repository found"
    cd "$MVD_SOURCE_DIR"

    # Verify it's the correct repository
    CURRENT_REMOTE=$(git config --get remote.origin.url 2>/dev/null || echo "")

    # Normalize URLs for comparison (handle .git suffix and https/git protocol differences)
    NORMALIZED_CURRENT=$(echo "$CURRENT_REMOTE" | sed 's/\.git$//' | sed 's|^git@github.com:|https://github.com/|')
    NORMALIZED_EXPECTED=$(echo "$MVD_REPO_URL" | sed 's/\.git$//')

    if [ "$NORMALIZED_CURRENT" != "$NORMALIZED_EXPECTED" ]; then
      echo "ERROR: Directory contains a different repository!"
      echo "  Current remote: $CURRENT_REMOTE"
      echo "  Expected: $MVD_REPO_URL"
      echo ""
      echo "Please remove the directory or use a different path:"
      echo "  rm -rf $MVD_SOURCE_DIR"
      exit 1
    fi

    echo "Fetching latest changes..."
    git fetch origin

    echo "Checking out ref: $MVD_REF"

    # Check if MVD_REF is a branch by checking if it exists as a remote branch
    if git rev-parse --verify "origin/$MVD_REF" >/dev/null 2>&1; then
      echo "✓ Detected as branch"
      git checkout "$MVD_REF"
      git pull origin "$MVD_REF"
    else
      # Try to checkout as commit ID or tag
      echo "✓ Detected as commit ID or tag"
      git checkout "$MVD_REF"
    fi

  else
    echo "ERROR: Directory exists but is not a git repository!"
    echo "  Directory: $MVD_SOURCE_DIR"
    echo ""
    echo "Please remove the directory or use a different path:"
    echo "  rm -rf $MVD_SOURCE_DIR"
    exit 1
  fi

else
  echo "Cloning repository..."

  # Check if MVD_REF looks like a commit hash (7-40 hex chars)
  if [[ "$MVD_REF" =~ ^[0-9a-f]{7,40}$ ]]; then
    # Clone without specifying branch, then checkout commit
    git clone "$MVD_REPO_URL" "$MVD_SOURCE_DIR"
    cd "$MVD_SOURCE_DIR"
    git checkout "$MVD_REF"
    cd - > /dev/null
  else
    # Clone with branch specified
    git clone --branch "$MVD_REF" "$MVD_REPO_URL" "$MVD_SOURCE_DIR"
  fi

  echo "✓ Repository cloned successfully"
fi

echo ""
echo "✓ MVD source setup complete!"
echo "  Location: $MVD_SOURCE_DIR"
echo "  Ref: $MVD_REF"

# Show current commit
cd "$MVD_SOURCE_DIR"
echo "  Current commit: $(git rev-parse --short HEAD) - $(git log -1 --pretty=format:'%s')"
