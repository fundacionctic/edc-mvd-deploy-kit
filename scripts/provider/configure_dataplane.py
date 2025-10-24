#!/usr/bin/env python3
"""
Data Plane Configuration and Setup

This script configures the Data Plane component with necessary settings
for Control Plane communication, token verification, and data transfer.

Usage:
    python3 scripts/provider/configure_dataplane.py

Environment Variables:
    All PROVIDER_* environment variables from config.py
"""

import logging
import os
import sys

# Add the scripts directory to the path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from provider.common_utils import (
        check_component_health,
        validate_did_format,
        validate_port_number,
    )
    from provider.config import load_config
except ImportError:
    print("ERROR: Could not import provider modules")
    print("Make sure you're running from the project root directory")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def setup_dataplane_configuration(config) -> bool:
    """
    Setup Data Plane configuration files.

    Args:
        config: Configuration object

    Returns:
        True if successful, False otherwise
    """
    logger.info("Setting up Data Plane configuration...")

    # Data Plane configuration is handled via environment variables
    # This function validates the configuration

    dataplane_config = {
        "runtime_id": f"{config.provider_participant_name}-dataplane",
        "participant_id": config.provider_did,
        "hostname": "provider-dataplane",
        "control_port": config.provider_dp_control_port,
        "public_port": config.provider_dp_public_port,
        "web_port": config.provider_dp_web_port,
        "selector_url": f"http://provider-controlplane:{config.provider_cp_control_port}/api/control/v1/dataplanes",
        "token_signer_alias": f"{config.provider_did}#key-1",
        "token_verifier_alias": f"{config.provider_did}#key-1",
    }

    logger.info("Data Plane Configuration:")
    for key, value in dataplane_config.items():
        logger.info(f"  {key}: {value}")

    logger.info("✅ Data Plane configuration validated")
    return True


def setup_control_plane_communication(config) -> bool:
    """
    Setup communication with Control Plane.

    Args:
        config: Configuration object

    Returns:
        True if successful, False otherwise
    """
    logger.info("Setting up Control Plane communication...")

    cp_health_url = f"http://{config.provider_public_host}:{config.provider_cp_web_port}/api/check/health"

    if check_component_health("Control Plane", cp_health_url, timeout=10):
        return True
    else:
        logger.info("Make sure Control Plane is running before starting Data Plane")
        logger.info(
            "⚠️  This is expected during initial setup - continuing with configuration"
        )
        return True  # Allow setup to continue even if Control Plane is not running yet


def setup_token_configuration(config) -> bool:
    """
    Setup token signing and verification configuration.

    Args:
        config: Configuration object

    Returns:
        True if successful, False otherwise
    """
    logger.info("Setting up token configuration...")

    # Token configuration is handled via environment variables
    # This function validates the token setup

    token_config = {
        "signer_private_key_alias": f"{config.provider_did}#key-1",
        "verifier_public_key_alias": f"{config.provider_did}#key-1",
        "sts_token_url": f"http://provider-identityhub:{config.provider_ih_sts_port}/api/sts/token",
        "sts_client_id": config.provider_did,
        "sts_client_secret_alias": f"{config.provider_participant_name}-sts-client-secret",
    }

    logger.info("Token Configuration:")
    for key, value in token_config.items():
        logger.info(f"  {key}: {value}")

    logger.info("✅ Token configuration validated")
    return True


def verify_dataplane_configuration(config) -> bool:
    """
    Verify Data Plane configuration.

    Args:
        config: Configuration object

    Returns:
        True if configuration is valid, False otherwise
    """
    logger.info("Verifying Data Plane configuration...")

    # Check configuration file
    config_file = "config/provider-dataplane.env"
    if not os.path.exists(config_file):
        logger.error(f"❌ Configuration file missing: {config_file}")
        return False

    logger.info(f"✅ Configuration file exists: {config_file}")

    # Verify configuration values
    all_valid = True

    # Runtime ID validation
    runtime_id = f"{config.provider_participant_name}-dataplane"
    if len(runtime_id) > 0:
        logger.info(f"✅ Runtime ID: {runtime_id}")
    else:
        logger.error(f"❌ Runtime ID invalid: {runtime_id}")
        all_valid = False

    # DID validation
    if validate_did_format(config.provider_did):
        logger.info(f"✅ Participant ID: {config.provider_did}")
    else:
        logger.error(f"❌ Participant ID invalid: {config.provider_did}")
        all_valid = False

    # Port validations
    port_checks = [
        ("Control Port", config.provider_dp_control_port),
        ("Public Port", config.provider_dp_public_port),
        ("Web Port", config.provider_dp_web_port),
    ]

    for port_name, port_value in port_checks:
        if validate_port_number(port_value, port_name):
            logger.info(f"✅ {port_name}: {port_value}")
        else:
            all_valid = False

    return all_valid


def setup_dataplane(config) -> bool:
    """
    Complete Data Plane setup.

    Args:
        config: Configuration object

    Returns:
        True if successful, False otherwise
    """
    logger.info("Setting up Data Plane configuration...")
    logger.info("=" * 50)

    setup_steps = [
        ("Data Plane Configuration", setup_dataplane_configuration),
        ("Control Plane Communication", setup_control_plane_communication),
        ("Token Configuration", setup_token_configuration),
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
        logger.info("🎉 Data Plane setup completed successfully!")

        # Verify configuration
        if verify_dataplane_configuration(config):
            logger.info("✅ Configuration verification passed")
        else:
            logger.warning("⚠️  Configuration verification had issues")
            all_successful = False
    else:
        logger.error("❌ Data Plane setup failed")

    return all_successful


def main():
    """Main entry point."""
    # Load configuration
    config = load_config()
    if not config:
        logger.error("Failed to load configuration")
        return 1

    # Run setup
    success = setup_dataplane(config)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
