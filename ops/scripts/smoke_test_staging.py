"""Staging smoke tests for CD pipeline.

Validates that core services are healthy after staging deployment
before promoting to production.

Usage:
    STAGING_API_URL=https://staging-api.example.com python ops/scripts/smoke_test_staging.py
"""

from __future__ import annotations

import os
import sys
import time
import urllib.request
import urllib.error


STAGING_API_URL = os.environ.get("STAGING_API_URL", "").rstrip("/")

HEALTH_ENDPOINTS = [
    ("/healthz", "api-gateway"),
    ("/v1/health/ready", "api-gateway-readiness"),
]

# Endpoints that should return a non-5xx response (401/403 is acceptable)
API_ENDPOINTS = [
    ("/v1/projects", "projects-api"),
    ("/v1/portfolios", "portfolios-api"),
]

MAX_RETRIES = 3
RETRY_DELAY_S = 5
TIMEOUT_S = 10
MAX_RESPONSE_TIME_S = 5.0


def check_endpoint(base_url: str, path: str, label: str) -> bool:
    url = f"{base_url}{path}"
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            start = time.monotonic()
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                elapsed = time.monotonic() - start
                status = resp.getcode()
                if 200 <= status < 300:
                    if elapsed > MAX_RESPONSE_TIME_S:
                        print(
                            f"  WARN  {label} ({url}) -> {status} "
                            f"but slow ({elapsed:.1f}s > {MAX_RESPONSE_TIME_S}s)"
                        )
                    else:
                        print(f"  PASS  {label} ({url}) -> {status} ({elapsed:.1f}s)")
                    return True
                print(f"  WARN  {label} ({url}) -> {status} (attempt {attempt}/{MAX_RETRIES})")
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            print(f"  FAIL  {label} ({url}) -> {exc} (attempt {attempt}/{MAX_RETRIES})")
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY_S)
    return False


def check_api_endpoint(base_url: str, path: str, label: str) -> bool:
    """Check that an API endpoint responds without a 5xx error."""
    url = f"{base_url}{path}"
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                status = resp.getcode()
                print(f"  PASS  {label} ({url}) -> {status}")
                return True
        except urllib.error.HTTPError as exc:
            if exc.code < 500:
                # 401/403/404 are acceptable -- service is running
                print(f"  PASS  {label} ({url}) -> {exc.code} (auth expected)")
                return True
            print(f"  FAIL  {label} ({url}) -> {exc.code} (attempt {attempt}/{MAX_RETRIES})")
        except (urllib.error.URLError, OSError) as exc:
            print(f"  FAIL  {label} ({url}) -> {exc} (attempt {attempt}/{MAX_RETRIES})")
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY_S)
    return False


def main() -> int:
    if not STAGING_API_URL:
        print("ERROR: STAGING_API_URL environment variable is required.")
        return 1

    print(f"Running staging smoke tests against: {STAGING_API_URL}")
    print()

    failures: list[str] = []

    print("--- Health endpoints ---")
    for path, label in HEALTH_ENDPOINTS:
        if not check_endpoint(STAGING_API_URL, path, label):
            failures.append(label)

    print("\n--- API endpoints (non-5xx check) ---")
    for path, label in API_ENDPOINTS:
        if not check_api_endpoint(STAGING_API_URL, path, label):
            failures.append(label)

    total = len(HEALTH_ENDPOINTS) + len(API_ENDPOINTS)
    print()
    if failures:
        print(f"FAILED: {len(failures)} endpoint(s) did not respond: {', '.join(failures)}")
        return 1

    print(f"All {total} staging smoke tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
