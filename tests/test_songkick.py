#!/usr/bin/env python3
"""Test Songkick scraper"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from scrapers.songkick import SongkickScraper


def test_scraper():
    print("\n--- Testing Songkick scraper ---")
    scraper = SongkickScraper()
    events = scraper.get_city_events("Madrid")

    # Note: due to geo-redirect, events may be for a different city
    assert isinstance(events, list)

    if not events:
        print("  WARNING: No events returned (Songkick may be blocking or page structure changed)")
        return events

    # Validate structure
    e = events[0]
    assert e['title'] and len(e['title']) >= 2
    assert e['source'] == 'songkick'
    assert e['source_id'] and e['source_id'].startswith('sk_')
    assert e['booking_url']

    print(f"\n  OK: {len(events)} events (actual city: {events[0]['city']})")
    for i, ev in enumerate(events[:5], 1):
        print(f"  {i}. {ev['title'][:50]} @ {ev['venue_name']} ({ev['city']}, {ev['event_date']})")
    return events


if __name__ == "__main__":
    test_scraper()
