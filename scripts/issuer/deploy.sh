#!/usr/bin/env bash
set -e

# Simple deployment script for Issuer Service
# All validation is done in Python scripts

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${PROJECT_ROOT}"

# Source environment
[ -f .env ] && source .env

# Generate keys if they don't exist
if [ ! -f assets/keys/issuer_private.pem ] || [ ! -f assets/keys/issuer_public.pem ]; then
    echo "Generating Issuer keys..."
    python3 scripts/issuer/generate_keys.py
fi

# Generate DID document
echo "Generating DID document..."
python3 scripts/issuer/generate_did.py

# Generate configuration
echo "Generating configuration..."
envsubst <config/issuer-service.env.template >config/issuer-service.env

# Start services
echo "Starting services..."
task issuer:up

# Run seeding
echo "Seeding Issuer Service..."
python3 scripts/issuer/seed_issuer.py

echo "✓ Deployment complete"
