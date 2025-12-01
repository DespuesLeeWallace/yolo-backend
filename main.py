#!/usr/bin/env python3
"""
YOLO Scrapers - Main Entry Point

This script runs all scrapers in sequence and logs the results.
Designed to be run on a schedule (e.g., every 6 hours via GitHub Actions or cron).
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from database import DatabaseManager
from scrapers.resident_advisor import ResidentAdvisorScraper
from scrapers.songkick import SongkickScraper
from scrapers.fever import FeverScraper

def log_scraper_run(db: DatabaseManager, scraper_name: str, started_at: datetime, 
                    status: str, events_found: int = 0, events_new: int = 0, 
                    error_message: str = None):
    """Log scraper run to database"""
    try:
        db.log_scraper_run(
            scraper_name=scraper_name,
            started_at=started_at,
            finished_at=datetime.now(),
            status=status,
            events_found=events_found,
            events_new=events_new,
            error_message=error_message
        )
    except Exception as e:
        print(f"Failed to log scraper run: {e}")

def run_resident_advisor(db: DatabaseManager):
    """Run Resident Advisor scraper"""
    scraper_name = "resident_advisor"
    started_at = datetime.now()
    
    print(f"\n{'='*60}")
    print(f"🎵 Starting Resident Advisor Scraper")
    print(f"{'='*60}\n")
    
    try:
        scraper = ResidentAdvisorScraper()
        
        # Cities to scrape
        cities = [
            ("madrid", "ES"),
            ("barcelona", "ES"),
            ("lisbon", "PT"),
            ("berlin", "DE"),
            ("amsterdam", "NL")
        ]
        
        all_events = []
        for city, country in cities:
            print(f"📍 Scraping {city.title()}, {country}...")
            events = scraper.scrape_city(city, country)
            all_events.extend(events)
        
        print(f"\n📊 Total events scraped: {len(all_events)}")
        
        # Save to database
        new_count, updated_count = db.save_events(all_events)
        
        print(f"✅ New events: {new_count}")
        print(f"🔄 Updated events: {updated_count}")
        
        log_scraper_run(
            db, scraper_name, started_at, "success",
            len(all_events), new_count
        )
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        log_scraper_run(
            db, scraper_name, started_at, "failed",
            error_message=str(e)
        )
        return False

def run_songkick(db: DatabaseManager):
    """Run Songkick API scraper"""
    scraper_name = "songkick"
    started_at = datetime.now()
    
    print(f"\n{'='*60}")
    print(f"🎸 Starting Songkick Scraper")
    print(f"{'='*60}\n")
    
    # Check if API key is set
    if not os.getenv('SONGKICK_API_KEY'):
        print("⚠️  Skipping Songkick: SONGKICK_API_KEY not set")
        return False
    
    try:
        scraper = SongkickScraper(os.getenv('SONGKICK_API_KEY'))
        
        cities = ["Madrid", "Barcelona", "Lisbon", "Berlin", "Amsterdam"]
        
        all_events = []
        for city in cities:
            print(f"📍 Fetching {city} events...")
            events = scraper.get_city_events(city)
            all_events.extend(events)
        
        print(f"\n📊 Total events fetched: {len(all_events)}")
        
        # Save to database
        new_count, updated_count = db.save_events(all_events)
        
        print(f"✅ New events: {new_count}")
        print(f"🔄 Updated events: {updated_count}")
        
        log_scraper_run(
            db, scraper_name, started_at, "success",
            len(all_events), new_count
        )
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        log_scraper_run(
            db, scraper_name, started_at, "failed",
            error_message=str(e)
        )
        return False

def run_fever(db: DatabaseManager):
    """Run Fever scraper"""
    scraper_name = "fever"
    started_at = datetime.now()
    
    print(f"\n{'='*60}")
    print(f"🎟️  Starting Fever Scraper")
    print(f"{'='*60}\n")
    
    try:
        scraper = FeverScraper()
        
        # City IDs for Fever
        cities = {
            "Madrid": 10,
            "Barcelona": 4,
            "Lisbon": 28,
            "Berlin": 74,
            "Amsterdam": 69
        }
        
        all_events = []
        for city_name, city_id in cities.items():
            print(f"📍 Fetching {city_name} events...")
            events = scraper.scrape_city(city_id, city_name)
            all_events.extend(events)
        
        print(f"\n📊 Total events fetched: {len(all_events)}")
        
        # Save to database
        new_count, updated_count = db.save_events(all_events)
        
        print(f"✅ New events: {new_count}")
        print(f"🔄 Updated events: {updated_count}")
        
        log_scraper_run(
            db, scraper_name, started_at, "success",
            len(all_events), new_count
        )
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        log_scraper_run(
            db, scraper_name, started_at, "failed",
            error_message=str(e)
        )
        return False

def main():
    """Main function to run all scrapers"""
    print("\n" + "="*60)
    print("🚀 YOLO Event Scrapers")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Initialize database
    try:
        db = DatabaseManager()
        print("✅ Database connection established")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)
    
    # Run scrapers
    results = {
        "resident_advisor": run_resident_advisor(db),
        "songkick": run_songkick(db),
        "fever": run_fever(db)
    }
    
    # Summary
    print("\n" + "="*60)
    print("📊 Scraping Summary")
    print("="*60)
    
    for scraper, success in results.items():
        status = "✅ Success" if success else "❌ Failed"
        print(f"{scraper.replace('_', ' ').title()}: {status}")
    
    print(f"\n⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")
    
    # Exit with error code if any scraper failed
    if not all(results.values()):
        sys.exit(1)

if __name__ == "__main__":
    main()