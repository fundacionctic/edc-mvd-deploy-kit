#!/usr/bin/env python3
"""
Generate DID Document for Issuer Service

This script generates a DID document dynamically based on environment variables.
It reads the public key from a file and constructs the DID document with the
correct hostname and port.

Usage:
    python3 scripts/issuer/generate_did.py

Environment Variables:
    ISSUER_PUBLIC_HOST: Public hostname (e.g., host.docker.internal or issuer.domain.com)
    ISSUER_DID_PORT: DID server port (e.g., 9876)
    ISSUER_PUBLIC_KEY_FILE: Path to public key PEM file

Output:
    Writes DID document to deployment/issuer/did.docker.json

Requirements:
    - cryptography package: pip install cryptography
"""

import base64
import json
import logging
import os
import sys
import urllib.parse

try:
    from cryptography.hazmat.primitives import serialization
except ImportError:
    print("ERROR: cryptography package not found")
    print("Install with: pip install cryptography")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def read_public_key_jwk(key_file_path):
    """
    Read public key from PEM file and convert to JWK format.

    Args:
        key_file_path: Path to PEM file

    Returns:
        Dictionary with JWK fields
    """
    logger.info(f"Reading public key from: {key_file_path}")

    if not os.path.exists(key_file_path):
        logger.error(f"Public key file not found: {key_file_path}")
        logger.error("Run: python3 scripts/issuer/generate_keys.py")
        raise FileNotFoundError(f"Public key file not found: {key_file_path}")

    # Load public key from PEM file
    with open(key_file_path, "rb") as f:
        public_key = serialization.load_pem_public_key(f.read())

    # Get raw public key bytes (32 bytes for Ed25519)
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )

    # Convert to base64url (without padding) for JWK
    x_value = base64.urlsafe_b64encode(public_bytes).decode("utf-8").rstrip("=")

    logger.info(f"✓ Public key loaded successfully")
    logger.debug(f"  JWK x value: {x_value}")

    return {
        "kty": "OKP",
        "crv": "Ed25519",
        "x": x_value,
    }


def generate_did_document(hostname, port, public_key_jwk):
    """
    Generate DID document.

    Args:
        hostname: Public hostname
        port: DID server port
        public_key_jwk: Public key in JWK format

    Returns:
        DID document dictionary
    """
    # URL-encode the hostname:port combination
    host_with_port = f"{hostname}:{port}" if port != "443" else hostname
    encoded_host = urllib.parse.quote(host_with_port, safe="")

    did_id = f"did:web:{encoded_host}"
    key_id = f"{did_id}#key-1"

    did_doc = {
        "id": did_id,
        "verificationMethod": [
            {
                "id": key_id,
                "type": "JsonWebKey2020",
                "controller": did_id,
                "publicKeyJwk": public_key_jwk,
            }
        ],
        "authentication": ["key-1"],
        "@context": ["https://www.w3.org/ns/did/v1"],
    }

    return did_doc


def main():
    """Main entry point."""
    logger.info("Generating DID document for Issuer Service")

    # Read environment variables
    hostname = os.getenv("ISSUER_PUBLIC_HOST")
    port = os.getenv("ISSUER_DID_PORT")
    key_file = os.getenv("ISSUER_PUBLIC_KEY_FILE", "assets/keys/issuer_public.pem")

    if not hostname:
        logger.error("ISSUER_PUBLIC_HOST environment variable not set")
        return 1

    if not port:
        logger.error("ISSUER_DID_PORT environment variable not set")
        return 1

    logger.info(f"Hostname: {hostname}")
    logger.info(f"Port: {port}")
    logger.info(f"Public key file: {key_file}")

    # Read public key from PEM file
    try:
        public_key_jwk = read_public_key_jwk(key_file)
    except FileNotFoundError as e:
        logger.error(str(e))
        return 1
    except Exception as e:
        logger.error(f"Failed to read public key: {e}")
        return 1

    # Generate DID document
    did_doc = generate_did_document(hostname, port, public_key_jwk)

    # Compute DID for logging
    host_with_port = f"{hostname}:{port}" if port != "443" else hostname
    encoded_host = urllib.parse.quote(host_with_port, safe="")
    did_id = f"did:web:{encoded_host}"

    logger.info(f"Generated DID: {did_id}")

    # Write to file
    output_file = "deployment/issuer/did.docker.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(did_doc, f, indent=2)

    logger.info(f"DID document written to: {output_file}")

    # Also set ISSUER_DID environment variable for use by other scripts
    logger.info(f"Set ISSUER_DID={did_id}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
