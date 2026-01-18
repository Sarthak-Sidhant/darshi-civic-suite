#!/usr/bin/env python3
"""
End-to-End Test Suite for Darshi Backend
Tests all critical endpoints to ensure production readiness
"""

import requests
import sys
import json
from typing import Dict, Any

# Configuration
BASE_URL = "https://api.darshi.app"
TEST_REPORT_ID = None  # Will be populated during tests

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_test(name: str):
    print(f"\n{Colors.BLUE}Testing:{Colors.END} {name}")

def print_success(message: str):
    print(f"  {Colors.GREEN}✓{Colors.END} {message}")

def print_error(message: str):
    print(f"  {Colors.RED}✗{Colors.END} {message}")

def print_warning(message: str):
    print(f"  {Colors.YELLOW}⚠{Colors.END} {message}")

def test_health_check() -> bool:
    """Test /health endpoint"""
    print_test("Health Check")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Status: {data.get('status')}")
            
            # Check individual services
            checks = data.get('checks', {})
            for service, status in checks.items():
                if status.get('status') == 'healthy':
                    print_success(f"{service}: healthy")
                else:
                    print_warning(f"{service}: {status.get('status')}")
            return True
        else:
            print_error(f"Failed with status {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Exception: {e}")
        return False

def test_get_reports() -> bool:
    """Test GET /api/v1/reports"""
    print_test("Get Reports List")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/reports?limit=5", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                print_success(f"Retrieved {len(data)} reports")
                if len(data) > 0:
                    global TEST_REPORT_ID
                    TEST_REPORT_ID = data[0].get('id')
                    print_success(f"Sample report ID: {TEST_REPORT_ID}")
                return True
            else:
                print_error(f"Unexpected response format: {type(data)}")
                return False
        else:
            print_error(f"Failed with status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print_error(f"Exception: {e}")
        return False

def test_get_single_report() -> bool:
    """Test GET /api/v1/report/{id}"""
    if not TEST_REPORT_ID:
        print_warning("Skipping - no report ID available")
        return True
    
    print_test("Get Single Report")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/report/{TEST_REPORT_ID}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Title: {data.get('title', 'N/A')}")
            print_success(f"Status: {data.get('status', 'N/A')}")
            print_success(f"Severity: {data.get('severity', 'N/A')}")
            return True
        else:
            print_error(f"Failed with status {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Exception: {e}")
        return False

def test_get_cities() -> bool:
    """Test GET /api/v1/cities"""
    print_test("Get Cities List")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/cities", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                print_success(f"Retrieved {len(data)} cities")
                return True
            else:
                print_error(f"Unexpected response format: {type(data)}")
                return False
        else:
            print_error(f"Failed with status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print_error(f"Exception: {e}")
        return False

def test_get_comments() -> bool:
    """Test GET /api/v1/report/{id}/comments"""
    if not TEST_REPORT_ID:
        print_warning("Skipping - no report ID available")
        return True
    
    print_test("Get Report Comments")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/report/{TEST_REPORT_ID}/comments", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                print_success(f"Retrieved {len(data)} comments")
                return True
            else:
                print_error(f"Unexpected response format: {type(data)}")
                return False
        else:
            print_error(f"Failed with status {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Exception: {e}")
        return False

def test_get_updates() -> bool:
    """Test GET /api/v1/reports/{id}/updates"""
    if not TEST_REPORT_ID:
        print_warning("Skipping - no report ID available")
        return True
    
    print_test("Get Report Updates")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/reports/{TEST_REPORT_ID}/updates", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                print_success(f"Retrieved {len(data)} updates")
                return True
            else:
                print_error(f"Unexpected response format: {type(data)}")
                return False
        else:
            print_error(f"Failed with status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print_error(f"Exception: {e}")
        return False

def test_geocoding() -> bool:
    """Test geocoding endpoints"""
    print_test("Geocoding Services")
    try:
        # Test reverse geocode
        response = requests.get(
            f"{BASE_URL}/api/v1/reverse-geocode?lat=23.3441&lng=85.3096",
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            print_success(f"Reverse geocode: {data.get('address', 'N/A')}")
            return True
        else:
            print_error(f"Failed with status {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Exception: {e}")
        return False

def test_ping() -> bool:
    """Test /ping endpoint for latency"""
    print_test("Ping (Latency Check)")
    try:
        import time
        start = time.time()
        response = requests.get(f"{BASE_URL}/ping", timeout=10)
        rtt = (time.time() - start) * 1000
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Round-trip time: {rtt:.2f}ms")
            print_success(f"Server region: {data.get('region', 'N/A')}")
            return True
        else:
            print_error(f"Failed with status {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Exception: {e}")
        return False

def run_all_tests():
    """Run all E2E tests"""
    print(f"\n{'='*60}")
    print(f"{Colors.BLUE}Darshi Backend E2E Test Suite{Colors.END}")
    print(f"Target: {BASE_URL}")
    print(f"{'='*60}")
    
    tests = [
        ("Health Check", test_health_check),
        ("Ping", test_ping),
        ("Get Reports", test_get_reports),
        ("Get Single Report", test_get_single_report),
        ("Get Cities", test_get_cities),
        ("Get Comments", test_get_comments),
        ("Get Updates", test_get_updates),
        ("Geocoding", test_geocoding),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print_error(f"Test crashed: {e}")
            results.append((name, False))
    
    # Summary
    print(f"\n{'='*60}")
    print(f"{Colors.BLUE}Test Summary{Colors.END}")
    print(f"{'='*60}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = f"{Colors.GREEN}PASS{Colors.END}" if result else f"{Colors.RED}FAIL{Colors.END}"
        print(f"{status} - {name}")
    
    print(f"\n{Colors.BLUE}Total: {passed}/{total} tests passed{Colors.END}")
    
    if passed == total:
        print(f"{Colors.GREEN}✓ All tests passed! Backend is ready for production.{Colors.END}\n")
        return 0
    else:
        print(f"{Colors.RED}✗ Some tests failed. Please fix issues before deploying.{Colors.END}\n")
        return 1

if __name__ == "__main__":
    sys.exit(run_all_tests())
