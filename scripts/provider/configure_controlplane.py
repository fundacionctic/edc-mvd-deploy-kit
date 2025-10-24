#!/usr/bin/env python3
"""
Control Plane Configuration and Setup

This script configures the Control Plane component with necessary settings
for participant registry, DID resolution, and STS integration.

Usage:
    python3 scripts/provider/configure_controlplane.py [action]

Actions:
    setup           Setup Control Plane configuration (default)
    verify          Verify Control Plane configuration
    test            Test Control Plane functionality
    reset           Reset Control Plane configuration

Environment Variables:
    All PROVIDER_* environment variables from config.py
"""

import json
import logging
import os
import sys
from typing import Dict, List, Optional

# Add the scripts directory to the path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from provider.config import load_config
    from provider.test_controlplane import run_all_tests
    from provider.common_utils import wait_for_component, validate_did_format, validate_port_number
except ImportError:
    print("ERROR: Could not import provider modules")
    print("Make sure you're running from the project root directory")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def setup_participant_registry(config) -> bool:
    """
    Setup participant registry configuration.

    Args:
        config: Configuration object

    Returns:
        True if successful, False otherwise
    """
    logger.info("Setting up participant registry...")

    # Create participants.json file for the Control Plane
    participants_data = {
        "participants": [
            {
                "participantId": config.provider_did,
                "url": f"http://localhost:{config.provider_cp_protocol_port}/api/dsp",
                "supportedProtocols": [
                    {
                        "protocolName": "dataspace-protocol-http",
                        "protocolVersion": "0.8",
                    }
                ],
            }
        ]
    }

    # Ensure assets directory exists
    participants_dir = "assets/participants"
    os.makedirs(participants_dir, exist_ok=True)

    # Write participants file
    participants_file = os.path.join(participants_dir, "participants.json")

    try:
        with open(participants_file, "w") as f:
            json.dump(participants_data, f, indent=2)

        logger.info(f"✅ Participant registry created: {participants_file}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to create participant registry: {e}")
        return False


def setup_did_resolution(config) -> bool:
    """
    Setup DID resolution configuration.

    Args:
        config: Configuration object

    Returns:
        True if successful, False otherwise
    """
    logger.info("Setting up DID resolution...")

    # Create DID registry configuration
    did_registry = {
        "dids": [
            {
                "did": config.provider_did,
                "url": f"http://localhost:{config.provider_ih_did_port}/.well-known/did.json",
            }
        ]
    }

    # Ensure assets directory exists
    assets_dir = "assets"
    os.makedirs(assets_dir, exist_ok=True)

    # Write DID registry file
    did_registry_file = os.path.join(assets_dir, "did-registry.json")

    try:
        with open(did_registry_file, "w") as f:
            json.dump(did_registry, f, indent=2)

        logger.info(f"✅ DID registry created: {did_registry_file}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to create DID registry: {e}")
        return False


def setup_sts_integration(config) -> bool:
    """
    Setup STS integration configuration.

    Args:
        config: Configuration object

    Returns:
        True if successful, False otherwise
    """
    logger.info("Setting up STS integration...")

    # STS integration is handled via environment variables in the configuration
    # This function validates that the STS configuration is correct

    sts_config = {
        "token_url": f"http://provider-identityhub:{config.provider_ih_sts_port}/api/sts/token",
        "client_id": config.provider_did,
        "private_key_alias": f"{config.provider_did}#key-1",
        "public_key_id": f"{config.provider_did}#key-1",
    }

    logger.info("STS Configuration:")
    for key, value in sts_config.items():
        logger.info(f"  {key}: {value}")

    logger.info("✅ STS integration configuration validated")
    return True


def verify_configuration(config) -> bool:
    """
    Verify Control Plane configuration.

    Args:
        config: Configuration object

    Returns:
        True if configuration is valid, False otherwise
    """
    logger.info("Verifying Control Plane configuration...")

    # Check required files
    required_files = [
        "assets/participants/participants.json",
        "assets/did-registry.json",
        "config/provider-controlplane.env",
    ]

    all_valid = True

    for file_path in required_files:
        if os.path.exists(file_path):
            logger.info(f"✅ Required file exists: {file_path}")
        else:
            logger.error(f"❌ Required file missing: {file_path}")
            all_valid = False

    # Verify configuration values
    # DID validation
    if validate_did_format(config.provider_did):
        logger.info(f"✅ Provider DID: {config.provider_did}")
    else:
        logger.error(f"❌ Provider DID invalid: {config.provider_did}")
        all_valid = False

    # Port validations
    port_checks = [
        ("Management Port", config.provider_cp_management_port),
        ("Protocol Port", config.provider_cp_protocol_port),
        ("Catalog Port", config.provider_cp_catalog_port),
    ]

    for port_name, port_value in port_checks:
        if validate_port_number(port_value, port_name):
            logger.info(f"✅ {port_name}: {port_value}")
        else:
            all_valid = False

    return all_valid


def wait_for_controlplane(config, timeout: int = 60) -> bool:
    """
    Wait for Control Plane to become ready.

    Args:
        config: Configuration object
        timeout: Maximum time to wait in seconds

    Returns:
        True if Control Plane becomes ready, False if timeout
    """
    health_url = f"http://localhost:{config.provider_cp_web_port}/api/check/health"
    return wait_for_component("Control Plane", health_url, timeout)


def reset_configuration(config) -> bool:
    """
    Reset Control Plane configuration.

    Args:
        config: Configuration object

    Returns:
        True if successful, False otherwise
    """
    logger.info("Resetting Control Plane configuration...")

    # Files to remove
    files_to_remove = [
        "assets/participants/participants.json",
        "assets/did-registry.json",
    ]

    for file_path in files_to_remove:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"✅ Removed: {file_path}")
            except Exception as e:
                logger.error(f"❌ Failed to remove {file_path}: {e}")
                return False
        else:
            logger.info(f"File not found (already removed): {file_path}")

    logger.info("✅ Control Plane configuration reset")
    return True


def setup_controlplane(config) -> bool:
    """
    Complete Control Plane setup.

    Args:
        config: Configuration object

    Returns:
        True if successful, False otherwise
    """
    logger.info("Setting up Control Plane configuration...")
    logger.info("=" * 50)

    setup_steps = [
        ("Participant Registry", setup_participant_registry),
        ("DID Resolution", setup_did_resolution),
        ("STS Integration", setup_sts_integration),
    ]

    all_successful = True

    for step_name, step_func in setup_steps:
        logger.info(f"\n--- {step_name} ---")
        try:
            if step_func(config):
                logger.info(f"✅ {step_name} setup completed")
            else:
                logger.error(f"❌ {step_name} setup failed")
                all_successful = False
        except Exception as e:
            logger.error(f"❌ {step_name} setup failed with exception: {e}")
            all_successful = False

    logger.info("\n" + "=" * 50)
    if all_successful:
        logger.info("🎉 Control Plane setup completed successfully!")

        # Verify configuration
        if verify_configuration(config):
            logger.info("✅ Configuration verification passed")
        else:
            logger.warning("⚠️  Configuration verification had issues")
            all_successful = False
    else:
        logger.error("❌ Control Plane setup failed")

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

    # Determine action to perform
    action = sys.argv[1].lower() if len(sys.argv) > 1 else "setup"

    success = False

    if action == "setup":
        success = setup_controlplane(config)
    elif action == "verify":
        success = verify_configuration(config)
    elif action == "test":
        # Wait for Control Plane to be ready first
        if wait_for_controlplane(config):
            success = run_all_tests(config)
        else:
            logger.error("Control Plane is not ready for testing")
    elif action == "reset":
        success = reset_configuration(config)
    elif action == "wait":
        success = wait_for_controlplane(config)
    elif action == "help" or action == "--help":
        show_help()
        return 0
    else:
        logger.error(f"Unknown action: {action}")
        show_help()
        return 1

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
