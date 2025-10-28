#!/usr/bin/env python3
"""Create participant holders in Issuer Service.

This script registers participants (holders) in the Issuer Service,
enabling them to request and receive verifiable credentials.

Participants:
    - Provider: DID generated from PROVIDER_IH_DID_PORT (default: 7003)

API Endpoint:
    POST /api/admin/v1alpha/participants/{issuer-context-id}/holders

Usage:
    python3 scripts/issuer/create_participants.py
"""

import logging
import sys

from http_utils import make_request

from config import Config, load_config

logger = logging.getLogger(__name__)


def create_participant_holder(
    cfg: Config, participant_did: str, participant_name: str
) -> bool:
    """Create a participant holder in the Issuer Service."""
    payload = {
        "did": participant_did,
        "holderId": participant_did,
        "name": participant_name,
    }

    logger.info(f"Creating participant holder: {participant_name}")
    logger.debug(f"DID: {participant_did}")

    success, _, _ = make_request(
        url=cfg.get_holders_url(),
        headers=cfg.get_headers(),
        method="POST",
        data=payload,
        entity_name=f"participant {participant_name}",
    )
    return success


def create_all_participants(cfg: Config) -> bool:
    """Create all participant holders in the Issuer Service."""
    participants = [
        {"did": cfg.provider_did, "name": "Provider Corp"},
    ]

    logger.info(f"Creating {len(participants)} participant holders...")

    results = [
        create_participant_holder(cfg, p["did"], p["name"]) for p in participants
    ]
    success_count = sum(results)
    failure_count = len(results) - success_count

    logger.info(f"Participant creation complete: ✓ {success_count}, ✗ {failure_count}")
    return failure_count == 0


def main() -> int:
    """Main entry point for participant creation script."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    logger.info("=" * 60)
    logger.info("Issuer Service - Create Participant Holders")
    logger.info("=" * 60)

    cfg = load_config()
    if not cfg:
        logger.error("Failed to load configuration")
        return 1

    if create_all_participants(cfg):
        logger.info("✓ All participants created successfully")
        return 0
    logger.error("✗ Some participants failed to create")
    return 1


if __name__ == "__main__":
    sys.exit(main())
