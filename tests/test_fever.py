#!/usr/bin/env python3
"""Test Fever scraper"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from scrapers.fever import FeverScraper, CITY_CATEGORIES


def test_single_city(city='madrid'):
    print(f"\n--- Testing Fever for {city.title()} ---")
    scraper = FeverScraper()
    events = scraper.scrape_city(city)

    assert len(events) > 0, f"No events found for {city}"

    # Validate structure
    e = events[0]
    assert e['title'] and len(e['title']) >= 3
    assert e['source'] == 'fever'
    assert e['source_id'] and e['source_id'].startswith('fever_')
    assert e['booking_url']

    print(f"\n  OK: {len(events)} events total")
    for i, ev in enumerate(events[:3], 1):
        print(f"  {i}. {ev['title'][:50]} | {ev['category']} | {ev['venue_name']} | {ev['price_min']}")
    return events


def test_all_cities():
    print("\n=== Testing all Fever cities ===")
    results = {}
    for city in CITY_CATEGORIES:
        try:
            events = test_single_city(city)
            results[city] = len(events)
        except Exception as e:
            results[city] = f"FAILED: {e}"
            print(f"  FAILED: {e}")

    print("\n--- Results ---")
    for city, result in results.items():
        status = f"{result} events" if isinstance(result, int) else result
        print(f"  {city:12} {status}")


if __name__ == "__main__":
    city = sys.argv[1] if len(sys.argv) > 1 else None
    if city:
        test_single_city(city)
    else:
        test_all_cities()
