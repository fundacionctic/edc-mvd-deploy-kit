#!/usr/bin/env python3
"""
Configuration Management for Issuer Service Seeding

This standalone script handles configuration loading, validation, and provides
constants used across all Issuer seeding scripts.

Environment Variables Required:
    ISSUER_ADMIN_PORT: Admin API port (default: 10013)
    ISSUER_PUBLIC_HOST: Public hostname for DID
    ISSUER_DID_PORT: DID server port
    ISSUER_SUPERUSER_KEY: Base64-encoded admin API key
    PARTICIPANT_DID: Consumer participant DID
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

ENV_ISSUER_ADMIN_PORT = "ISSUER_ADMIN_PORT"
ENV_ISSUER_PUBLIC_HOST = "ISSUER_PUBLIC_HOST"
ENV_ISSUER_DID_PORT = "ISSUER_DID_PORT"
ENV_ISSUER_SUPERUSER_KEY = "ISSUER_SUPERUSER_KEY"
ENV_PARTICIPANT_DID = "PARTICIPANT_DID"
ENV_ISSUER_HTTP_PORT = "ISSUER_HTTP_PORT"

# ============================================================
# DEFAULT VALUES
# ============================================================

DEFAULT_ISSUER_ADMIN_PORT = "10013"
DEFAULT_ISSUER_HTTP_PORT = "10010"
DEFAULT_ISSUER_PUBLIC_HOST = "host.docker.internal"
DEFAULT_ISSUER_DID_PORT = "9876"
DEFAULT_ISSUER_SUPERUSER_KEY = "c3VwZXItdXNlcg==.c3VwZXItc2VjcmV0LWtleQo="
DEFAULT_CONSUMER_DID_TEMPLATE = "did:web:{host}%3A7083:consumer"
DEFAULT_PROVIDER_DID_TEMPLATE = "did:web:{host}%3A7093:provider"

# ============================================================
# VALIDATION CONSTANTS
# ============================================================

MIN_PORT_NUMBER = 1
MAX_PORT_NUMBER = 65535
MASK_CHARACTER = "*"
MASK_LENGTH = 20

# ============================================================
# API ENDPOINTS
# ============================================================

API_PATH_HEALTH = "/api/check/health"
API_PATH_HOLDERS = "/api/admin/v1alpha/participants/{context}/holders"
API_PATH_ATTESTATIONS = "/api/admin/v1alpha/participants/{context}/attestations"
API_PATH_CREDENTIALS = "/api/admin/v1alpha/participants/{context}/credentialdefinitions"

# Query endpoints (based on Postman collection analysis)
API_PATH_QUERY_ATTESTATIONS = (
    "/api/admin/v1alpha/participants/{context}/attestations/query"
)
API_PATH_QUERY_CREDENTIALS = (
    "/api/admin/v1alpha/participants/{context}/credentialdefinitions/query"
)
API_PATH_QUERY_PARTICIPANTS = "/api/identity/v1alpha/participants"

# ============================================================
# HTTP CONSTANTS
# ============================================================

HTTP_TIMEOUT_SECONDS = 30
HTTP_RETRY_COUNT = 3
HTTP_RETRY_DELAY_SECONDS = 5

# ============================================================
# CREDENTIAL TYPES
# ============================================================

CREDENTIAL_TYPE_MEMBERSHIP = "MembershipCredential"
CREDENTIAL_TYPE_DATA_PROCESSOR = "DataProcessorCredential"

# ============================================================
# ATTESTATION TYPES
# ============================================================

ATTESTATION_TYPE_DEMO = "demo"
ATTESTATION_TYPE_DATABASE = "database"

# ============================================================
# DATABASE CONFIGURATION
# ============================================================

DB_DATASOURCE_NAME = "membership"
DB_TABLE_MEMBERSHIP = "membership_attestations"
DB_TABLE_DATA_PROCESSOR = "data_processor_attestations"
DB_COLUMN_HOLDER_ID = "holder_id"

# ============================================================
# CREDENTIAL FORMATS
# ============================================================

CREDENTIAL_FORMAT_JWT = "VC1_0_JWT"


class Config:
    """
    Configuration class for Issuer Service seeding operations.

    Loads and validates environment variables, provides helper methods
    for constructing URLs and API endpoints.
    """

    def __init__(self):
        """Initialize configuration from environment variables."""
        self.issuer_admin_port = self._get_env(
            ENV_ISSUER_ADMIN_PORT, DEFAULT_ISSUER_ADMIN_PORT
        )
        self.issuer_http_port = self._get_env(
            ENV_ISSUER_HTTP_PORT, DEFAULT_ISSUER_HTTP_PORT
        )
        self.issuer_public_host = self._get_env(
            ENV_ISSUER_PUBLIC_HOST, DEFAULT_ISSUER_PUBLIC_HOST
        )
        self.issuer_did_port = self._get_env(
            ENV_ISSUER_DID_PORT, DEFAULT_ISSUER_DID_PORT
        )
        self.issuer_superuser_key = self._get_env(
            ENV_ISSUER_SUPERUSER_KEY, DEFAULT_ISSUER_SUPERUSER_KEY
        )

        # Generate DIDs dynamically based on host
        encoded_host = self._encode_host_with_port(
            self.issuer_public_host, self.issuer_did_port
        )
        self.issuer_did = f"did:web:{encoded_host}"

        # Generate participant DIDs from templates
        consumer_host = self.issuer_public_host
        self.consumer_did = self._get_env(
            ENV_PARTICIPANT_DID,
            DEFAULT_CONSUMER_DID_TEMPLATE.format(host=consumer_host),
        )
        self.provider_did = DEFAULT_PROVIDER_DID_TEMPLATE.format(host=consumer_host)

        # Construct base URLs
        self.issuer_admin_url = self._build_localhost_url(self.issuer_admin_port)
        self.issuer_http_url = self._build_localhost_url(self.issuer_http_port)

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

    def _encode_host_with_port(self, host: str, port: str) -> str:
        """
        Encode host with port for DID web format.

        Args:
            host: Hostname
            port: Port number

        Returns:
            URL-encoded host:port string
        """
        host_with_port = f"{host}:{port}"
        return urllib.parse.quote(host_with_port, safe="")

    def _build_localhost_url(self, port: str) -> str:
        """
        Build localhost URL with given port.

        Args:
            port: Port number

        Returns:
            Complete localhost URL
        """
        return f"http://localhost:{port}"

    def _encode_context_for_api(self, context: str) -> str:
        """
        Encode context (DID) for API endpoint usage.

        Args:
            context: Context string (typically a DID)

        Returns:
            Base64 encoded context
        """
        return base64.b64encode(context.encode()).decode()

    def _log_configuration(self) -> None:
        """Log configuration details with sensitive data masked."""
        logger.info("Configuration loaded:")
        logger.info(f"  Issuer Admin URL: {self.issuer_admin_url}")
        logger.info(f"  Issuer HTTP URL: {self.issuer_http_url}")
        logger.info(f"  Issuer DID: {self.issuer_did}")
        logger.info(f"  Consumer DID: {self.consumer_did}")
        logger.info(f"  Provider DID: {self.provider_did}")
        logger.info(f"  API Key: {MASK_CHARACTER * MASK_LENGTH}[MASKED]")

    def get_headers(self) -> Dict[str, str]:
        """
        Get HTTP headers for API requests.

        Returns:
            Dictionary of HTTP headers including authentication
        """
        return {
            "Content-Type": "application/json",
            "X-Api-Key": self.issuer_superuser_key,
        }

    def get_health_url(self) -> str:
        """
        Get health check endpoint URL.

        Returns:
            Full URL for health check endpoint
        """
        return f"{self.issuer_http_url}{API_PATH_HEALTH}"

    def _build_admin_api_url(self, api_path: str) -> str:
        """
        Build admin API URL with encoded context.

        Args:
            api_path: API path template with {context} placeholder

        Returns:
            Complete API URL with Base64 encoded context
        """
        encoded_context = self._encode_context_for_api(self.issuer_did)
        path = api_path.format(context=encoded_context)
        return f"{self.issuer_admin_url}{path}"

    def get_holders_url(self) -> str:
        """
        Get holders API endpoint URL.

        Returns:
            Full URL for creating participant holders
        """
        return self._build_admin_api_url(API_PATH_HOLDERS)

    def get_attestations_url(self) -> str:
        """
        Get attestations API endpoint URL.

        Returns:
            Full URL for creating attestation definitions
        """
        return self._build_admin_api_url(API_PATH_ATTESTATIONS)

    def get_credentials_url(self) -> str:
        """
        Get credential definitions API endpoint URL.

        Returns:
            Full URL for creating credential definitions
        """
        return self._build_admin_api_url(API_PATH_CREDENTIALS)

    def get_query_attestations_url(self) -> str:
        """
        Get attestations query API endpoint URL.

        Returns:
            Full URL for querying attestation definitions
        """
        return self._build_admin_api_url(API_PATH_QUERY_ATTESTATIONS)

    def get_query_credentials_url(self) -> str:
        """
        Get credential definitions query API endpoint URL.

        Returns:
            Full URL for querying credential definitions
        """
        return self._build_admin_api_url(API_PATH_QUERY_CREDENTIALS)

    def get_query_participants_url(self) -> str:
        """
        Get participants query API endpoint URL.

        Returns:
            Full URL for querying participants
        """
        return f"{self.issuer_admin_url}{API_PATH_QUERY_PARTICIPANTS}"

    def _validate_required_fields(self) -> bool:
        """
        Validate that all required fields are present and non-empty.

        Returns:
            True if all required fields are valid, False otherwise
        """
        required_fields = [
            ("issuer_admin_port", self.issuer_admin_port),
            ("issuer_http_port", self.issuer_http_port),
            ("issuer_public_host", self.issuer_public_host),
            ("issuer_did_port", self.issuer_did_port),
            ("issuer_superuser_key", self.issuer_superuser_key),
            ("consumer_did", self.consumer_did),
            ("provider_did", self.provider_did),
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
            ("issuer_admin_port", self.issuer_admin_port),
            ("issuer_http_port", self.issuer_http_port),
            ("issuer_did_port", self.issuer_did_port),
        ]

        return all(
            self._validate_port(port_name, port_value)
            for port_name, port_value in ports_to_validate
        )

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
