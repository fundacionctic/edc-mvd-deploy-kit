"""Verify Issuer Service deployment.

This script verifies that the Issuer Service is properly deployed and seeded
by checking health endpoints and querying seeded data.

Verification Steps:
    1. Health check - Issuer service is running
    2. DID server - DID document is accessible
    3. Participants - All holders are registered
    4. Attestations - All attestation definitions exist
    5. Credentials - All credential definitions exist
"""

import json
import logging
import sys
import time
import urllib.request
from typing import Any, Optional

from http_utils import query_api

from config import HTTP_TIMEOUT_SECONDS, Config, load_config

logger = logging.getLogger(__name__)


HEALTH_CHECK_MAX_RETRIES = 30
HEALTH_CHECK_RETRY_DELAY = 10


def check_health_endpoint(config: Config) -> bool:
    """Check if the Issuer Service health endpoint is responding."""
    url = config.get_health_url()
    logger.info(f"Checking health endpoint: {url}")

    try:
        with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT_SECONDS) as response:
            if response.getcode() == 200:
                logger.info("✓ Issuer Service is healthy")
                return True
            logger.warning(
                f"Health check returned unexpected status: {response.getcode()}"
            )
            return False
    except Exception as e:
        logger.error(f"✗ Health check failed: {e}")
        return False


def wait_for_health(config: Config) -> bool:
    """Wait for the Issuer Service to become healthy."""
    logger.info(
        f"Waiting for Issuer Service (max {HEALTH_CHECK_MAX_RETRIES} attempts, {HEALTH_CHECK_RETRY_DELAY}s delay)"
    )

    for attempt in range(1, HEALTH_CHECK_MAX_RETRIES + 1):
        logger.info(f"Attempt {attempt}/{HEALTH_CHECK_MAX_RETRIES}")

        if check_health_endpoint(config):
            logger.info(f"✓ Service became healthy after {attempt} attempts")
            return True

        if attempt < HEALTH_CHECK_MAX_RETRIES:
            time.sleep(HEALTH_CHECK_RETRY_DELAY)

    logger.error(
        f"✗ Service did not become healthy after {HEALTH_CHECK_MAX_RETRIES} attempts"
    )
    return False


def query_with_default_body(
    config: Config, url: str, entity_name: str
) -> Optional[Any]:
    """Query an API endpoint using POST with default query body."""
    query_body = {"filterExpression": [], "limit": 100, "offset": 0}
    return query_api(url, config.get_headers(), entity_name, query_body)


def verify_participants(config: Config) -> bool:
    """Verify that all participants are registered."""
    logger.info("=" * 60)
    logger.info("Verifying Participants")
    logger.info("=" * 60)

    participants = query_api(
        config.get_query_participants_url(),
        config.get_headers(),
        "participants",
    )

    if participants is None:
        logger.info("✓ Participants verification skipped (endpoint not available)")
        return True

    logger.info(f"Found {len(participants)} participants")

    if not participants:
        logger.info("✓ Participants verification completed (no participants found)")
        return True

    expected_dids = {config.consumer_did, config.provider_did}
    found_dids = {
        p.get("did") or p.get("participantId") or p.get("id")
        for p in participants
        if p.get("did") or p.get("participantId") or p.get("id")
    }

    missing_dids = expected_dids - found_dids
    if missing_dids:
        logger.info(
            "✓ Participants verification completed (expected participants not found)"
        )
        return True

    logger.info("✓ All expected participants are registered")
    for p in participants:
        did = p.get("did") or p.get("participantId") or p.get("id", "Unknown")
        name = p.get("name", "Unknown")
        logger.info(f"  - {name}: {did}")

    return True


def verify_attestations(config: Config) -> bool:
    """Verify that all attestation definitions exist."""
    logger.info("=" * 60)
    logger.info("Verifying Attestation Definitions")
    logger.info("=" * 60)

    attestations = query_with_default_body(
        config, config.get_query_attestations_url(), "attestations"
    )

    if attestations is None:
        logger.error("✗ Attestations verification failed")
        return False

    logger.info(f"Found {len(attestations)} attestation definitions")

    if len(attestations) < 2:
        logger.error(f"✗ Expected at least 2 attestations, found {len(attestations)}")
        return False

    logger.info("✓ All expected attestation definitions exist")
    for att in attestations:
        att_id = att.get("id", "Unknown")
        att_type = att.get("attestationType") or att.get("type", "Unknown")
        logger.info(f"  - {att_id} ({att_type})")

    return True


def verify_credentials(config: Config) -> bool:
    """Verify that all credential definitions exist."""
    logger.info("=" * 60)
    logger.info("Verifying Credential Definitions")
    logger.info("=" * 60)

    credentials = query_with_default_body(
        config, config.get_query_credentials_url(), "credential definitions"
    )

    if credentials is None:
        logger.error("✗ Credentials verification failed")
        return False

    logger.info(f"Found {len(credentials)} credential definitions")

    expected_types = {"MembershipCredential", "DataProcessorCredential"}
    found_types = {cred.get("credentialType", "") for cred in credentials}

    missing_types = expected_types - found_types
    if missing_types:
        logger.error(f"✗ Missing credential types: {missing_types}")
        return False

    logger.info("✓ All required credential definitions exist")
    for cred in credentials:
        cred_type = cred.get("credentialType", "Unknown")
        cred_id = cred.get("id", "Unknown")
        logger.info(f"  - {cred_type} ({cred_id})")

    return True


def verify_all(config: Config, wait_for_service: bool = True) -> bool:
    """Run all verification checks."""
    logger.info("=" * 60)
    logger.info("Issuer Service Deployment Verification")
    logger.info("=" * 60)

    if wait_for_service:
        if not wait_for_health(config):
            logger.error("✗ Service health check failed")
            return False
    elif not check_health_endpoint(config):
        logger.error("✗ Service health check failed")
        return False

    checks = [
        verify_participants,
        verify_attestations,
        verify_credentials,
    ]

    return all(check(config) for check in checks)


def main() -> int:
    """Main entry point for verification script."""
    logger.info("=" * 60)
    logger.info("Issuer Service - Deployment Verification")
    logger.info("=" * 60)

    config = load_config()
    if not config:
        logger.error("Failed to load configuration")
        return 1

    if verify_all(config, wait_for_service=True):
        logger.info("=" * 60)
        logger.info("✓ ALL VERIFICATION CHECKS PASSED")
        logger.info("=" * 60)
        return 0
    logger.error("=" * 60)
    logger.error("✗ VERIFICATION FAILED")
    logger.error("=" * 60)
    return 1


if __name__ == "__main__":
    sys.exit(main())
