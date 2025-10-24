#!/usr/bin/env python3
"""
Generate Configuration Files for Provider Participant

This script generates environment configuration files for all provider participant
components based on the loaded configuration. It creates separate .env files for:
- Control Plane (provider-controlplane.env)
- Data Plane (provider-dataplane.env)
- Identity Hub (provider-identityhub.env)

Usage:
    python3 scripts/provider/generate_config.py

Environment Variables:
    All PROVIDER_* environment variables from config.py

Output:
    - config/provider-controlplane.env
    - config/provider-dataplane.env
    - config/provider-identityhub.env

Requirements:
    - Provider configuration loaded via config.py
"""

import logging
import os
import sys
import urllib.parse
from pathlib import Path

# Add the scripts directory to the path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from provider.config import load_config
except ImportError:
    print("ERROR: Could not import provider config")
    print("Make sure you're running from the project root directory")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def generate_controlplane_config(config) -> str:
    """
    Generate Control Plane environment configuration.

    Args:
        config: Loaded configuration object

    Returns:
        Environment file content as string
    """
    return f"""# ============================================================
# PROVIDER CONTROL PLANE CONFIGURATION
# ============================================================
# Generated automatically by scripts/provider/generate_config.py
# DO NOT EDIT MANUALLY - Changes will be overwritten

# ============================================================
# PARTICIPANT CONFIGURATION
# ============================================================
EDC_PARTICIPANT_ID={config.provider_did}
EDC_IAM_ISSUER_ID={config.provider_did}
EDC_IAM_DID_WEB_USE_HTTPS=false

# ============================================================
# WEB API CONFIGURATION
# ============================================================
WEB_HTTP_PORT={config.provider_cp_web_port}
WEB_HTTP_PATH=/api
WEB_HTTP_MANAGEMENT_PORT={config.provider_cp_management_port}
WEB_HTTP_MANAGEMENT_PATH=/api/management
WEB_HTTP_MANAGEMENT_AUTH_TYPE=tokenbased
WEB_HTTP_MANAGEMENT_AUTH_KEY={config.provider_management_api_key}
WEB_HTTP_CONTROL_PORT={config.provider_cp_control_port}
WEB_HTTP_CONTROL_PATH=/api/control
WEB_HTTP_PROTOCOL_PORT={config.provider_cp_protocol_port}
WEB_HTTP_PROTOCOL_PATH=/api/dsp
WEB_HTTP_CATALOG_PORT={config.provider_cp_catalog_port}
WEB_HTTP_CATALOG_PATH=/api/catalog
WEB_HTTP_CATALOG_AUTH_TYPE=tokenbased
WEB_HTTP_CATALOG_AUTH_KEY={config.provider_catalog_api_key}

# ============================================================
# DSP CONFIGURATION
# ============================================================
EDC_DSP_CALLBACK_ADDRESS=http://provider-controlplane:{config.provider_cp_protocol_port}/api/dsp

# ============================================================
# IAM & STS CONFIGURATION
# ============================================================
EDC_IAM_STS_PRIVATEKEY_ALIAS={config.provider_did}#key-1
EDC_IAM_STS_PUBLICKEY_ID={config.provider_did}#key-1
EDC_IAM_STS_OAUTH_TOKEN_URL=http://provider-identityhub:{config.provider_ih_sts_port}/api/sts/token
EDC_IAM_STS_OAUTH_CLIENT_ID={config.provider_did}
EDC_IAM_STS_OAUTH_CLIENT_SECRET_ALIAS={config.provider_participant_name}-sts-client-secret

# ============================================================
# VAULT CONFIGURATION
# ============================================================
EDC_VAULT_HASHICORP_URL=http://provider-vault:8200
EDC_VAULT_HASHICORP_TOKEN={config.provider_vault_token}

# ============================================================
# DATABASE CONFIGURATION
# ============================================================
EDC_DATASOURCE_DEFAULT_URL=jdbc:postgresql://provider-postgres:5432/provider_controlplane
EDC_DATASOURCE_DEFAULT_USER={config.provider_cp_db_user}
EDC_DATASOURCE_DEFAULT_PASSWORD={config.provider_cp_db_password}
EDC_SQL_SCHEMA_AUTOCREATE=true

# ============================================================
# CATALOG CONFIGURATION
# ============================================================
EDC_CATALOG_CACHE_EXECUTION_DELAY_SECONDS=10
EDC_CATALOG_CACHE_EXECUTION_PERIOD_SECONDS=10

# ============================================================
# PARTICIPANTS CONFIGURATION
# ============================================================
# Participants list file for catalog node resolver
EDC_MVD_PARTICIPANTS_LIST_FILE=/app/deployment/provider/participants.json

# ============================================================
# DEBUGGING (REMOVE IN PRODUCTION)
# ============================================================
JAVA_TOOL_OPTIONS=-agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address={config.provider_cp_debug_port}

# ============================================================
# PARTICIPANT REGISTRY
# ============================================================
# Note: Participant registry configuration will be added when implementing
# multi-participant scenarios. For now, using single participant setup.
"""


def generate_dataplane_config(config) -> str:
    """
    Generate Data Plane environment configuration.

    Args:
        config: Loaded configuration object

    Returns:
        Environment file content as string
    """
    return f"""# ============================================================
# PROVIDER DATA PLANE CONFIGURATION
# ============================================================
# Generated automatically by scripts/provider/generate_config.py
# DO NOT EDIT MANUALLY - Changes will be overwritten

# ============================================================
# RUNTIME CONFIGURATION
# ============================================================
EDC_HOSTNAME=provider-dataplane
EDC_RUNTIME_ID={config.provider_participant_name}-dataplane
EDC_PARTICIPANT_ID={config.provider_did}

# ============================================================
# TOKEN CONFIGURATION
# ============================================================
EDC_TRANSFER_PROXY_TOKEN_VERIFIER_PUBLICKEY_ALIAS={config.provider_did}#key-1
EDC_TRANSFER_PROXY_TOKEN_SIGNER_PRIVATEKEY_ALIAS={config.provider_did}#key-1

# ============================================================
# CONTROL PLANE COMMUNICATION
# ============================================================
EDC_DPF_SELECTOR_URL=http://provider-controlplane:{config.provider_cp_control_port}/api/control/v1/dataplanes

# ============================================================
# WEB API CONFIGURATION
# ============================================================
WEB_HTTP_PORT={config.provider_dp_web_port}
WEB_HTTP_PATH=/api
WEB_HTTP_CONTROL_PORT={config.provider_dp_control_port}
WEB_HTTP_CONTROL_PATH=/api/control
WEB_HTTP_PUBLIC_PORT={config.provider_dp_public_port}
WEB_HTTP_PUBLIC_PATH=/api/public

# ============================================================
# VAULT CONFIGURATION
# ============================================================
EDC_VAULT_HASHICORP_URL=http://provider-vault:8200
EDC_VAULT_HASHICORP_TOKEN={config.provider_vault_token}

# ============================================================
# DATABASE CONFIGURATION
# ============================================================
EDC_DATASOURCE_DEFAULT_URL=jdbc:postgresql://provider-postgres:5432/provider_dataplane
EDC_DATASOURCE_DEFAULT_USER={config.provider_dp_db_user}
EDC_DATASOURCE_DEFAULT_PASSWORD={config.provider_dp_db_password}
EDC_SQL_SCHEMA_AUTOCREATE=true

# ============================================================
# STS CONFIGURATION
# ============================================================
EDC_IAM_STS_OAUTH_TOKEN_URL=http://provider-identityhub:{config.provider_ih_sts_port}/api/sts/token
EDC_IAM_STS_OAUTH_CLIENT_ID={config.provider_did}
EDC_IAM_STS_OAUTH_CLIENT_SECRET_ALIAS={config.provider_participant_name}-sts-client-secret

# ============================================================
# DEBUGGING (REMOVE IN PRODUCTION)
# ============================================================
JAVA_TOOL_OPTIONS=-agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address={config.provider_dp_debug_port}
"""


def generate_identityhub_config(config) -> str:
    """
    Generate Identity Hub environment configuration.

    Args:
        config: Loaded configuration object

    Returns:
        Environment file content as string
    """
    return f"""# ============================================================
# PROVIDER IDENTITY HUB CONFIGURATION
# ============================================================
# Generated automatically by scripts/provider/generate_config.py
# DO NOT EDIT MANUALLY - Changes will be overwritten

# ============================================================
# IDENTITY HUB CONFIGURATION
# ============================================================
EDC_IH_IAM_ID={config.provider_did}
EDC_IAM_DID_WEB_USE_HTTPS=false
EDC_IH_IAM_PUBLICKEY_ALIAS={config.provider_participant_name}-publickey

# ============================================================
# AUTHENTICATION
# ============================================================
# Superuser API key for Identity API seeding operations
# Format: base64(username).base64(password)
# Default: super-user / super-secret-key
# ⚠️  CRITICAL: CHANGE FOR PRODUCTION!
EDC_IH_API_SUPERUSER_KEY={config.provider_identity_superuser_key}

# ============================================================
# API CONFIGURATION
# ============================================================
WEB_HTTP_PORT={config.provider_ih_web_port}
WEB_HTTP_PATH=/api
WEB_HTTP_IDENTITY_PORT={config.provider_ih_identity_port}
WEB_HTTP_IDENTITY_PATH=/api/identity
WEB_HTTP_IDENTITY_AUTH_KEY={config.provider_identity_api_key}
WEB_HTTP_CREDENTIALS_PORT={config.provider_ih_credentials_port}
WEB_HTTP_CREDENTIALS_PATH=/api/credentials
WEB_HTTP_DID_PORT={config.provider_ih_did_port}
WEB_HTTP_DID_PATH=/
WEB_HTTP_STS_PORT={config.provider_ih_sts_port}
WEB_HTTP_STS_PATH=/api/sts

# ============================================================
# STS CONFIGURATION
# ============================================================
EDC_IAM_STS_PRIVATEKEY_ALIAS=key-1
EDC_IAM_STS_PUBLICKEY_ID=key-1

# ============================================================
# CREDENTIALS CONFIGURATION
# ============================================================
EDC_MVD_CREDENTIALS_PATH=/etc/credentials/

# ============================================================
# VAULT CONFIGURATION
# ============================================================
EDC_VAULT_HASHICORP_URL=http://provider-vault:8200
EDC_VAULT_HASHICORP_TOKEN={config.provider_vault_token}

# ============================================================
# DATABASE CONFIGURATION
# ============================================================
EDC_DATASOURCE_DEFAULT_URL=jdbc:postgresql://provider-postgres:5432/provider_identity
EDC_DATASOURCE_DEFAULT_USER={config.provider_ih_db_user}
EDC_DATASOURCE_DEFAULT_PASSWORD={config.provider_ih_db_password}
EDC_SQL_SCHEMA_AUTOCREATE=true

# ============================================================
# ACCESS TOKEN VALIDATION
# ============================================================
EDC_IAM_ACCESSTOKEN_JTI_VALIDATION=true

# ============================================================
# DEBUGGING (REMOVE IN PRODUCTION)
# ============================================================
JAVA_TOOL_OPTIONS=-agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address={config.provider_ih_debug_port}
"""


def write_config_file(filename: str, content: str) -> bool:
    """
    Write configuration content to file.

    Args:
        filename: Output filename
        content: Configuration content

    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure config directory exists
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)

        # Write configuration file
        config_file = config_dir / filename
        with open(config_file, "w") as f:
            f.write(content)

        logger.info(f"✓ Generated: {config_file}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to write {filename}: {str(e)}")
        return False


def generate_participants_json(config) -> str:
    """
    Generate participants.json file for catalog node resolver.

    This file contains a mapping of participant names to their DIDs,
    used by the catalog node resolver to discover other participants.

    Args:
        config: Loaded configuration object

    Returns:
        JSON content as string
    """
    import json

    # Build participants dictionary
    # Consumer DID is derived from config
    consumer_host_port = f"{config.provider_public_host}:7083"
    encoded_consumer_host = urllib.parse.quote(consumer_host_port, safe="")
    consumer_did = f"did:web:{encoded_consumer_host}:consumer"

    participants = {
        "consumer": consumer_did,
        "provider": config.provider_did,
    }

    return json.dumps(participants, indent=2) + "\n"


def write_participants_file(config) -> bool:
    """
    Write participants.json file to deployment directory.

    Args:
        config: Loaded configuration object

    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure deployment/provider directory exists
        deployment_dir = Path("deployment/provider")
        deployment_dir.mkdir(parents=True, exist_ok=True)

        # Generate participants JSON
        participants_json = generate_participants_json(config)

        # Write participants file
        participants_file = deployment_dir / "participants.json"
        with open(participants_file, "w") as f:
            f.write(participants_json)

        logger.info(f"✓ Generated: {participants_file}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to write participants.json: {str(e)}")
        return False


def main():
    """Main entry point."""
    logger.info("Generating Provider Participant configuration files")
    logger.info("=" * 60)

    # Load configuration
    config = load_config()
    if not config:
        logger.error("Failed to load configuration")
        return 1

    logger.info("Configuration loaded successfully")
    logger.info(f"Provider DID: {config.provider_did}")
    logger.info("")

    # Generate configuration files
    success = True

    # Control Plane configuration
    logger.info("Generating Control Plane configuration...")
    cp_config = generate_controlplane_config(config)
    if not write_config_file("provider-controlplane.env", cp_config):
        success = False

    # Data Plane configuration
    logger.info("Generating Data Plane configuration...")
    dp_config = generate_dataplane_config(config)
    if not write_config_file("provider-dataplane.env", dp_config):
        success = False

    # Identity Hub configuration
    logger.info("Generating Identity Hub configuration...")
    ih_config = generate_identityhub_config(config)
    if not write_config_file("provider-identityhub.env", ih_config):
        success = False

    # Participants file
    logger.info("Generating participants list...")
    if not write_participants_file(config):
        success = False

    logger.info("")
    if success:
        logger.info("🎉 All configuration files generated successfully!")
        logger.info("")
        logger.info("Generated files:")
        logger.info("  - config/provider-controlplane.env")
        logger.info("  - config/provider-dataplane.env")
        logger.info("  - config/provider-identityhub.env")
        logger.info("  - deployment/provider/participants.json")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Review the generated configuration files")
        logger.info("  2. Start the provider services with Docker Compose")
        logger.info("  3. Verify all components are healthy")
        return 0
    else:
        logger.error("❌ Failed to generate some configuration files")
        return 1


if __name__ == "__main__":
    sys.exit(main())
