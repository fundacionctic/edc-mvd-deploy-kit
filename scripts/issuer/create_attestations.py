"""
Create Attestation Definitions in Issuer Service

This script creates attestation definitions that specify how the Issuer Service
retrieves evidence/claims data when issuing credentials.

Attestation Types:
    - Database: Queries PostgreSQL tables for participant data
    - Demo: Returns hardcoded test data (not used in production)

API Endpoint:
    POST /api/admin/v1alpha/participants/{issuer-context-id}/attestations
"""

import json
import logging
import sys
import urllib.error
import urllib.request
from typing import Dict

from config import (
    ATTESTATION_TYPE_DATABASE,
    DB_COLUMN_HOLDER_ID,
    DB_DATASOURCE_NAME,
    DB_TABLE_DATA_PROCESSOR,
    DB_TABLE_MEMBERSHIP,
    HTTP_TIMEOUT_SECONDS,
    Config,
    load_config,
)

logger = logging.getLogger(__name__)


# ============================================================
# ATTESTATION DEFINITION IDs
# ============================================================

ATTESTATION_ID_MEMBERSHIP = "membership-attestation-db"
ATTESTATION_ID_DATA_PROCESSOR = "data-processor-attestation-db"


def create_attestation_definition(
    config: Config, attestation_id: str, attestation_type: str, configuration: Dict
) -> bool:
    """
    Create an attestation definition in the Issuer Service.

    Args:
        config: Configuration instance
        attestation_id: Unique identifier for the attestation
        attestation_type: Type of attestation (e.g., 'database', 'demo')
        configuration: Type-specific configuration dictionary

    Returns:
        True if successful, False otherwise
    """
    url = config.get_attestations_url()
    headers = config.get_headers()

    payload = {
        "id": attestation_id,
        "attestationType": attestation_type,
        "configuration": configuration,
    }

    logger.info(f"Creating attestation definition: {attestation_id}")
    logger.debug(f"  Type: {attestation_type}")
    logger.debug(f"  Config: {json.dumps(configuration, indent=2)}")
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
                logger.info(f"✓ Successfully created attestation: {attestation_id}")
                logger.debug(f"  Response: {response_data}")
                return True
            else:
                logger.warning(
                    f"Unexpected status code {status_code} for {attestation_id}"
                )
                logger.debug(f"  Response: {response_data}")
                return False

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else "No error body"

        # 409 Conflict means attestation already exists - this is OK
        if e.code == 409:
            logger.info(f"✓ Attestation already exists: {attestation_id}")
            return True
        else:
            logger.error(f"✗ HTTP error creating {attestation_id}: {e.code} {e.reason}")
            logger.error(f"  Error body: {error_body}")
            return False

    except urllib.error.URLError as e:
        logger.error(f"✗ URL error creating {attestation_id}: {e.reason}")
        return False

    except Exception as e:
        logger.error(f"✗ Unexpected error creating {attestation_id}: {e}")
        return False


def create_membership_attestation(config: Config) -> bool:
    """
    Create database attestation for membership data.

    This attestation queries the membership_attestations table
    to retrieve participant membership information.

    Args:
        config: Configuration instance

    Returns:
        True if successful, False otherwise
    """
    configuration = {
        "tableName": DB_TABLE_MEMBERSHIP,
        "dataSourceName": DB_DATASOURCE_NAME,
        "idColumn": DB_COLUMN_HOLDER_ID,
    }

    return create_attestation_definition(
        config, ATTESTATION_ID_MEMBERSHIP, ATTESTATION_TYPE_DATABASE, configuration
    )


def create_data_processor_attestation(config: Config) -> bool:
    """
    Create database attestation for data processor capabilities.

    This attestation queries the data_processor_attestations table
    to retrieve participant data processing capabilities.

    Args:
        config: Configuration instance

    Returns:
        True if successful, False otherwise
    """
    configuration = {
        "tableName": DB_TABLE_DATA_PROCESSOR,
        "dataSourceName": DB_DATASOURCE_NAME,
        "idColumn": DB_COLUMN_HOLDER_ID,
    }

    return create_attestation_definition(
        config, ATTESTATION_ID_DATA_PROCESSOR, ATTESTATION_TYPE_DATABASE, configuration
    )


def create_all_attestations(config: Config) -> bool:
    """
    Create all attestation definitions in the Issuer Service.

    Args:
        config: Configuration instance

    Returns:
        True if all attestations created successfully, False otherwise
    """
    attestations = [
        ("Membership Attestation", lambda: create_membership_attestation(config)),
        (
            "Data Processor Attestation",
            lambda: create_data_processor_attestation(config),
        ),
    ]

    logger.info(f"Creating {len(attestations)} attestation definitions...")

    success_count = 0
    failure_count = 0

    for name, create_func in attestations:
        logger.info(f"Processing: {name}")
        if create_func():
            success_count += 1
        else:
            failure_count += 1

    logger.info(f"Attestation creation complete:")
    logger.info(f"  ✓ Success: {success_count}")
    logger.info(f"  ✗ Failed: {failure_count}")

    return failure_count == 0


def main() -> int:
    """
    Main entry point for attestation creation script.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    logger.info("=" * 60)
    logger.info("Issuer Service - Create Attestation Definitions")
    logger.info("=" * 60)

    # Load configuration
    config = load_config()
    if not config:
        logger.error("Failed to load configuration")
        return 1

    # Create attestations
    if create_all_attestations(config):
        logger.info("✓ All attestations created successfully")
        return 0
    else:
        logger.error("✗ Some attestations failed to create")
        return 1


if __name__ == "__main__":
    sys.exit(main())
