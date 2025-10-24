"""HTTP utilities for Provider API interactions.

This module provides HTTP request utilities with consistent error handling,
logging, and retry logic for interacting with various EDC component APIs.
"""

import json
import logging
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Tuple

from config import HTTP_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


def make_request(
    url: str,
    headers: Dict[str, str],
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    entity_name: str = "resource",
    timeout: Optional[int] = None,
) -> Tuple[bool, Optional[str], Optional[int]]:
    """
    Make an HTTP request and handle common error cases.

    This function provides consistent error handling and logging for HTTP requests,
    with special handling for 409 Conflict responses (resource already exists).

    Args:
        url: Target URL
        headers: HTTP headers
        method: HTTP method (GET, POST, etc.)
        data: Optional request payload (will be JSON-encoded)
        entity_name: Name of resource for logging
        timeout: Request timeout in seconds (default: HTTP_TIMEOUT_SECONDS)

    Returns:
        Tuple of (success, response_body, status_code)
    """
    logger.debug(f"{method} {url}")

    if timeout is None:
        timeout = HTTP_TIMEOUT_SECONDS

    try:
        request_data = json.dumps(data).encode("utf-8") if data else None
        req = urllib.request.Request(
            url, data=request_data, headers=headers, method=method
        )

        with urllib.request.urlopen(req, timeout=timeout) as response:
            response_data = response.read().decode("utf-8")
            status_code = response.getcode()

            if status_code in (200, 201, 204):
                logger.info(f"✓ Successfully processed {entity_name}")
                logger.debug(f"Response: {response_data}")
                return True, response_data, status_code
            else:
                logger.warning(f"Unexpected status {status_code} for {entity_name}")
                logger.debug(f"Response: {response_data}")
                return False, response_data, status_code

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else "No error body"

        if e.code == 409:
            logger.info(f"✓ {entity_name} already exists")
            return True, error_body, e.code
        else:
            logger.error(f"✗ HTTP {e.code} error for {entity_name}: {e.reason}")
            logger.error(f"Error body: {error_body}")
            return False, error_body, e.code

    except urllib.error.URLError as e:
        logger.error(f"✗ URL error for {entity_name}: {e.reason}")
        return False, None, None

    except Exception as e:
        logger.error(f"✗ Unexpected error for {entity_name}: {e}")
        return False, None, None


def make_http_request(
    url: str,
    method: str = "POST",
    headers: Optional[Dict[str, str]] = None,
    data: Optional[str] = None,
    timeout: Optional[int] = None,
) -> Tuple[bool, int, str]:
    """
    Make HTTP request with error handling (alternative API, used by seed_participant).

    This is an alternative HTTP request function that accepts pre-encoded data.
    Use make_request() for most cases with automatic JSON encoding.

    Args:
        url: Request URL
        method: HTTP method
        headers: Request headers
        data: Request body data (pre-encoded string)
        timeout: Request timeout in seconds (default: HTTP_TIMEOUT_SECONDS)

    Returns:
        Tuple of (success, status_code, response_body)
    """
    if timeout is None:
        timeout = HTTP_TIMEOUT_SECONDS

    try:
        request = urllib.request.Request(url, method=method)

        # Add headers
        if headers:
            for key, value in headers.items():
                request.add_header(key, value)

        # Add data for POST requests
        if data:
            request.data = data.encode("utf-8")

        logger.debug(f"Making {method} request to {url}")

        with urllib.request.urlopen(request, timeout=timeout) as response:
            status_code = response.getcode()
            response_body = response.read().decode("utf-8")
            return True, status_code, response_body

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else str(e)
        logger.debug(f"HTTP Error {e.code}: {error_body}")
        return False, e.code, error_body
    except urllib.error.URLError as e:
        logger.debug(f"URL Error: {e.reason}")
        return False, 0, str(e.reason)
    except Exception as e:
        logger.debug(f"Request Error: {e}")
        return False, 0, str(e)


def query_api(
    url: str,
    headers: Dict[str, str],
    entity_name: str,
    query_body: Optional[Dict[str, Any]] = None,
    timeout: Optional[int] = None,
) -> Optional[Any]:
    """
    Query an API endpoint (GET or POST with query body).

    Args:
        url: API endpoint URL
        headers: HTTP headers
        entity_name: Resource name for logging
        query_body: Optional query payload (if provided, uses POST, otherwise GET)
        timeout: Request timeout in seconds (default: HTTP_TIMEOUT_SECONDS)

    Returns:
        Parsed JSON response or None on failure
    """
    logger.debug(f"Querying {entity_name}: {url}")

    method = "POST" if query_body else "GET"
    success, response_body, status_code = make_request(
        url=url,
        headers=headers,
        method=method,
        data=query_body,
        entity_name=entity_name,
        timeout=timeout,
    )

    if success and response_body:
        try:
            return json.loads(response_body)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON response for {entity_name}")
            return None

    return None
