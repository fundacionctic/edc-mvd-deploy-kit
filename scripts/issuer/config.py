#!/usr/bin/env python3
"""Configuration management for Issuer Service seeding.

This module handles configuration loading, validation, and provides
constants used across all Issuer seeding scripts.

Environment Variables:
    ISSUER_ADMIN_PORT: Admin API port (default: 10013)
    ISSUER_IDENTITY_PORT: Identity Hub port (default: 10015)
    ISSUER_ISSUANCE_PORT: Issuance API port (default: 10012)
    ISSUER_HTTP_PORT: HTTP API port (default: 10010)
    ISSUER_PUBLIC_HOST: Public hostname (default: host.docker.internal)
    ISSUER_DID_API_PORT: DID API port (default: 10016)
    ISSUER_SUPERUSER_KEY: Base64-encoded admin API key
    CONSUMER_DID_SERVER_PORT: Consumer DID server port (default: 7083)
    PROVIDER_IH_DID_PORT: Provider IdentityHub DID API port (default: 7003)
"""

import base64
import logging
import os
import sys
import urllib.parse
from typing import Dict, Optional

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


# Environment variable names
ENV_ISSUER_ADMIN_PORT = "ISSUER_ADMIN_PORT"
ENV_ISSUER_IDENTITY_PORT = "ISSUER_IDENTITY_PORT"
ENV_ISSUER_ISSUANCE_PORT = "ISSUER_ISSUANCE_PORT"
ENV_ISSUER_PUBLIC_HOST = "ISSUER_PUBLIC_HOST"
ENV_ISSUER_DID_API_PORT = "ISSUER_DID_API_PORT"
ENV_ISSUER_SUPERUSER_KEY = "ISSUER_SUPERUSER_KEY"
ENV_ISSUER_HTTP_PORT = "ISSUER_HTTP_PORT"
ENV_CONSUMER_DID_SERVER_PORT = "CONSUMER_DID_SERVER_PORT"
ENV_PROVIDER_IH_DID_PORT = "PROVIDER_IH_DID_PORT"

# Default values
DEFAULT_ISSUER_ADMIN_PORT = "10013"
DEFAULT_ISSUER_IDENTITY_PORT = "10015"
DEFAULT_ISSUER_ISSUANCE_PORT = "10012"
DEFAULT_ISSUER_HTTP_PORT = "10010"
DEFAULT_ISSUER_PUBLIC_HOST = "host.docker.internal"
DEFAULT_ISSUER_DID_API_PORT = "10016"
DEFAULT_ISSUER_SUPERUSER_KEY = "c3VwZXItdXNlcg==.c3VwZXItc2VjcmV0LWtleQo="
DEFAULT_CONSUMER_DID_SERVER_PORT = "7083"
DEFAULT_PROVIDER_IH_DID_PORT = "7003"

# Validation constants
MIN_PORT_NUMBER = 1
MAX_PORT_NUMBER = 65535
MASK_CHARACTER = "*"
MASK_LENGTH = 20

# API endpoints
API_PATH_HEALTH = "/api/check/health"
API_PATH_HOLDERS = "/api/admin/v1alpha/participants/{context}/holders"
API_PATH_ATTESTATIONS = "/api/admin/v1alpha/participants/{context}/attestations"
API_PATH_CREDENTIALS = "/api/admin/v1alpha/participants/{context}/credentialdefinitions"
API_PATH_QUERY_ATTESTATIONS = (
    "/api/admin/v1alpha/participants/{context}/attestations/query"
)
API_PATH_QUERY_CREDENTIALS = (
    "/api/admin/v1alpha/participants/{context}/credentialdefinitions/query"
)
API_PATH_QUERY_PARTICIPANTS = "/api/identity/v1alpha/participants"

# HTTP constants
HTTP_TIMEOUT_SECONDS = 30
HTTP_RETRY_COUNT = 3
HTTP_RETRY_DELAY_SECONDS = 5

# Credential types
CREDENTIAL_TYPE_MEMBERSHIP = "MembershipCredential"
CREDENTIAL_TYPE_DATA_PROCESSOR = "DataProcessorCredential"

# Attestation types
ATTESTATION_TYPE_DATABASE = "database"

# Database configuration
DB_DATASOURCE_NAME = "membership"
DB_TABLE_MEMBERSHIP = "membership_attestations"
DB_TABLE_DATA_PROCESSOR = "data_processor_attestations"
DB_COLUMN_HOLDER_ID = "holder_id"

# Credential formats
CREDENTIAL_FORMAT_JWT = "VC1_0_JWT"


class Config:
    """Configuration for Issuer Service seeding operations."""

    def __init__(self) -> None:
        """Initialize configuration from environment variables."""
        self.issuer_admin_port = self._get_env(
            ENV_ISSUER_ADMIN_PORT, DEFAULT_ISSUER_ADMIN_PORT
        )
        self.issuer_identity_port = self._get_env(
            ENV_ISSUER_IDENTITY_PORT, DEFAULT_ISSUER_IDENTITY_PORT
        )
        self.issuer_issuance_port = self._get_env(
            ENV_ISSUER_ISSUANCE_PORT, DEFAULT_ISSUER_ISSUANCE_PORT
        )
        self.issuer_http_port = self._get_env(
            ENV_ISSUER_HTTP_PORT, DEFAULT_ISSUER_HTTP_PORT
        )
        self.issuer_public_host = self._get_env(
            ENV_ISSUER_PUBLIC_HOST, DEFAULT_ISSUER_PUBLIC_HOST
        )
        self.issuer_did_api_port = self._get_env(
            ENV_ISSUER_DID_API_PORT, DEFAULT_ISSUER_DID_API_PORT
        )
        self.issuer_superuser_key = self._get_env(
            ENV_ISSUER_SUPERUSER_KEY, DEFAULT_ISSUER_SUPERUSER_KEY
        )

        encoded_host = self._encode_host_with_port(
            self.issuer_public_host, self.issuer_did_api_port
        )
        self.issuer_did = f"did:web:{encoded_host}"

        self.consumer_did_server_port = self._get_env(
            ENV_CONSUMER_DID_SERVER_PORT, DEFAULT_CONSUMER_DID_SERVER_PORT
        )
        self.provider_ih_did_port = self._get_env(
            ENV_PROVIDER_IH_DID_PORT, DEFAULT_PROVIDER_IH_DID_PORT
        )

        self.consumer_did = self._generate_participant_did(
            self.issuer_public_host, self.consumer_did_server_port, "consumer"
        )
        self.provider_did = self._generate_participant_did(
            self.issuer_public_host, self.provider_ih_did_port, "provider"
        )

        self.issuer_admin_url = self._build_url(
            self.issuer_public_host, self.issuer_admin_port
        )
        self.issuer_http_url = self._build_url(
            self.issuer_public_host, self.issuer_http_port
        )

        self._log_configuration()

    def _get_env(self, var_name: str, default: str) -> str:
        """Get environment variable with fallback to default."""
        value = os.environ.get(var_name, default)
        if value == default:
            logger.debug(f"Using default for {var_name}: {default}")
        return value

    def _encode_host_with_port(self, host: str, port: str) -> str:
        """Encode host with port for DID web format."""
        return urllib.parse.quote(f"{host}:{port}", safe="")

    def _generate_participant_did(
        self, host: str, port: str, participant_name: str
    ) -> str:
        """Generate participant DID based on hostname, port, and participant name."""
        if port in ("443", "80"):
            return f"did:web:{host}:{participant_name}"
        encoded_host = self._encode_host_with_port(host, port)
        return f"did:web:{encoded_host}:{participant_name}"

    def _build_url(self, host: str, port: str) -> str:
        """Build URL with given host and port."""
        return f"http://{host}:{port}"

    def _encode_context_for_api(self, context: str) -> str:
        """Encode context (DID) for API endpoint usage."""
        return base64.b64encode(context.encode()).decode()

    def _log_configuration(self) -> None:
        """Log configuration details with sensitive data masked."""
        logger.info("Configuration loaded:")
        logger.info(f"  Issuer Admin URL: {self.issuer_admin_url}")
        logger.info(f"  Issuer Identity Port: {self.issuer_identity_port}")
        logger.info(f"  Issuer Issuance Port: {self.issuer_issuance_port}")
        logger.info(f"  Issuer HTTP URL: {self.issuer_http_url}")
        logger.info(f"  Issuer DID: {self.issuer_did}")
        logger.info(f"  Consumer DID: {self.consumer_did}")
        logger.info(f"  Provider DID: {self.provider_did}")
        logger.info(f"  API Key: {MASK_CHARACTER * MASK_LENGTH}[MASKED]")

    def get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests."""
        return {
            "Content-Type": "application/json",
            "X-Api-Key": self.issuer_superuser_key,
        }

    def get_health_url(self) -> str:
        """Get health check endpoint URL."""
        return f"{self.issuer_http_url}{API_PATH_HEALTH}"

    def _build_admin_api_url(self, api_path: str) -> str:
        """Build admin API URL with encoded context."""
        encoded_context = self._encode_context_for_api(self.issuer_did)
        path = api_path.format(context=encoded_context)
        return f"{self.issuer_admin_url}{path}"

    def get_holders_url(self) -> str:
        """Get holders API endpoint URL."""
        return self._build_admin_api_url(API_PATH_HOLDERS)

    def get_attestations_url(self) -> str:
        """Get attestations API endpoint URL."""
        return self._build_admin_api_url(API_PATH_ATTESTATIONS)

    def get_credentials_url(self) -> str:
        """Get credential definitions API endpoint URL."""
        return self._build_admin_api_url(API_PATH_CREDENTIALS)

    def get_query_attestations_url(self) -> str:
        """Get attestations query API endpoint URL."""
        return self._build_admin_api_url(API_PATH_QUERY_ATTESTATIONS)

    def get_query_credentials_url(self) -> str:
        """Get credential definitions query API endpoint URL."""
        return self._build_admin_api_url(API_PATH_QUERY_CREDENTIALS)

    def get_query_participants_url(self) -> str:
        """Get participants query API endpoint URL."""
        return f"{self.issuer_admin_url}{API_PATH_QUERY_PARTICIPANTS}"

    def get_identity_participants_url(self) -> str:
        """Get Identity Hub participants API endpoint URL."""
        identity_url = self._build_url(
            self.issuer_public_host, self.issuer_identity_port
        )
        return f"{identity_url}/api/identity/v1alpha/participants/"

    def _validate_required_fields(self) -> bool:
        """Validate that all required fields are present and non-empty."""
        required_fields = [
            ("issuer_admin_port", self.issuer_admin_port),
            ("issuer_http_port", self.issuer_http_port),
            ("issuer_public_host", self.issuer_public_host),
            ("issuer_did_api_port", self.issuer_did_api_port),
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
        """Validate that a port value is numeric and within valid range."""
        try:
            port = int(port_value)
            if not (MIN_PORT_NUMBER <= port <= MAX_PORT_NUMBER):
                logger.error(
                    f"Invalid {port_name}: {port} (must be {MIN_PORT_NUMBER}-{MAX_PORT_NUMBER})"
                )
                return False
            return True
        except ValueError:
            logger.error(f"{port_name} is not a number: {port_value}")
            return False

    def _validate_ports(self) -> bool:
        """Validate all port configurations."""
        ports = [
            ("issuer_admin_port", self.issuer_admin_port),
            ("issuer_http_port", self.issuer_http_port),
            ("issuer_did_api_port", self.issuer_did_api_port),
        ]
        return all(self._validate_port(name, value) for name, value in ports)

    def validate(self) -> bool:
        """Validate configuration."""
        if not self._validate_required_fields():
            return False
        if not self._validate_ports():
            return False
        logger.info("Configuration validation successful")
        return True


def load_config() -> Optional[Config]:
    """Load and validate configuration."""
    try:
        config = Config()
        if config.validate():
            return config
        logger.error("Configuration validation failed")
        return None
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return None


if __name__ == "__main__":
    config = load_config()
    if config:
        logger.info("Configuration loaded and validated successfully")
        sys.exit(0)
    logger.error("Configuration loading failed")
    sys.exit(1)
