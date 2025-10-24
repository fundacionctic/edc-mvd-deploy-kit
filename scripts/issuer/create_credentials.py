"""Create credential definitions in Issuer Service.

This script creates credential definitions that specify how to generate
verifiable credentials from attestation data.

Credential Types:
    - MembershipCredential: Proves dataspace membership (REQUIRED for MVD)
    - DataProcessorCredential: Attests to data processing capabilities (REQUIRED for MVD)

API Endpoint:
    POST /api/admin/v1alpha/participants/{issuer-context-id}/credentialdefinitions
"""

import logging
import sys
from typing import Dict, List

from create_attestations import ATTESTATION_ID_DATA_PROCESSOR, ATTESTATION_ID_MEMBERSHIP
from http_utils import make_request

from config import (
    CREDENTIAL_FORMAT_JWT,
    CREDENTIAL_TYPE_DATA_PROCESSOR,
    CREDENTIAL_TYPE_MEMBERSHIP,
    Config,
    load_config,
)

logger = logging.getLogger(__name__)


CREDENTIAL_DEF_ID_MEMBERSHIP = "membership-credential-def"
CREDENTIAL_DEF_ID_DATA_PROCESSOR = "data-processor-credential-def"


def create_credential_definition(
    config: Config,
    credential_def_id: str,
    credential_type: str,
    attestation_ids: List[str],
    mappings: List[Dict],
    rules: List[Dict] = None,
) -> bool:
    """Create a credential definition in the Issuer Service."""
    payload = {
        "id": credential_def_id,
        "credentialType": credential_type,
        "attestations": attestation_ids,
        "jsonSchema": "{}",
        "jsonSchemaUrl": f"https://example.com/schema/{credential_type.lower()}.json",
        "mappings": mappings,
        "rules": rules or [],
        "format": CREDENTIAL_FORMAT_JWT,
    }

    logger.info(f"Creating credential definition: {credential_def_id}")
    logger.debug(f"Type: {credential_type}, Attestations: {attestation_ids}")

    success, _, _ = make_request(
        url=config.get_credentials_url(),
        headers=config.get_headers(),
        method="POST",
        data=payload,
        entity_name=f"credential {credential_def_id}",
    )
    return success


def create_membership_credential(config: Config) -> bool:
    """Create MembershipCredential definition."""
    mappings = [
        {
            "input": "membership_type",
            "output": "credentialSubject.membershipType",
            "required": True,
        },
        {
            "input": "membership_start_date",
            "output": "credentialSubject.membershipStartDate",
            "required": True,
        },
        {"input": "holder_id", "output": "credentialSubject.id", "required": True},
    ]
    return create_credential_definition(
        config,
        CREDENTIAL_DEF_ID_MEMBERSHIP,
        CREDENTIAL_TYPE_MEMBERSHIP,
        [ATTESTATION_ID_MEMBERSHIP],
        mappings,
    )


def create_data_processor_credential(config: Config) -> bool:
    """Create DataProcessorCredential definition."""
    mappings = [
        {
            "input": "contract_version",
            "output": "credentialSubject.contractVersion",
            "required": True,
        },
        {
            "input": "processing_level",
            "output": "credentialSubject.level",
            "required": True,
        },
        {"input": "holder_id", "output": "credentialSubject.id", "required": True},
    ]
    return create_credential_definition(
        config,
        CREDENTIAL_DEF_ID_DATA_PROCESSOR,
        CREDENTIAL_TYPE_DATA_PROCESSOR,
        [ATTESTATION_ID_DATA_PROCESSOR],
        mappings,
    )


def create_all_credentials(config: Config) -> bool:
    """Create all credential definitions in the Issuer Service."""
    credentials = [
        ("MembershipCredential", create_membership_credential),
        ("DataProcessorCredential", create_data_processor_credential),
    ]

    logger.info(f"Creating {len(credentials)} credential definitions...")

    results = [create_func(config) for name, create_func in credentials]
    success_count = sum(results)
    failure_count = len(results) - success_count

    logger.info(f"Credential creation complete: ✓ {success_count}, ✗ {failure_count}")
    return failure_count == 0


def main() -> int:
    """Main entry point for credential definition creation script."""
    logger.info("=" * 60)
    logger.info("Issuer Service - Create Credential Definitions")
    logger.info("=" * 60)

    config = load_config()
    if not config:
        logger.error("Failed to load configuration")
        return 1

    if create_all_credentials(config):
        logger.info("✓ All credential definitions created successfully")
        return 0
    logger.error("✗ Some credential definitions failed to create")
    return 1


if __name__ == "__main__":
    sys.exit(main())
