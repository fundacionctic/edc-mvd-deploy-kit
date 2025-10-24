#!/usr/bin/env python3
"""
Seed Provider Participant with Assets, Policies, and Contracts

This script seeds the provider participant with initial data assets, policy
definitions, and contract definitions based on the edc-mvds Postman collection
structure.

Usage:
    python3 scripts/provider/seed_participant.py [component]

Components:
    assets          Create data assets
    policies        Create policy definitions
    contracts       Create contract definitions
    all             Create all components (default)
    verify          Verify seeded data

Environment Variables:
    All PROVIDER_* environment variables from config.py

Based on:
    edc-mvds/deployment/postman/MVD.postman_collection.json
"""

import json
import logging
import os
import sys
from typing import Dict, List, Optional, Tuple

from http_utils import make_http_request

from config import load_config

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def check_provider_availability(config) -> bool:
    """
    Check if provider Control Plane is available.

    Args:
        config: Configuration object

    Returns:
        True if provider is available, False otherwise
    """
    logger.info("Checking provider Control Plane availability...")

    health_url = f"http://localhost:{config.provider_cp_web_port}/api/check/health"

    success, status_code, response = make_http_request(health_url, "GET")

    if success and status_code == 200:
        logger.info("✅ Provider Control Plane is available")
        return True
    else:
        logger.error(f"❌ Provider Control Plane is not available: {status_code}")
        logger.error("Make sure provider services are running: task provider:up")
        return False


def create_asset(config, asset_data: Dict) -> bool:
    """
    Create a data asset.

    Args:
        config: Configuration object
        asset_data: Asset definition

    Returns:
        True if successful, False otherwise
    """
    asset_id = asset_data.get("@id", "unknown")
    logger.info(f"Creating asset: {asset_id}")

    url = f"http://localhost:{config.provider_cp_management_port}/api/management/v3/assets"
    headers = config.get_management_headers()

    success, status_code, response = make_http_request(
        url, "POST", headers, json.dumps(asset_data)
    )

    if success and status_code in [200, 204, 409]:  # 409 = already exists
        if status_code == 409:
            logger.info(f"✅ Asset {asset_id} already exists")
        else:
            logger.info(f"✅ Asset {asset_id} created successfully")
        return True
    else:
        logger.error(f"❌ Failed to create asset {asset_id}: {status_code}")
        if response:
            logger.debug(f"Error response: {response}")
        return False


def create_policy(config, policy_data: Dict) -> bool:
    """
    Create a policy definition.

    Args:
        config: Configuration object
        policy_data: Policy definition

    Returns:
        True if successful, False otherwise
    """
    policy_id = policy_data.get("@id", "unknown")
    logger.info(f"Creating policy: {policy_id}")

    url = f"http://localhost:{config.provider_cp_management_port}/api/management/v3/policydefinitions"
    headers = config.get_management_headers()

    success, status_code, response = make_http_request(
        url, "POST", headers, json.dumps(policy_data)
    )

    if success and status_code in [200, 204, 409]:  # 409 = already exists
        if status_code == 409:
            logger.info(f"✅ Policy {policy_id} already exists")
        else:
            logger.info(f"✅ Policy {policy_id} created successfully")
        return True
    else:
        logger.error(f"❌ Failed to create policy {policy_id}: {status_code}")
        if response:
            logger.debug(f"Error response: {response}")
        return False


def create_contract_definition(config, contract_data: Dict) -> bool:
    """
    Create a contract definition.

    Args:
        config: Configuration object
        contract_data: Contract definition

    Returns:
        True if successful, False otherwise
    """
    contract_id = contract_data.get("@id", "unknown")
    logger.info(f"Creating contract definition: {contract_id}")

    url = f"http://localhost:{config.provider_cp_management_port}/api/management/v3/contractdefinitions"
    headers = config.get_management_headers()

    success, status_code, response = make_http_request(
        url, "POST", headers, json.dumps(contract_data)
    )

    if success and status_code in [200, 204, 409]:  # 409 = already exists
        if status_code == 409:
            logger.info(f"✅ Contract definition {contract_id} already exists")
        else:
            logger.info(f"✅ Contract definition {contract_id} created successfully")
        return True
    else:
        logger.error(
            f"❌ Failed to create contract definition {contract_id}: {status_code}"
        )
        if response:
            logger.debug(f"Error response: {response}")
        return False


def get_asset_definitions() -> List[Dict]:
    """
    Get asset definitions based on edc-mvds Postman collection.

    Returns:
        List of asset definitions
    """
    return [
        {
            "@context": ["https://w3id.org/edc/connector/management/v0.0.1"],
            "@id": "asset-1",
            "@type": "Asset",
            "properties": {
                "description": "This asset requires Membership to view and negotiate."
            },
            "dataAddress": {
                "@type": "DataAddress",
                "type": "HttpData",
                "baseUrl": "https://jsonplaceholder.typicode.com/todos",
                "proxyPath": "true",
                "proxyQueryParams": "true",
            },
        },
        {
            "@context": ["https://w3id.org/edc/connector/management/v0.0.1"],
            "@id": "asset-2",
            "@type": "Asset",
            "properties": {
                "description": "This asset requires Membership to view and SensitiveData credential to negotiate."
            },
            "dataAddress": {
                "@type": "DataAddress",
                "type": "HttpData",
                "baseUrl": "https://jsonplaceholder.typicode.com/todos",
                "proxyPath": "true",
                "proxyQueryParams": "true",
            },
        },
    ]


def get_policy_definitions() -> List[Dict]:
    """
    Get policy definitions based on edc-mvds Postman collection.

    Returns:
        List of policy definitions
    """
    return [
        {
            "@context": ["https://w3id.org/edc/connector/management/v0.0.1"],
            "@type": "PolicyDefinition",
            "@id": "require-membership",
            "policy": {
                "@type": "Set",
                "permission": [
                    {
                        "action": "use",
                        "constraint": {
                            "leftOperand": "MembershipCredential",
                            "operator": "eq",
                            "rightOperand": "active",
                        },
                    }
                ],
            },
        },
        {
            "@context": ["https://w3id.org/edc/connector/management/v0.0.1"],
            "@type": "PolicyDefinition",
            "@id": "require-dataprocessor",
            "policy": {
                "@type": "Set",
                "obligation": [
                    {
                        "action": "use",
                        "constraint": {
                            "leftOperand": "DataAccess.level",
                            "operator": "eq",
                            "rightOperand": "processing",
                        },
                    }
                ],
            },
        },
        {
            "@context": ["https://w3id.org/edc/connector/management/v0.0.1"],
            "@type": "PolicyDefinition",
            "@id": "require-sensitive",
            "policy": {
                "@type": "Set",
                "obligation": [
                    {
                        "action": "use",
                        "constraint": {
                            "leftOperand": "DataAccess.level",
                            "operator": "eq",
                            "rightOperand": "sensitive",
                        },
                    }
                ],
            },
        },
    ]


def get_contract_definitions() -> List[Dict]:
    """
    Get contract definitions based on edc-mvds Postman collection.

    Returns:
        List of contract definitions
    """
    return [
        {
            "@context": ["https://w3id.org/edc/connector/management/v0.0.1"],
            "@id": "member-and-dataprocessor-def",
            "@type": "ContractDefinition",
            "accessPolicyId": "require-membership",
            "contractPolicyId": "require-dataprocessor",
            "assetsSelector": {
                "@type": "Criterion",
                "operandLeft": "https://w3id.org/edc/v0.0.1/ns/id",
                "operator": "=",
                "operandRight": "asset-1",
            },
        },
        {
            "@context": ["https://w3id.org/edc/connector/management/v0.0.1"],
            "@id": "sensitive-only-def",
            "@type": "ContractDefinition",
            "accessPolicyId": "require-membership",
            "contractPolicyId": "require-sensitive",
            "assetsSelector": {
                "@type": "Criterion",
                "operandLeft": "https://w3id.org/edc/v0.0.1/ns/id",
                "operator": "=",
                "operandRight": "asset-2",
            },
        },
    ]


def seed_assets(config) -> bool:
    """
    Seed provider with data assets.

    Args:
        config: Configuration object

    Returns:
        True if successful, False otherwise
    """
    logger.info("Seeding data assets...")

    assets = get_asset_definitions()
    all_successful = True

    for asset in assets:
        if not create_asset(config, asset):
            all_successful = False

    if all_successful:
        logger.info(f"✅ All {len(assets)} assets created successfully")
    else:
        logger.error("❌ Some assets failed to create")

    return all_successful


def seed_policies(config) -> bool:
    """
    Seed provider with policy definitions.

    Args:
        config: Configuration object

    Returns:
        True if successful, False otherwise
    """
    logger.info("Seeding policy definitions...")

    policies = get_policy_definitions()
    all_successful = True

    for policy in policies:
        if not create_policy(config, policy):
            all_successful = False

    if all_successful:
        logger.info(f"✅ All {len(policies)} policies created successfully")
    else:
        logger.error("❌ Some policies failed to create")

    return all_successful


def seed_contracts(config) -> bool:
    """
    Seed provider with contract definitions.

    Args:
        config: Configuration object

    Returns:
        True if successful, False otherwise
    """
    logger.info("Seeding contract definitions...")

    contracts = get_contract_definitions()
    all_successful = True

    for contract in contracts:
        if not create_contract_definition(config, contract):
            all_successful = False

    if all_successful:
        logger.info(
            f"✅ All {len(contracts)} contract definitions created successfully"
        )
    else:
        logger.error("❌ Some contract definitions failed to create")

    return all_successful


def verify_seeded_data(config) -> bool:
    """
    Verify seeded data by querying the Management API.

    Args:
        config: Configuration object

    Returns:
        True if verification successful, False otherwise
    """
    logger.info("Verifying seeded data...")

    # Verification endpoints
    endpoints = [
        (
            "assets",
            f"http://localhost:{config.provider_cp_management_port}/api/management/v3/assets/request",
        ),
        (
            "policies",
            f"http://localhost:{config.provider_cp_management_port}/api/management/v3/policydefinitions/request",
        ),
        (
            "contracts",
            f"http://localhost:{config.provider_cp_management_port}/api/management/v3/contractdefinitions/request",
        ),
    ]

    headers = config.get_management_headers()
    query_body = json.dumps(
        {
            "@context": ["https://w3id.org/edc/connector/management/v0.0.1"],
            "@type": "QuerySpec",
        }
    )

    all_successful = True

    for endpoint_name, url in endpoints:
        success, status_code, response = make_http_request(
            url, "POST", headers, query_body
        )

        if success and status_code == 200:
            try:
                data = json.loads(response)
                if isinstance(data, list):
                    logger.info(f"✅ {endpoint_name}: {len(data)} items found")
                else:
                    logger.info(f"✅ {endpoint_name}: response received")
            except json.JSONDecodeError:
                logger.warning(f"⚠️  {endpoint_name}: non-JSON response")
        else:
            logger.error(f"❌ {endpoint_name} verification failed: {status_code}")
            all_successful = False

    return all_successful


def seed_all_components(config) -> bool:
    """
    Seed all provider components.

    Args:
        config: Configuration object

    Returns:
        True if successful, False otherwise
    """
    logger.info("Seeding all provider components...")
    logger.info("=" * 60)

    # Seeding steps (order matters - policies before contracts)
    seeding_steps = [
        ("Assets", seed_assets),
        ("Policies", seed_policies),
        ("Contract Definitions", seed_contracts),
    ]

    all_successful = True

    for step_name, step_func in seeding_steps:
        logger.info(f"\n--- {step_name} ---")
        try:
            if step_func(config):
                logger.info(f"✅ {step_name} seeding completed")
            else:
                logger.error(f"❌ {step_name} seeding failed")
                all_successful = False
        except Exception as e:
            logger.error(f"❌ {step_name} seeding failed with exception: {e}")
            all_successful = False

    # Verification
    logger.info(f"\n--- Verification ---")
    if verify_seeded_data(config):
        logger.info("✅ Seeded data verification passed")
    else:
        logger.warning("⚠️  Seeded data verification had issues")

    # Summary
    if all_successful:
        logger.info(
            "\n" + "=" * 60 + "\n"
            "🎉 Provider participant seeding completed successfully!\n\n"
            "Provider is now ready for:\n"
            "  - Catalog queries from consumers\n"
            "  - Contract negotiations\n"
            "  - Data transfers\n\n"
            "Test the provider:\n"
            "  - Check catalog: task provider:test-controlplane\n"
            "  - Verify policies are enforced\n"
            "  - Test end-to-end data sharing"
        )
    else:
        logger.error(
            "❌ Provider participant seeding failed\n"
            "Please check the errors above and retry"
        )

    return all_successful


def show_help():
    """Show help message."""
    print(__doc__)


def main():
    """Main entry point."""
    # Load configuration
    config = load_config()
    if not config:
        logger.error("Failed to load configuration")
        return 1

    # Check provider availability
    if not check_provider_availability(config):
        return 1

    # Determine component to seed
    component = sys.argv[1].lower() if len(sys.argv) > 1 else "all"

    success = False

    if component == "assets":
        success = seed_assets(config)
    elif component == "policies":
        success = seed_policies(config)
    elif component == "contracts":
        success = seed_contracts(config)
    elif component == "verify":
        success = verify_seeded_data(config)
    elif component == "all":
        success = seed_all_components(config)
    elif component == "help" or component == "--help":
        show_help()
        return 0
    else:
        logger.error(f"Unknown component: {component}")
        show_help()
        return 1

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
