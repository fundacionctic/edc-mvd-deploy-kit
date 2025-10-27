#!/usr/bin/env python3
"""
End-to-End Test for Minimum Viable Dataspace

This script performs a complete E2E test of the dataspace following the test
procedure outlined in E2E_TEST_GUIDE.md. It validates that all prerequisites
are met and executes a full data space transaction including catalog discovery,
contract negotiation, data transfer, and data access.

Prerequisites:
    - Issuer service deployed and seeded
    - Provider participant deployed and seeded
    - Assets, policies, and contract definitions created
    - Verifiable credentials issued to provider

Test Flow:
    Phase 1: Catalog Discovery - Request catalog and extract asset/policy IDs
    Phase 2: Contract Negotiation - Negotiate contract until FINALIZED
    Phase 3: Transfer Process - Initiate transfer until STARTED
    Phase 4: Data Access - Retrieve EDR and access data via dataplane

Usage:
    python3 scripts/provider/e2e_test.py [--skip-prerequisites] [--asset-id ASSET_ID]

    Or using Task automation:
        task e2e:test
        task e2e:test-verbose
        ASSET_ID=asset-2 task e2e:test-asset

Options:
    --skip-prerequisites  Skip prerequisite checks (not recommended)
    --asset-id ASSET_ID   Target specific asset ID (default: asset-1)
    --verbose            Enable verbose output

Environment Variables:
    All configuration from .env file (see .env.example for reference)
    Key variables:
        PROVIDER_CP_MANAGEMENT_PORT: Management API port (default: 8081)
        PROVIDER_CP_PROTOCOL_PORT: DSP protocol port (default: 8082)
        PROVIDER_DP_PUBLIC_PORT: Data plane public API port (default: 11002)
        PROVIDER_MANAGEMENT_API_KEY: Management API key (default: password)
"""

import argparse
import json
import logging
import sys
import time
from typing import Dict, Optional, Tuple

from http_utils import make_http_request

from config import load_config

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# ============================================================
# CONSTANTS
# ============================================================

# Polling configuration (from E2E_TEST_GUIDE.md recommendations)
POLL_MAX_ATTEMPTS = 60  # Max 2 minutes (60 * 2s)
POLL_INTERVAL_SECONDS = 2

# DSP Protocol
DSP_PROTOCOL = "dataspace-protocol-http"

# JSON-LD context
EDC_CONTEXT = {"edc": "https://w3id.org/edc/v0.0.1/ns/"}

# Expected asset ID for testing (from seed_participant.py)
DEFAULT_TARGET_ASSET_ID = "asset-1"

# Contract negotiation states
STATE_FINALIZED = "FINALIZED"
STATE_TERMINATED = "TERMINATED"

# Transfer process states
STATE_STARTED = "STARTED"


# ============================================================
# PREREQUISITE CHECKS
# ============================================================


def check_service_health(config) -> bool:
    """
    Check that all required services are healthy.

    Args:
        config: Configuration object

    Returns:
        True if all services are healthy, False otherwise
    """
    logger.info("Checking service health...")

    # Use public host with ports from config
    health_urls = {
        "Control Plane": f"http://{config.provider_public_host}:{config.provider_cp_web_port}/api/check/health",
        "Data Plane": f"http://{config.provider_public_host}:{config.provider_dp_web_port}/api/check/health",
        "Identity Hub": f"http://{config.provider_public_host}:{config.provider_ih_web_port}/api/check/health",
    }

    all_healthy = True

    for service_name, health_url in health_urls.items():
        success, status_code, response = make_http_request(health_url, "GET")

        if success and status_code == 200:
            logger.info(f"✅ {service_name} is healthy")
        else:
            logger.error(f"❌ {service_name} is not healthy: {status_code}")
            all_healthy = False

    if not all_healthy:
        logger.error(
            "\n❌ Service health check failed\n"
            "Please ensure all services are running:\n"
            "  task provider:status\n"
            "  docker ps\n"
        )

    return all_healthy


def check_assets_exist(config) -> bool:
    """
    Verify that assets have been seeded.

    Args:
        config: Configuration object

    Returns:
        True if assets exist, False otherwise
    """
    logger.info("Checking if assets are seeded...")

    # Use public host from config
    url = f"http://{config.provider_public_host}:{config.provider_cp_management_port}/api/management/v3/assets/request"
    headers = config.get_management_headers()

    query_body = json.dumps(
        {"@context": EDC_CONTEXT, "@type": "QuerySpec", "limit": 50}
    )

    success, status_code, response = make_http_request(url, "POST", headers, query_body)

    if success and status_code == 200:
        try:
            assets = json.loads(response)
            if isinstance(assets, list) and len(assets) > 0:
                logger.info(f"✅ Found {len(assets)} assets")
                return True
            else:
                logger.error("❌ No assets found")
                return False
        except json.JSONDecodeError:
            logger.error("❌ Failed to parse assets response")
            return False
    else:
        logger.error(f"❌ Failed to query assets: {status_code}")
        return False


def check_policies_exist(config) -> bool:
    """
    Verify that policy definitions have been created.

    Args:
        config: Configuration object

    Returns:
        True if policies exist, False otherwise
    """
    logger.info("Checking if policies are configured...")

    # Use public host from config
    url = f"http://{config.provider_public_host}:{config.provider_cp_management_port}/api/management/v3/policydefinitions/request"
    headers = config.get_management_headers()

    query_body = json.dumps(
        {"@context": EDC_CONTEXT, "@type": "QuerySpec", "limit": 50}
    )

    success, status_code, response = make_http_request(url, "POST", headers, query_body)

    if success and status_code == 200:
        try:
            policies = json.loads(response)
            if isinstance(policies, list) and len(policies) > 0:
                logger.info(f"✅ Found {len(policies)} policy definitions")
                return True
            else:
                logger.error("❌ No policies found")
                return False
        except json.JSONDecodeError:
            logger.error("❌ Failed to parse policies response")
            return False
    else:
        logger.error(f"❌ Failed to query policies: {status_code}")
        return False


def check_contract_definitions_exist(config) -> bool:
    """
    Verify that contract definitions have been created.

    Args:
        config: Configuration object

    Returns:
        True if contract definitions exist, False otherwise
    """
    logger.info("Checking if contract definitions are configured...")

    # Use public host from config
    url = f"http://{config.provider_public_host}:{config.provider_cp_management_port}/api/management/v3/contractdefinitions/request"
    headers = config.get_management_headers()

    query_body = json.dumps(
        {"@context": EDC_CONTEXT, "@type": "QuerySpec", "limit": 50}
    )

    success, status_code, response = make_http_request(url, "POST", headers, query_body)

    if success and status_code == 200:
        try:
            contracts = json.loads(response)
            if isinstance(contracts, list) and len(contracts) > 0:
                logger.info(f"✅ Found {len(contracts)} contract definitions")
                return True
            else:
                logger.error("❌ No contract definitions found")
                return False
        except json.JSONDecodeError:
            logger.error("❌ Failed to parse contract definitions response")
            return False
    else:
        logger.error(f"❌ Failed to query contract definitions: {status_code}")
        return False


def check_dataplane_available(config) -> bool:
    """
    Verify that dataplane is registered and available.

    Args:
        config: Configuration object

    Returns:
        True if dataplane is available, False otherwise
    """
    logger.info("Checking if dataplane is available...")

    url = f"http://{config.provider_public_host}:{config.provider_cp_management_port}/api/management/v3/dataplanes"
    headers = config.get_management_headers()

    success, status_code, response = make_http_request(url, "GET", headers)

    if success and status_code == 200:
        try:
            data = json.loads(response)
            if isinstance(data, list) and len(data) > 0:
                state = data[0].get("state", "UNKNOWN")
                if state == "AVAILABLE":
                    logger.info("✅ Dataplane is available")
                    return True
                else:
                    logger.error(f"❌ Dataplane state is {state}, expected AVAILABLE")
                    return False
            else:
                logger.error("❌ No dataplane registered")
                return False
        except json.JSONDecodeError:
            logger.error("❌ Invalid response from dataplane endpoint")
            return False
    else:
        logger.error(f"❌ Failed to query dataplane status: {status_code}")
        return False


def check_prerequisites(config) -> bool:
    """
    Check all prerequisites for E2E testing.

    Args:
        config: Configuration object

    Returns:
        True if all prerequisites are met, False otherwise
    """
    logger.info("=" * 60)
    logger.info("PHASE 0: PREREQUISITE VERIFICATION")
    logger.info("=" * 60)

    checks = [
        ("Service Health", check_service_health),
        ("Assets Seeded", check_assets_exist),
        ("Policies Configured", check_policies_exist),
        ("Contract Definitions Configured", check_contract_definitions_exist),
        ("Dataplane Available", check_dataplane_available),
    ]

    all_passed = True

    for check_name, check_func in checks:
        logger.info(f"\n--- {check_name} ---")
        try:
            if not check_func(config):
                logger.error(f"❌ {check_name} check failed")
                all_passed = False
        except Exception as e:
            logger.error(f"❌ {check_name} check failed with exception: {e}")
            all_passed = False

    if all_passed:
        logger.info("\n✅ All prerequisite checks passed\n")
    else:
        logger.error(
            "\n❌ Prerequisite checks failed\n"
            "Please resolve the issues above before running E2E test:\n"
            "  1. Ensure services are running: task provider:up\n"
            "  2. Seed the provider: task provider:seed\n"
            "  3. Request credentials: task provider:request-credentials\n"
        )

    return all_passed


# ============================================================
# PHASE 1: CATALOG DISCOVERY
# ============================================================


def request_catalog(config) -> Optional[Dict]:
    """
    Request catalog from provider (Phase 1).

    Following E2E_TEST_GUIDE.md Phase 1: Catalog Discovery

    Args:
        config: Configuration object

    Returns:
        Catalog response or None on failure
    """
    logger.info("Requesting catalog from provider...")

    # Use public host from config
    url = f"http://{config.provider_public_host}:{config.provider_cp_management_port}/api/management/v3/catalog/request"
    headers = config.get_management_headers()

    # Catalog request format from E2E_TEST_GUIDE.md
    catalog_request = json.dumps(
        {
            "@context": EDC_CONTEXT,
            "@type": "CatalogRequest",
            "counterPartyAddress": f"http://{config.provider_public_host}:{config.provider_cp_protocol_port}/api/dsp",
            "counterPartyId": config.provider_did,
            "protocol": DSP_PROTOCOL,
            "querySpec": {"filterExpression": []},
        }
    )

    success, status_code, response = make_http_request(
        url, "POST", headers, catalog_request
    )

    if success and status_code == 200:
        try:
            catalog = json.loads(response)
            logger.info("✅ Catalog retrieved successfully")
            logger.debug(f"Catalog: {json.dumps(catalog, indent=2)}")
            return catalog
        except json.JSONDecodeError:
            logger.error("❌ Failed to parse catalog response")
            return None
    else:
        logger.error(f"❌ Failed to retrieve catalog: {status_code}")
        if response:
            logger.debug(f"Response: {response}")
        return None


def extract_offer_from_catalog(
    catalog: Dict, target_asset_id: str
) -> Optional[Tuple[str, Dict]]:
    """
    Extract asset ID and full policy from catalog for target asset.

    Following E2E_TEST_GUIDE.md Step 1.2: Parse Catalog Response

    Args:
        catalog: Catalog response from provider
        target_asset_id: Asset ID to find in catalog

    Returns:
        Tuple of (asset_id, policy_dict) or None if not found
    """
    logger.info(f"Searching for asset '{target_asset_id}' in catalog...")

    datasets = catalog.get("dcat:dataset", [])
    if not datasets:
        logger.error("❌ Catalog contains no datasets")
        return None

    # Handle both single dataset (dict) and multiple datasets (list)
    if isinstance(datasets, dict):
        datasets = [datasets]
    elif not isinstance(datasets, list):
        logger.error("❌ Invalid dataset format in catalog")
        return None

    logger.info(f"Catalog contains {len(datasets)} datasets")

    for dataset in datasets:
        asset_id = dataset.get("@id")
        logger.debug(f"Checking dataset: {asset_id}")

        if asset_id == target_asset_id:
            # Extract full policy from odrl:hasPolicy (E2E_TEST_GUIDE.md format)
            policy = dataset.get("odrl:hasPolicy", {})
            policy_id = policy.get("@id")

            if not policy_id:
                logger.error(f"❌ Asset {asset_id} has no policy")
                return None

            logger.info(f"✅ Found asset: {asset_id}")
            logger.info(f"✅ Policy ID: {policy_id}")
            return asset_id, policy

    logger.error(
        f"❌ Asset '{target_asset_id}' not found in catalog\n"
        f"Available assets: {[ds.get('@id') for ds in datasets]}"
    )
    return None


def phase_1_catalog_discovery(
    config, target_asset_id: str
) -> Optional[Tuple[str, Dict]]:
    """
    Execute Phase 1: Catalog Discovery.

    Args:
        config: Configuration object
        target_asset_id: Asset ID to search for

    Returns:
        Tuple of (asset_id, policy_dict) or None on failure
    """
    logger.info("=" * 60)
    logger.info("PHASE 1: CATALOG DISCOVERY")
    logger.info("=" * 60)

    catalog = request_catalog(config)
    if not catalog:
        return None

    offer = extract_offer_from_catalog(catalog, target_asset_id)
    if not offer:
        return None

    logger.info("\n✅ Phase 1 completed successfully\n")
    return offer


# ============================================================
# PHASE 2: CONTRACT NEGOTIATION
# ============================================================


def initiate_contract_negotiation(
    config, asset_id: str, policy: Dict
) -> Optional[str]:
    """
    Initiate contract negotiation (Phase 2).

    Following E2E_TEST_GUIDE.md Step 2.1: Initiate Contract Negotiation

    Args:
        config: Configuration object
        asset_id: Asset ID from catalog
        policy: Full policy object from catalog

    Returns:
        Negotiation ID or None on failure
    """
    logger.info("Initiating contract negotiation...")

    url = f"http://{config.provider_public_host}:{config.provider_cp_management_port}/api/management/v3/contractnegotiations"
    headers = config.get_management_headers()

    # Contract negotiation request format from E2E_TEST_GUIDE.md
    # Use the policy from catalog but add required fields for negotiation
    negotiation_policy = policy.copy()
    negotiation_policy["odrl:assigner"] = {"@id": config.provider_did}
    negotiation_policy["odrl:target"] = {"@id": asset_id}
    
    negotiation_request = json.dumps(
        {
            "@context": {
                "edc": "https://w3id.org/edc/v0.0.1/ns/",
                "odrl": "http://www.w3.org/ns/odrl/2/"
            },
            "@type": "ContractRequest",
            "counterPartyAddress": f"http://{config.provider_public_host}:{config.provider_cp_protocol_port}/api/dsp",
            "counterPartyId": config.provider_did,
            "protocol": DSP_PROTOCOL,
            "policy": negotiation_policy,
        }
    )

    success, status_code, response = make_http_request(
        url, "POST", headers, negotiation_request
    )

    if success and status_code == 200:
        try:
            result = json.loads(response)
            negotiation_id = result.get("@id")
            logger.info(f"✅ Negotiation initiated: {negotiation_id}")
            return negotiation_id
        except json.JSONDecodeError:
            logger.error("❌ Failed to parse negotiation response")
            return None
    else:
        logger.error(f"❌ Failed to initiate negotiation: {status_code}")
        if response:
            logger.debug(f"Response: {response}")
        return None


def poll_negotiation_status(config, negotiation_id: str) -> Optional[str]:
    """
    Poll negotiation status until FINALIZED or TERMINATED.

    Following E2E_TEST_GUIDE.md Step 2.2: Poll Negotiation Status

    Args:
        config: Configuration object
        negotiation_id: Negotiation ID to poll

    Returns:
        Agreement ID if successful, None otherwise
    """
    logger.info("Polling negotiation status (every 2s, max 2 minutes)...")

    url = f"http://{config.provider_public_host}:{config.provider_cp_management_port}/api/management/v3/contractnegotiations/{negotiation_id}"
    headers = config.get_management_headers()

    for attempt in range(1, POLL_MAX_ATTEMPTS + 1):
        logger.debug(f"Poll attempt {attempt}/{POLL_MAX_ATTEMPTS}")

        success, status_code, response = make_http_request(url, "GET", headers)

        if success and status_code == 200:
            try:
                negotiation = json.loads(response)
                state = negotiation.get("state")
                logger.info(f"Negotiation state: {state}")

                if state == STATE_FINALIZED:
                    agreement_id = negotiation.get("contractAgreementId")
                    logger.info(f"✅ Negotiation finalized: {agreement_id}")
                    return agreement_id
                elif state == STATE_TERMINATED:
                    logger.error(
                        "❌ Negotiation terminated\n"
                        "Possible causes (from E2E_TEST_GUIDE.md):\n"
                        "  - Policy evaluation failed\n"
                        "  - Missing or invalid credentials\n"
                        "  - DID resolution failed\n"
                        "Check logs: docker logs mvd-provider-controlplane"
                    )
                    return None
                else:
                    # Still in progress (REQUESTING, REQUESTED, AGREEING, etc.)
                    time.sleep(POLL_INTERVAL_SECONDS)

            except json.JSONDecodeError:
                logger.error("❌ Failed to parse negotiation status")
                return None
        else:
            logger.error(f"❌ Failed to query negotiation: {status_code}")
            return None

    logger.error(
        f"❌ Negotiation polling timed out after {POLL_MAX_ATTEMPTS * POLL_INTERVAL_SECONDS} seconds"
    )
    return None


def phase_2_contract_negotiation(
    config, asset_id: str, policy: Dict
) -> Optional[str]:
    """
    Execute Phase 2: Contract Negotiation.

    Args:
        config: Configuration object
        asset_id: Asset ID from catalog
        policy: Full policy object from catalog

    Returns:
        Agreement ID or None on failure
    """
    logger.info("=" * 60)
    logger.info("PHASE 2: CONTRACT NEGOTIATION")
    logger.info("=" * 60)

    negotiation_id = initiate_contract_negotiation(config, asset_id, policy)
    if not negotiation_id:
        return None

    agreement_id = poll_negotiation_status(config, negotiation_id)
    if not agreement_id:
        return None

    logger.info("\n✅ Phase 2 completed successfully\n")
    return agreement_id


# ============================================================
# PHASE 3: TRANSFER PROCESS
# ============================================================


def initiate_transfer_process(
    config, asset_id: str, agreement_id: str
) -> Optional[str]:
    """
    Initiate transfer process (Phase 3).

    Following E2E_TEST_GUIDE.md Step 3.1: Initiate Transfer

    Args:
        config: Configuration object
        asset_id: Asset ID from catalog
        agreement_id: Agreement ID from negotiation

    Returns:
        Transfer process ID or None on failure
    """
    logger.info("Initiating transfer process...")

    url = f"http://{config.provider_public_host}:{config.provider_cp_management_port}/api/management/v3/transferprocesses"
    headers = config.get_management_headers()

    # Transfer request format from E2E_TEST_GUIDE.md (HttpProxy type)
    transfer_request = json.dumps(
        {
            "@context": EDC_CONTEXT,
            "@type": "TransferRequest",
            "counterPartyAddress": f"http://{config.provider_public_host}:{config.provider_cp_protocol_port}/api/dsp",
            "counterPartyId": config.provider_did,
            "contractId": agreement_id,
            "assetId": asset_id,
            "protocol": DSP_PROTOCOL,
            "transferType": "HttpData-PULL",
            "dataDestination": {"@type": "DataAddress", "type": "HttpProxy"},
        }
    )

    success, status_code, response = make_http_request(
        url, "POST", headers, transfer_request
    )

    if success and status_code == 200:
        try:
            result = json.loads(response)
            transfer_id = result.get("@id")
            logger.info(f"✅ Transfer initiated: {transfer_id}")
            return transfer_id
        except json.JSONDecodeError:
            logger.error("❌ Failed to parse transfer response")
            return None
    else:
        logger.error(f"❌ Failed to initiate transfer: {status_code}")
        if response:
            logger.debug(f"Response: {response}")
        return None


def poll_transfer_status(config, transfer_id: str) -> bool:
    """
    Poll transfer status until STARTED or TERMINATED.

    Following E2E_TEST_GUIDE.md Step 3.2: Poll Transfer Status

    Args:
        config: Configuration object
        transfer_id: Transfer process ID to poll

    Returns:
        True if transfer started, False otherwise
    """
    logger.info("Polling transfer status (every 2s, max 2 minutes)...")

    url = f"http://{config.provider_public_host}:{config.provider_cp_management_port}/api/management/v3/transferprocesses/{transfer_id}"
    headers = config.get_management_headers()

    for attempt in range(1, POLL_MAX_ATTEMPTS + 1):
        logger.debug(f"Poll attempt {attempt}/{POLL_MAX_ATTEMPTS}")

        success, status_code, response = make_http_request(url, "GET", headers)

        if success and status_code == 200:
            try:
                transfer = json.loads(response)
                state = transfer.get("state")
                logger.info(f"Transfer state: {state}")

                if state == STATE_STARTED:
                    logger.info("✅ Transfer started successfully")
                    return True
                elif state == STATE_TERMINATED:
                    logger.error(
                        "❌ Transfer terminated\n"
                        "Possible causes (from E2E_TEST_GUIDE.md):\n"
                        "  - Invalid agreement ID\n"
                        "  - Dataplane not reachable\n"
                        "  - Backend API not configured\n"
                        "Check logs: docker logs mvd-provider-dataplane"
                    )
                    return False
                else:
                    # Still in progress (REQUESTING, REQUESTED, STARTING, etc.)
                    time.sleep(POLL_INTERVAL_SECONDS)

            except json.JSONDecodeError:
                logger.error("❌ Failed to parse transfer status")
                return False
        else:
            logger.error(f"❌ Failed to query transfer: {status_code}")
            return False

    logger.error(
        f"❌ Transfer polling timed out after {POLL_MAX_ATTEMPTS * POLL_INTERVAL_SECONDS} seconds"
    )
    return False


def phase_3_transfer_process(config, asset_id: str, agreement_id: str) -> Optional[str]:
    """
    Execute Phase 3: Transfer Process.

    Args:
        config: Configuration object
        asset_id: Asset ID from catalog
        agreement_id: Agreement ID from negotiation

    Returns:
        Transfer process ID or None on failure
    """
    logger.info("=" * 60)
    logger.info("PHASE 3: TRANSFER PROCESS")
    logger.info("=" * 60)

    transfer_id = initiate_transfer_process(config, asset_id, agreement_id)
    if not transfer_id:
        return None

    if not poll_transfer_status(config, transfer_id):
        return None

    logger.info("\n✅ Phase 3 completed successfully\n")
    return transfer_id


# ============================================================
# PHASE 4: DATA ACCESS VIA EDR
# ============================================================


def retrieve_edr(config, transfer_id: str) -> Optional[Dict]:
    """
    Retrieve Endpoint Data Reference (EDR) for transfer.

    Following E2E_TEST_GUIDE.md Step 4.1: Retrieve EDR (Option A: V1 API)

    Args:
        config: Configuration object
        transfer_id: Transfer process ID

    Returns:
        EDR data or None on failure
    """
    logger.info("Retrieving EDR (Endpoint Data Reference)...")

    # Use V1 API as recommended in E2E_TEST_GUIDE.md (Option A: simpler)
    url = f"http://{config.provider_public_host}:{config.provider_cp_management_port}/api/management/v1/edrs?transferProcessId={transfer_id}"
    headers = config.get_management_headers()

    success, status_code, response = make_http_request(url, "GET", headers)

    if success and status_code == 200:
        try:
            edrs = json.loads(response)
            if isinstance(edrs, list) and len(edrs) > 0:
                edr = edrs[0]
                logger.info("✅ EDR retrieved successfully")
                logger.debug(f"EDR: {json.dumps(edr, indent=2)}")
                return edr
            else:
                logger.error("❌ No EDR found for transfer")
                return None
        except json.JSONDecodeError:
            logger.error("❌ Failed to parse EDR response")
            return None
    else:
        logger.error(f"❌ Failed to retrieve EDR: {status_code}")
        return None


def extract_edr_details(edr: Dict) -> Optional[Tuple[str, str]]:
    """
    Extract endpoint and auth code from EDR.

    Following E2E_TEST_GUIDE.md EDR response format

    Args:
        edr: EDR response

    Returns:
        Tuple of (endpoint, auth_code) or None on failure
    """
    # EDR field names from E2E_TEST_GUIDE.md
    endpoint = edr.get("edc:endpoint")
    auth_code = edr.get("edc:authCode")
    auth_key = edr.get("edc:authKey", "Authorization")

    if not endpoint or not auth_code:
        logger.error("❌ EDR missing required fields (endpoint or authCode)")
        return None

    logger.info(f"✅ Endpoint: {endpoint}")
    logger.info(f"✅ Auth Key: {auth_key}")
    logger.debug(f"Auth Code: {auth_code[:20]}...")

    return endpoint, auth_code


def access_data_via_edr(endpoint: str, auth_code: str) -> Optional[str]:
    """
    Access data through dataplane using EDR token.

    Following E2E_TEST_GUIDE.md Step 4.2: Access Data Through Dataplane

    Args:
        endpoint: Dataplane public endpoint
        auth_code: EDR authorization token

    Returns:
        Response data or None on failure
    """
    logger.info("Accessing data through dataplane...")

    # Auth header as specified in E2E_TEST_GUIDE.md
    headers = {"Authorization": auth_code}

    success, status_code, response = make_http_request(endpoint, "GET", headers)

    if success and status_code == 200:
        logger.info("✅ Data retrieved successfully")
        try:
            data = json.loads(response)
            # Show preview (first 2 items if list, or full object if small)
            preview = data[:2] if isinstance(data, list) else data
            logger.info(f"Response preview:\n{json.dumps(preview, indent=2)}")
            if isinstance(data, list) and len(data) > 2:
                logger.info(f"... and {len(data) - 2} more items")
            return response
        except json.JSONDecodeError:
            # Not JSON, return as-is
            logger.info(f"Response preview: {response[:200]}...")
            return response
    else:
        # Error handling from E2E_TEST_GUIDE.md troubleshooting section
        logger.error(f"❌ Failed to access data: {status_code}")
        if status_code == 401:
            logger.error("Cause: Token invalid or expired")
        elif status_code == 403:
            logger.error("Cause: Contract agreement validation failed")
        elif status_code == 404:
            logger.error("Cause: Wrong endpoint or path")
        elif status_code in [502, 504]:
            logger.error("Cause: Backend API unreachable")
        if response:
            logger.debug(f"Response: {response[:500]}")
        return None


def phase_4_data_access(config, transfer_id: str) -> bool:
    """
    Execute Phase 4: Data Access via EDR.

    Args:
        config: Configuration object
        transfer_id: Transfer process ID

    Returns:
        True if data access successful, False otherwise
    """
    logger.info("=" * 60)
    logger.info("PHASE 4: DATA ACCESS VIA EDR")
    logger.info("=" * 60)

    edr = retrieve_edr(config, transfer_id)
    if not edr:
        return False

    edr_details = extract_edr_details(edr)
    if not edr_details:
        return False

    endpoint, auth_code = edr_details

    data = access_data_via_edr(endpoint, auth_code)
    if not data:
        return False

    logger.info("\n✅ Phase 4 completed successfully\n")
    return True


# ============================================================
# MAIN E2E TEST FLOW
# ============================================================


def run_e2e_test(
    config, target_asset_id: str, skip_prerequisites: bool = False
) -> bool:
    """
    Run complete end-to-end test.

    Args:
        config: Configuration object
        target_asset_id: Asset ID to test with
        skip_prerequisites: Skip prerequisite checks (not recommended)

    Returns:
        True if all phases successful, False otherwise
    """
    logger.info("=" * 60)
    logger.info("MINIMUM VIABLE DATASPACE - END-TO-END TEST")
    logger.info("=" * 60)
    logger.info(f"Target Asset: {target_asset_id}")
    logger.info(f"Provider DID: {config.provider_did}")
    logger.info(f"Provider Host: {config.provider_public_host}")
    logger.info(
        f"Management API: {config.provider_public_host}:{config.provider_cp_management_port}"
    )
    logger.info(
        f"DSP Protocol: {config.provider_public_host}:{config.provider_cp_protocol_port}"
    )
    logger.info(
        f"Data Plane Public API: {config.provider_public_host}:{config.provider_dp_public_port}"
    )
    logger.info("=" * 60)

    # Phase 0: Prerequisites (optional skip)
    if not skip_prerequisites:
        if not check_prerequisites(config):
            logger.error("\n❌ E2E Test Failed - Prerequisites not met\n")
            return False
    else:
        logger.warning("⚠️  Skipping prerequisite checks (not recommended)")

    # Phase 1: Catalog Discovery
    offer = phase_1_catalog_discovery(config, target_asset_id)
    if not offer:
        logger.error("\n❌ E2E Test Failed - Phase 1: Catalog Discovery\n")
        return False

    asset_id, policy = offer

    # Phase 2: Contract Negotiation
    agreement_id = phase_2_contract_negotiation(config, asset_id, policy)
    if not agreement_id:
        logger.error("\n❌ E2E Test Failed - Phase 2: Contract Negotiation\n")
        return False

    # Phase 3: Transfer Process
    transfer_id = phase_3_transfer_process(config, asset_id, agreement_id)
    if not transfer_id:
        logger.error("\n❌ E2E Test Failed - Phase 3: Transfer Process\n")
        return False

    # Phase 4: Data Access
    if not phase_4_data_access(config, transfer_id):
        logger.error("\n❌ E2E Test Failed - Phase 4: Data Access\n")
        return False

    # Success!
    logger.info("=" * 60)
    logger.info("🎉 END-TO-END TEST COMPLETED SUCCESSFULLY!")
    logger.info("=" * 60)
    logger.info(
        "\nTest Summary:\n"
        f"  ✅ Phase 0: Prerequisites - All checks passed\n"
        f"  ✅ Phase 1: Catalog Discovery - Asset: {asset_id}\n"
        f"  ✅ Phase 2: Contract Negotiation - Agreement: {agreement_id}\n"
        f"  ✅ Phase 3: Transfer Process - Transfer: {transfer_id}\n"
        f"  ✅ Phase 4: Data Access - Data retrieved successfully\n"
        "\nThe dataspace is functioning correctly!\n"
    )

    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="End-to-End Test for Minimum Viable Dataspace",
        epilog="For more information, see E2E_TEST_GUIDE.md",
    )
    parser.add_argument(
        "--skip-prerequisites",
        action="store_true",
        help="Skip prerequisite checks (not recommended)",
    )
    parser.add_argument(
        "--asset-id",
        default=DEFAULT_TARGET_ASSET_ID,
        help=f"Target asset ID (default: {DEFAULT_TARGET_ASSET_ID})",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output (DEBUG level)",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load configuration from .env file
    config = load_config()
    if not config:
        logger.error(
            "Failed to load configuration\n"
            "Ensure .env file exists (copy from .env.example if needed)"
        )
        return 1

    # Run E2E test
    success = run_e2e_test(config, args.asset_id, args.skip_prerequisites)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
