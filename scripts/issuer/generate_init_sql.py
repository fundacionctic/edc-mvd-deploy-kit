#!/usr/bin/env python3
"""
Generate Issuer Database Initialization SQL

This script generates the init-issuer-db.sql file from the template,
substituting participant DIDs based on configuration.

Usage:
    python3 scripts/issuer/generate_init_sql.py

Environment Variables:
    All ISSUER_* and participant configuration from config.py

Output:
    - deployment/issuer/init-issuer-db.sql
"""

import logging
import os
import sys
from pathlib import Path

# Add the scripts directory to the path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from issuer.config import load_config
except ImportError:
    print("ERROR: Could not import issuer config")
    print("Make sure you're running from the project root directory")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def generate_init_sql(config) -> str:
    """
    Generate init-issuer-db.sql content from template.

    Args:
        config: Loaded configuration object

    Returns:
        SQL content as string
    """
    template_file = Path("deployment/issuer/init-issuer-db.sql.template")

    if not template_file.exists():
        raise FileNotFoundError(f"Template file not found: {template_file}")

    # Read template
    with open(template_file, "r") as f:
        template_content = f.read()

    # Substitute variables
    sql_content = template_content.replace("${PROVIDER_DID}", config.provider_did)
    sql_content = sql_content.replace(
        "${PROVIDER_IH_DID_PORT}", config.provider_ih_did_port
    )

    return sql_content


def write_init_sql(config) -> bool:
    """
    Write generated SQL to deployment directory.

    Args:
        config: Loaded configuration object

    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure deployment/issuer directory exists
        deployment_dir = Path("deployment/issuer")
        deployment_dir.mkdir(parents=True, exist_ok=True)

        # Generate SQL content
        sql_content = generate_init_sql(config)

        # Write SQL file
        sql_file = deployment_dir / "init-issuer-db.sql"
        with open(sql_file, "w") as f:
            f.write(sql_content)

        logger.info(f"✓ Generated: {sql_file}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to generate init-issuer-db.sql: {str(e)}")
        return False


def main():
    """Main entry point."""
    logger.info("Generating Issuer Database Initialization SQL")
    logger.info("=" * 60)

    # Load configuration
    config = load_config()
    if not config:
        logger.error("Failed to load configuration")
        return 1

    logger.info("Configuration loaded successfully")
    logger.info(f"Provider DID: {config.provider_did}")
    logger.info("")

    # Generate SQL file
    if not write_init_sql(config):
        logger.error("❌ Failed to generate SQL file")
        return 1

    logger.info("")
    logger.info("🎉 SQL file generated successfully!")
    logger.info("")
    logger.info("Generated file:")
    logger.info("  - deployment/issuer/init-issuer-db.sql")
    logger.info("")
    logger.info("Next steps:")
    logger.info("  1. Review the generated SQL file")
    logger.info("  2. Restart the issuer-postgres container to apply changes")
    logger.info("  3. Run: task issuer:seed")

    return 0


if __name__ == "__main__":
    sys.exit(main())
