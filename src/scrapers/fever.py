"""
Fever Scraper

Scrapes events from Fever (feverup.com) category pages.
Extracts event URLs from the category page's JSON-LD ItemList,
then fetches each event page for structured Event data.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict
import re
import json
import time
import random


# Category page URLs per city.
# Each entry is (category_label, url).
CITY_CATEGORIES = {
    'madrid': [
        ('nightlife', 'https://feverup.com/es/madrid/vida-nocturna-clubs'),
        ('fabrik', 'https://feverup.com/es/madrid/fabrik'),
        ('comedy', 'https://feverup.com/es/madrid/monologos'),
    ],
}

COUNTRY_CODES = {
    'madrid': 'ES',
    'barcelona': 'ES',
    'lisbon': 'PT',
    'berlin': 'DE',
    'amsterdam': 'NL',
}


class FeverScraper:
    """Scraper for Fever experiences via HTML + JSON-LD"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })

    def scrape_city(self, city: str) -> List[Dict]:
        """
        Scrape all configured categories for a city.

        Args:
            city: City name (e.g., 'madrid')

        Returns:
            List of event dictionaries
        """
        city_lower = city.lower()
        categories = CITY_CATEGORIES.get(city_lower)
        if not categories:
            print(f"  No Fever categories configured for {city}")
            return []

        all_events = []
        for category_label, url in categories:
            print(f"  Fetching Fever {category_label} for {city.title()}...")
            event_urls = self._get_event_urls(url)
            print(f"    Found {len(event_urls)} event URLs")

            for event_url in event_urls:
                time.sleep(random.uniform(0.3, 0.8))
                event = self._fetch_event(event_url, city_lower, category_label)
                if event:
                    all_events.append(event)

            print(f"    Parsed {len([e for e in all_events])} events so far")

        print(f"  Total: {len(all_events)} Fever events for {city.title()}")
        return all_events

    def _get_event_urls(self, category_url: str) -> List[str]:
        """Extract event URLs from a category page's JSON-LD ItemList."""
        try:
            r = self.session.get(category_url, timeout=15)
            r.raise_for_status()
        except Exception as e:
            print(f"    Error fetching category page: {e}")
            return []

        urls = []
        # Look for JSON-LD with ItemList
        for m in re.finditer(
            r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
            r.text, re.DOTALL
        ):
            try:
                data = json.loads(m.group(1))
                if data.get('@type') == 'ItemList':
                    for item in data.get('itemListElement', []):
                        url = item.get('url')
                        if url:
                            urls.append(url)
            except (json.JSONDecodeError, AttributeError):
                continue

        # Fallback: search for ItemList in non-typed scripts
        if not urls:
            scripts = re.findall(r'<script[^>]*>(.*?)</script>', r.text, re.DOTALL)
            for s in scripts:
                s = s.strip()
                if s.startswith('{') and 'ItemList' in s:
                    try:
                        data = json.loads(s)
                        if data.get('@type') == 'ItemList':
                            for item in data.get('itemListElement', []):
                                url = item.get('url')
                                if url:
                                    urls.append(url)
                    except (json.JSONDecodeError, AttributeError):
                        continue

        return urls

    def _fetch_event(self, event_url: str, city: str, category_label: str) -> Dict | None:
        """Fetch an event page and extract structured data from JSON-LD."""
        try:
            r = self.session.get(event_url, timeout=15)
            r.raise_for_status()
        except Exception as e:
            print(f"    Error fetching {event_url}: {e}")
            return None

        event_data = None
        product_data = None

        for m in re.finditer(
            r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
            r.text, re.DOTALL
        ):
            try:
                data = json.loads(m.group(1))
                if data.get('@type') == 'Event':
                    event_data = data
                elif data.get('@type') == 'Product':
                    product_data = data
            except (json.JSONDecodeError, AttributeError):
                continue

        if not event_data and not product_data:
            return None

        return self._parse_jsonld(event_data, product_data, event_url, city, category_label)

    def _parse_jsonld(self, event_data: Dict | None, product_data: Dict | None,
                      event_url: str, city: str, category_label: str) -> Dict | None:
        """Parse JSON-LD Event and/or Product data into our standard format."""
        # Prefer Event data, fall back to Product
        source = event_data or product_data or {}

        title = source.get('name', '').strip()
        # Fix double-encoded UTF-8
        try:
            title = title.encode('latin-1').decode('utf-8')
        except (UnicodeDecodeError, UnicodeEncodeError):
            pass

        if not title or len(title) < 3:
            return None

        description = source.get('description', '')
        try:
            description = description.encode('latin-1').decode('utf-8')
        except (UnicodeDecodeError, UnicodeEncodeError):
            pass

        # Dates
        event_date = None
        start_time = None
        if event_data and event_data.get('startDate'):
            try:
                dt = datetime.fromisoformat(event_data['startDate'])
                event_date = dt.date()
                start_time = dt.strftime('%H:%M:%S')
            except (ValueError, TypeError):
                pass

        # Duration
        duration_hours = 2.0
        if event_data and event_data.get('startDate') and event_data.get('endDate'):
            try:
                start_dt = datetime.fromisoformat(event_data['startDate'])
                end_dt = datetime.fromisoformat(event_data['endDate'])
                diff = (end_dt - start_dt).total_seconds() / 3600
                if 0 < diff < 24:
                    duration_hours = round(diff, 1)
            except (ValueError, TypeError):
                pass

        # Price — from event offers or product offers
        price_min = None
        offers = (event_data or {}).get('offers', []) or (product_data or {}).get('offers', [])
        if offers:
            prices = []
            for o in offers:
                p = o.get('price')
                if p is not None:
                    try:
                        prices.append(float(p))
                    except (ValueError, TypeError):
                        pass
            if prices:
                price_min = min(prices)

        # Location
        location = (event_data or {}).get('location', {})
        venue_name = location.get('name')
        venue_address = None
        address = location.get('address', {})
        if isinstance(address, dict):
            venue_address = address.get('streetAddress') or address.get('addressLocality')
        elif isinstance(address, str):
            venue_address = address

        # Image
        image_url = source.get('image')

        # Extract Fever event ID from URL
        source_id = None
        id_match = re.search(r'/m/(\d+)', event_url)
        if id_match:
            source_id = f"fever_{id_match.group(1)}"

        country = COUNTRY_CODES.get(city.lower(), 'EU')
        category, tags, vibe = self._classify(title, description, category_label)

        return {
            'title': title,
            'description': description[:500] if description else None,
            'category': category,
            'tags': tags,
            'city': city.capitalize(),
            'country': country,
            'venue_name': venue_name,
            'venue_address': venue_address,
            'event_date': event_date,
            'start_time': start_time or '20:00:00',
            'duration_hours': duration_hours,
            'price_min': price_min,
            'price_max': None,
            'currency': 'EUR',
            'image_url': image_url,
            'booking_url': event_url,
            'source': 'fever',
            'source_id': source_id,
            'vibe': vibe,
            'age_min': 18 if category_label == 'nightlife' else 12,
        }

    def _classify(self, title: str, description: str, category_label: str) -> tuple:
        """Classify event based on category label and text content."""
        if category_label == 'nightlife':
            return 'party', ['nightlife', 'club'], 'Vibrant nightlife experience'
        if category_label == 'fabrik':
            return 'party', ['nightlife', 'club', 'fabrik'], 'Legendary Madrid mega-club experience'
        if category_label == 'comedy':
            return 'comedy', ['comedy', 'standup'], 'Live stand-up comedy show'

        text = f"{title} {description}".lower()
        if any(w in text for w in ['museum', 'exhibition', 'gallery', 'art', 'immersive']):
            return 'culture', ['art', 'exhibition'], 'Immersive cultural experience'
        if any(w in text for w in ['party', 'club', 'night', 'dj']):
            return 'party', ['nightlife', 'music'], 'Vibrant nightlife'
        return 'culture', ['experience'], 'Curated cultural experience'


def test_scraper():
    """Test the scraper locally"""
    print("Testing Fever scraper...\n")

    scraper = FeverScraper()
    events = scraper.scrape_city("madrid")

    print(f"\n{'='*60}")
    print(f"Found {len(events)} events in Madrid")
    print(f"{'='*60}\n")

    for i, event in enumerate(events[:5], 1):
        print(f"Event {i}:")
        print(f"  Title: {event['title']}")
        print(f"  Venue: {event['venue_name']}")
        print(f"  Date: {event['event_date']}")
        print(f"  Price: {event['price_min']}")
        print(f"  Category: {event['category']}")
        print(f"  Tags: {', '.join(event['tags'])}")
        print(f"  Vibe: {event['vibe']}")
        print(f"  URL: {event['booking_url']}")
        print()


if __name__ == "__main__":
    test_scraper()
