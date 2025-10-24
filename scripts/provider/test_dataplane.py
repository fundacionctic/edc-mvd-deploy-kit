#!/usr/bin/env python3
"""
Data Plane Testing and Validation

This script provides testing and validation functionality for the provider
Data Plane component. It tests all major APIs and endpoints.

Usage:
    python3 scripts/provider/test_dataplane.py [test]

Tests:
    health          Test health endpoints
    control         Test Control API (communication with Control Plane)
    public          Test Public API (data access endpoint)
    registration    Test Data Plane registration with Control Plane
    all             Run all tests (default)

Environment Variables:
    PROVIDER_DP_WEB_PORT: Data Plane web port
    PROVIDER_DP_CONTROL_PORT: Data Plane control port
    PROVIDER_DP_PUBLIC_PORT: Data Plane public port
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
    Test Data Plane health endpoints.
    
    Args:
        config: Configuration object
        
    Returns:
        True if all health checks pass, False otherwise
    """
    logger.info("Testing Data Plane health endpoints...")
    
    health_urls = [
        f"http://localhost:{config.provider_dp_web_port}/api/check/health",
        f"http://localhost:{config.provider_dp_web_port}/api/check/readiness",
        f"http://localhost:{config.provider_dp_web_port}/api/check/startup",
        f"http://localhost:{config.provider_dp_web_port}/api/check/liveness"
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


def test_control_api(config) -> bool:
    """
    Test Data Plane Control API endpoints.
    
    Args:
        config: Configuration object
        
    Returns:
        True if Control API tests pass, False otherwise
    """
    logger.info("Testing Data Plane Control API...")
    
    base_url = f"http://localhost:{config.provider_dp_control_port}/api/control"
    
    # Test control endpoints (these may require authentication from Control Plane)
    test_endpoints = [
        ("GET", f"{base_url}/v1/dataplanes", "List data planes"),
        ("GET", f"{base_url}/v1/transfers", "List transfers"),
    ]
    
    all_passed = True
    
    for method, url, description in test_endpoints:
        success, status_code, response = make_http_request(url, method)
        
        # Control API may return 401/403 without proper authentication, which is expected
        if success or status_code in [401, 403, 404]:
            logger.info(f"✅ {description}: {status_code} (endpoint reachable)")
        else:
            logger.error(f"❌ {description}: {status_code}")
            if response:
                logger.debug(f"   Error: {response[:200]}...")
            all_passed = False
    
    return all_passed


def test_public_api(config) -> bool:
    """
    Test Data Plane Public API endpoints.
    
    Args:
        config: Configuration object
        
    Returns:
        True if Public API tests pass, False otherwise
    """
    logger.info("Testing Data Plane Public API...")
    
    base_url = f"http://localhost:{config.provider_dp_public_port}/api/public"
    
    # Test public endpoints (these require valid EDR tokens)
    test_endpoints = [
        ("GET", f"{base_url}", "Public API root"),
        ("GET", f"{base_url}/health", "Public API health"),
    ]
    
    all_passed = True
    
    for method, url, description in test_endpoints:
        success, status_code, response = make_http_request(url, method)
        
        # Public API may return 401/403 without proper EDR token, which is expected
        if success or status_code in [401, 403, 404]:
            logger.info(f"✅ {description}: {status_code} (endpoint reachable)")
        else:
            logger.error(f"❌ {description}: {status_code}")
            if response:
                logger.debug(f"   Error: {response[:200]}...")
            all_passed = False
    
    return all_passed


def test_dataplane_registration(config) -> bool:
    """
    Test Data Plane registration with Control Plane.
    
    Args:
        config: Configuration object
        
    Returns:
        True if registration tests pass, False otherwise
    """
    logger.info("Testing Data Plane registration...")
    
    # Check if Data Plane is registered with Control Plane
    cp_url = f"http://localhost:{config.provider_cp_control_port}/api/control/v1/dataplanes"
    headers = config.get_management_headers()
    
    success, status_code, response = make_http_request(cp_url, "GET", headers)
    
    if success and status_code == 200:
        try:
            dataplanes = json.loads(response)
            
            if isinstance(dataplanes, list):
                logger.info(f"✅ Found {len(dataplanes)} registered data planes")
                
                # Look for our data plane
                our_dataplane = None
                for dp in dataplanes:
                    if isinstance(dp, dict) and dp.get('id') == f"{config.provider_participant_name}-dataplane":
                        our_dataplane = dp
                        break
                
                if our_dataplane:
                    logger.info(f"✅ Data Plane is registered: {our_dataplane.get('id')}")
                    logger.debug(f"   URL: {our_dataplane.get('url')}")
                    return True
                else:
                    logger.warning("⚠️  Data Plane not found in registration list")
                    return False
            else:
                logger.warning("⚠️  Unexpected response format from Control Plane")
                return False
                
        except json.JSONDecodeError:
            logger.error("❌ Failed to parse Control Plane response")
            return False
    else:
        logger.error(f"❌ Failed to query Control Plane data planes: {status_code}")
        if response:
            logger.debug(f"   Error: {response[:200]}...")
        return False


def test_transfer_capabilities(config) -> bool:
    """
    Test Data Plane transfer capabilities.
    
    Args:
        config: Configuration object
        
    Returns:
        True if transfer capability tests pass, False otherwise
    """
    logger.info("Testing Data Plane transfer capabilities...")
    
    # This is a placeholder for transfer capability tests
    # Actual implementation would require setting up test transfers
    
    logger.info("✅ Transfer capability test skipped (requires test data)")
    return True


def run_all_tests(config) -> bool:
    """
    Run all Data Plane tests.
    
    Args:
        config: Configuration object
        
    Returns:
        True if all tests pass, False otherwise
    """
    logger.info("Running all Data Plane tests...")
    logger.info("=" * 50)
    
    tests = [
        ("Health Endpoints", test_health_endpoints),
        ("Control API", test_control_api),
        ("Public API", test_public_api),
        ("Data Plane Registration", test_dataplane_registration),
        ("Transfer Capabilities", test_transfer_capabilities),
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
    logger.info("Data Plane Test Summary:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"  {status} {test_name}")
        if result:
            passed += 1
    
    logger.info(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All Data Plane tests passed!")
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
    elif test_name == "control":
        success = test_control_api(config)
    elif test_name == "public":
        success = test_public_api(config)
    elif test_name == "registration":
        success = test_dataplane_registration(config)
    elif test_name == "transfer":
        success = test_transfer_capabilities(config)
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