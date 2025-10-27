#!/usr/bin/env python3
"""
Validate Provider Participant Configuration

This script validates the generated configuration files for all provider
participant components. It checks for:
- File existence and readability
- Required environment variables presence
- Port conflicts and validity
- Database connection strings
- DID format validation

Usage:
    python3 scripts/provider/validate_config.py

Requirements:
    - Generated configuration files in config/ directory
"""

import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Expected configuration files
CONFIG_FILES = [
    "provider-controlplane.env",
    "provider-dataplane.env",
    "provider-identityhub.env",
]

# Required environment variables for each component
REQUIRED_VARS = {
    "provider-controlplane.env": [
        "EDC_PARTICIPANT_ID",
        "WEB_HTTP_PORT",
        "WEB_HTTP_MANAGEMENT_PORT",
        "WEB_HTTP_PROTOCOL_PORT",
        "WEB_HTTP_CONTROL_PORT",
        "WEB_HTTP_CATALOG_PORT",
        "EDC_DATASOURCE_DEFAULT_URL",
        "EDC_VAULT_HASHICORP_URL",
        "EDC_DSP_CALLBACK_ADDRESS",
    ],
    "provider-dataplane.env": [
        "EDC_PARTICIPANT_ID",
        "EDC_RUNTIME_ID",
        "WEB_HTTP_PORT",
        "WEB_HTTP_CONTROL_PORT",
        "WEB_HTTP_PUBLIC_PORT",
        "EDC_DATASOURCE_DEFAULT_URL",
        "EDC_VAULT_HASHICORP_URL",
        "EDC_DPF_SELECTOR_URL",
    ],
    "provider-identityhub.env": [
        "EDC_IH_IAM_ID",
        "WEB_HTTP_PORT",
        "WEB_HTTP_CREDENTIALS_PORT",
        "WEB_HTTP_STS_PORT",
        "WEB_HTTP_DID_PORT",
        "EDC_DATASOURCE_DEFAULT_URL",
        "EDC_VAULT_HASHICORP_URL",
        "EDC_MVD_CREDENTIALS_PATH",
    ],
}


def load_env_file(file_path: Path) -> Dict[str, str]:
    """
    Load environment variables from a .env file.

    Args:
        file_path: Path to .env file

    Returns:
        Dictionary of environment variables
    """
    env_vars = {}

    try:
        with open(file_path, "r") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                # Parse KEY=VALUE format
                if "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()
                else:
                    logger.warning(
                        f"Invalid line format in {file_path}:{line_num}: {line}"
                    )

        return env_vars

    except Exception as e:
        logger.error(f"Failed to load {file_path}: {str(e)}")
        return {}


def validate_file_exists(file_path: Path) -> bool:
    """
    Validate that configuration file exists and is readable.

    Args:
        file_path: Path to configuration file

    Returns:
        True if file exists and is readable, False otherwise
    """
    if not file_path.exists():
        logger.error(f"❌ Configuration file not found: {file_path}")
        return False

    if not file_path.is_file():
        logger.error(f"❌ Path is not a file: {file_path}")
        return False

    if not os.access(file_path, os.R_OK):
        logger.error(f"❌ Configuration file is not readable: {file_path}")
        return False

    logger.info(f"✅ Configuration file exists: {file_path.name}")
    return True


def validate_required_variables(filename: str, env_vars: Dict[str, str]) -> bool:
    """
    Validate that all required environment variables are present.

    Args:
        filename: Configuration filename
        env_vars: Loaded environment variables

    Returns:
        True if all required variables present, False otherwise
    """
    if filename not in REQUIRED_VARS:
        logger.warning(f"⚠️  No validation rules for {filename}")
        return True

    required = REQUIRED_VARS[filename]
    missing = []

    for var in required:
        if var not in env_vars or not env_vars[var]:
            missing.append(var)

    if missing:
        logger.error(
            f"❌ Missing required variables in {filename}: {', '.join(missing)}"
        )
        return False

    logger.info(f"✅ All required variables present in {filename}")
    return True


def validate_port_format(port_value: str) -> bool:
    """
    Validate port number format and range.

    Args:
        port_value: Port value to validate

    Returns:
        True if port is valid, False otherwise
    """
    try:
        port = int(port_value)
        return 1 <= port <= 65535
    except ValueError:
        return False


def validate_ports(all_env_vars: Dict[str, Dict[str, str]]) -> bool:
    """
    Validate port configurations across all components.

    Args:
        all_env_vars: Dictionary mapping filenames to their env vars

    Returns:
        True if all ports are valid, False otherwise
    """
    logger.info("Validating port configurations...")

    all_ports: Set[str] = set()
    port_conflicts: List[Tuple[str, str, str]] = []
    invalid_ports: List[Tuple[str, str, str]] = []

    # Collect all ports from all components
    port_to_files: Dict[str, List[Tuple[str, str]]] = {}

    for filename, env_vars in all_env_vars.items():
        for var_name, var_value in env_vars.items():
            if var_name.endswith("_PORT") or var_name.endswith("PORT") and not var_name.endswith("_URL"):
                # Validate port format
                if not validate_port_format(var_value):
                    invalid_ports.append((filename, var_name, var_value))
                    continue

                # Track which files use which ports
                if var_value not in port_to_files:
                    port_to_files[var_value] = []
                port_to_files[var_value].append((filename, var_name))
                all_ports.add(var_value)

    # Check for cross-service port conflicts (same port used by different services)
    for port, file_vars in port_to_files.items():
        if len(file_vars) > 1:
            # Check if all uses are from the same service (same config file)
            unique_files = set(filename for filename, _ in file_vars)
            if len(unique_files) > 1:
                # This is a real conflict - same port used by different services
                for filename, var_name in file_vars:
                    port_conflicts.append((filename, var_name, port))

    # Report invalid ports
    if invalid_ports:
        logger.error("❌ Invalid port configurations:")
        for filename, var_name, var_value in invalid_ports:
            logger.error(f"   {filename}: {var_name}={var_value}")
        return False

    # Report port conflicts
    if port_conflicts:
        logger.error("❌ Port conflicts detected:")
        for filename, var_name, var_value in port_conflicts:
            logger.error(f"   {filename}: {var_name}={var_value}")
        return False

    logger.info(f"✅ All {len(all_ports)} ports are valid and unique")
    return True


def validate_database_urls(all_env_vars: Dict[str, Dict[str, str]]) -> bool:
    """
    Validate database connection URLs.

    Args:
        all_env_vars: Dictionary mapping filenames to their env vars

    Returns:
        True if all database URLs are valid, False otherwise
    """
    logger.info("Validating database configurations...")

    db_url_pattern = re.compile(r"^jdbc:postgresql://[^:]+:\d+/\w+$")
    invalid_urls: List[Tuple[str, str]] = []

    for filename, env_vars in all_env_vars.items():
        for var_name, var_value in env_vars.items():
            if var_name == "EDC_DATASOURCE_DEFAULT_URL":
                if not db_url_pattern.match(var_value):
                    invalid_urls.append((filename, var_value))

    if invalid_urls:
        logger.error("❌ Invalid database URLs:")
        for filename, url in invalid_urls:
            logger.error(f"   {filename}: {url}")
        return False

    logger.info("✅ All database URLs are valid")
    return True


def validate_did_format(all_env_vars: Dict[str, Dict[str, str]]) -> bool:
    """
    Validate DID format consistency.

    Args:
        all_env_vars: Dictionary mapping filenames to their env vars

    Returns:
        True if DIDs are valid and consistent, False otherwise
    """
    logger.info("Validating DID configurations...")

    did_pattern = re.compile(r"^did:web:[^:]+(?:%3A\d+)?(?::[^:]+)?$")
    dids: Set[str] = set()
    invalid_dids: List[Tuple[str, str, str]] = []

    for filename, env_vars in all_env_vars.items():
        for var_name, var_value in env_vars.items():
            if "PARTICIPANT_ID" in var_name or "IAM_ID" in var_name:
                if not did_pattern.match(var_value):
                    invalid_dids.append((filename, var_name, var_value))
                else:
                    dids.add(var_value)

    if invalid_dids:
        logger.error("❌ Invalid DID formats:")
        for filename, var_name, var_value in invalid_dids:
            logger.error(f"   {filename}: {var_name}={var_value}")
        return False

    if len(dids) > 1:
        logger.error(f"❌ Inconsistent DIDs across components: {dids}")
        return False

    if dids:
        logger.info(f"✅ DID format is valid and consistent: {list(dids)[0]}")

    return True


def validate_vault_configuration(all_env_vars: Dict[str, Dict[str, str]]) -> bool:
    """
    Validate Vault configuration consistency.

    Args:
        all_env_vars: Dictionary mapping filenames to their env vars

    Returns:
        True if Vault config is consistent, False otherwise
    """
    logger.info("Validating Vault configurations...")

    vault_urls: Set[str] = set()
    vault_tokens: Set[str] = set()

    for filename, env_vars in all_env_vars.items():
        vault_url = env_vars.get("EDC_VAULT_HASHICORP_URL")
        vault_token = env_vars.get("EDC_VAULT_HASHICORP_TOKEN")

        if vault_url:
            vault_urls.add(vault_url)
        if vault_token:
            vault_tokens.add(vault_token)

    if len(vault_urls) > 1:
        logger.error(f"❌ Inconsistent Vault URLs: {vault_urls}")
        return False

    if len(vault_tokens) > 1:
        logger.error(f"❌ Inconsistent Vault tokens: {vault_tokens}")
        return False

    logger.info("✅ Vault configuration is consistent")
    return True


def main():
    """Main entry point."""
    logger.info("Validating Provider Participant configuration files")
    logger.info("=" * 60)

    config_dir = Path("config")

    if not config_dir.exists():
        logger.error(
            "❌ Config directory not found. Run: task provider:generate-config"
        )
        return 1

    # Load all configuration files
    all_env_vars: Dict[str, Dict[str, str]] = {}
    validation_passed = True

    for filename in CONFIG_FILES:
        file_path = config_dir / filename

        # Check file existence
        if not validate_file_exists(file_path):
            validation_passed = False
            continue

        # Load environment variables
        env_vars = load_env_file(file_path)
        if not env_vars:
            logger.error(f"❌ Failed to load variables from {filename}")
            validation_passed = False
            continue

        all_env_vars[filename] = env_vars

        # Validate required variables
        if not validate_required_variables(filename, env_vars):
            validation_passed = False

    if not all_env_vars:
        logger.error("❌ No configuration files could be loaded")
        return 1

    # Cross-component validations
    if validation_passed:
        if not validate_ports(all_env_vars):
            validation_passed = False

        if not validate_database_urls(all_env_vars):
            validation_passed = False

        if not validate_did_format(all_env_vars):
            validation_passed = False

        if not validate_vault_configuration(all_env_vars):
            validation_passed = False

    # Final result
    logger.info("")
    if validation_passed:
        logger.info("🎉 All configuration validations passed!")
        logger.info("")
        logger.info("Configuration files are ready for deployment:")
        for filename in CONFIG_FILES:
            logger.info(f"  ✅ {filename}")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Start provider services with Docker Compose")
        logger.info("  2. Verify component health checks")
        logger.info("  3. Test API endpoints")
        return 0
    else:
        logger.error("❌ Configuration validation failed")
        logger.error("Please fix the issues and regenerate configuration files")
        return 1


if __name__ == "__main__":
    sys.exit(main())
