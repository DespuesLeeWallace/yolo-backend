#!/usr/bin/env python3
"""Test Xceed scraper"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from scrapers.xceed import XceedScraper


def test_single_city(city='madrid'):
    print(f"\n--- Testing Xceed for {city.title()} ---")
    scraper = XceedScraper()
    events = scraper.scrape_city(city)

    assert len(events) > 0, f"No events found for {city}"

    e = events[0]
    assert e['title'] and len(e['title']) >= 3
    assert e['source'] == 'xceed'
    assert e['source_id'] and e['source_id'].startswith('xceed_')
    assert e['booking_url']

    print(f"\n  OK: {len(events)} events")
    for i, ev in enumerate(events[:5], 1):
        print(f"  {i}. {ev['title'][:50]} | {ev['venue_name']} | {ev['event_date']} | {ev['price_min']}")
    return events


if __name__ == "__main__":
    city = sys.argv[1] if len(sys.argv) > 1 else 'madrid'
    test_single_city(city)
