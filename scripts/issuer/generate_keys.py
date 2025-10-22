#!/usr/bin/env python3
"""
Generate Key Pair for Issuer Service

This script generates an Ed25519 key pair for the Issuer Service to use
for signing credentials.

Usage:
    python3 scripts/issuer/generate_keys.py

Environment Variables:
    ISSUER_PUBLIC_KEY_FILE: Output path for public key (default: assets/keys/issuer_public.pem)
    ISSUER_PRIVATE_KEY_FILE: Output path for private key (default: assets/keys/issuer_private.pem)

Output:
    - Public key in PEM format (PKCS#8)
    - Private key in PEM format (PKCS#8)
    - Public key JWK representation (for DID document)

Requirements:
    - cryptography package: pip install cryptography
"""

import base64
import logging
import os
import sys

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519
except ImportError:
    print("ERROR: cryptography package not found")
    print("Install with: pip install cryptography")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def generate_ed25519_keys():
    """
    Generate Ed25519 key pair using the cryptography library.

    Returns:
        Tuple of (private_key_pem, public_key_pem, public_key_jwk)
    """
    logger.info("Generating new Ed25519 key pair...")

    # Generate private key
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    # Serialize private key to PEM (PKCS#8)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    # Serialize public key to PEM (SubjectPublicKeyInfo)
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    # Get raw public key bytes for JWK
    public_bytes_raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )

    # Convert to base64url (without padding) for JWK
    x_value = base64.urlsafe_b64encode(public_bytes_raw).decode("utf-8").rstrip("=")

    # Create JWK representation
    public_key_jwk = {"kty": "OKP", "crv": "Ed25519", "x": x_value}

    logger.info("✓ Key pair generated successfully")
    return private_pem, public_pem, public_key_jwk


def main():
    """Main entry point."""
    logger.info("Generating Issuer Service key pair")

    # Get output paths from environment or use defaults
    private_key_file = os.getenv(
        "ISSUER_PRIVATE_KEY_FILE", "assets/keys/issuer_private.pem"
    )
    public_key_file = os.getenv(
        "ISSUER_PUBLIC_KEY_FILE", "assets/keys/issuer_public.pem"
    )

    logger.info(f"Private key output: {private_key_file}")
    logger.info(f"Public key output:  {public_key_file}")

    # Create directories if they don't exist
    os.makedirs(os.path.dirname(private_key_file), exist_ok=True)
    os.makedirs(os.path.dirname(public_key_file), exist_ok=True)

    # Generate keys
    private_pem, public_pem, public_jwk = generate_ed25519_keys()

    # Write private key
    with open(private_key_file, "w") as f:
        f.write(private_pem)
    logger.info(f"✓ Private key written to: {private_key_file}")

    # Write public key
    with open(public_key_file, "w") as f:
        f.write(public_pem)
    logger.info(f"✓ Public key written to: {public_key_file}")

    # Log JWK for reference
    logger.info(f"✓ Public key JWK: {public_jwk}")
    logger.info("")
    logger.info("Key generation complete!")
    logger.info("")
    logger.info("Next steps:")
    logger.info("  1. The public key JWK will be used in the DID document")
    logger.info("  2. The private key will be stored in HashiCorp Vault")
    logger.info("  3. Run 'task issuer:generate-did' to create the DID document")
    logger.info("")

    return 0


if __name__ == "__main__":
    sys.exit(main())
