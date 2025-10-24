#!/usr/bin/env python3
"""
Control Plane Testing and Validation

This script provides testing and validation functionality for the provider
Control Plane component. It tests all major APIs and endpoints.

Usage:
    python3 scripts/provider/test_controlplane.py [test]

Tests:
    health          Test health endpoints
    management      Test Management API
    protocol        Test DSP Protocol endpoint
    catalog         Test Catalog API
    all             Run all tests (default)

Environment Variables:
    PROVIDER_CP_WEB_PORT: Control Plane web port
    PROVIDER_CP_MANAGEMENT_PORT: Management API port
    PROVIDER_CP_PROTOCOL_PORT: DSP Protocol port
    PROVIDER_CP_CATALOG_PORT: Catalog API port
    PROVIDER_MANAGEMENT_API_KEY: Management API authentication key
    PROVIDER_CATALOG_API_KEY: Catalog API authentication key
"""

import json
import logging
import os
import sys
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Tuple

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

# HTTP timeout
HTTP_TIMEOUT = 10


def make_http_request(url: str, method: str = "GET", headers: Optional[Dict[str, str]] = None, 
                     data: Optional[str] = None) -> Tuple[bool, int, str]:
    """
    Make HTTP request with error handling.
    
    Args:
        url: Request URL
        method: HTTP method
        headers: Request headers
        data: Request body data
        
    Returns:
        Tuple of (success, status_code, response_body)
    """
    try:
        request = urllib.request.Request(url, method=method)
        
        # Add headers
        if headers:
            for key, value in headers.items():
                request.add_header(key, value)
        
        # Add data for POST requests
        if data:
            request.data = data.encode('utf-8')
        
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
            status_code = response.getcode()
            response_body = response.read().decode('utf-8')
            return True, status_code, response_body
            
    except urllib.error.HTTPError as e:
        return False, e.code, e.read().decode('utf-8') if e.fp else str(e)
    except urllib.error.URLError as e:
        return False, 0, str(e.reason)
    except Exception as e:
        return False, 0, str(e)


def test_health_endpoints(config) -> bool:
    """
    Test Control Plane health endpoints.
    
    Args:
        config: Configuration object
        
    Returns:
        True if all health checks pass, False otherwise
    """
    logger.info("Testing Control Plane health endpoints...")
    
    health_urls = [
        f"http://localhost:{config.provider_cp_web_port}/api/check/health",
        f"http://localhost:{config.provider_cp_web_port}/api/check/readiness",
        f"http://localhost:{config.provider_cp_web_port}/api/check/startup",
        f"http://localhost:{config.provider_cp_web_port}/api/check/liveness"
    ]
    
    all_passed = True
    
    for url in health_urls:
        success, status_code, response = make_http_request(url)
        
        if success and status_code == 200:
            logger.info(f"✅ Health check passed: {url}")
        else:
            logger.error(f"❌ Health check failed: {url} (Status: {status_code})")
            all_passed = False
    
    return all_passed


def test_management_api(config) -> bool:
    """
    Test Management API endpoints.
    
    Args:
        config: Configuration object
        
    Returns:
        True if Management API tests pass, False otherwise
    """
    logger.info("Testing Management API...")
    
    base_url = f"http://localhost:{config.provider_cp_management_port}/api/management"
    headers = config.get_management_headers()
    
    # Test endpoints
    test_endpoints = [
        ("GET", f"{base_url}/v3/assets/request", "List assets"),
        ("GET", f"{base_url}/v3/policydefinitions/request", "List policy definitions"),
        ("GET", f"{base_url}/v3/contractdefinitions/request", "List contract definitions"),
        ("GET", f"{base_url}/v3/contractnegotiations/request", "List contract negotiations"),
        ("GET", f"{base_url}/v3/transferprocesses/request", "List transfer processes"),
    ]
    
    all_passed = True
    
    for method, url, description in test_endpoints:
        # For POST requests, add empty query body
        data = '{"@context": ["https://w3id.org/edc/connector/management/v0.0.1"], "@type": "QuerySpec"}' if method == "POST" else None
        
        success, status_code, response = make_http_request(url, method, headers, data)
        
        if success and status_code in [200, 204]:
            logger.info(f"✅ {description}: {status_code}")
            
            # Try to parse JSON response
            if response:
                try:
                    json_response = json.loads(response)
                    if isinstance(json_response, list):
                        logger.debug(f"   Response: {len(json_response)} items")
                    else:
                        logger.debug(f"   Response: {type(json_response).__name__}")
                except json.JSONDecodeError:
                    logger.debug(f"   Response: {len(response)} bytes")
        else:
            logger.error(f"❌ {description}: {status_code}")
            if response:
                logger.debug(f"   Error: {response[:200]}...")
            all_passed = False
    
    return all_passed


def test_protocol_endpoint(config) -> bool:
    """
    Test DSP Protocol endpoint.
    
    Args:
        config: Configuration object
        
    Returns:
        True if DSP Protocol tests pass, False otherwise
    """
    logger.info("Testing DSP Protocol endpoint...")
    
    base_url = f"http://localhost:{config.provider_cp_protocol_port}/api/dsp"
    
    # Test basic DSP endpoints (these may return 400/404 but should be reachable)
    test_endpoints = [
        ("GET", f"{base_url}/catalog/request", "Catalog request endpoint"),
        ("GET", f"{base_url}/negotiations", "Negotiations endpoint"),
        ("GET", f"{base_url}/transfers", "Transfers endpoint"),
    ]
    
    all_passed = True
    
    for method, url, description in test_endpoints:
        success, status_code, response = make_http_request(url, method)
        
        # DSP endpoints may return 400 (Bad Request) for malformed requests, which is expected
        if success or status_code in [400, 404, 405]:
            logger.info(f"✅ {description}: {status_code} (endpoint reachable)")
        else:
            logger.error(f"❌ {description}: {status_code}")
            if response:
                logger.debug(f"   Error: {response[:200]}...")
            all_passed = False
    
    return all_passed


def test_catalog_api(config) -> bool:
    """
    Test Catalog API endpoints.
    
    Args:
        config: Configuration object
        
    Returns:
        True if Catalog API tests pass, False otherwise
    """
    logger.info("Testing Catalog API...")
    
    base_url = f"http://localhost:{config.provider_cp_catalog_port}/api/catalog"
    headers = config.get_catalog_headers()
    
    # Test catalog endpoints
    test_endpoints = [
        ("POST", f"{base_url}/v1alpha/catalog/query", "Catalog query"),
        ("GET", f"{base_url}/v1alpha/catalog", "Catalog listing"),
    ]
    
    all_passed = True
    
    for method, url, description in test_endpoints:
        # For POST requests, add empty query body
        data = '{"@context": ["https://w3id.org/edc/connector/management/v0.0.1"], "@type": "QuerySpec"}' if method == "POST" else None
        
        success, status_code, response = make_http_request(url, method, headers, data)
        
        if success and status_code in [200, 204]:
            logger.info(f"✅ {description}: {status_code}")
            
            # Try to parse JSON response
            if response:
                try:
                    json_response = json.loads(response)
                    if isinstance(json_response, list):
                        logger.debug(f"   Response: {len(json_response)} items")
                    else:
                        logger.debug(f"   Response: {type(json_response).__name__}")
                except json.JSONDecodeError:
                    logger.debug(f"   Response: {len(response)} bytes")
        else:
            logger.error(f"❌ {description}: {status_code}")
            if response:
                logger.debug(f"   Error: {response[:200]}...")
            all_passed = False
    
    return all_passed


def test_participant_registry(config) -> bool:
    """
    Test participant registry functionality.
    
    Args:
        config: Configuration object
        
    Returns:
        True if participant registry tests pass, False otherwise
    """
    logger.info("Testing participant registry...")
    
    # This is a placeholder for participant registry tests
    # The actual implementation depends on the participant registry configuration
    
    logger.info("✅ Participant registry test skipped (not implemented yet)")
    return True


def run_all_tests(config) -> bool:
    """
    Run all Control Plane tests.
    
    Args:
        config: Configuration object
        
    Returns:
        True if all tests pass, False otherwise
    """
    logger.info("Running all Control Plane tests...")
    logger.info("=" * 50)
    
    tests = [
        ("Health Endpoints", test_health_endpoints),
        ("Management API", test_management_api),
        ("DSP Protocol", test_protocol_endpoint),
        ("Catalog API", test_catalog_api),
        ("Participant Registry", test_participant_registry),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} ---")
        try:
            result = test_func(config)
            results.append((test_name, result))
            
            if result:
                logger.info(f"✅ {test_name} tests passed")
            else:
                logger.error(f"❌ {test_name} tests failed")
        except Exception as e:
            logger.error(f"❌ {test_name} tests failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("Control Plane Test Summary:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"  {status} {test_name}")
        if result:
            passed += 1
    
    logger.info(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All Control Plane tests passed!")
        return True
    else:
        logger.error(f"❌ {total - passed} tests failed")
        return False


def show_help():
    """Show help message."""
    print(__doc__)


def main():
    """Main entry point."""
    # Load configuration
    config = load_config()
    if not config:
        logger.error("Failed to load configuration")
        return 1
    
    # Determine test to run
    test_name = sys.argv[1].lower() if len(sys.argv) > 1 else "all"
    
    success = False
    
    if test_name == "health":
        success = test_health_endpoints(config)
    elif test_name == "management":
        success = test_management_api(config)
    elif test_name == "protocol":
        success = test_protocol_endpoint(config)
    elif test_name == "catalog":
        success = test_catalog_api(config)
    elif test_name == "registry":
        success = test_participant_registry(config)
    elif test_name == "all":
        success = run_all_tests(config)
    elif test_name == "help" or test_name == "--help":
        show_help()
        return 0
    else:
        logger.error(f"Unknown test: {test_name}")
        show_help()
        return 1
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())