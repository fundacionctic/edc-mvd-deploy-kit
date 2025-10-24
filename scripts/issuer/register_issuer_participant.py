#!/usr/bin/env python3
"""Register Issuer as participant in its own Identity Hub.

This script registers the Issuer itself as a participant in its own Identity Hub,
including the IssuerService endpoint. This is a critical step that must be done
before the Issuer can issue credentials.

The Issuer needs to be registered with:
- Its own DID as participantId
- Admin role
- IssuerService endpoint pointing to the issuance API
- Key configuration for signing

API Endpoint:
    POST /api/identity/v1alpha/participants/

Usage:
    python3 scripts/issuer/register_issuer_participant.py
"""

import base64
import logging
import sys

from http_utils import make_request

from config import Config, load_config

logger = logging.getLogger(__name__)


def register_issuer_participant(cfg: Config) -> bool:
    """Register the Issuer as a participant in its own Identity Hub."""
    issuer_did_encoded = base64.urlsafe_b64encode(cfg.issuer_did.encode()).decode()

    issuer_service_endpoint = (
        f"http://{cfg.issuer_public_host}:{cfg.issuer_issuance_port}"
        f"/api/issuance/v1alpha/participants/{issuer_did_encoded}"
    )

    headers = {
        "Content-Type": "application/json",
        "x-api-key": cfg.issuer_superuser_key,
    }

    payload = {
        "roles": ["admin"],
        "serviceEndpoints": [
            {
                "type": "IssuerService",
                "serviceEndpoint": issuer_service_endpoint,
                "id": "issuer-service-1",
            }
        ],
        "active": True,
        "participantId": cfg.issuer_did,
        "did": cfg.issuer_did,
        "key": {
            "keyId": f"{cfg.issuer_did}#key-1",
            "privateKeyAlias": "key-1",
            "keyGeneratorParams": {"algorithm": "EdDSA"},
        },
    }

    logger.info("Registering Issuer as participant in Identity Hub")
    logger.debug(f"Issuer DID: {cfg.issuer_did}")
    logger.debug(f"Service Endpoint: {issuer_service_endpoint}")

    success, _, _ = make_request(
        url=cfg.get_identity_participants_url(),
        headers=headers,
        method="POST",
        data=payload,
        entity_name="Issuer participant",
    )
    return success


def main() -> int:
    """Main entry point for Issuer participant registration script."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    logger.info("=" * 60)
    logger.info("Register Issuer as Participant in Identity Hub")
    logger.info("=" * 60)

    cfg = load_config()
    if not cfg:
        logger.error("Failed to load configuration")
        return 1

    if register_issuer_participant(cfg):
        logger.info("✓ Issuer participant registration complete")
        return 0
    logger.error("✗ Issuer participant registration failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
