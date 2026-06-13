#!/usr/bin/env python3
"""
Dynamic IP Rotator – Guaranteed Delivery for Brute Force
- Every request retries until success (or max attempts)
- Auto‑refreshes proxy pool in background
- Strict validation (2/2 tests)
- Large pool (200 proxies)
- Fast failover to next proxy
"""

import random
import sys
import time
import threading
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from fake_useragent import UserAgent
from collections import deque

# Disable SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ========== CONFIGURATION ==========
REQUEST_TIMEOUT = 10
PROXY_VALIDATION_TIMEOUT = 5
MAX_WORKING_PROXIES = 200           # Keep a large pool
MIN_PROXIES_BEFORE_REFRESH = 50     # Refresh when below this
VALIDATE_WORKERS = 60
MAX_RETRIES_PER_REQUEST = 30        # Try up to 30 different proxies per request
MIN_DELAY = 0.3                     # Lower delay for speed
MAX_DELAY = 1.0

# ========== PROXY SOURCES (HTTP only for speed) ==========
PROXY_SOURCES = [
    "https://raw.githubusercontent.com/proxyscrape/free-proxy-list/main/proxies/http/data.txt",
    "https://raw.githubusercontent.com/fyvri/fresh-proxy-list/archive/storage/classic/http.txt",
    "https://raw.githubusercontent.com/Thordata/awesome-free-proxy-list/main/proxies/http.txt",
]

# ========== PROXY FETCHER ==========
def fetch_proxies_from_source(url, limit=2000):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            proxies = r.text.strip().split('\n')
            valid = []
            for p in proxies[:limit]:
                p = p.strip()
                if p and ':' in p and len(p.split(':')) == 2:
                    if not p.startswith('http://'):
                        p = f'http://{p}'
                    valid.append(p)
            return valid
    except:
        return []
    return []

def fetch_all_proxies():
    print("[*] Fetching fresh proxies...")
    all_proxies = set()
    for url in PROXY_SOURCES:
        proxies = fetch_proxies_from_source(url, limit=2000)
        all_proxies.update(proxies)
        print(f"    {url.split('/')[-1][:20]}: {len(proxies)} proxies")
    
    all_list = list(all_proxies)
    print(f"[+] Total unique: {len(all_list)}")
    
    if len(all_list) > 5000:
        all_list = random.sample(all_list, 5000)
        print(f"[+] Randomly selected 5000 for validation")
    return all_list

# ========== STRICT VALIDATION ==========
def validate_proxy_strict(proxy):
    """Test proxy twice – must pass both times."""
    test_url = "http://httpbin.org/ip"
    for _ in range(2):
        try:
            r = requests.get(test_url, proxies={"http": proxy}, timeout=PROXY_VALIDATION_TIMEOUT)
            if r.status_code != 200:
                return proxy, False
        except:
            return proxy, False
    return proxy, True

def validate_proxies(proxies, target=MAX_WORKING_PROXIES):
    print(f"[*] Validating proxies (strict, target: {target})...")
    working = []
    with ThreadPoolExecutor(max_workers=VALIDATE_WORKERS) as executor:
        futures = {executor.submit(validate_proxy_strict, p): p for p in proxies}
        for future in as_completed(futures):
            proxy, ok = future.result()
            if ok:
                working.append(proxy)
                if len(working) % 20 == 0:
                    print(f"    ... found {len(working)} stable proxies")
                if len(working) >= target:
                    for f in futures:
                        f.cancel()
                    break
    print(f"[+] Found {len(working)} stable proxies")
    return working[:target]

# ========== STEALTH ==========
ua_gen = UserAgent()

def get_random_headers():
    return {
        "User-Agent": ua_gen.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    }

def random_delay():
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

# ========== CORE ROTATOR ==========
class IPRotator:
    def __init__(self):
        self.proxies = deque()
        self.lock = threading.Lock()
        self.refresh_pool()
        # Start background refresher
        self.stop_refresh = False
        self.refresh_thread = threading.Thread(target=self._background_refresh, daemon=True)
        self.refresh_thread.start()

    def refresh_pool(self):
        """Fetch and validate fresh proxies (blocking)."""
        raw = fetch_all_proxies()
        working = validate_proxies(raw, target=MAX_WORKING_PROXIES)
        with self.lock:
            self.proxies.clear()
            self.proxies.extend(working)
        if len(self.proxies) == 0:
            print("[!] No working proxies found. Trying again in 10 seconds...")
            time.sleep(10)
            self.refresh_pool()
        else:
            print(f"[+] Proxy pool ready: {len(self.proxies)} working proxies\n")

    def _background_refresh(self):
        """Keep pool fresh every 3 minutes."""
        while not self.stop_refresh:
            time.sleep(180)  # 3 minutes
            with self.lock:
                if len(self.proxies) < MIN_PROXIES_BEFORE_REFRESH:
                    print("\n[*] Proxy pool low. Refreshing in background...")
                    threading.Thread(target=self.refresh_pool, daemon=True).start()

    def _get_proxy(self):
        """Get next proxy (non-blocking). Returns None if empty."""
        with self.lock:
            if not self.proxies:
                return None
            proxy = self.proxies.popleft()
            self.proxies.append(proxy)
            return proxy

    def _mark_dead(self, proxy):
        """Remove dead proxy from pool."""
        with self.lock:
            if proxy in self.proxies:
                self.proxies.remove(proxy)

    def send_request(self, url, method="GET", data=None, custom_headers=None):
        """
        Send request – retry with different proxies until success or max retries.
        Returns response object on success.
        Raises exception only after MAX_RETRIES_PER_REQUEST attempts.
        """
        random_delay()
        headers = get_random_headers()
        if custom_headers:
            headers.update(custom_headers)

        for attempt in range(MAX_RETRIES_PER_REQUEST):
            proxy = self._get_proxy()
            if not proxy:
                print("    [!] No proxies left. Forcing pool refresh...")
                self.refresh_pool()
                proxy = self._get_proxy()
                if not proxy:
                    continue

            try:
                print(f"    [{attempt+1}] {proxy[:50]}...", end=" ", flush=True)
                response = requests.request(
                    method=method,
                    url=url,
                    proxies={"http": proxy, "https": proxy},
                    headers=headers,
                    data=data,
                    timeout=REQUEST_TIMEOUT,
                    verify=False
                )
                print(f"✓ {response.status_code}")
                return response
            except Exception as e:
                print(f"✗ {str(e)[:30]}")
                self._mark_dead(proxy)
                # Continue to next proxy

        raise Exception(f"Failed after {MAX_RETRIES_PER_REQUEST} proxy attempts")

# ========== COMMAND LINE ==========
def legal_warning():
    print("\033[91m" + "="*60)
    print("WARNING: This tool is for AUTHORIZED SECURITY TESTING ONLY.")
    print("Using it without written permission is ILLEGAL.")
    print("="*60 + "\033[0m")
    ans = input("Do you have explicit permission? (yes/no): ")
    if ans.lower() != "yes":
        print("Aborted.")
        sys.exit(0)

def main():
    if len(sys.argv) < 2:
        print("Usage: python rotator.py <URL> [-n count] [-m GET|POST] [-d data]")
        print("Example: python rotator.py https://httpbin.org/ip -n 10")
        sys.exit(1)

    url = sys.argv[1]
    num = 1
    method = "GET"
    data = None

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "-n" and i+1 < len(sys.argv):
            num = int(sys.argv[i+1]); i += 2
        elif sys.argv[i] == "-m" and i+1 < len(sys.argv):
            method = sys.argv[i+1].upper(); i += 2
        elif sys.argv[i] == "-d" and i+1 < len(sys.argv):
            data = sys.argv[i+1]; i += 2
        else:
            print(f"Unknown option: {sys.argv[i]}"); sys.exit(1)

    legal_warning()
    rotator = IPRotator()

    print(f"\n[*] Target: {url}")
    print(f"[*] Requests: {num}")
    print("-"*50)

    successful = 0
    for i in range(num):
        print(f"\n--- Request {i+1}/{num} ---")
        try:
            resp = rotator.send_request(url, method=method, data=data)
            successful += 1
            if resp.text:
                preview = resp.text[:200].replace('\n', ' ')
                print(f"    Response: {preview}")
        except Exception as e:
            print(f"    ❌ Final failure: {e}")

    print("\n" + "="*50)
    print(f"[*] Complete: {successful}/{num} successful ({successful/num*100:.0f}%)")

if __name__ == "__main__":
    main()
