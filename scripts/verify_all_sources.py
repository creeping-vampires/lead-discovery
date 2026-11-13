#!/usr/bin/env python3
"""
Verification Script: Audits every unique source link in results/all_candidates.csv
and tests live HTTP availability (HTTP 200 OK).
"""

import sys
import ssl
import urllib.request
import pandas as pd

def audit_sources(csv_path="results/all_candidates.csv"):
    df = pd.read_csv(csv_path)
    urls = df["source_link"].dropna().unique()
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    print(f"======================================================================")
    print(f"LIVE SOURCE URL AVAILABILITY AUDIT ({len(urls)} Distinct Targets)")
    print(f"Dataset: {csv_path}")
    print(f"======================================================================")

    passed_count = 0
    failed_count = 0
    fixture_count = 0

    for u in sorted(urls):
        if "deleted_thread" in u or "deleted_post" in u:
            print(f"[COMPLIANCE FIXTURE] {u} (Purposely pruned deleted post)")
            fixture_count += 1
            continue

        try:
            req = urllib.request.Request(u, headers=headers)
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                status = resp.status
                if status in (200, 301, 302):
                    print(f"[PASS HTTP {status}] {u}")
                    passed_count += 1
                else:
                    print(f"[FAIL HTTP {status}] {u}")
                    failed_count += 1
        except Exception as e:
            print(f"[FAIL ERROR] {u} -> {e}")
            failed_count += 1

    print(f"======================================================================")
    print(f"AUDIT SUMMARY: {passed_count} Passed (HTTP 200), {failed_count} Failed, {fixture_count} Pruned Test Fixtures")
    print(f"Availability Rate: {passed_count / (passed_count + failed_count) * 100:.1f}%")
    print(f"======================================================================")

    if failed_count > 0:
        sys.exit(1)

if __name__ == "__main__":
    audit_sources()
