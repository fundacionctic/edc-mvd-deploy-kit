#!/usr/bin/env python3
"""
Common Utility Functions for Provider Scripts

This module provides shared functionality used across multiple provider scripts:
- Component health checking and waiting
- Logging configuration
- DID validation
- Common patterns

Usage:
    from common_utils import wait_for_component, setup_logging
"""

import logging
import time
import urllib.error
import urllib.request
from typing import Optional

logger = logging.getLogger(__name__)


def setup_logging(
    level: int = logging.INFO, format_string: Optional[str] = None
) -> None:
    """
    Configure logging with standardized format.

    Args:
        level: Logging level (default: logging.INFO)
        format_string: Custom format string (optional)
    """
    if format_string is None:
        format_string = "%(asctime)s - %(levelname)s - %(message)s"

    logging.basicConfig(level=level, format=format_string)


def wait_for_component(
    component_name: str, health_url: str, timeout: int = 60, check_interval: int = 5
) -> bool:
    """
    Wait for a component to become ready by polling its health endpoint.

    Args:
        component_name: Human-readable component name (e.g., "Control Plane")
        health_url: Health check endpoint URL
        timeout: Maximum time to wait in seconds (default: 60)
        check_interval: Time between health checks in seconds (default: 5)

    Returns:
        True if component becomes ready within timeout, False otherwise
    """
    logger.info(f"Waiting for {component_name} to become ready (timeout: {timeout}s)")

    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(health_url, timeout=5) as response:
                if response.getcode() == 200:
                    elapsed = int(time.time() - start_time)
                    logger.info(f"✅ {component_name} ready after {elapsed}s")
                    return True
        except (urllib.error.URLError, urllib.error.HTTPError):
            pass

        logger.debug(f"⏳ {component_name} not ready yet, waiting {check_interval}s...")
        time.sleep(check_interval)

    logger.error(f"❌ {component_name} did not become ready within {timeout}s")
    return False


def validate_did_format(did: str) -> bool:
    """
    Validate that a DID string follows the did:web format.

    Args:
        did: DID string to validate

    Returns:
        True if DID format is valid, False otherwise
    """
    if not did or not isinstance(did, str):
        logger.debug("DID validation failed: empty or non-string value")
        return False

    if not did.startswith("did:web:"):
        logger.debug(f"DID validation failed: does not start with 'did:web:' - {did}")
        return False

    # Basic validation - at minimum should have did:web:host
    parts = did.split(":")
    if len(parts) < 3:
        logger.debug(f"DID validation failed: insufficient parts - {did}")
        return False

    logger.debug(f"DID validation passed: {did}")
    return True


def validate_port_number(port_value: str, port_name: str = "port") -> bool:
    """
    Validate that a port value is numeric and within valid range.

    Args:
        port_value: Port value to validate (as string)
        port_name: Name of the port for error reporting

    Returns:
        True if port is valid, False otherwise
    """
    try:
        port = int(port_value)
        if port < 1 or port > 65535:
            logger.error(f"Invalid {port_name}: {port} (must be between 1-65535)")
            return False
        return True
    except ValueError:
        logger.error(f"{port_name} is not a number: {port_value}")
        return False


def mask_sensitive_value(
    value: str, visible_chars: int = 4, mask_char: str = "*"
) -> str:
    """
    Mask a sensitive value for logging, showing only last few characters.

    Args:
        value: Value to mask
        visible_chars: Number of characters to show at the end
        mask_char: Character to use for masking

    Returns:
        Masked string
    """
    if not value or len(value) <= visible_chars:
        return mask_char * 10

    return mask_char * 10 + value[-visible_chars:]


def check_component_health(
    component_name: str, health_url: str, timeout: int = 10
) -> bool:
    """
    Check if a component is currently healthy (single check, no retries).

    Args:
        component_name: Human-readable component name
        health_url: Health check endpoint URL
        timeout: Request timeout in seconds

    Returns:
        True if component is healthy, False otherwise
    """
    try:
        with urllib.request.urlopen(health_url, timeout=timeout) as response:
            if response.getcode() == 200:
                logger.info(f"✅ {component_name} is healthy")
                return True
            else:
                logger.warning(
                    f"⚠️  {component_name} returned status: {response.getcode()}"
                )
                return False
    except Exception as e:
        logger.debug(f"❌ Cannot reach {component_name}: {e}")
        return False
