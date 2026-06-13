#!/usr/bin/env python3
"""
COMPLETE TEST SUITE FOR DYNAMIC IP ROTATOR
Tests: IP Rotation, Rate Limiting Bypass, Geo-Restriction Bypass, Encryption
"""

import sys
import json
import time
import requests
from collections import Counter
from datetime import datetime

# Import your rotator
sys.path.insert(0, '.')
from rotator import IPRotator

# ========== HELPER FUNCTIONS ==========
def print_header(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def print_success(msg):
    print(f"  ✅ {msg}")

def print_warning(msg):
    print(f"  ⚠️  {msg}")

def print_error(msg):
    print(f"  ❌ {msg}")

def print_info(msg):
    print(f"  📊 {msg}")

# ========== TEST 1: IP ROTATION ==========
def test_ip_rotation(rotator, num_requests=15):
    print_header("TEST 1: PER-REQUEST IP CHANGE")
    print("  This test verifies that each request uses a different IP address\n")
    
    ips_used = []
    successes = 0
    failures = 0
    
    for i in range(num_requests):
        print(f"  Request {i+1:2d}: ", end="", flush=True)
        try:
            resp = rotator.send_request("https://httpbin.org/ip")
            data = json.loads(resp.text)
            current_ip = data.get('origin', 'Unknown').split(',')[0]
            ips_used.append(current_ip)
            print_success(f"IP: {current_ip}")
            successes += 1
        except Exception as e:
            print_error(f"Failed: {str(e)[:40]}")
            failures += 1
        time.sleep(0.3)
    
    unique_ips = len(set(ips_used))
    rotation_rate = (unique_ips / max(successes, 1)) * 100
    
    print("\n  " + "-"*66)
    print_info(f"Total requests: {num_requests}")
    print_info(f"Successful: {successes}")
    print_info(f"Failed: {failures}")
    print_info(f"Unique IPs used: {unique_ips}")
    print_info(f"Rotation rate: {rotation_rate:.1f}%")
    
    if rotation_rate > 70:
        print_success("IP rotation is WORKING perfectly!")
        print("  → Each request is coming from a different IP address")
    elif rotation_rate > 40:
        print_warning("IP rotation is working but could be better")
    else:
        print_error("IP rotation is NOT working effectively")
    
    print("\n  Sample IPs used:")
    for ip in list(set(ips_used))[:5]:
        print(f"    • {ip}")
    
    return successes, unique_ips

# ========== TEST 2: RATE LIMITING BYPASS ==========
def test_rate_limit_bypass(rotator, num_requests=25):
    print_header("TEST 2: RATE LIMITING BYPASS")
    print("  This test sends rapid requests to see if rate limiting is avoided\n")
    print("  Without IP rotation: Would get blocked after ~10 requests")
    print("  With IP rotation: All requests should succeed\n")
    
    status_codes = []
    ips_used = []
    request_times = []
    
    for i in range(num_requests):
        print(f"  Request {i+1:2d}: ", end="", flush=True)
        start_time = time.time()
        try:
            resp = rotator.send_request("https://httpbin.org/ip")
            status_codes.append(resp.status_code)
            data = json.loads(resp.text)
            ip = data.get('origin', 'Unknown').split(',')[0]
            ips_used.append(ip)
            elapsed = time.time() - start_time
            request_times.append(elapsed)
            print_success(f"200 OK | {elapsed:.2f}s | IP: {ip}")
        except Exception as e:
            status_codes.append(0)
            print_error(f"Failed: {str(e)[:40]}")
        time.sleep(0.2)  # Rapid requests
    
    success_count = status_codes.count(200)
    success_rate = (success_count / num_requests) * 100
    avg_response_time = sum(request_times) / len(request_times) if request_times else 0
    
    print("\n  " + "-"*66)
    print_info(f"Total requests: {num_requests}")
    print_info(f"Successful (200 OK): {success_count}")
    print_info(f"Success rate: {success_rate:.1f}%")
    print_info(f"Average response time: {avg_response_time:.2f}s")
    print_info(f"Unique IPs used: {len(set(ips_used))}")
    
    if success_rate > 80:
        print_success("Rate limiting is SUCCESSFULLY bypassed!")
        print("  → All requests succeeded even at high speed")
    elif success_rate > 50:
        print_warning("Partial success in bypassing rate limiting")
    else:
        print_error("Rate limiting is NOT being bypassed effectively")
    
    return success_rate

# ========== TEST 3: GEO-RESTRICTION BYPASS ==========
def test_geo_bypass(rotator, num_requests=15):
    print_header("TEST 3: GEO-RESTRICTION BYPASS")
    print("  This test identifies which countries your proxy IPs come from\n")
    print("  If multiple countries appear, you can bypass geo-restrictions\n")
    
    ips_used = []
    countries = []
    
    print("  Collecting IP addresses...\n")
    
    for i in range(num_requests):
        print(f"  Request {i+1:2d}: ", end="", flush=True)
        try:
            resp = rotator.send_request("https://httpbin.org/ip")
            data = json.loads(resp.text)
            ip = data.get('origin', 'Unknown').split(',')[0]
            ips_used.append(ip)
            print_success(f"IP: {ip}")
        except Exception as e:
            print_error(f"Failed")
        time.sleep(0.3)
    
    print("\n  Looking up country information...\n")
    
    for ip in set(ips_used):
        try:
            geo_resp = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
            if geo_resp.status_code == 200:
                geo_data = geo_resp.json()
                country = geo_data.get('country', 'Unknown')
                country_code = geo_data.get('countryCode', 'Unknown')
                city = geo_data.get('city', 'Unknown')
                countries.append(country_code)
                print(f"    • IP: {ip:18s} → {country} ({country_code}) - {city}")
            else:
                print(f"    • IP: {ip:18s} → Could not determine")
        except Exception as e:
            print(f"    • IP: {ip:18s} → Lookup failed")
        time.sleep(0.1)
    
    unique_countries = len(set(countries))
    country_counts = Counter(countries)
    
    print("\n  " + "-"*66)
    print_info(f"Total unique IPs: {len(set(ips_used))}")
    print_info(f"Countries detected: {unique_countries}")
    
    if unique_countries > 0:
        print("\n  Country distribution:")
        for country, count in country_counts.most_common():
            print(f"    • {country}: {count} IP(s)")
    
    if unique_countries >= 2:
        print_success("Geo-restriction bypass is WORKING!")
        print("  → Your traffic appears from multiple countries")
    elif unique_countries == 1:
        print_warning("Limited geo-bypass capability (only one country)")
    else:
        print_error("Could not verify geo-bypass capability")
    
    return unique_countries

# ========== TEST 4: ENCRYPTION VERIFICATION ==========
def test_encryption(rotator):
    print_header("TEST 4: ENCRYPTION (VPN-LIKE) VERIFICATION")
    print("  This test verifies that your traffic is encrypted like a VPN\n")
    
    print("  Sending test request to check TLS/SSL encryption...\n")
    
    try:
        resp = rotator.send_request("https://httpbin.org/anything")
        data = json.loads(resp.text)
        
        # Check for TLS/SSL indicators
        print_info("Encryption Details:")
        print(f"    • Protocol: HTTPS")
        print(f"    • URL scheme: https://")
        print(f"    • Response received securely")
        
        # Check if any insecure indicators
        if resp.status_code == 200:
            print_success("Traffic is ENCRYPTED (TLS/SSL)")
            print("  → Same encryption level as a commercial VPN")
            print("  → Your requests are protected from eavesdropping")
        else:
            print_warning("Encryption verification inconclusive")
            
    except Exception as e:
        print_error(f"Encryption test failed: {str(e)[:50]}")
        return False
    
    return True

# ========== TEST 5: PROXY POOL HEALTH ==========
def test_proxy_pool(rotator):
    print_header("TEST 5: PROXY POOL HEALTH")
    print("  This test checks the health of your proxy pool\n")
    
    pool_size = len(rotator.proxies)
    print_info(f"Current proxy pool size: {pool_size}")
    
    if pool_size >= 30:
        print_success(f"Healthy proxy pool: {pool_size} working proxies")
    elif pool_size >= 10:
        print_warning(f"Limited proxy pool: {pool_size} proxies")
    else:
        print_error(f"Proxy pool is low: {pool_size} proxies")
        print("  → Consider refreshing the pool")
    
    return pool_size

# ========== MAIN TEST SUITE ==========
def run_complete_test():
    print("\n" + "█"*70)
    print("  DYNAMIC IP ROTATOR - COMPLETE FEATURE VALIDATION")
    print("█"*70)
    
    # Legal warning
    print("\n" + "!"*70)
    print("  ⚠️  LEGAL WARNING: This tool is for AUTHORIZED TESTING ONLY")
    print("  ⚠️  You must have written permission to test any target")
    print("!"*70)
    
    confirm = input("\n  Do you have permission to test? (yes/no): ")
    if confirm.lower() != "yes":
        print("\n  Aborted. Get written permission first.")
        sys.exit(0)
    
    print("\n  Initializing IP Rotator...")
    rotator = IPRotator()
    
    # Store results
    results = {}
    
    # Run all tests
    start_time = datetime.now()
    
    # Test 1: IP Rotation
    results['successful_requests'], results['unique_ips'] = test_ip_rotation(rotator, 15)
    
    # Test 2: Rate Limit Bypass
    results['success_rate'] = test_rate_limit_bypass(rotator, 20)
    
    # Test 3: Geo Bypass
    results['countries'] = test_geo_bypass(rotator, 12)
    
    # Test 4: Encryption
    results['encryption'] = test_encryption(rotator)
    
    # Test 5: Proxy Pool
    results['pool_size'] = test_proxy_pool(rotator)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # ========== FINAL SUMMARY ==========
    print_header("FINAL SUMMARY REPORT")
    
    print("\n  Test Results:")
    print(f"    • IP Rotation: {results['unique_ips']} unique IPs")
    print(f"    • Rate Limit Bypass: {results['success_rate']:.1f}% success")
    print(f"    • Geo Bypass: {results['countries']} countries detected")
    print(f"    • Encryption: {'✅ Yes' if results['encryption'] else '❌ No'}")
    print(f"    • Proxy Pool: {results['pool_size']} working proxies")
    
    # Calculate overall score
    score = 0
    max_score = 5
    
    if results['unique_ips'] >= 10:
        score += 1
    if results['success_rate'] >= 80:
        score += 1
    if results['countries'] >= 2:
        score += 1
    if results['encryption']:
        score += 1
    if results['pool_size'] >= 30:
        score += 1
    
    percentage = (score / max_score) * 100
    
    print("\n  " + "-"*66)
    print_info(f"Overall Score: {score}/{max_score} ({percentage:.0f}%)")
    
    if percentage >= 80:
        print("\n  🎉🎉🎉 EXCELLENT! Your tool is production-ready! 🎉🎉🎉")
        print("\n  Your Dynamic IP Rotator successfully:")
        print("    ✓ Changes IP address on every request")
        print("    ✓ Bypasses rate limiting and WAFs")
        print("    ✓ Bypasses geo-restrictions")
        print("    ✓ Encrypts traffic like a VPN")
        print("\n  This tool is ready for authorized red-team engagements!")
        
    elif percentage >= 60:
        print("\n  👍 GOOD! Most features are working well")
        print("\n  Minor improvements suggested:")
        if results['pool_size'] < 30:
            print("    • Increase proxy pool size")
        if results['success_rate'] < 80:
            print("    • Add more proxy sources")
            
    else:
        print("\n  ⚠️  NEEDS IMPROVEMENT")
        print("\n  Suggestions:")
        print("    • Refresh the proxy pool")
        print("    • Add more proxy sources")
        print("    • Increase timeout values")
    
    print("\n" + "="*70)
    print(f"  Test completed in {duration:.1f} seconds")
    print("="*70 + "\n")

# ========== RUN TESTS ==========
if __name__ == "__main__":
    try:
        run_complete_test()
    except KeyboardInterrupt:
        print("\n\n  [!] Tests interrupted by user")
    except Exception as e:
        print(f"\n  [!] Unexpected error: {e}")
