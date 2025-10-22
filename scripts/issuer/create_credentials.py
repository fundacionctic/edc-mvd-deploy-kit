"""
Create Credential Definitions in Issuer Service

This script creates credential definitions that specify how to generate
verifiable credentials from attestation data.

Credential Types:
    - MembershipCredential: Proves dataspace membership (REQUIRED for MVD)
    - DataProcessorCredential: Attests to data processing capabilities (REQUIRED for MVD)

API Endpoint:
    POST /api/admin/v1alpha/participants/{issuer-context-id}/credentialdefinitions
"""

import json
import logging
import sys
import urllib.error
import urllib.request
from typing import Dict, List

from create_attestations import ATTESTATION_ID_DATA_PROCESSOR, ATTESTATION_ID_MEMBERSHIP

from config import (
    CREDENTIAL_FORMAT_JWT,
    CREDENTIAL_TYPE_DATA_PROCESSOR,
    CREDENTIAL_TYPE_MEMBERSHIP,
    HTTP_TIMEOUT_SECONDS,
    Config,
    load_config,
)

logger = logging.getLogger(__name__)


# ============================================================
# CREDENTIAL DEFINITION IDs
# ============================================================

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
    """
    Create a credential definition in the Issuer Service.

    Args:
        config: Configuration instance
        credential_def_id: Unique identifier for the credential definition
        credential_type: Type of credential (e.g., 'MembershipCredential')
        attestation_ids: List of attestation IDs to use as data sources
        mappings: List of field mappings from attestations to credential claims
        rules: Optional list of validation rules

    Returns:
        True if successful, False otherwise
    """
    url = config.get_credentials_url()
    headers = config.get_headers()

    payload = {
        "id": credential_def_id,
        "credentialType": credential_type,
        "attestations": attestation_ids,
        "jsonSchema": "{}",
        "jsonSchemaUrl": f"https://example.com/schema/{credential_type.lower()}.json",
        "mappings": mappings,
        "rules": rules if rules else [],
        "format": CREDENTIAL_FORMAT_JWT,
    }

    logger.info(f"Creating credential definition: {credential_def_id}")
    logger.debug(f"  Type: {credential_type}")
    logger.debug(f"  Attestations: {attestation_ids}")
    logger.debug(f"  Mappings: {len(mappings)} fields")
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
                logger.info(f"✓ Successfully created credential: {credential_def_id}")
                logger.debug(f"  Response: {response_data}")
                return True
            else:
                logger.warning(
                    f"Unexpected status code {status_code} for {credential_def_id}"
                )
                logger.debug(f"  Response: {response_data}")
                return False

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else "No error body"

        # 409 Conflict means credential definition already exists - this is OK
        if e.code == 409:
            logger.info(f"✓ Credential definition already exists: {credential_def_id}")
            return True
        else:
            logger.error(
                f"✗ HTTP error creating {credential_def_id}: {e.code} {e.reason}"
            )
            logger.error(f"  Error body: {error_body}")
            return False

    except urllib.error.URLError as e:
        logger.error(f"✗ URL error creating {credential_def_id}: {e.reason}")
        return False

    except Exception as e:
        logger.error(f"✗ Unexpected error creating {credential_def_id}: {e}")
        return False


def create_membership_credential(config: Config) -> bool:
    """
    Create MembershipCredential definition.

    This credential proves that a participant is a member of the dataspace.
    It is REQUIRED for all DSP protocol interactions in the MVD.

    Mappings:
        - membership_type → credentialSubject.membershipType
        - membership_start_date → credentialSubject.membershipStartDate
        - holder_id → credentialSubject.id

    Args:
        config: Configuration instance

    Returns:
        True if successful, False otherwise
    """
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
    """
    Create DataProcessorCredential definition.

    This credential attests to a participant's data processing capabilities
    and security levels. It is REQUIRED for contract negotiation based on
    data sensitivity in the MVD.

    Mappings:
        - contract_version → credentialSubject.contractVersion
        - processing_level → credentialSubject.level
        - holder_id → credentialSubject.id

    Args:
        config: Configuration instance

    Returns:
        True if successful, False otherwise
    """
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
    """
    Create all credential definitions in the Issuer Service.

    Args:
        config: Configuration instance

    Returns:
        True if all credentials created successfully, False otherwise
    """
    credentials = [
        ("MembershipCredential", lambda: create_membership_credential(config)),
        ("DataProcessorCredential", lambda: create_data_processor_credential(config)),
    ]

    logger.info(f"Creating {len(credentials)} credential definitions...")

    success_count = 0
    failure_count = 0

    for name, create_func in credentials:
        logger.info(f"Processing: {name}")
        if create_func():
            success_count += 1
        else:
            failure_count += 1

    logger.info(f"Credential definition creation complete:")
    logger.info(f"  ✓ Success: {success_count}")
    logger.info(f"  ✗ Failed: {failure_count}")

    return failure_count == 0


def main() -> int:
    """
    Main entry point for credential definition creation script.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    logger.info("=" * 60)
    logger.info("Issuer Service - Create Credential Definitions")
    logger.info("=" * 60)

    # Load configuration
    config = load_config()
    if not config:
        logger.error("Failed to load configuration")
        return 1

    # Create credential definitions
    if create_all_credentials(config):
        logger.info("✓ All credential definitions created successfully")
        return 0
    else:
        logger.error("✗ Some credential definitions failed to create")
        return 1


if __name__ == "__main__":
    sys.exit(main())
