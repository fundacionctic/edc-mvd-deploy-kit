#!/usr/bin/env python3
"""
Add Participant to Running Issuer Service

This script dynamically adds a new participant to an already-deployed Issuer Service
without requiring database restart or issuer redeployment.

Operations performed:
1. Insert participant as holder in Identity Hub
2. Insert membership attestation (authorizes MembershipCredential issuance)
3. Insert data processor attestation (authorizes DataProcessorCredential issuance)

Usage:
    # Via command line arguments
    python3 scripts/issuer/add_participant.py \
        --did "did:web:dsctic02.cticpoc.com%3A9083:provider" \
        --name "Provider Corp (dsctic02)" \
        --membership-type 2 \
        --processing-level processing

    # Via environment variables
    export PARTICIPANT_DID="did:web:..."
    export PARTICIPANT_NAME="..."
    python3 scripts/issuer/add_participant.py

Arguments:
    --did                 Participant DID (required)
                         Format: did:web:{HOST}%3A{PORT}:{name}
                         Example: did:web:dsctic02.cticpoc.com%3A9083:provider

    --name                Display name for the participant (required)
                         Example: "Provider Corp (dsctic02)"

    --membership-type     Membership type integer (default: 2)
                         2 = Provider (offers data)
                         3 = Consumer (consumes data)

    --processing-level    Data processing level (default: "processing")
                         Options: "processing", "sensitive"

    --contract-version    Contract version (default: "1.0.0")
                         Format: Semantic versioning (e.g., 1.0.0, 1.2.3)

Environment Variables:
    ISSUER_PUBLIC_HOST    Hostname of the issuer PostgreSQL (default: localhost)
    ISSUER_DB_PORT        PostgreSQL port (default: 5432)
    ISSUER_DB_NAME        Database name (default: issuer)
    ISSUER_DB_USER        Database user (default: issuer)
    ISSUER_DB_PASSWORD    Database password (default: issuer)
    ISSUER_DID            Issuer's DID for participant_context_id

Exit Codes:
    0: Success - participant added
    1: Failure - validation error, database error, or participant already exists
"""

import argparse
import logging
import os
import sys
from enum import Enum, IntEnum
from typing import Any, Dict

# Try to import psycopg2, handle gracefully if missing
try:
    import psycopg2
except ImportError:
    psycopg2 = None


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


# Constants and Enums
class MembershipType(IntEnum):
    PROVIDER = 2
    CONSUMER = 3


class ProcessingLevel(str, Enum):
    PROCESSING = "processing"
    SENSITIVE = "sensitive"


# Default Configuration
DEFAULT_DB_HOST = "localhost"
DEFAULT_DB_PORT = 5432
DEFAULT_DB_NAME = "issuer"
DEFAULT_DB_USER = "issuer"
DEFAULT_DB_PASS = "issuer"
DEFAULT_ISSUER_DID = "did:web:host.docker.internal%3A10084"
DEFAULT_CONTRACT_VERSION = "1.0.0"
DEFAULT_START_DATE = "2023-01-01T00:00:00Z"
TIMESTAMP_PLACEHOLDER = 0

# SQL Queries
SQL_CHECK_HOLDER = "SELECT holder_id FROM holders WHERE holder_id = %s"

SQL_INSERT_HOLDER = """
    INSERT INTO holders (
        holder_id,
        participant_context_id,
        did,
        holder_name,
        created_date,
        last_modified_date
    )
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (holder_id) DO NOTHING
    RETURNING holder_id
"""

SQL_INSERT_MEMBERSHIP = """
    INSERT INTO membership_attestations (
        membership_type,
        holder_id,
        membership_start_date
    )
    VALUES (%s, %s, %s)
    ON CONFLICT (holder_id) DO NOTHING
    RETURNING id
"""

SQL_INSERT_DATA_PROCESSOR = """
    INSERT INTO data_processor_attestations (
        holder_id,
        contract_version,
        processing_level,
        attestation_date
    )
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (holder_id) DO NOTHING
    RETURNING id
"""


class ParticipantRegistration:
    """Handles participant registration operations."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize with database configuration."""
        self.config = config
        self.conn = None
        self.cursor = None

    def connect(self) -> bool:
        """Establish database connection."""
        if psycopg2 is None:
            logger.error(
                "❌ psycopg2 module not found. Install with: pip install psycopg2-binary"
            )
            return False

        try:
            logger.info(
                f"Connecting to PostgreSQL at {self.config['host']}:{self.config['port']}"
            )
            self.conn = psycopg2.connect(
                host=self.config["host"],
                port=self.config["port"],
                database=self.config["database"],
                user=self.config["user"],
                password=self.config["password"],
            )
            self.cursor = self.conn.cursor()
            logger.info("✓ Database connection established")
            return True

        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False

    def disconnect(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.debug("Database connection closed")

    def validate_did(self, did: str) -> bool:
        """Validate DID format."""
        if not did.startswith("did:web:"):
            logger.error(
                f"Invalid DID format: {did}\n" "DID must start with 'did:web:'"
            )
            return False

        parts = did.split(":")
        if len(parts) < 3:
            logger.error(
                f"Invalid DID structure: {did}\n"
                "Expected format: did:web:host%3Aport:name or did:web:host:name"
            )
            return False

        return True

    def participant_exists(self, participant_did: str) -> bool:
        """Check if participant already exists."""
        try:
            self.cursor.execute(SQL_CHECK_HOLDER, (participant_did,))
            result = self.cursor.fetchone()
            return result is not None

        except Exception as e:
            logger.warning(f"Could not check if participant exists: {e}")
            return False

    def add_holder(
        self, participant_did: str, participant_name: str, issuer_did: str
    ) -> bool:
        """Add participant to holders table."""
        try:
            logger.info(f"Adding holder: {participant_name}")
            logger.debug(f"  DID: {participant_did}")
            logger.debug(f"  Issuer DID: {issuer_did}")

            self.cursor.execute(
                SQL_INSERT_HOLDER,
                (
                    participant_did,
                    issuer_did,
                    participant_did,
                    participant_name,
                    TIMESTAMP_PLACEHOLDER,
                    TIMESTAMP_PLACEHOLDER,
                ),
            )

            result = self.cursor.fetchone()
            if result:
                logger.info("✓ Holder record created")
                return True
            else:
                logger.warning("⚠ Holder already exists (no conflict)")
                return True

        except Exception as e:
            logger.error(f"❌ Failed to add holder: {e}")
            return False

    def add_membership_attestation(
        self, participant_did: str, membership_type: int
    ) -> bool:
        """Add membership attestation for participant."""
        try:
            logger.info(f"Adding membership attestation (type={membership_type})")

            self.cursor.execute(
                SQL_INSERT_MEMBERSHIP,
                (membership_type, participant_did, DEFAULT_START_DATE),
            )

            result = self.cursor.fetchone()
            if result:
                logger.info("✓ Membership attestation created")
                return True
            else:
                logger.warning("⚠ Membership attestation already exists")
                return True

        except Exception as e:
            logger.error(f"❌ Failed to add membership attestation: {e}")
            return False

    def add_dataprocessor_attestation(
        self, participant_did: str, processing_level: str, contract_version: str
    ) -> bool:
        """Add data processor attestation for participant."""
        try:
            logger.info(f"Adding data processor attestation (level={processing_level})")

            self.cursor.execute(
                SQL_INSERT_DATA_PROCESSOR,
                (
                    participant_did,
                    contract_version,
                    processing_level,
                    DEFAULT_START_DATE,
                ),
            )

            result = self.cursor.fetchone()
            if result:
                logger.info("✓ Data processor attestation created")
                return True
            else:
                logger.warning("⚠ Data processor attestation already exists")
                return True

        except Exception as e:
            logger.error(f"❌ Failed to add data processor attestation: {e}")
            return False

    def add_participant(
        self,
        participant_did: str,
        participant_name: str,
        issuer_did: str,
        membership_type: int,
        processing_level: str,
        contract_version: str,
    ) -> bool:
        """Add participant with all required records."""
        try:
            # Validate DID format
            if not self.validate_did(participant_did):
                return False

            # Check if participant already exists
            if self.participant_exists(participant_did):
                logger.warning(f"⚠ Participant {participant_did} already exists")
                logger.info("Skipping registration to avoid conflicts")
                logger.info(
                    "If you need to update the participant, delete it first and re-add"
                )
                return True

            # Add holder record
            if not self.add_holder(participant_did, participant_name, issuer_did):
                return False

            # Add membership attestation
            if not self.add_membership_attestation(participant_did, membership_type):
                self.conn.rollback()
                return False

            # Add data processor attestation
            if not self.add_dataprocessor_attestation(
                participant_did, processing_level, contract_version
            ):
                self.conn.rollback()
                return False

            # Commit all changes
            self.conn.commit()
            logger.info("✓ All records committed successfully")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to add participant: {e}")
            if self.conn:
                self.conn.rollback()
            return False


def load_config_from_env() -> Dict[str, Any]:
    """Load database configuration from environment variables."""
    config = {
        "host": os.environ.get("ISSUER_PUBLIC_HOST", DEFAULT_DB_HOST),
        "port": int(os.environ.get("ISSUER_DB_PORT", str(DEFAULT_DB_PORT))),
        "database": os.environ.get("ISSUER_DB_NAME", DEFAULT_DB_NAME),
        "user": os.environ.get("ISSUER_DB_USER", DEFAULT_DB_USER),
        "password": os.environ.get("ISSUER_DB_PASSWORD", DEFAULT_DB_PASS),
        "issuer_did": os.environ.get("ISSUER_DID", DEFAULT_ISSUER_DID),
    }

    logger.debug(
        "Configuration loaded:\n"
        f"  Host: {config['host']}\n"
        f"  Port: {config['port']}\n"
        f"  Database: {config['database']}\n"
        f"  User: {config['user']}\n"
        f"  Issuer DID: {config['issuer_did']}"
    )

    return config


def main() -> int:
    """Main entry point for participant addition script."""
    parser = argparse.ArgumentParser(
        description="Add participant to Issuer Service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add a provider
  python3 scripts/issuer/add_participant.py \\
    --did "did:web:dsctic02.cticpoc.com%3A9083:provider" \\
    --name "Provider Corp (dsctic02)" \\
    --membership-type 2

  # Add a consumer with sensitive processing
  python3 scripts/issuer/add_participant.py \\
    --did "did:web:consumer.example.com:consumer" \\
    --name "Consumer Corp" \\
    --membership-type 3 \\
    --processing-level sensitive

Environment Variables:
  ISSUER_PUBLIC_HOST, ISSUER_DB_PORT, ISSUER_DB_NAME, ISSUER_DB_USER,
  ISSUER_DB_PASSWORD, ISSUER_DID
        """,
    )

    parser.add_argument(
        "--did",
        required=True,
        help="Participant DID (e.g., did:web:host.com%%3A9083:provider)",
    )
    parser.add_argument(
        "--name", required=True, help="Display name for the participant"
    )
    parser.add_argument(
        "--membership-type",
        type=int,
        default=MembershipType.PROVIDER.value,
        choices=[t.value for t in MembershipType],
        help="Membership type: 2=Provider, 3=Consumer (default: 2)",
    )
    parser.add_argument(
        "--processing-level",
        default=ProcessingLevel.PROCESSING.value,
        choices=[l.value for l in ProcessingLevel],
        help="Processing level (default: processing)",
    )
    parser.add_argument(
        "--contract-version",
        default=DEFAULT_CONTRACT_VERSION,
        help=f"Contract version (default: {DEFAULT_CONTRACT_VERSION})",
    )
    parser.add_argument(
        "--issuer-did",
        help="Issuer DID (overrides ISSUER_DID env var)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info(f"{'=' * 70}\n" "Add Participant to Issuer Service\n" f"{'=' * 70}\n")

    # Load configuration
    config = load_config_from_env()

    # Override issuer DID if provided
    if args.issuer_did:
        config["issuer_did"] = args.issuer_did

    # Display operation summary
    membership_name = (
        "Provider" if args.membership_type == MembershipType.PROVIDER else "Consumer"
    )
    logger.info(
        "Operation Summary:\n"
        f"  Participant DID:     {args.did}\n"
        f"  Participant Name:    {args.name}\n"
        f"  Membership Type:     {args.membership_type} ({membership_name})\n"
        f"  Processing Level:    {args.processing_level}\n"
        f"  Contract Version:    {args.contract_version}\n"
        f"  Issuer DID:          {config['issuer_did']}\n"
    )

    # Create registration handler
    registration = ParticipantRegistration(config)

    try:
        # Connect to database
        if not registration.connect():
            return 1

        # Add participant
        logger.info("Registering participant...\n" f"{'-' * 70}")

        success = registration.add_participant(
            participant_did=args.did,
            participant_name=args.name,
            issuer_did=config["issuer_did"],
            membership_type=args.membership_type,
            processing_level=args.processing_level,
            contract_version=args.contract_version,
        )

        if success:
            logger.info(
                f"{'-' * 70}\n\n"
                f"{'=' * 70}\n"
                f"✓ ✓ ✓  SUCCESS: Participant '{args.name}' added successfully!\n"
                f"{'=' * 70}\n\n"
                "Next Steps:\n"
                "  1. Participant can now request credentials from this issuer\n"
                "  2. Configure provider's Identity Hub to use this issuer\n"
                "  3. Run: python3 scripts/provider/request_credentials.py\n\n"
                "Verification:\n"
                "  docker exec mvd-issuer-postgres psql -U issuer -d issuer \\\n"
                '    -c "SELECT holder_id, holder_name FROM holders ORDER BY holder_id;"\n'
            )
            return 0
        else:
            logger.error(
                "\n"
                f"{'=' * 70}\n"
                "✗ ✗ ✗  FAILED: Could not add participant\n"
                f"{'=' * 70}\n\n"
                "Troubleshooting:\n"
                "  1. Check database connection parameters\n"
                "  2. Verify DID format is correct\n"
                "  3. Check issuer-postgres container is running\n"
                "  4. Review error messages above\n"
            )
            return 1

    except KeyboardInterrupt:
        logger.warning(
            "\n" f"{'=' * 70}\n" "Operation cancelled by user (Ctrl+C)\n" f"{'=' * 70}"
        )
        return 1

    except Exception as e:
        logger.error("\n" f"{'=' * 70}\n" f"Unexpected error: {e}\n" f"{'=' * 70}")
        logger.exception("Stack trace:")
        return 1

    finally:
        registration.disconnect()


if __name__ == "__main__":
    sys.exit(main())
