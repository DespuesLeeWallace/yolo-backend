#!/usr/bin/env python3
"""Test Resident Advisor scraper"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from scrapers.resident_advisor import ResidentAdvisorScraper, AREA_IDS


def test_single_city(city='madrid'):
    print(f"\n--- Testing RA for {city.title()} ---")
    scraper = ResidentAdvisorScraper()
    events = scraper.scrape_city(city)

    assert len(events) > 0, f"No events found for {city}"

    # Validate structure of first event
    e = events[0]
    assert e['title'] and len(e['title']) >= 3
    assert e['source'] == 'resident_advisor'
    assert e['source_id'] and e['source_id'].startswith('ra_')
    assert e['city'].lower() == city.lower()
    assert e['event_date'] is not None
    assert e['venue_name'] is not None

    print(f"  OK: {len(events)} events, first: {e['title']} @ {e['venue_name']} ({e['event_date']})")
    return events


def test_all_cities():
    print("\n=== Testing all RA cities ===")
    results = {}
    for city in AREA_IDS:
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
