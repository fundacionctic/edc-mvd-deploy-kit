#!/bin/bash

#
# Generate Issuer Cryptographic Keys
#
# Same logic as original, but magic numbers/strings are extracted
# into tunable env vars (safe defaults provided).
#

set -e

echo "============================================="
echo "Issuer Key Generation"
echo "============================================="
echo ""

# Key material & display
: "${ED25519_PUBLIC_KEY_BYTES:=32}" # Ed25519 public key length in bytes
: "${PUBLIC_KEY_PREVIEW_CHARS:=20}" # How many chars of 'x' to preview in logs

# DID doc fields
: "${DID_VERIFICATION_KEY_ID:=key-1}" # Used in '#key-1' and authentication array
: "${DID_CONTEXT_URL:=https://www.w3.org/ns/did/v1}"

# NGINX defaults
: "${NGINX_WORKER_CONNECTIONS:=1024}"
: "${NGINX_LISTEN_PORT:=80}"
: "${NGINX_SERVER_NAME:=_}"
: "${NGINX_ROOT_DIR:=/var/www}"
: "${NGINX_WELL_KNOWN_PATH:=/.well-known/did.json}"
: "${NGINX_HEALTH_PATH:=/health}"
: "${NGINX_HEALTH_STATUS:=200}"
: "${NGINX_HEALTH_MESSAGE:=healthy}"
: "${NGINX_HEALTH_CONTENT_TYPE:=text/plain}"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Check if .env exists
if [ ! -f "$ROOT_DIR/.env" ]; then
  echo "❌ Error: .env file not found"
  echo "   Please create .env from .env.example first"
  exit 1
fi

# Source .env to get configuration
set -a
# Must define: ISSUER_PRIVATE_KEY_FILE, ISSUER_PUBLIC_KEY_FILE, ISSUER_DID, ISSUER_PUBLIC_HOST, ISSUER_PUBLIC_PORT
source "$ROOT_DIR/.env"
set +a

# Create assets/issuer directory if it doesn't exist
ISSUER_ASSETS_DIR="$ROOT_DIR/assets/issuer"
mkdir -p "$ISSUER_ASSETS_DIR"

echo "📁 Output directory: $ISSUER_ASSETS_DIR"
echo ""

# Check if keys already exist
if [ -f "$ROOT_DIR/$ISSUER_PRIVATE_KEY_FILE" ]; then
  echo "⚠️  Issuer keys already exist!"
  echo ""
  read -p "Regenerate keys? This will invalidate existing credentials. (y/N) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted"
    exit 0
  fi
  echo ""
fi

# Generate Ed25519 key pair
echo "🔑 Step 1: Generating Ed25519 key pair..."
openssl genpkey -algorithm ed25519 -out "$ROOT_DIR/$ISSUER_PRIVATE_KEY_FILE"
openssl pkey -in "$ROOT_DIR/$ISSUER_PRIVATE_KEY_FILE" -pubout -out "$ROOT_DIR/$ISSUER_PUBLIC_KEY_FILE"
echo "✓ Key pair generated"
echo ""

# Extract public key in JWK format for DID document
echo "🔑 Step 2: Extracting public key in JWK format..."

# Convert public key to JWK 'x' using DER -> last ED25519_PUBLIC_KEY_BYTES -> base64url (no padding)
PUBLIC_KEY_JWK_X=$(
  openssl pkey -pubin -in "$ROOT_DIR/$ISSUER_PUBLIC_KEY_FILE" -outform DER 2>/dev/null |
    tail -c "$ED25519_PUBLIC_KEY_BYTES" |
    base64 | tr -d '\n' | tr '+/' '-_' | tr -d '='
)

echo "✓ Public key JWK x-coordinate: ${PUBLIC_KEY_JWK_X:0:$PUBLIC_KEY_PREVIEW_CHARS}..."
echo ""

# Generate DID document
echo "📄 Step 3: Generating DID document..."

cat >"$ISSUER_ASSETS_DIR/did.json" <<EOF
{
  "service": [],
  "verificationMethod": [
    {
      "id": "${ISSUER_DID}#${DID_VERIFICATION_KEY_ID}",
      "type": "JsonWebKey2020",
      "controller": "${ISSUER_DID}",
      "publicKeyMultibase": null,
      "publicKeyJwk": {
        "kty": "OKP",
        "crv": "Ed25519",
        "x": "${PUBLIC_KEY_JWK_X}"
      }
    }
  ],
  "authentication": [
    "${DID_VERIFICATION_KEY_ID}"
  ],
  "id": "${ISSUER_DID}",
  "@context": [
    "${DID_CONTEXT_URL}",
    {
      "@base": "${ISSUER_DID}"
    }
  ]
}
EOF

echo "✓ DID document created: $ISSUER_ASSETS_DIR/did.json"
echo ""

# Generate NGINX configuration
echo "📄 Step 4: Generating NGINX configuration..."

cat >"$ROOT_DIR/config/issuer-nginx.conf" <<EOF
events {
    worker_connections ${NGINX_WORKER_CONNECTIONS};
}

http {
    server {
        listen ${NGINX_LISTEN_PORT};
        server_name ${NGINX_SERVER_NAME};

        location ${NGINX_WELL_KNOWN_PATH} {
            root ${NGINX_ROOT_DIR};
            add_header Content-Type application/json;
            add_header Access-Control-Allow-Origin *;
        }

        # Health check endpoint
        location ${NGINX_HEALTH_PATH} {
            access_log off;
            return ${NGINX_HEALTH_STATUS} "${NGINX_HEALTH_MESSAGE}\n";
            add_header Content-Type ${NGINX_HEALTH_CONTENT_TYPE};
        }
    }
}
EOF

echo "✓ NGINX configuration created"
echo ""

# Display summary
echo "============================================="
echo "✓ Issuer keys generated successfully!"
echo "============================================="
echo ""
echo "Generated files:"
echo "  Private key: $ISSUER_PRIVATE_KEY_FILE"
echo "  Public key:  $ISSUER_PUBLIC_KEY_FILE"
echo "  DID document: assets/issuer/did.json"
echo "  NGINX config: config/issuer-nginx.conf"
echo ""
echo "Issuer DID: $ISSUER_DID"
echo ""
echo "Next steps:"
echo "  1. Review the DID document: cat $ISSUER_ASSETS_DIR/did.json | jq ."
echo "  2. Build issuer service: task build-issuer"
echo "  3. Start issuer stack: task issuer-up"
echo "  4. Verify DID resolution: curl http://${ISSUER_PUBLIC_HOST}:${ISSUER_PUBLIC_PORT}/.well-known/did.json"
echo ""
