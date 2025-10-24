"""Create attestation definitions in Issuer Service.

This script creates attestation definitions that specify how the Issuer Service
retrieves evidence/claims data when issuing credentials.

Attestation Types:
    - Database: Queries PostgreSQL tables for participant data

API Endpoint:
    POST /api/admin/v1alpha/participants/{issuer-context-id}/attestations
"""

import logging
import sys
from typing import Dict

from http_utils import make_request

from config import (
    ATTESTATION_TYPE_DATABASE,
    DB_COLUMN_HOLDER_ID,
    DB_DATASOURCE_NAME,
    DB_TABLE_DATA_PROCESSOR,
    DB_TABLE_MEMBERSHIP,
    Config,
    load_config,
)

logger = logging.getLogger(__name__)


ATTESTATION_ID_MEMBERSHIP = "membership-attestation-db"
ATTESTATION_ID_DATA_PROCESSOR = "data-processor-attestation-db"


def create_attestation_definition(
    config: Config, attestation_id: str, attestation_type: str, configuration: Dict
) -> bool:
    """Create an attestation definition in the Issuer Service."""
    payload = {
        "id": attestation_id,
        "attestationType": attestation_type,
        "configuration": configuration,
    }

    logger.info(f"Creating attestation definition: {attestation_id}")
    logger.debug(f"Type: {attestation_type}")

    success, _, _ = make_request(
        url=config.get_attestations_url(),
        headers=config.get_headers(),
        method="POST",
        data=payload,
        entity_name=f"attestation {attestation_id}",
    )
    return success


def create_membership_attestation(config: Config) -> bool:
    """Create database attestation for membership data."""
    configuration = {
        "tableName": DB_TABLE_MEMBERSHIP,
        "dataSourceName": DB_DATASOURCE_NAME,
        "idColumn": DB_COLUMN_HOLDER_ID,
    }
    return create_attestation_definition(
        config, ATTESTATION_ID_MEMBERSHIP, ATTESTATION_TYPE_DATABASE, configuration
    )


def create_data_processor_attestation(config: Config) -> bool:
    """Create database attestation for data processor capabilities."""
    configuration = {
        "tableName": DB_TABLE_DATA_PROCESSOR,
        "dataSourceName": DB_DATASOURCE_NAME,
        "idColumn": DB_COLUMN_HOLDER_ID,
    }
    return create_attestation_definition(
        config, ATTESTATION_ID_DATA_PROCESSOR, ATTESTATION_TYPE_DATABASE, configuration
    )


def create_all_attestations(config: Config) -> bool:
    """Create all attestation definitions in the Issuer Service."""
    attestations = [
        ("Membership", create_membership_attestation),
        ("Data Processor", create_data_processor_attestation),
    ]

    logger.info(f"Creating {len(attestations)} attestation definitions...")

    results = [create_func(config) for name, create_func in attestations]
    success_count = sum(results)
    failure_count = len(results) - success_count

    logger.info(f"Attestation creation complete: ✓ {success_count}, ✗ {failure_count}")
    return failure_count == 0


def main() -> int:
    """Main entry point for attestation creation script."""
    logger.info("=" * 60)
    logger.info("Issuer Service - Create Attestation Definitions")
    logger.info("=" * 60)

    config = load_config()
    if not config:
        logger.error("Failed to load configuration")
        return 1

    if create_all_attestations(config):
        logger.info("✓ All attestations created successfully")
        return 0
    logger.error("✗ Some attestations failed to create")
    return 1


if __name__ == "__main__":
    sys.exit(main())
