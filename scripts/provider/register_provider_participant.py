#!/usr/bin/env python3
"""Register Provider as participant in its own Identity Hub.

This script registers the Provider itself as a participant in its own Identity Hub,
including the CredentialService and ProtocolEndpoint. This is a critical step that must
be done before the Provider can participate in the dataspace.

The Provider needs to be registered with:
- Its own DID as participantId
- No admin role (unlike Issuer, this is a dataspace participant)
- CredentialService endpoint pointing to the credentials API
- ProtocolEndpoint pointing to the DSP protocol API
- Key configuration for signing (EC algorithm)

API Endpoint:
    POST /api/identity/v1alpha/participants/

Usage:
    python3 scripts/provider/register_provider_participant.py
"""

import base64
import logging
import sys

from http_utils import make_request

from config import Config, load_config

logger = logging.getLogger(__name__)


def register_provider_participant(cfg: Config) -> bool:
    """Register the Provider as a participant in its own Identity Hub."""
    provider_did_encoded = base64.urlsafe_b64encode(cfg.provider_did.encode()).decode()

    # CredentialService endpoint - points to the Identity Hub credentials API
    # Uses public host for external resolution
    credential_service_endpoint = (
        f"http://{cfg.provider_public_host}:{cfg.provider_ih_credentials_port}"
        f"/api/credentials/v1/participants/{provider_did_encoded}"
    )

    # ProtocolEndpoint - points to the Control Plane DSP protocol API
    # Uses public host for external resolution
    protocol_endpoint = (
        f"http://{cfg.provider_public_host}:{cfg.provider_cp_protocol_port}/api/dsp"
    )

    headers = {
        "Content-Type": "application/json",
        "x-api-key": cfg.provider_identity_superuser_key,
    }

    payload = {
        "roles": [],  # No admin role - this is a dataspace participant
        "serviceEndpoints": [
            {
                "type": "CredentialService",
                "serviceEndpoint": credential_service_endpoint,
                "id": "provider-credentialservice-1",
            },
            {
                "type": "ProtocolEndpoint",
                "serviceEndpoint": protocol_endpoint,
                "id": "provider-dsp",
            },
        ],
        "active": True,
        "participantId": cfg.provider_did,
        "did": cfg.provider_did,
        "key": {
            "keyId": f"{cfg.provider_did}#key-1",
            "privateKeyAlias": f"{cfg.provider_did}#key-1",
            "keyGeneratorParams": {"algorithm": "EC"},
        },
    }

    logger.info("Registering Provider as participant in Identity Hub")
    logger.debug(f"Provider DID: {cfg.provider_did}")
    logger.debug(f"Credential Service Endpoint: {credential_service_endpoint}")
    logger.debug(f"Protocol Endpoint: {protocol_endpoint}")

    identity_participants_url = (
        f"http://{cfg.provider_public_host}:{cfg.provider_ih_identity_port}"
        f"/api/identity/v1alpha/participants/"
    )

    success, _, _ = make_request(
        url=identity_participants_url,
        headers=headers,
        method="POST",
        data=payload,
        entity_name="Provider participant",
    )
    return success


def main() -> int:
    """Main entry point for Provider participant registration script."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    logger.info("=" * 60)
    logger.info("Register Provider as Participant in Identity Hub")
    logger.info("=" * 60)

    cfg = load_config()
    if not cfg:
        logger.error("Failed to load configuration")
        return 1

    if register_provider_participant(cfg):
        logger.info("✓ Provider participant registration complete")
        return 0
    logger.error("✗ Provider participant registration failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
