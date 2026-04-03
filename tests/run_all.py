#!/usr/bin/env python3
"""Run all scraper tests"""

import subprocess
import sys
import os

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON = sys.executable

TESTS = [
    "test_resident_advisor.py",
    "test_fever.py",
    "test_songkick.py",
    "test_xceed.py",
]


def main():
    results = {}
    for test in TESTS:
        print(f"\n{'='*60}")
        print(f"Running {test}")
        print(f"{'='*60}")
        result = subprocess.run([PYTHON, os.path.join(TESTS_DIR, test)])
        results[test] = result.returncode == 0

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for test, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {test:40} {status}")

    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
