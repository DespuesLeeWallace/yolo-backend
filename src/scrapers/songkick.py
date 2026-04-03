"""
Songkick Scraper

Scrapes concert/live music events from Songkick (songkick.com).
Uses web scraping with JSON-LD extraction since the official API is defunct.

NOTE: Songkick does a server-side 301 redirect based on IP geolocation,
so you always get events for the city closest to your server's IP.
To scrape a specific city, you'd need a proxy in that city.
The metro_area_id in the URL is ignored by Songkick's servers.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict
import re
import json
import time
import random


METRO_AREAS = {
    'madrid': ('28843', 'spain-madrid', 'ES'),
    'barcelona': ('28714', 'spain-barcelona', 'ES'),
    'lisbon': ('31802', 'portugal-lisbon', 'PT'),
    'berlin': ('28443', 'germany-berlin', 'DE'),
    'amsterdam': ('31366', 'netherlands-amsterdam', 'NL'),
}


class SongkickScraper:
    """Scraper for Songkick concert data via web scraping + JSON-LD."""

    BASE_URL = "https://www.songkick.com"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })

    def get_city_events(self, city_name: str, max_events: int = 50) -> List[Dict]:
        """
        Get events for a city. Due to Songkick's geo-redirect, the actual
        city returned depends on the server's IP location.

        Args:
            city_name: Requested city name (e.g., "Madrid")
            max_events: Maximum number of events to return

        Returns:
            List of event dictionaries
        """
        city_lower = city_name.lower()
        metro_info = METRO_AREAS.get(city_lower)
        if not metro_info:
            print(f"  Unknown city: {city_name}")
            return []

        metro_id, metro_slug, country = metro_info
        url = f"{self.BASE_URL}/metro-areas/{metro_id}-{metro_slug}"

        print(f"  Fetching Songkick events from {url}")

        try:
            time.sleep(random.uniform(0.5, 1.5))
            r = self.session.get(url, timeout=15)

            # Check for geo-redirect
            if r.url != url and metro_slug not in r.url:
                actual_city = re.search(r'/metro-areas/\d+-\w+-(\w+)', r.url)
                actual = actual_city.group(1) if actual_city else r.url
                print(f"  WARNING: Songkick geo-redirected to {actual} (requested {city_name})")
                print(f"  This is a Songkick limitation — results may not match requested city.")

            r.raise_for_status()
            events = self._extract_events(r.text, city_name, country)
            print(f"  Found {len(events)} events")
            return events[:max_events]

        except Exception as e:
            print(f"  Error fetching {city_name}: {e}")
            return []

    def _extract_events(self, html: str, city_name: str, country: str) -> List[Dict]:
        """Extract events from JSON-LD blocks in the page."""
        events = []

        for m in re.finditer(
            r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
            html, re.DOTALL
        ):
            try:
                data = json.loads(m.group(1))
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get('@type') == 'MusicEvent':
                        event = self._parse_event(item, city_name, country)
                        if event:
                            events.append(event)
            except (json.JSONDecodeError, AttributeError):
                continue

        return events

    def _parse_event(self, raw: Dict, city_name: str, country: str) -> Dict | None:
        """Parse a JSON-LD MusicEvent into our standard format."""
        title = raw.get('name', '').strip()
        # Clean "Artist @ Venue" format — keep just the artist part as title
        if ' @ ' in title:
            parts = title.split(' @ ', 1)
            title = parts[0].strip()
            venue_from_title = parts[1].strip()
        else:
            venue_from_title = None

        if not title or len(title) < 2:
            return None

        # Location
        location = raw.get('location', {})
        venue_name = location.get('name') or venue_from_title
        address = location.get('address', {})
        actual_city = address.get('addressLocality', city_name)
        actual_country = address.get('addressCountry', country)
        venue_address = address.get('streetAddress')

        # Dates
        event_date = None
        start_time = None
        start_str = raw.get('startDate', '')
        if start_str:
            try:
                if 'T' in start_str:
                    dt = datetime.fromisoformat(start_str)
                    event_date = dt.date()
                    start_time = dt.strftime('%H:%M:%S')
                else:
                    event_date = datetime.fromisoformat(start_str).date()
            except (ValueError, TypeError):
                pass

        # Duration from start/end
        duration_hours = 3.0
        end_str = raw.get('endDate', '')
        if start_str and end_str and 'T' in start_str and 'T' in end_str:
            try:
                start_dt = datetime.fromisoformat(start_str)
                end_dt = datetime.fromisoformat(end_str)
                diff = (end_dt - start_dt).total_seconds() / 3600
                if 0 < diff < 48:
                    duration_hours = round(diff, 1)
            except (ValueError, TypeError):
                pass

        # Performers
        performers = raw.get('performer', [])
        artists = [p.get('name', '') for p in performers if p.get('name')]
        description = None
        if artists:
            if len(artists) == 1:
                description = f"{artists[0]} live in concert"
            elif len(artists) == 2:
                description = f"{artists[0]} and {artists[1]} live"
            else:
                description = f"{artists[0]}, {artists[1]} and {len(artists)-2} more artists"

        # Image
        image_url = raw.get('image')

        # Event URL
        event_url = raw.get('url')
        source_id = None
        if event_url:
            id_match = re.search(r'/(\d+)', event_url)
            if id_match:
                source_id = f"sk_{id_match.group(1)}"

        # Classify
        category, tags, vibe = self._classify(title, artists)

        # Map country names to codes
        country_code_map = {
            'Spain': 'ES', 'Portugal': 'PT', 'Germany': 'DE',
            'Netherlands': 'NL', 'France': 'FR', 'United Kingdom': 'GB',
            'UK': 'GB', 'Italy': 'IT',
        }
        country_code = country_code_map.get(actual_country, actual_country)

        return {
            'title': title,
            'description': description,
            'category': category,
            'tags': tags,
            'city': actual_city,
            'country': country_code,
            'venue_name': venue_name,
            'venue_address': venue_address,
            'event_date': event_date,
            'start_time': start_time or '20:00:00',
            'duration_hours': duration_hours,
            'price_min': 20.0,
            'price_max': None,
            'currency': 'EUR',
            'image_url': image_url,
            'booking_url': event_url,
            'source': 'songkick',
            'source_id': source_id,
            'vibe': vibe,
            'age_min': 16,
        }

    def _classify(self, title: str, artists: list) -> tuple:
        text = f"{title} {' '.join(artists)}".lower()
        if any(w in text for w in ['jazz', 'blues']):
            return 'culture', ['live-music', 'concert', 'jazz'], 'Intimate jazz vibes'
        if any(w in text for w in ['classical', 'orchestra', 'symphony']):
            return 'culture', ['live-music', 'concert', 'classical'], 'Classical elegance'
        if any(w in text for w in ['indie', 'alternative']):
            return 'party', ['live-music', 'concert', 'indie'], 'Indie music scene'
        if any(w in text for w in ['metal', 'rock', 'punk']):
            return 'party', ['live-music', 'concert', 'rock'], 'High-energy rock concert'
        if any(w in text for w in ['electronic', 'techno', 'dj']):
            return 'party', ['live-music', 'electronic'], 'Electronic beats'
        return 'party', ['live-music', 'concert'], 'Live music energy'


def test_scraper():
    """Test the scraper locally"""
    print("Testing Songkick scraper...\n")

    scraper = SongkickScraper()
    events = scraper.get_city_events("Madrid")

    print(f"\n{'='*60}")
    print(f"Found {len(events)} events")
    print(f"{'='*60}\n")

    for i, event in enumerate(events[:5], 1):
        print(f"Event {i}:")
        print(f"  Title: {event['title']}")
        print(f"  Venue: {event['venue_name']}")
        print(f"  City: {event['city']}")
        print(f"  Date: {event['event_date']}")
        print(f"  Category: {event['category']}")
        print(f"  Vibe: {event['vibe']}")
        print(f"  URL: {event['booking_url']}")
        print()


if __name__ == "__main__":
    test_scraper()
