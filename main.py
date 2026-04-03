#!/usr/bin/env python3
"""
YOLO Scrapers - Main Entry Point

Runs all scrapers and saves results to Supabase.
Designed to be run on a schedule (GitHub Actions, cron, Cloud Run Job, etc).
"""

import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from database import DatabaseManager
from scrapers.resident_advisor import ResidentAdvisorScraper, AREA_IDS
from scrapers.fever import FeverScraper, CITY_CATEGORIES
from scrapers.xceed import XceedScraper, CITY_SLUGS
from scrapers.songkick import SongkickScraper


def run_scraper(db, name, scrape_fn):
    """Run a scraper, save events, and log the run."""
    started_at = datetime.now()
    print(f"\n{'='*60}")
    print(f"Starting {name}")
    print(f"{'='*60}\n")

    try:
        events = scrape_fn()
        print(f"\nScraped {len(events)} events")

        new_count, updated_count = db.save_events(events)
        print(f"New: {new_count}, Updated: {updated_count}")

        db.log_scraper_run(name, started_at, datetime.now(), 'success',
                           events_found=len(events), events_new=new_count)
        return True

    except Exception as e:
        print(f"Error: {e}")
        db.log_scraper_run(name, started_at, datetime.now(), 'failed',
                           error_message=str(e))
        return False


def scrape_resident_advisor():
    scraper = ResidentAdvisorScraper()
    all_events = []
    for city in AREA_IDS:
        print(f"Scraping {city.title()}...")
        all_events.extend(scraper.scrape_city(city))
    return all_events


def scrape_fever():
    scraper = FeverScraper()
    all_events = []
    for city in CITY_CATEGORIES:
        print(f"Scraping {city.title()}...")
        all_events.extend(scraper.scrape_city(city))
    return all_events


def scrape_xceed():
    scraper = XceedScraper()
    all_events = []
    for city in CITY_SLUGS:
        print(f"Scraping {city.title()}...")
        all_events.extend(scraper.scrape_city(city))
    return all_events


def scrape_songkick():
    scraper = SongkickScraper()
    all_events = []
    for city in ['Madrid', 'Barcelona', 'Lisbon', 'Berlin', 'Amsterdam']:
        print(f"Scraping {city}...")
        all_events.extend(scraper.get_city_events(city))
    return all_events


def main():
    print("="*60)
    print(f"YOLO Event Scrapers — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    db = DatabaseManager()
    print("Database connection OK\n")

    results = {}
    results['resident_advisor'] = run_scraper(db, 'resident_advisor', scrape_resident_advisor)
    results['fever'] = run_scraper(db, 'fever', scrape_fever)
    results['xceed'] = run_scraper(db, 'xceed', scrape_xceed)
    results['songkick'] = run_scraper(db, 'songkick', scrape_songkick)

    # Deactivate past events
    print(f"\n{'='*60}")
    print("Deactivating old events...")
    db.deactivate_old_events()

    # Summary
    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}")
    for name, success in results.items():
        status = "OK" if success else "FAILED"
        print(f"  {name:25} {status}")
    print(f"{'='*60}\n")

    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
