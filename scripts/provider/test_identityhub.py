#!/usr/bin/env python3
"""
Identity Hub Testing and Validation

This script provides testing and validation functionality for the provider
Identity Hub component. It tests all major APIs and endpoints.

Usage:
    python3 scripts/provider/test_identityhub.py [test]

Tests:
    health          Test health endpoints
    credentials     Test Credentials API
    sts             Test STS (Secure Token Service) API
    did             Test DID API
    all             Run all tests (default)

Environment Variables:
    PROVIDER_IH_WEB_PORT: Identity Hub web port
    PROVIDER_IH_CREDENTIALS_PORT: Credentials API port
    PROVIDER_IH_STS_PORT: STS API port
    PROVIDER_IH_DID_PORT: DID API port
    PROVIDER_IDENTITY_API_KEY: Identity API authentication key
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
    Test Identity Hub health endpoints.
    
    Args:
        config: Configuration object
        
    Returns:
        True if all health checks pass, False otherwise
    """
    logger.info("Testing Identity Hub health endpoints...")
    
    health_urls = [
        f"http://localhost:{config.provider_ih_web_port}/api/check/health",
        f"http://localhost:{config.provider_ih_web_port}/api/check/readiness",
        f"http://localhost:{config.provider_ih_web_port}/api/check/startup",
        f"http://localhost:{config.provider_ih_web_port}/api/check/liveness"
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


def test_credentials_api(config) -> bool:
    """
    Test Credentials API endpoints.
    
    Args:
        config: Configuration object
        
    Returns:
        True if Credentials API tests pass, False otherwise
    """
    logger.info("Testing Credentials API...")
    
    base_url = f"http://localhost:{config.provider_ih_credentials_port}/api/credentials"
    headers = config.get_identity_headers()
    
    # Test credentials endpoints
    test_endpoints = [
        ("GET", f"{base_url}", "List credentials"),
        ("POST", f"{base_url}/query", "Query credentials"),
    ]
    
    all_passed = True
    
    for method, url, description in test_endpoints:
        # For POST requests, add empty query body
        data = '{"@context": ["https://w3id.org/edc/v0.0.1/ns/"], "@type": "QuerySpec"}' if method == "POST" else None
        
        success, status_code, response = make_http_request(url, method, headers, data)
        
        if success and status_code in [200, 204]:
            logger.info(f"✅ {description}: {status_code}")
            
            # Try to parse JSON response
            if response:
                try:
                    json_response = json.loads(response)
                    if isinstance(json_response, list):
                        logger.debug(f"   Response: {len(json_response)} credentials")
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


def test_sts_api(config) -> bool:
    """
    Test STS (Secure Token Service) API endpoints.
    
    Args:
        config: Configuration object
        
    Returns:
        True if STS API tests pass, False otherwise
    """
    logger.info("Testing STS API...")
    
    base_url = f"http://localhost:{config.provider_ih_sts_port}/api/sts"
    
    # Test STS endpoints (these require proper authentication)
    test_endpoints = [
        ("GET", f"{base_url}", "STS root endpoint"),
        ("POST", f"{base_url}/token", "Token issuance endpoint"),
    ]
    
    all_passed = True
    
    for method, url, description in test_endpoints:
        success, status_code, response = make_http_request(url, method)
        
        # STS endpoints may return 400/401 without proper authentication, which is expected
        if success or status_code in [400, 401, 404, 405]:
            logger.info(f"✅ {description}: {status_code} (endpoint reachable)")
        else:
            logger.error(f"❌ {description}: {status_code}")
            if response:
                logger.debug(f"   Error: {response[:200]}...")
            all_passed = False
    
    return all_passed


def test_did_api(config) -> bool:
    """
    Test DID API endpoints.
    
    Args:
        config: Configuration object
        
    Returns:
        True if DID API tests pass, False otherwise
    """
    logger.info("Testing DID API...")
    
    base_url = f"http://localhost:{config.provider_ih_did_port}"
    
    # Test DID endpoints
    test_endpoints = [
        ("GET", f"{base_url}/", "DID root endpoint"),
        ("GET", f"{base_url}/.well-known/did.json", "DID document endpoint"),
    ]
    
    all_passed = True
    
    for method, url, description in test_endpoints:
        success, status_code, response = make_http_request(url, method)
        
        if success and status_code == 200:
            logger.info(f"✅ {description}: {status_code}")
            
            # For DID document, try to parse JSON
            if "did.json" in url and response:
                try:
                    did_doc = json.loads(response)
                    if "id" in did_doc and did_doc["id"].startswith("did:web:"):
                        logger.debug(f"   DID: {did_doc['id']}")
                    else:
                        logger.warning("⚠️  DID document format may be incorrect")
                except json.JSONDecodeError:
                    logger.warning("⚠️  DID document is not valid JSON")
        else:
            logger.error(f"❌ {description}: {status_code}")
            if response:
                logger.debug(f"   Error: {response[:200]}...")
            all_passed = False
    
    return all_passed


def test_credential_storage(config) -> bool:
    """
    Test credential storage and retrieval.
    
    Args:
        config: Configuration object
        
    Returns:
        True if credential storage tests pass, False otherwise
    """
    logger.info("Testing credential storage...")
    
    # Check if credentials directory is mounted and accessible
    credentials_path = "assets/credentials"
    
    if os.path.exists(credentials_path):
        credential_files = [f for f in os.listdir(credentials_path) if f.endswith('.json')]
        logger.info(f"✅ Found {len(credential_files)} credential files in {credentials_path}")
        
        for cred_file in credential_files:
            logger.debug(f"   - {cred_file}")
        
        return True
    else:
        logger.warning(f"⚠️  Credentials directory not found: {credentials_path}")
        return False


def test_vault_integration(config) -> bool:
    """
    Test Vault integration for key storage.
    
    Args:
        config: Configuration object
        
    Returns:
        True if Vault integration tests pass, False otherwise
    """
    logger.info("Testing Vault integration...")
    
    # Test Vault connectivity
    vault_url = "http://localhost:8200/v1/sys/health"
    
    success, status_code, response = make_http_request(vault_url)
    
    if success and status_code in [200, 429, 472, 473]:
        logger.info(f"✅ Vault is accessible: {status_code}")
        return True
    else:
        logger.error(f"❌ Vault is not accessible: {status_code}")
        return False


def run_all_tests(config) -> bool:
    """
    Run all Identity Hub tests.
    
    Args:
        config: Configuration object
        
    Returns:
        True if all tests pass, False otherwise
    """
    logger.info("Running all Identity Hub tests...")
    logger.info("=" * 50)
    
    tests = [
        ("Health Endpoints", test_health_endpoints),
        ("Credentials API", test_credentials_api),
        ("STS API", test_sts_api),
        ("DID API", test_did_api),
        ("Credential Storage", test_credential_storage),
        ("Vault Integration", test_vault_integration),
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
    logger.info("Identity Hub Test Summary:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"  {status} {test_name}")
        if result:
            passed += 1
    
    logger.info(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All Identity Hub tests passed!")
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
    elif test_name == "credentials":
        success = test_credentials_api(config)
    elif test_name == "sts":
        success = test_sts_api(config)
    elif test_name == "did":
        success = test_did_api(config)
    elif test_name == "storage":
        success = test_credential_storage(config)
    elif test_name == "vault":
        success = test_vault_integration(config)
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