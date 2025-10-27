#!/usr/bin/env python3
"""
Request Credentials from Issuer Service

This script requests verifiable credentials from the Issuer service for the
provider participant. It assumes the participant context has already been
registered via register_provider_participant.py.

Prerequisites:
- Provider participant must be registered in Identity Hub
- Issuer service must be running and seeded with participant holders
- Provider must be seeded as a holder in the Issuer database

This script ONLY requests credentials - it does not handle participant registration
or key management, which are handled by separate scripts.
"""

import json
import logging
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import List

from config import load_config

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# HTTP timeout
HTTP_TIMEOUT = 30

# Polling configuration
POLL_MAX_ATTEMPTS = 30
POLL_INTERVAL_SECONDS = 2

# Credential types and their definition IDs
CREDENTIAL_TYPE_MEMBERSHIP = "MembershipCredential"
CREDENTIAL_TYPE_DATA_PROCESSOR = "DataProcessorCredential"

# Credential definition IDs (must match those registered in issuer service)
CREDENTIAL_DEF_ID_MEMBERSHIP = "membership-credential-def"
CREDENTIAL_DEF_ID_DATA_PROCESSOR = "data-processor-credential-def"

# Mapping of credential types to their definition IDs
CREDENTIAL_TYPE_TO_DEF_ID = {
    CREDENTIAL_TYPE_MEMBERSHIP: CREDENTIAL_DEF_ID_MEMBERSHIP,
    CREDENTIAL_TYPE_DATA_PROCESSOR: CREDENTIAL_DEF_ID_DATA_PROCESSOR,
}

# API paths
API_PATH_IDENTITY_PARTICIPANTS = "/api/identity/v1alpha/participants/"
API_PATH_CREDENTIALS_REQUEST = "/credentials/request"


def poll_credential_status(config, status_url: str) -> bool:
    """
    Poll credential request status until issued or timeout.

    Args:
        config: Configuration object
        status_url: URL to poll for credential status

    Returns:
        True if credentials were issued, False otherwise
    """
    headers = config.get_identity_superuser_headers()

    for attempt in range(1, POLL_MAX_ATTEMPTS + 1):
        logger.debug(f"Polling attempt {attempt}/{POLL_MAX_ATTEMPTS}...")

        try:
            request = urllib.request.Request(status_url, headers=headers, method="GET")

            with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
                status_data = json.loads(response.read().decode("utf-8"))
                logger.debug(f"Status response: {json.dumps(status_data, indent=2)}")

                status = status_data.get("status")
                logger.info(f"Credential request status: {status}")

                if status == "ISSUED":
                    logger.info("✅ Credentials have been issued successfully")
                    return True
                elif status in ["FAILED", "REJECTED"]:
                    logger.error(f"❌ Credential request failed with status: {status}")
                    return False
                else:
                    logger.debug(
                        f"Status is '{status}', waiting {POLL_INTERVAL_SECONDS}s before next poll..."
                    )
                    time.sleep(POLL_INTERVAL_SECONDS)

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else "No error details"
            logger.error(f"❌ HTTP {e.code} error polling credential status")
            logger.error(f"Response: {error_body}")
            return False
        except urllib.error.URLError as e:
            logger.error(f"❌ Network error polling credential status: {e.reason}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error polling credential status: {e}")
            return False

    logger.error(
        f"❌ Credential status polling timed out after {POLL_MAX_ATTEMPTS} attempts"
    )
    return False


def request_credentials_from_issuer(
    config, participant_did: str, issuer_did: str, credential_types: List[str]
) -> bool:
    """
    Request credentials from issuer via Identity Hub.

    This uses the Identity Hub credential request mechanism to request
    verifiable credentials from the issuer service. The issuer will sign
    and issue the credentials.

    Args:
        config: Configuration object
        participant_did: Participant DID requesting credentials
        issuer_did: Issuer DID that will sign credentials
        credential_types: List of credential types to request

    Returns:
        True if successful, False otherwise
    """
    # Base64 encode the participant DID for URL
    import base64

    participant_id_base64 = (
        base64.urlsafe_b64encode(participant_did.encode("utf-8"))
        .decode("utf-8")
        .rstrip("=")
    )

    url = f"{config.provider_ih_identity_url}{API_PATH_IDENTITY_PARTICIPANTS}{participant_id_base64}{API_PATH_CREDENTIALS_REQUEST}"

    credentials = [
        {
            "format": "VC1_0_JWT",
            "type": cred_type,
            "id": CREDENTIAL_TYPE_TO_DEF_ID[cred_type],
        }
        for cred_type in credential_types
    ]

    payload = {
        "issuerDid": issuer_did,
        "holderPid": "credential-request-1",
        "credentials": credentials,
    }

    headers = config.get_identity_superuser_headers()

    logger.info(f"Requesting credentials from issuer: {issuer_did}")
    logger.info(f"Credential types: {', '.join(credential_types)}")
    logger.debug(f"POST {url}")
    logger.debug(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
            response_data = response.read().decode("utf-8")
            response_headers = dict(response.headers)
            logger.info("✅ Credentials requested successfully")
            logger.debug(f"Response headers: {json.dumps(response_headers, indent=2)}")
            logger.debug(f"Response: {response_data}")

            # Check for Location header to poll status
            location_url = response_headers.get("Location")
            if location_url:
                # Fix Location URL by prepending /api/identity if needed
                # The Location header from the API doesn't include the context path
                if location_url.startswith("http://"):
                    # Extract the path part and prepend /api/identity
                    from urllib.parse import urlparse

                    parsed = urlparse(location_url)
                    fixed_path = f"/api/identity{parsed.path}"
                    location_url = f"{parsed.scheme}://{parsed.netloc}{fixed_path}"
                elif location_url.startswith("/v1alpha"):
                    # Relative path - prepend /api/identity
                    location_url = f"{config.provider_ih_identity_url}{location_url}"

                logger.info(f"Polling credential status at: {location_url}")
                if not poll_credential_status(config, location_url):
                    logger.warning(
                        "Credential status polling did not complete successfully"
                    )
                    return False
            else:
                logger.warning("No Location header in response - cannot poll status")

            return True

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else "No error details"
        logger.error(f"❌ HTTP {e.code} error requesting credentials")
        logger.error(f"Response: {error_body}")
        return False
    except urllib.error.URLError as e:
        logger.error(f"❌ Network error requesting credentials: {e.reason}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error requesting credentials: {e}")
        return False


def main():
    """Main entry point."""
    # Load configuration
    config = load_config()
    if not config:
        logger.error("Failed to load configuration")
        return 1

    logger.info(
        "=" * 60 + "\n" +
        "Request Credentials from Issuer Service\n" +
        "=" * 60 + "\n\n" +
        "Prerequisites:\n"
        "  ✓ Provider participant registered in Identity Hub\n"
        "  ✓ Issuer service running and seeded\n"
        "  ✓ Provider seeded as holder in Issuer database\n"
    )

    # Get participant DID from configuration
    participant_did = config.provider_did

    # Construct issuer DID
    # Issuer uses DID API port, so we need to URL encode it
    issuer_host_with_port = f"{config.issuer_public_host}:{config.issuer_did_api_port}"
    encoded_issuer_host = urllib.parse.quote(issuer_host_with_port, safe="")
    issuer_did = f"did:web:{encoded_issuer_host}"

    logger.info(f"Provider DID: {participant_did}\n" f"Issuer DID: {issuer_did}\n")

    # Request credentials from issuer
    credential_types = [CREDENTIAL_TYPE_MEMBERSHIP, CREDENTIAL_TYPE_DATA_PROCESSOR]

    logger.info("=" * 30 + "\nRequesting Credentials from Issuer")

    if not request_credentials_from_issuer(
        config, participant_did, issuer_did, credential_types
    ):
        logger.error(
            "Failed to request credentials from issuer\n\n"
            "Troubleshooting:\n"
            "  1. Verify provider participant is registered:\n"
            "     python3 scripts/provider/register_provider_participant.py\n"
            "  2. Verify issuer is running and seeded:\n"
            "     task issuer:verify\n"
            "  3. Check Identity Hub logs:\n"
            "     docker logs mvd-provider-identityhub"
        )
        return 1

    logger.info(
        "\n" + "=" * 60 + "\n" +
        "✅ Credentials Requested Successfully\n" +
        "=" * 60 + "\n\n" +
        "The credentials have been requested from the Issuer service.\n"
        "The Issuer will sign and issue the credentials."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
