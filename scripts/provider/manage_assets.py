#!/usr/bin/env python3
"""
Asset Configuration Management Utility

This utility helps manage data source configurations for the Provider participant.
It provides commands to list, add, remove, and validate asset configurations.

Usage:
    python3 scripts/provider/manage_assets.py list
    python3 scripts/provider/manage_assets.py add --id my-api --url https://api.example.com/data
    python3 scripts/provider/manage_assets.py remove --id my-api
    python3 scripts/provider/manage_assets.py validate

Environment Variables:
    All PROVIDER_ASSET_* environment variables from .env file
"""

import argparse
import logging
import os
import sys
from typing import Dict, List, Optional

from config import load_config

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def list_assets() -> bool:
    """
    List all configured assets.

    Returns:
        True if successful, False otherwise
    """
    config = load_config()
    if not config:
        logger.error("Failed to load configuration")
        return False

    assets = config.get_asset_definitions()

    if not assets:
        print("No assets configured.")
        print("\nTo add assets, set environment variables in your .env file:")
        print("PROVIDER_ASSET_1_ID=my-asset")
        print("PROVIDER_ASSET_1_BASE_URL=https://api.example.com/data")
        return True

    print(f"\nConfigured Assets ({len(assets)}):")
    print("=" * 60)

    for i, asset in enumerate(assets, 1):
        asset_id = asset.get("@id", "unknown")
        description = asset.get("properties", {}).get("description", "No description")
        base_url = asset.get("dataAddress", {}).get("baseUrl", "No URL")

        print(f"{i}. ID: {asset_id}")
        print(f"   Description: {description}")
        print(f"   URL: {base_url}")

        # Show additional properties
        properties = asset.get("properties", {})
        data_address = asset.get("dataAddress", {})

        extra_props = {k: v for k, v in properties.items() if k != "description"}
        extra_data = {
            k: v
            for k, v in data_address.items()
            if k not in ["@type", "type", "baseUrl", "proxyPath", "proxyQueryParams"]
        }

        if extra_props:
            print(f"   Properties: {extra_props}")
        if extra_data:
            print(f"   Data Config: {extra_data}")
        print()

    return True


def validate_assets() -> bool:
    """
    Validate asset configurations.

    Returns:
        True if all assets are valid, False otherwise
    """
    config = load_config()
    if not config:
        logger.error("Failed to load configuration")
        return False

    assets = config.get_asset_definitions()

    if not assets:
        logger.warning("No assets configured")
        return True

    all_valid = True

    print(f"\nValidating {len(assets)} assets:")
    print("=" * 40)

    asset_ids = set()

    for i, asset in enumerate(assets, 1):
        asset_id = asset.get("@id")
        base_url = asset.get("dataAddress", {}).get("baseUrl")

        print(f"{i}. {asset_id}")

        # Check required fields
        if not asset_id:
            print("   ❌ Missing asset ID")
            all_valid = False
        elif asset_id in asset_ids:
            print(f"   ❌ Duplicate asset ID: {asset_id}")
            all_valid = False
        else:
            asset_ids.add(asset_id)
            print("   ✅ Valid asset ID")

        if not base_url:
            print("   ❌ Missing base URL")
            all_valid = False
        elif not base_url.startswith(("http://", "https://")):
            print(f"   ⚠️  Base URL should start with http:// or https://: {base_url}")
        else:
            print("   ✅ Valid base URL")

        print()

    if all_valid:
        print("✅ All asset configurations are valid")
    else:
        print("❌ Some asset configurations have issues")

    return all_valid


def show_env_vars() -> bool:
    """
    Show environment variables for currently configured assets.

    Returns:
        True if successful, False otherwise
    """
    # Scan environment for asset configurations
    asset_numbers = set()
    for env_var in os.environ:
        if env_var.startswith("PROVIDER_ASSET_") and env_var.endswith("_ID"):
            try:
                asset_num_str = env_var.replace("PROVIDER_ASSET_", "").replace(
                    "_ID", ""
                )
                asset_num = int(asset_num_str)
                asset_numbers.add(asset_num)
            except ValueError:
                continue

    if not asset_numbers:
        print("No asset environment variables found.")
        return True

    print("\nCurrent Asset Environment Variables:")
    print("=" * 50)

    for asset_num in sorted(asset_numbers):
        print(f"\n# Asset {asset_num}")

        # Show all environment variables for this asset
        for env_var in sorted(os.environ.keys()):
            if env_var.startswith(f"PROVIDER_ASSET_{asset_num}_"):
                value = os.environ[env_var]
                print(f"{env_var}={value}")

    return True


def generate_example_config(num_assets: int = 3) -> bool:
    """
    Generate example asset configuration.

    Args:
        num_assets: Number of example assets to generate

    Returns:
        True if successful, False otherwise
    """
    print(f"\nExample Asset Configuration ({num_assets} assets):")
    print("=" * 50)
    print("# Add these to your .env file:\n")

    examples = [
        {
            "id": "todos-api",
            "description": "Public TODO API for testing",
            "url": "https://jsonplaceholder.typicode.com/todos",
        },
        {
            "id": "customer-data",
            "description": "Customer database requiring membership",
            "url": "https://api.example.com/customers",
            "extra": {
                "PROPERTY_CATEGORY": "customer-data",
                "PROPERTY_SENSITIVITY": "high",
            },
        },
        {
            "id": "analytics-api",
            "description": "Real-time analytics API",
            "url": "https://analytics.example.com/api/v1",
            "extra": {"DATA_APIKEY": "your-api-key-here", "PROPERTY_REALTIME": "true"},
        },
    ]

    for i in range(min(num_assets, len(examples))):
        asset_num = i + 1
        example = examples[i]

        print(f"# Asset {asset_num}: {example['description']}")
        print(f"PROVIDER_ASSET_{asset_num}_ID={example['id']}")
        print(f"PROVIDER_ASSET_{asset_num}_DESCRIPTION={example['description']}")
        print(f"PROVIDER_ASSET_{asset_num}_BASE_URL={example['url']}")

        if "extra" in example:
            for key, value in example["extra"].items():
                print(f"PROVIDER_ASSET_{asset_num}_{key}={value}")

        print()

    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Manage Provider asset configurations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/provider/manage_assets.py list
  python3 scripts/provider/manage_assets.py validate
  python3 scripts/provider/manage_assets.py env-vars
  python3 scripts/provider/manage_assets.py example --count 5
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List command
    subparsers.add_parser("list", help="List all configured assets")

    # Validate command
    subparsers.add_parser("validate", help="Validate asset configurations")

    # Show environment variables command
    subparsers.add_parser("env-vars", help="Show current asset environment variables")

    # Generate example command
    example_parser = subparsers.add_parser(
        "example", help="Generate example configuration"
    )
    example_parser.add_argument(
        "--count",
        type=int,
        default=3,
        help="Number of example assets to generate (default: 3)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    success = False

    if args.command == "list":
        success = list_assets()
    elif args.command == "validate":
        success = validate_assets()
    elif args.command == "env-vars":
        success = show_env_vars()
    elif args.command == "example":
        success = generate_example_config(args.count)
    else:
        logger.error(f"Unknown command: {args.command}")
        parser.print_help()
        return 1

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
