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
import json
import logging
import sys

from http_utils import make_request

from config import Config, load_config

logger = logging.getLogger(__name__)


def store_client_secret_in_vault(cfg: Config, client_secret: str) -> bool:
    """Store the STS client secret in Vault via the Management API.

    The client secret is returned by the Identity Hub when registering a participant.
    It must be stored in Vault so the Control Plane and Data Plane can authenticate
    with the STS (Secure Token Service) to obtain access tokens.

    Args:
        cfg: Configuration object
        client_secret: The client secret returned by Identity Hub

    Returns:
        True if successful, False otherwise
    """
    secret_alias = f"{cfg.provider_participant_name}-sts-client-secret"

    logger.info(f"Storing STS client secret in Vault with alias: {secret_alias}")

    # Management API endpoint for secrets
    secrets_url = (
        f"http://{cfg.provider_public_host}:{cfg.provider_cp_management_port}"
        f"/api/management/v3/secrets"
    )

    headers = {
        "Content-Type": "application/json",
        "x-api-key": cfg.provider_management_api_key,
    }

    # EDC Secret format (from original seed.sh)
    payload = {
        "@context": {"edc": "https://w3id.org/edc/v0.0.1/ns/"},
        "@type": "https://w3id.org/edc/v0.0.1/ns/Secret",
        "@id": secret_alias,
        "https://w3id.org/edc/v0.0.1/ns/value": client_secret,
    }

    success, response_body, status_code = make_request(
        url=secrets_url,
        headers=headers,
        method="POST",
        data=payload,
        entity_name="STS client secret",
    )

    if success:
        logger.info(f"✓ STS client secret stored successfully in Vault")
        return True
    else:
        logger.error(
            f"✗ Failed to store STS client secret in Vault (status: {status_code})"
        )
        if response_body:
            logger.error(f"Response: {response_body}")
        return False


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

    success, response_body, status_code = make_request(
        url=identity_participants_url,
        headers=headers,
        method="POST",
        data=payload,
        entity_name="Provider participant",
    )

    if not success:
        logger.error("Failed to register provider participant")
        return False

    # Handle the case where participant already exists (409 Conflict)
    # In this case, we can't retrieve the client secret from the response
    if status_code == 409:
        logger.warning(
            "⚠️  Provider participant already exists. Cannot retrieve client secret from this response."
        )
        logger.info(
            "If the STS client secret is missing from Vault, you need to:\n"
            "  1. Delete the participant from Identity Hub\n"
            "  2. Re-run provider:seed to register and store the secret"
        )
        # Return True since the participant exists, even if we can't store the secret
        return True

    # Extract client secret from response (for new registrations)
    # The Identity Hub returns a response with a "clientSecret" field
    if not response_body:
        logger.error("No response body received from Identity Hub")
        return False

    try:
        response_data = json.loads(response_body)

        # Response should be a dict with clientSecret field
        if not isinstance(response_data, dict):
            logger.error(
                f"Unexpected response format: expected dict, got {type(response_data)}"
            )
            logger.debug(f"Response: {response_body}")
            return False

        client_secret = response_data.get("clientSecret")

        if not client_secret:
            logger.error("No clientSecret in Identity Hub response")
            logger.debug(f"Response: {response_body}")
            return False

        logger.info("✓ Received client secret from Identity Hub")

        # Store the client secret in Vault via Management API
        if not store_client_secret_in_vault(cfg, client_secret):
            logger.error("Failed to store client secret in Vault")
            return False

        return True

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Identity Hub response: {e}")
        logger.debug(f"Response body: {response_body}")
        return False


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
