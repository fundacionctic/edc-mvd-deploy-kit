"""
Issuer Service Seeding Orchestration Script

This is the main entry point for seeding the Issuer Service with
attestation definitions and credential definitions.

Seeding Sequence:
    1. Wait for Issuer Service health
    2. Check DID document server
    3. Register Issuer as participant in its own Identity Hub
    4. Create participant holders (Consumer, Provider)
    5. Create attestation definitions (Database attestations)
    6. Create credential definitions (MembershipCredential, DataProcessorCredential)

Usage:
    python scripts/issuer/seed_issuer.py

    Or from project root:
    python -m scripts.issuer.seed_issuer

Exit Codes:
    0: Success - all seeding operations completed
    1: Failure - one or more operations failed
"""

import logging
import sys
import time

from create_attestations import main as main_create_all_attestations
from create_credentials import main as main_create_all_credentials
from create_participants import main as main_create_all_participants
from register_issuer_participant import main as main_register_issuer_participant
from verify_deployment import wait_for_health

from config import load_config

logger = logging.getLogger(__name__)

DELAY_BETWEEN_STEPS = 2  # seconds


def run_seeding_sequence() -> bool:
    """
    Execute the complete seeding sequence for the Issuer Service.

    Returns:
        True if all steps succeed, False otherwise
    """
    logger.info("Step 0: Loading configuration...")
    config = load_config()
    if not config:
        logger.error("✗ Configuration loading failed")
        return False
    logger.info("✓ Configuration loaded successfully")
    time.sleep(DELAY_BETWEEN_STEPS)

    if not wait_for_health(config):
        logger.error("✗ Service health check failed")
        return False
    logger.info("✓ Issuer Service is healthy")
    time.sleep(DELAY_BETWEEN_STEPS)

    main_register_issuer_participant()
    time.sleep(DELAY_BETWEEN_STEPS)

    main_create_all_participants()
    time.sleep(DELAY_BETWEEN_STEPS)

    main_create_all_attestations()
    time.sleep(DELAY_BETWEEN_STEPS)

    main_create_all_credentials()
    time.sleep(DELAY_BETWEEN_STEPS)

    return True


def main() -> int:
    """
    Main entry point for the seeding orchestration script.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        if run_seeding_sequence():
            logger.info("=" * 70)
            logger.info("✓ ✓ ✓  ISSUER SERVICE SEEDING COMPLETED SUCCESSFULLY  ✓ ✓ ✓")
            logger.info("=" * 70)
            return 0
        else:
            logger.error("=" * 70)
            logger.error("✗ ✗ ✗  ISSUER SERVICE SEEDING FAILED  ✗ ✗ ✗")
            logger.error("=" * 70)
            return 1

    except KeyboardInterrupt:
        logger.warning("")
        logger.warning("=" * 70)
        logger.warning("Seeding interrupted by user (Ctrl+C)")
        logger.warning("=" * 70)
        return 1

    except Exception as e:
        logger.error("")
        logger.error("=" * 70)
        logger.error(f"Unexpected error during seeding: {e}")
        logger.error("=" * 70)
        logger.exception("Stack trace:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
