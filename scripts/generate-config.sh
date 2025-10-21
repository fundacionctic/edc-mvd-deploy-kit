#!/bin/bash

#
# Generate Configuration Files from Templates
#
# This script generates all configuration files from templates using
# environment variables defined in .env
#
# Generated files:
#   - config/identityhub.env
#   - config/controlplane.env
#   - config/dataplane.env
#   - config/issuer-service.env (if ISSUER_MODE=local)
#   - assets/participants/participants.json
#

set -e

echo "============================================="
echo "Configuration Generation"
echo "============================================="
echo ""

# Default configuration (can be overridden by environment)
: "${CONFIG_VERBOSE:=false}"
: "${CONFIG_VALIDATE_TEMPLATES:=true}"
: "${CONFIG_SKIP_ISSUER:=false}"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration paths
CONFIG_DIR="$ROOT_DIR/config"
ASSETS_DIR="$ROOT_DIR/assets"

# Load environment configuration
set -a
source "$ROOT_DIR/.env"
set +a

if [ "$CONFIG_VERBOSE" = "true" ]; then
  echo "✓ Environment loaded"
  echo "  Participant DID: $PARTICIPANT_DID"
  echo "  Issuer Mode: $ISSUER_MODE"
  echo "  Config directory: $CONFIG_DIR"
  echo ""
else
  echo "✓ Environment loaded (Participant: $PARTICIPANT_DID, Issuer: $ISSUER_MODE)"
  echo ""
fi

# ============================================
# Generate Participant Service Configs
# ============================================

echo "📄 Generating participant service configs..."

# Template files to process
PARTICIPANT_CONFIGS=(
  "identityhub.env"
  "controlplane.env"
  "dataplane.env"
)

for config in "${PARTICIPANT_CONFIGS[@]}"; do
  TEMPLATE_FILE="$CONFIG_DIR/${config}.template"
  OUTPUT_FILE="$CONFIG_DIR/${config}"

  if [ "$CONFIG_VALIDATE_TEMPLATES" = "true" ] && [ ! -f "$TEMPLATE_FILE" ]; then
    echo "  ❌ Template not found: $TEMPLATE_FILE"
    exit 1
  fi

  envsubst <"$TEMPLATE_FILE" >"$OUTPUT_FILE"

  if [ "$CONFIG_VERBOSE" = "true" ]; then
    echo "  ✓ Generated: $OUTPUT_FILE (from $(basename "$TEMPLATE_FILE"))"
  else
    echo "  ✓ config/$config"
  fi
done

echo ""

# ============================================
# Generate Issuer Service Config (if local)
# ============================================

if [ "$CONFIG_SKIP_ISSUER" = "true" ]; then
  echo "⚠️  Skipping issuer config generation (CONFIG_SKIP_ISSUER=true)"
  echo ""
elif [ "$ISSUER_MODE" = "local" ]; then
  echo "📄 Generating issuer service config (local mode)..."

  ISSUER_TEMPLATE="$CONFIG_DIR/issuer-service.env.template"
  ISSUER_OUTPUT="$CONFIG_DIR/issuer-service.env"

  if [ -f "$ISSUER_TEMPLATE" ]; then
    envsubst <"$ISSUER_TEMPLATE" >"$ISSUER_OUTPUT"
    if [ "$CONFIG_VERBOSE" = "true" ]; then
      echo "  ✓ Generated: $ISSUER_OUTPUT"
    else
      echo "  ✓ config/issuer-service.env"
    fi
  else
    echo "  ⚠️  Template not found: $ISSUER_TEMPLATE"
    echo "     Run 'task configure-issuer' to generate issuer configuration"
  fi

  echo ""
elif [ "$ISSUER_MODE" = "external" ]; then
  echo "ℹ️  Issuer mode is 'external' - skipping local issuer config generation"
  echo ""
fi

# ============================================
# Generate Participants List
# ============================================

echo "📄 Generating participants list..."

# Create assets/participants directory if it doesn't exist
PARTICIPANTS_DIR="$ASSETS_DIR/participants"
PARTICIPANTS_FILE="$PARTICIPANTS_DIR/participants.json"
PARTICIPANTS_KEY="${PARTICIPANT_KEY_NAME:-mvd-participant}"

mkdir -p "$PARTICIPANTS_DIR"

# Generate participants.json with the current participant DID
cat >"$PARTICIPANTS_FILE" <<EOF
{
  "$PARTICIPANTS_KEY": "$PARTICIPANT_DID"
}
EOF

if [ "$CONFIG_VERBOSE" = "true" ]; then
  echo "  ✓ Generated: $PARTICIPANTS_FILE"
  echo "    Participant key: $PARTICIPANTS_KEY"
  echo "    Participant DID: $PARTICIPANT_DID"
else
  echo "  ✓ assets/participants/participants.json"
fi
echo ""

# ============================================
# Validation
# ============================================

echo "🔍 Validating generated configs..."

VALIDATION_ERRORS=0

# Check that all expected files exist
EXPECTED_FILES=(
  "config/identityhub.env"
  "config/controlplane.env"
  "config/dataplane.env"
  "assets/participants/participants.json"
)

for file in "${EXPECTED_FILES[@]}"; do
  if [ ! -f "$ROOT_DIR/$file" ]; then
    echo "  ❌ Missing: $file"
    VALIDATION_ERRORS=$((VALIDATION_ERRORS + 1))
  fi
done

# Validate host.docker.internal accessibility
echo "  🔍 Checking host.docker.internal resolution..."
if ping -c 1 -W 1000 host.docker.internal >/dev/null 2>&1; then
  echo "  ✓ host.docker.internal resolves successfully"
elif command -v nslookup >/dev/null 2>&1; then
  if nslookup host.docker.internal >/dev/null 2>&1; then
    echo "  ✓ host.docker.internal resolves successfully"
  else
    echo "  ⚠️  host.docker.internal resolution failed"
    echo "     This is expected on Linux without Docker Desktop"
    echo "     Use: docker run --add-host=host.docker.internal:host-gateway ..."
  fi
elif command -v getent >/dev/null 2>&1; then
  if getent hosts host.docker.internal >/dev/null 2>&1; then
    echo "  ✓ host.docker.internal resolves successfully"
  else
    echo "  ⚠️  host.docker.internal resolution failed"
    echo "     This is expected on Linux without Docker Desktop"
    echo "     Use: docker run --add-host=host.docker.internal:host-gateway ..."
  fi
else
  echo "  ℹ️  Cannot validate host.docker.internal resolution (no ping/nslookup/getent)"
fi

if [ $VALIDATION_ERRORS -eq 0 ]; then
  echo "  ✓ All expected files generated"
else
  echo "  ❌ $VALIDATION_ERRORS file(s) missing"
  exit 1
fi

echo ""
echo "============================================="
echo "✓ Configuration generation complete!"
echo "============================================="
echo ""
echo "Generated files:"
echo "  - config/identityhub.env"
echo "  - config/controlplane.env"
echo "  - config/dataplane.env"
if [ "$ISSUER_MODE" = "local" ] && [ -f "$ROOT_DIR/config/issuer-service.env" ]; then
  echo "  - config/issuer-service.env"
fi
echo "  - assets/participants/participants.json"
echo ""
echo "⚠️  Note: These are generated files - do not edit manually!"
echo "   Edit .env and re-run this script to regenerate."
echo ""
