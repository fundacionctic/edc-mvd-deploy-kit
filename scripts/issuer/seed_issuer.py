"""
Issuer Service Seeding Orchestration Script

This is the main entry point for seeding the Issuer Service with
attestation definitions and credential definitions.

Seeding Sequence:
    1. Wait for Issuer Service health
    2. Create participant holders (Consumer, Provider)
    3. Create attestation definitions (Database attestations)
    4. Create credential definitions (MembershipCredential, DataProcessorCredential)
    5. Verify all seeded data

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

from create_attestations import create_all_attestations
from create_credentials import create_all_credentials
from create_participants import create_all_participants
from verify_deployment import check_did_server, wait_for_health

from config import load_config

logger = logging.getLogger(__name__)


# ============================================================
# SEEDING CONSTANTS
# ============================================================

DELAY_BETWEEN_STEPS = 2  # seconds


def run_seeding_sequence() -> bool:
    """
    Execute the complete seeding sequence for the Issuer Service.

    Returns:
        True if all steps succeed, False otherwise
    """
    logger.info("=" * 70)
    logger.info("ISSUER SERVICE SEEDING - ORCHESTRATION")
    logger.info("=" * 70)

    # Load configuration
    logger.info("Step 0: Loading configuration...")
    config = load_config()
    if not config:
        logger.error("✗ Configuration loading failed")
        return False
    logger.info("✓ Configuration loaded successfully")
    time.sleep(DELAY_BETWEEN_STEPS)

    # Wait for service health
    logger.info("")
    logger.info("=" * 70)
    logger.info("Step 1: Waiting for Issuer Service to become healthy...")
    logger.info("=" * 70)
    if not wait_for_health(config):
        logger.error("✗ Service health check failed")
        return False
    logger.info("✓ Issuer Service is healthy")
    time.sleep(DELAY_BETWEEN_STEPS)

    # Check DID server
    logger.info("")
    logger.info("=" * 70)
    logger.info("Step 2: Checking DID document server...")
    logger.info("=" * 70)
    if not check_did_server():
        logger.error("✗ DID server check failed")
        return False
    logger.info("✓ DID server is accessible")
    time.sleep(DELAY_BETWEEN_STEPS)

    # Create participants
    logger.info("")
    logger.info("=" * 70)
    logger.info("Step 3: Creating participant holders...")
    logger.info("=" * 70)
    if not create_all_participants(config):
        logger.error("✗ Participant creation failed")
        return False
    logger.info("✓ All participants created successfully")
    time.sleep(DELAY_BETWEEN_STEPS)

    # Create attestation definitions
    logger.info("")
    logger.info("=" * 70)
    logger.info("Step 4: Creating attestation definitions...")
    logger.info("=" * 70)
    if not create_all_attestations(config):
        logger.error("✗ Attestation creation failed")
        return False
    logger.info("✓ All attestation definitions created successfully")
    time.sleep(DELAY_BETWEEN_STEPS)

    # Create credential definitions
    logger.info("")
    logger.info("=" * 70)
    logger.info("Step 5: Creating credential definitions...")
    logger.info("=" * 70)
    if not create_all_credentials(config):
        logger.error("✗ Credential definition creation failed")
        return False
    logger.info("✓ All credential definitions created successfully")
    time.sleep(DELAY_BETWEEN_STEPS)

    # Final summary
    logger.info("")
    logger.info("=" * 70)
    logger.info("SEEDING SUMMARY")
    logger.info("=" * 70)
    logger.info("✓ Configuration loaded")
    logger.info("✓ Service health verified")
    logger.info("✓ DID server verified")
    logger.info("✓ Participants created (2)")
    logger.info("✓ Attestation definitions created (2)")
    logger.info("✓ Credential definitions created (2)")
    logger.info("")
    logger.info("Seeding operations completed successfully!")
    logger.info("")
    logger.info("Next steps:")
    logger.info("  1. Verify deployment: python scripts/issuer/verify_deployment.py")
    logger.info("  2. Test credential issuance from Consumer/Provider")
    logger.info("")

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
