#!/usr/bin/env python3
"""
Test RA with different header combinations across all cities
Find the combination that works for EVERYONE
"""

import requests
import time

CITIES = [
    ('madrid', 'ES'),
    ('barcelona', 'ES'),
    ('lisbon', 'PT'),
    ('berlin', 'DE'),
    ('amsterdam', 'NL'),
]


def test_headers(name, headers, test_all=True):
    """Test a header combination across all cities"""
    print(f"\n{'=' * 60}")
    print(f"Testing: {name}")
    print(f"{'=' * 60}")

    results = {}
    session = requests.Session()
    session.headers.update(headers)

    for city, country in CITIES:
        url = f"https://ra.co/events/{country.lower()}/{city.lower()}"

        try:
            time.sleep(2)  # Delay between requests
            response = session.get(url, timeout=10)

            success = response.status_code == 200 and len(response.content) > 10000
            results[city] = success

            status = "✅" if success else "❌"
            print(f"  {city:12} {status}  (Status: {response.status_code}, Size: {len(response.content)})")

            # If testing all, continue; otherwise stop on first failure
            if not test_all and not success:
                break

        except Exception as e:
            results[city] = False
            print(f"  {city:12} ❌  Error: {e}")
            if not test_all:
                break

    # Summary
    success_count = sum(results.values())
    total_count = len(results)
    print(f"\n  Result: {success_count}/{total_count} cities working")

    return results


def test_combo_1():
    """Your current headers (Chrome 142 with Client Hints)"""
    return test_headers(
        "Combo 1: Chrome 142 + Client Hints (Current)",
        {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en,es-ES;q=0.9,es;q=0.8,da;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
        }
    )


def test_combo_2():
    """Chrome 119 that worked for Barcelona before"""
    return test_headers(
        "Combo 2: Chrome 119 (Previously Working)",
        {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.google.com/',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    )


def test_combo_3():
    """Chrome 142 WITHOUT Client Hints"""
    return test_headers(
        "Combo 3: Chrome 142 WITHOUT Client Hints",
        {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en,es-ES;q=0.9,es;q=0.8,da;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    )


def test_combo_4():
    """Chrome 142 with Google Referer (no Client Hints)"""
    return test_headers(
        "Combo 4: Chrome 142 + Google Referer (no Client Hints)",
        {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.google.com/',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    )


def test_combo_5():
    """Minimal headers"""
    return test_headers(
        "Combo 5: Minimal Headers (User-Agent + Accept only)",
        {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
    )


def test_combo_6():
    """Chrome 119 with matching Client Hints"""
    return test_headers(
        "Combo 6: Chrome 119 + Client Hints (Version Match)",
        {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.google.com/',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'sec-ch-ua': '"Chromium";v="119", "Google Chrome";v="119", "Not?A_Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
        }
    )


def test_combo_7():
    """Chrome 142 + Sec-Fetch headers (no Client Hints)"""
    return test_headers(
        "Combo 7: Chrome 142 + Sec-Fetch (no Client Hints)",
        {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.google.com/',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
        }
    )


def main():
    print("\n" + "=" * 60)
    print("RA Header Compatibility Test - All Cities")
    print("=" * 60)
    print("\nTesting different header combinations...")
    print("Goal: Find headers that work for ALL cities\n")

    all_results = {}

    # Test all combinations
    all_results['combo1'] = test_combo_1()
    time.sleep(5)

    all_results['combo2'] = test_combo_2()
    time.sleep(5)

    all_results['combo3'] = test_combo_3()
    time.sleep(5)

    all_results['combo4'] = test_combo_4()
    time.sleep(5)

    all_results['combo5'] = test_combo_5()
    time.sleep(5)

    all_results['combo6'] = test_combo_6()
    time.sleep(5)

    all_results['combo7'] = test_combo_7()

    # Final summary
    print("\n" + "=" * 60)
    print("FINAL RESULTS - COMPATIBILITY MATRIX")
    print("=" * 60)

    print(f"\n{'Combination':<45} {'Success Rate':<15}")
    print("-" * 60)

    best_combo = None
    best_score = 0

    for combo_name, results in all_results.items():
        score = sum(results.values())
        total = len(results)
        percentage = (score / total * 100) if total > 0 else 0

        print(f"{combo_name:<45} {score}/{total} ({percentage:.0f}%)")

        if score > best_score:
            best_score = score
            best_combo = combo_name

    print("\n" + "=" * 60)
    if best_score == 5:
        print(f"🎉 WINNER: {best_combo} works for ALL cities!")
    elif best_score >= 3:
        print(f"✅ BEST: {best_combo} works for {best_score}/5 cities")
        print(f"   Consider using this with retry logic for failed cities")
    else:
        print(f"⚠️  No combination works reliably")
        print(f"   Best option: {best_combo} ({best_score}/5)")
        print(f"   Recommendation: Use multiple scrapers or wait for IP cooldown")
    print("=" * 60)

    # Show which cities worked
    if best_combo:
        print(f"\n{best_combo} results per city:")
        for city, worked in all_results[best_combo].items():
            status = "✅" if worked else "❌"
            print(f"  {city:12} {status}")


if __name__ == "__main__":
    main()