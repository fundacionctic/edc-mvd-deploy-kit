#!/usr/bin/env bash

set -e

MVD_SOURCE_DIR="${1}"
MVD_BRANCH="${2}"
MVD_REPO_URL="${3:-https://github.com/eclipse-edc/MinimumViableDataspace}"

if [ -z "$MVD_SOURCE_DIR" ] || [ -z "$MVD_BRANCH" ]; then
  echo "Usage: $0 <mvd_source_dir> <branch> [repo_url]"
  exit 1
fi

echo "Setting up MVD source repository..."
echo "  Repository: $MVD_REPO_URL"
echo "  Target directory: $MVD_SOURCE_DIR"
echo "  Branch: $MVD_BRANCH"
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

    echo "Checking out branch: $MVD_BRANCH"
    git checkout "$MVD_BRANCH"

    echo "Pulling latest changes..."
    git pull origin "$MVD_BRANCH"

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
  git clone --branch "$MVD_BRANCH" "$MVD_REPO_URL" "$MVD_SOURCE_DIR"
  echo "✓ Repository cloned successfully"
fi

echo ""
echo "✓ MVD source setup complete!"
echo "  Location: $MVD_SOURCE_DIR"
echo "  Branch: $MVD_BRANCH"

# Show current commit
cd "$MVD_SOURCE_DIR"
echo "  Current commit: $(git rev-parse --short HEAD) - $(git log -1 --pretty=format:'%s')"
