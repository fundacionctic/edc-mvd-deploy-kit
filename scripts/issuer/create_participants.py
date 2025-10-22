#!/usr/bin/env python3
"""
Create Participant Holders in Issuer Service

This standalone script registers participants (holders) in the Issuer Service,
enabling them to request and receive verifiable credentials.

Participants:
    - Consumer: did:web:host.docker.internal%3A7083:consumer
    - Provider: did:web:host.docker.internal%3A7093:provider

API Endpoint:
    POST /api/admin/v1alpha/participants/{issuer-context-id}/holders

Usage:
    python3 scripts/issuer/create_participants.py
"""

import json
import logging
import os
import sys
import urllib.error
import urllib.request

import config

HTTP_TIMEOUT_SECONDS = config.HTTP_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


def create_participant_holder(cfg, participant_did, participant_name):
    """
    Create a participant holder in the Issuer Service.

    Args:
        cfg: Configuration instance
        participant_did: DID of the participant to create
        participant_name: Human-readable name for the participant

    Returns:
        True if successful, False otherwise
    """
    url = cfg.get_holders_url()
    headers = cfg.get_headers()

    payload = {
        "did": participant_did,
        "holderId": participant_did,
        "name": participant_name,
    }

    logger.info(f"Creating participant holder: {participant_name}")
    logger.debug(f"  DID: {participant_did}")
    logger.debug(f"  URL: {url}")

    try:
        # Prepare request
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        # Execute request
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as response:
            response_data = response.read().decode("utf-8")
            status_code = response.getcode()

            if status_code == 200 or status_code == 201:
                logger.info(f"✓ Successfully created participant: {participant_name}")
                logger.debug(f"  Response: {response_data}")
                return True
            else:
                logger.warning(
                    f"Unexpected status code {status_code} for {participant_name}"
                )
                logger.debug(f"  Response: {response_data}")
                return False

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else "No error body"

        # 409 Conflict means holder already exists - this is OK
        if e.code == 409:
            logger.info(f"✓ Participant already exists: {participant_name}")
            return True
        else:
            logger.error(
                f"✗ HTTP error creating {participant_name}: {e.code} {e.reason}"
            )
            logger.error(f"  Error body: {error_body}")
            return False

    except urllib.error.URLError as e:
        logger.error(f"✗ URL error creating {participant_name}: {e.reason}")
        return False

    except Exception as e:
        logger.error(f"✗ Unexpected error creating {participant_name}: {e}")
        return False


def create_all_participants(cfg):
    """
    Create all participant holders in the Issuer Service.

    Args:
        cfg: Configuration instance

    Returns:
        True if all participants created successfully, False otherwise
    """
    participants = [
        {"did": cfg.consumer_did, "name": "Consumer Corp"},
        {"did": cfg.provider_did, "name": "Provider Corp"},
    ]

    logger.info(f"Creating {len(participants)} participant holders...")

    success_count = 0
    failure_count = 0

    for participant in participants:
        if create_participant_holder(cfg, participant["did"], participant["name"]):
            success_count += 1
        else:
            failure_count += 1

    logger.info(f"Participant creation complete:")
    logger.info(f"  ✓ Success: {success_count}")
    logger.info(f"  ✗ Failed: {failure_count}")

    return failure_count == 0


def main():
    """
    Main entry point for participant creation script.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    logger.info("=" * 60)
    logger.info("Issuer Service - Create Participant Holders")
    logger.info("=" * 60)

    # Load configuration
    cfg = config.load_config()
    if not cfg:
        logger.error("Failed to load configuration")
        return 1

    # Create participants
    if create_all_participants(cfg):
        logger.info("✓ All participants created successfully")
        return 0
    else:
        logger.error("✗ Some participants failed to create")
        return 1


if __name__ == "__main__":
    sys.exit(main())
