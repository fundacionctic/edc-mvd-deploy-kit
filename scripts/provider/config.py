#!/usr/bin/env python3
"""
Configuration Management for Provider Participant

This standalone script handles configuration loading, validation, and provides
constants used across all Provider participant scripts.

Environment Variables Required:
    PROVIDER_PUBLIC_HOST: Public hostname for DID resolution
    PROVIDER_PARTICIPANT_NAME: Participant name (default: provider)
    PROVIDER_CP_*: Control Plane port configuration
    PROVIDER_DP_*: Data Plane port configuration
    PROVIDER_IH_*: Identity Hub port configuration (including PROVIDER_IH_DID_PORT for DID generation)
    PROVIDER_*_DB_*: Database configuration
    PROVIDER_VAULT_TOKEN: Vault authentication token
    PROVIDER_*_API_KEY: API authentication keys
"""

import base64
import logging
import os
import sys
import urllib.parse
from typing import Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


# ============================================================
# ENVIRONMENT VARIABLE NAMES
# ============================================================

# Core Configuration
ENV_PROVIDER_PUBLIC_HOST = "PROVIDER_PUBLIC_HOST"
ENV_PROVIDER_PARTICIPANT_NAME = "PROVIDER_PARTICIPANT_NAME"

# Control Plane Ports
ENV_PROVIDER_CP_WEB_PORT = "PROVIDER_CP_WEB_PORT"
ENV_PROVIDER_CP_MANAGEMENT_PORT = "PROVIDER_CP_MANAGEMENT_PORT"
ENV_PROVIDER_CP_PROTOCOL_PORT = "PROVIDER_CP_PROTOCOL_PORT"
ENV_PROVIDER_CP_CONTROL_PORT = "PROVIDER_CP_CONTROL_PORT"
ENV_PROVIDER_CP_CATALOG_PORT = "PROVIDER_CP_CATALOG_PORT"
ENV_PROVIDER_CP_DEBUG_PORT = "PROVIDER_CP_DEBUG_PORT"

# Data Plane Ports
ENV_PROVIDER_DP_WEB_PORT = "PROVIDER_DP_WEB_PORT"
ENV_PROVIDER_DP_CONTROL_PORT = "PROVIDER_DP_CONTROL_PORT"
ENV_PROVIDER_DP_PUBLIC_PORT = "PROVIDER_DP_PUBLIC_PORT"
ENV_PROVIDER_DP_DEBUG_PORT = "PROVIDER_DP_DEBUG_PORT"

# Identity Hub Ports
ENV_PROVIDER_IH_WEB_PORT = "PROVIDER_IH_WEB_PORT"
ENV_PROVIDER_IH_CREDENTIALS_PORT = "PROVIDER_IH_CREDENTIALS_PORT"
ENV_PROVIDER_IH_STS_PORT = "PROVIDER_IH_STS_PORT"
ENV_PROVIDER_IH_DID_PORT = "PROVIDER_IH_DID_PORT"
ENV_PROVIDER_IH_IDENTITY_PORT = "PROVIDER_IH_IDENTITY_PORT"
ENV_PROVIDER_IH_DEBUG_PORT = "PROVIDER_IH_DEBUG_PORT"

# Database Configuration
ENV_PROVIDER_DB_NAME = "PROVIDER_DB_NAME"
ENV_PROVIDER_DB_USER = "PROVIDER_DB_USER"
ENV_PROVIDER_DB_PASSWORD = "PROVIDER_DB_PASSWORD"
ENV_PROVIDER_CP_DB_USER = "PROVIDER_CP_DB_USER"
ENV_PROVIDER_CP_DB_PASSWORD = "PROVIDER_CP_DB_PASSWORD"
ENV_PROVIDER_DP_DB_USER = "PROVIDER_DP_DB_USER"
ENV_PROVIDER_DP_DB_PASSWORD = "PROVIDER_DP_DB_PASSWORD"
ENV_PROVIDER_IH_DB_USER = "PROVIDER_IH_DB_USER"
ENV_PROVIDER_IH_DB_PASSWORD = "PROVIDER_IH_DB_PASSWORD"

# Vault Configuration
ENV_PROVIDER_VAULT_TOKEN = "PROVIDER_VAULT_TOKEN"

# Authentication
ENV_PROVIDER_MANAGEMENT_API_KEY = "PROVIDER_MANAGEMENT_API_KEY"
ENV_PROVIDER_CATALOG_API_KEY = "PROVIDER_CATALOG_API_KEY"
ENV_PROVIDER_IDENTITY_API_KEY = "PROVIDER_IDENTITY_API_KEY"
ENV_PROVIDER_IDENTITY_SUPERUSER_KEY = "PROVIDER_IDENTITY_SUPERUSER_KEY"

# Issuer Integration
ENV_ISSUER_PUBLIC_HOST = "ISSUER_PUBLIC_HOST"
ENV_ISSUER_HTTP_PORT = "ISSUER_HTTP_PORT"
ENV_ISSUER_ISSUANCE_PORT = "ISSUER_ISSUANCE_PORT"
ENV_ISSUER_ADMIN_PORT = "ISSUER_ADMIN_PORT"
ENV_ISSUER_DID_API_PORT = "ISSUER_DID_API_PORT"
ENV_ISSUER_SUPERUSER_KEY = "ISSUER_SUPERUSER_KEY"


# ============================================================
# DEFAULT VALUES
# ============================================================

DEFAULT_PROVIDER_PUBLIC_HOST = "host.docker.internal"
DEFAULT_PROVIDER_PARTICIPANT_NAME = "provider"

# Control Plane Defaults
DEFAULT_PROVIDER_CP_WEB_PORT = "8080"
DEFAULT_PROVIDER_CP_MANAGEMENT_PORT = "8081"
DEFAULT_PROVIDER_CP_PROTOCOL_PORT = "8082"
DEFAULT_PROVIDER_CP_CONTROL_PORT = "8083"
DEFAULT_PROVIDER_CP_CATALOG_PORT = "8084"
DEFAULT_PROVIDER_CP_DEBUG_PORT = "1044"

# Data Plane Defaults
DEFAULT_PROVIDER_DP_WEB_PORT = "8090"
DEFAULT_PROVIDER_DP_CONTROL_PORT = "8093"
DEFAULT_PROVIDER_DP_PUBLIC_PORT = "11002"
DEFAULT_PROVIDER_DP_DEBUG_PORT = "1045"

# Identity Hub Defaults
DEFAULT_PROVIDER_IH_WEB_PORT = "7000"
DEFAULT_PROVIDER_IH_CREDENTIALS_PORT = "7001"
DEFAULT_PROVIDER_IH_STS_PORT = "7002"
DEFAULT_PROVIDER_IH_DID_PORT = "7003"
DEFAULT_PROVIDER_IH_IDENTITY_PORT = "7005"
DEFAULT_PROVIDER_IH_DEBUG_PORT = "1046"

# Database Defaults
DEFAULT_PROVIDER_DB_NAME = "provider"
DEFAULT_PROVIDER_DB_USER = "provider"
DEFAULT_PROVIDER_DB_PASSWORD = "provider"
DEFAULT_PROVIDER_CP_DB_USER = "provider_cp"
DEFAULT_PROVIDER_CP_DB_PASSWORD = "provider_cp"
DEFAULT_PROVIDER_DP_DB_USER = "provider_dp"
DEFAULT_PROVIDER_DP_DB_PASSWORD = "provider_dp"
DEFAULT_PROVIDER_IH_DB_USER = "provider_ih"
DEFAULT_PROVIDER_IH_DB_PASSWORD = "provider_ih"

# Vault Defaults
DEFAULT_PROVIDER_VAULT_TOKEN = "root"

# Authentication Defaults
DEFAULT_PROVIDER_MANAGEMENT_API_KEY = "password"
DEFAULT_PROVIDER_CATALOG_API_KEY = "password"
DEFAULT_PROVIDER_IDENTITY_API_KEY = "password"
DEFAULT_PROVIDER_IDENTITY_SUPERUSER_KEY = "c3VwZXItdXNlcg==.c3VwZXItc2VjcmV0LWtleQo="

# Issuer Integration Defaults
DEFAULT_ISSUER_PUBLIC_HOST = "host.docker.internal"
DEFAULT_ISSUER_HTTP_PORT = "10010"
DEFAULT_ISSUER_ISSUANCE_PORT = "10012"
DEFAULT_ISSUER_ADMIN_PORT = "10013"
DEFAULT_ISSUER_DID_API_PORT = "10016"  # Using built-in DID API, not NGINX
DEFAULT_ISSUER_SUPERUSER_KEY = "c3VwZXItdXNlcg==.c3VwZXItc2VjcmV0LWtleQo="


# ============================================================
# VALIDATION CONSTANTS
# ============================================================

MIN_PORT_NUMBER = 1
MAX_PORT_NUMBER = 65535
MASK_CHARACTER = "*"
MASK_LENGTH = 20

# ============================================================
# HTTP CONSTANTS
# ============================================================

HTTP_TIMEOUT_SECONDS = 30
HTTP_RETRY_COUNT = 3
HTTP_RETRY_DELAY_SECONDS = 5


class Config:
    """
    Configuration class for Provider Participant operations.

    Loads and validates environment variables, provides helper methods
    for constructing URLs and API endpoints.
    """

    def __init__(self):
        """Initialize configuration from environment variables."""
        # Core Configuration
        self.provider_public_host = self._get_env(
            ENV_PROVIDER_PUBLIC_HOST, DEFAULT_PROVIDER_PUBLIC_HOST
        )
        self.provider_participant_name = self._get_env(
            ENV_PROVIDER_PARTICIPANT_NAME, DEFAULT_PROVIDER_PARTICIPANT_NAME
        )

        # Control Plane Ports
        self.provider_cp_web_port = self._get_env(
            ENV_PROVIDER_CP_WEB_PORT, DEFAULT_PROVIDER_CP_WEB_PORT
        )
        self.provider_cp_management_port = self._get_env(
            ENV_PROVIDER_CP_MANAGEMENT_PORT, DEFAULT_PROVIDER_CP_MANAGEMENT_PORT
        )
        self.provider_cp_protocol_port = self._get_env(
            ENV_PROVIDER_CP_PROTOCOL_PORT, DEFAULT_PROVIDER_CP_PROTOCOL_PORT
        )
        self.provider_cp_control_port = self._get_env(
            ENV_PROVIDER_CP_CONTROL_PORT, DEFAULT_PROVIDER_CP_CONTROL_PORT
        )
        self.provider_cp_catalog_port = self._get_env(
            ENV_PROVIDER_CP_CATALOG_PORT, DEFAULT_PROVIDER_CP_CATALOG_PORT
        )
        self.provider_cp_debug_port = self._get_env(
            ENV_PROVIDER_CP_DEBUG_PORT, DEFAULT_PROVIDER_CP_DEBUG_PORT
        )

        # Data Plane Ports
        self.provider_dp_web_port = self._get_env(
            ENV_PROVIDER_DP_WEB_PORT, DEFAULT_PROVIDER_DP_WEB_PORT
        )
        self.provider_dp_control_port = self._get_env(
            ENV_PROVIDER_DP_CONTROL_PORT, DEFAULT_PROVIDER_DP_CONTROL_PORT
        )
        self.provider_dp_public_port = self._get_env(
            ENV_PROVIDER_DP_PUBLIC_PORT, DEFAULT_PROVIDER_DP_PUBLIC_PORT
        )
        self.provider_dp_debug_port = self._get_env(
            ENV_PROVIDER_DP_DEBUG_PORT, DEFAULT_PROVIDER_DP_DEBUG_PORT
        )

        # Identity Hub Ports
        self.provider_ih_web_port = self._get_env(
            ENV_PROVIDER_IH_WEB_PORT, DEFAULT_PROVIDER_IH_WEB_PORT
        )
        self.provider_ih_credentials_port = self._get_env(
            ENV_PROVIDER_IH_CREDENTIALS_PORT, DEFAULT_PROVIDER_IH_CREDENTIALS_PORT
        )
        self.provider_ih_sts_port = self._get_env(
            ENV_PROVIDER_IH_STS_PORT, DEFAULT_PROVIDER_IH_STS_PORT
        )
        self.provider_ih_did_port = self._get_env(
            ENV_PROVIDER_IH_DID_PORT, DEFAULT_PROVIDER_IH_DID_PORT
        )
        self.provider_ih_identity_port = self._get_env(
            ENV_PROVIDER_IH_IDENTITY_PORT, DEFAULT_PROVIDER_IH_IDENTITY_PORT
        )
        self.provider_ih_debug_port = self._get_env(
            ENV_PROVIDER_IH_DEBUG_PORT, DEFAULT_PROVIDER_IH_DEBUG_PORT
        )

        # Database Configuration
        self.provider_db_name = self._get_env(
            ENV_PROVIDER_DB_NAME, DEFAULT_PROVIDER_DB_NAME
        )
        self.provider_db_user = self._get_env(
            ENV_PROVIDER_DB_USER, DEFAULT_PROVIDER_DB_USER
        )
        self.provider_db_password = self._get_env(
            ENV_PROVIDER_DB_PASSWORD, DEFAULT_PROVIDER_DB_PASSWORD
        )
        self.provider_cp_db_user = self._get_env(
            ENV_PROVIDER_CP_DB_USER, DEFAULT_PROVIDER_CP_DB_USER
        )
        self.provider_cp_db_password = self._get_env(
            ENV_PROVIDER_CP_DB_PASSWORD, DEFAULT_PROVIDER_CP_DB_PASSWORD
        )
        self.provider_dp_db_user = self._get_env(
            ENV_PROVIDER_DP_DB_USER, DEFAULT_PROVIDER_DP_DB_USER
        )
        self.provider_dp_db_password = self._get_env(
            ENV_PROVIDER_DP_DB_PASSWORD, DEFAULT_PROVIDER_DP_DB_PASSWORD
        )
        self.provider_ih_db_user = self._get_env(
            ENV_PROVIDER_IH_DB_USER, DEFAULT_PROVIDER_IH_DB_USER
        )
        self.provider_ih_db_password = self._get_env(
            ENV_PROVIDER_IH_DB_PASSWORD, DEFAULT_PROVIDER_IH_DB_PASSWORD
        )

        # Vault Configuration
        self.provider_vault_token = self._get_env(
            ENV_PROVIDER_VAULT_TOKEN, DEFAULT_PROVIDER_VAULT_TOKEN
        )

        # Authentication
        self.provider_management_api_key = self._get_env(
            ENV_PROVIDER_MANAGEMENT_API_KEY, DEFAULT_PROVIDER_MANAGEMENT_API_KEY
        )
        self.provider_catalog_api_key = self._get_env(
            ENV_PROVIDER_CATALOG_API_KEY, DEFAULT_PROVIDER_CATALOG_API_KEY
        )
        self.provider_identity_api_key = self._get_env(
            ENV_PROVIDER_IDENTITY_API_KEY, DEFAULT_PROVIDER_IDENTITY_API_KEY
        )
        self.provider_identity_superuser_key = self._get_env(
            ENV_PROVIDER_IDENTITY_SUPERUSER_KEY, DEFAULT_PROVIDER_IDENTITY_SUPERUSER_KEY
        )

        # Issuer Integration
        self.issuer_public_host = self._get_env(
            ENV_ISSUER_PUBLIC_HOST, DEFAULT_ISSUER_PUBLIC_HOST
        )
        self.issuer_http_port = self._get_env(
            ENV_ISSUER_HTTP_PORT, DEFAULT_ISSUER_HTTP_PORT
        )
        self.issuer_issuance_port = self._get_env(
            ENV_ISSUER_ISSUANCE_PORT, DEFAULT_ISSUER_ISSUANCE_PORT
        )
        self.issuer_admin_port = self._get_env(
            ENV_ISSUER_ADMIN_PORT, DEFAULT_ISSUER_ADMIN_PORT
        )
        self.issuer_did_api_port = self._get_env(
            ENV_ISSUER_DID_API_PORT, DEFAULT_ISSUER_DID_API_PORT
        )
        self.issuer_superuser_key = self._get_env(
            ENV_ISSUER_SUPERUSER_KEY, DEFAULT_ISSUER_SUPERUSER_KEY
        )

        # Generate DIDs dynamically
        self.provider_did = self._generate_provider_did()

        # Construct base URLs using proper hostnames
        self.provider_cp_management_url = self._build_url(
            self.provider_public_host, self.provider_cp_management_port
        )
        self.provider_cp_protocol_url = self._build_url(
            self.provider_public_host, self.provider_cp_protocol_port
        )
        self.provider_cp_catalog_url = self._build_url(
            self.provider_public_host, self.provider_cp_catalog_port
        )
        self.provider_dp_public_url = self._build_url(
            self.provider_public_host, self.provider_dp_public_port
        )
        self.provider_ih_credentials_url = self._build_url(
            self.provider_public_host, self.provider_ih_credentials_port
        )
        self.provider_ih_sts_url = self._build_url(
            self.provider_public_host, self.provider_ih_sts_port
        )
        self.provider_ih_identity_url = self._build_url(
            self.provider_public_host, self.provider_ih_identity_port
        )
        self.issuer_admin_url = self._build_url(
            self.issuer_public_host, self.issuer_admin_port
        )
        self.issuer_issuance_url = self._build_url(
            self.issuer_public_host, self.issuer_issuance_port
        )

        self._log_configuration()

    def _get_env(self, var_name: str, default: str) -> str:
        """
        Get environment variable with fallback to default.

        Args:
            var_name: Environment variable name
            default: Default value if not set

        Returns:
            Environment variable value or default
        """
        value = os.environ.get(var_name, default)
        if value == default:
            logger.debug(f"Using default for {var_name}: {default}")
        return value

    def _generate_provider_did(self) -> str:
        """
        Generate provider DID based on hostname and IdentityHub DID port.

        Returns:
            Provider DID string
        """
        if self.provider_ih_did_port in ["443", "80"]:
            # Standard ports don't need URL encoding
            return (
                f"did:web:{self.provider_public_host}:{self.provider_participant_name}"
            )
        else:
            # Non-standard ports need URL encoding
            host_with_port = f"{self.provider_public_host}:{self.provider_ih_did_port}"
            encoded_host = urllib.parse.quote(host_with_port, safe="")
            return f"did:web:{encoded_host}:{self.provider_participant_name}"

    def _build_url(self, host: str, port: str) -> str:
        """
        Build URL with given host and port.

        Args:
            host: Hostname
            port: Port number

        Returns:
            Complete URL
        """
        return f"http://{host}:{port}"

    def _log_configuration(self) -> None:
        """Log configuration details with sensitive data masked."""
        logger.info(
            f"Provider Participant configuration loaded:\n"
            f"  Provider DID: {self.provider_did}\n"
            f"  Public Host: {self.provider_public_host}\n"
            f"  Participant Name: {self.provider_participant_name}\n"
            f"  Management API: {self.provider_cp_management_url}\n"
            f"  DSP Protocol: {self.provider_cp_protocol_url}\n"
            f"  Catalog API: {self.provider_cp_catalog_url}\n"
            f"  Public Data API: {self.provider_dp_public_url}\n"
            f"  Credentials API: {self.provider_ih_credentials_url}\n"
            f"  STS API: {self.provider_ih_sts_url}\n"
            f"  Issuer Admin API: {self.issuer_admin_url}\n"
            f"  API Keys: {MASK_CHARACTER * MASK_LENGTH}[MASKED]"
        )

    def get_management_headers(self) -> Dict[str, str]:
        """
        Get HTTP headers for Management API requests.

        Returns:
            Dictionary of HTTP headers including authentication
        """
        return {
            "Content-Type": "application/json",
            "X-Api-Key": self.provider_management_api_key,
        }

    def get_catalog_headers(self) -> Dict[str, str]:
        """
        Get HTTP headers for Catalog API requests.

        Returns:
            Dictionary of HTTP headers including authentication
        """
        return {
            "Content-Type": "application/json",
            "X-Api-Key": self.provider_catalog_api_key,
        }

    def get_identity_headers(self) -> Dict[str, str]:
        """
        Get HTTP headers for Identity Hub API requests.

        Returns:
            Dictionary of HTTP headers including authentication
        """
        return {
            "Content-Type": "application/json",
            "X-Api-Key": self.provider_identity_api_key,
        }

    def get_identity_superuser_headers(self) -> Dict[str, str]:
        """
        Get HTTP headers for Identity Hub seeding operations (Identity API).

        The Identity API requires superuser authentication for participant
        context creation and other administrative operations.

        Returns:
            Dictionary of HTTP headers including superuser authentication
        """
        return {
            "Content-Type": "application/json",
            "X-Api-Key": self.provider_identity_superuser_key,
        }

    def get_issuer_headers(self) -> Dict[str, str]:
        """
        Get HTTP headers for Issuer service API requests.

        Returns:
            Dictionary of HTTP headers including authentication
        """
        return {
            "Content-Type": "application/json",
            "X-Api-Key": self.issuer_superuser_key,
        }

    def get_health_urls(self) -> Dict[str, str]:
        """
        Get health check endpoint URLs for all components.

        Returns:
            Dictionary mapping component names to health URLs
        """
        return {
            "controlplane": f"{self.provider_cp_management_url}/api/check/health",
            "dataplane": f"{self._build_url(self.provider_public_host, self.provider_dp_web_port)}/api/check/health",
            "identityhub": f"{self._build_url(self.provider_public_host, self.provider_ih_web_port)}/api/check/health",
            "did-api": f"{self._build_url(self.provider_public_host, self.provider_ih_did_port)}/.well-known/did.json",
        }

    def validate(self) -> bool:
        """
        Validate configuration.

        Checks that all required configuration values are present and valid.

        Returns:
            True if valid, False otherwise
        """
        if not self._validate_required_fields():
            return False

        if not self._validate_ports():
            return False

        logger.info("Configuration validation successful")
        return True

    def _validate_required_fields(self) -> bool:
        """
        Validate that all required fields are present and non-empty.

        Returns:
            True if all required fields are valid, False otherwise
        """
        required_fields = [
            ("provider_public_host", self.provider_public_host),
            ("provider_participant_name", self.provider_participant_name),
            ("provider_ih_did_port", self.provider_ih_did_port),
            ("provider_cp_management_port", self.provider_cp_management_port),
            ("provider_dp_public_port", self.provider_dp_public_port),
            ("provider_ih_credentials_port", self.provider_ih_credentials_port),
        ]

        for field_name, field_value in required_fields:
            if not field_value or field_value.strip() == "":
                logger.error(f"Configuration validation failed: {field_name} is empty")
                return False
        return True

    def _validate_port(self, port_name: str, port_value: str) -> bool:
        """
        Validate that a port value is numeric and within valid range.

        Args:
            port_name: Name of the port for error reporting
            port_value: Port value to validate

        Returns:
            True if port is valid, False otherwise
        """
        try:
            port = int(port_value)
            if port < MIN_PORT_NUMBER or port > MAX_PORT_NUMBER:
                logger.error(
                    f"Invalid {port_name}: {port} (must be between {MIN_PORT_NUMBER}-{MAX_PORT_NUMBER})"
                )
                return False
            return True
        except ValueError:
            logger.error(f"{port_name} is not a number: {port_value}")
            return False

    def _validate_ports(self) -> bool:
        """
        Validate all port configurations.

        Returns:
            True if all ports are valid, False otherwise
        """
        ports_to_validate = [
            ("provider_cp_web_port", self.provider_cp_web_port),
            ("provider_cp_management_port", self.provider_cp_management_port),
            ("provider_cp_protocol_port", self.provider_cp_protocol_port),
            ("provider_cp_control_port", self.provider_cp_control_port),
            ("provider_cp_catalog_port", self.provider_cp_catalog_port),
            ("provider_dp_web_port", self.provider_dp_web_port),
            ("provider_dp_control_port", self.provider_dp_control_port),
            ("provider_dp_public_port", self.provider_dp_public_port),
            ("provider_ih_web_port", self.provider_ih_web_port),
            ("provider_ih_credentials_port", self.provider_ih_credentials_port),
            ("provider_ih_sts_port", self.provider_ih_sts_port),
            ("provider_ih_did_port", self.provider_ih_did_port),
            ("provider_ih_identity_port", self.provider_ih_identity_port),
        ]

        return all(
            self._validate_port(port_name, port_value)
            for port_name, port_value in ports_to_validate
        )


def load_config() -> Optional[Config]:
    """
    Load and validate configuration.

    Returns:
        Config instance if successful, None if validation fails
    """
    try:
        config = Config()
        if config.validate():
            return config
        else:
            logger.error("Configuration validation failed")
            return None
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return None


if __name__ == "__main__":
    # Test configuration loading
    config = load_config()
    if config:
        logger.info("Configuration loaded and validated successfully")
        sys.exit(0)
    else:
        logger.error("Configuration loading failed")
        sys.exit(1)
