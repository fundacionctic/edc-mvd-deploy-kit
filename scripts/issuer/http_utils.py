"""HTTP utilities for Issuer Service API interactions."""

import json
import logging
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from config import HTTP_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


def make_request(
    url: str,
    headers: Dict[str, str],
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    entity_name: str = "resource",
) -> tuple[bool, Optional[str], Optional[int]]:
    """
    Make an HTTP request and handle common error cases.

    Args:
        url: Target URL
        headers: HTTP headers
        method: HTTP method (GET, POST, etc.)
        data: Optional request payload
        entity_name: Name of resource for logging

    Returns:
        Tuple of (success, response_body, status_code)
    """
    logger.debug(f"{method} {url}")

    try:
        request_data = json.dumps(data).encode("utf-8") if data else None
        req = urllib.request.Request(
            url, data=request_data, headers=headers, method=method
        )

        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as response:
            response_data = response.read().decode("utf-8")
            status_code = response.getcode()

            if status_code in (200, 201):
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


def query_api(
    url: str,
    headers: Dict[str, str],
    entity_name: str,
    query_body: Optional[Dict[str, Any]] = None,
) -> Optional[Any]:
    """
    Query an API endpoint (GET or POST with query body).

    Args:
        url: API endpoint URL
        headers: HTTP headers
        entity_name: Resource name for logging
        query_body: Optional query payload (if provided, uses POST, otherwise GET)

    Returns:
        Parsed JSON response or None on failure
    """
    logger.info(f"Querying {entity_name}: {url}")

    method = "POST" if query_body else "GET"
    success, response_body, status_code = make_request(
        url=url,
        headers=headers,
        method=method,
        data=query_body,
        entity_name=entity_name,
    )

    if success and response_body:
        try:
            return json.loads(response_body)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON response for {entity_name}")
            return None

    return None
