"""
Xceed Scraper

Scrapes nightlife/club events from Xceed (xceed.me).
Extracts event data from the listing page HTML and JSON-LD.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict
import re
import json
import time
import random


CITY_SLUGS = {
    'madrid': 'madrid',
    'barcelona': 'barcelona',
}

COUNTRY_CODES = {
    'madrid': 'ES',
    'barcelona': 'ES',
}


class XceedScraper:
    """Scraper for Xceed nightlife events."""

    BASE_URL = "https://xceed.me"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })

    def scrape_city(self, city: str) -> List[Dict]:
        """
        Scrape nightlife events for a city.

        Args:
            city: City name (e.g., 'madrid')

        Returns:
            List of event dictionaries
        """
        city_lower = city.lower()
        slug = CITY_SLUGS.get(city_lower)
        if not slug:
            print(f"  Unknown Xceed city: {city}")
            return []

        country = COUNTRY_CODES[city_lower]
        url = f"{self.BASE_URL}/en/{slug}/events"
        print(f"  Fetching Xceed events from {url}")

        try:
            time.sleep(random.uniform(0.5, 1.5))
            r = self.session.get(url, timeout=15)
            r.raise_for_status()
        except Exception as e:
            print(f"  Error fetching {url}: {e}")
            return []

        # First, extract rich data from JSON-LD (only a few events)
        jsonld_events = self._extract_jsonld_events(r.text, city_lower, country)
        # Normalize URLs for dedup: strip /en/ prefix so both formats match
        jsonld_ids = set()
        for e in jsonld_events:
            if e.get('source_id'):
                jsonld_ids.add(e['source_id'])

        # Then, extract remaining events from HTML cards
        card_events = self._extract_card_events(r.text, city_lower, country, skip_ids=jsonld_ids)

        all_events = jsonld_events + card_events
        print(f"  Found {len(all_events)} events ({len(jsonld_events)} from JSON-LD, {len(card_events)} from cards)")
        return all_events

    def _extract_jsonld_events(self, html: str, city: str, country: str) -> List[Dict]:
        """Extract events from JSON-LD script blocks."""
        events = []

        # Plain JSON-LD arrays in script tags
        scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
        for s in scripts:
            s = s.strip()
            if s.startswith('[{') and '"@type":"Event"' in s:
                try:
                    data = json.loads(s)
                    for item in data:
                        if item.get('@type') == 'Event':
                            event = self._parse_jsonld_event(item, city, country)
                            if event:
                                events.append(event)
                except (json.JSONDecodeError, AttributeError):
                    continue

        # Also check typed JSON-LD blocks
        for m in re.finditer(
            r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
            html, re.DOTALL
        ):
            try:
                data = json.loads(m.group(1))
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get('@type') == 'Event':
                        event = self._parse_jsonld_event(item, city, country)
                        if event and event['booking_url'] not in {e['booking_url'] for e in events}:
                            events.append(event)
            except (json.JSONDecodeError, AttributeError):
                continue

        return events

    def _parse_jsonld_event(self, raw: Dict, city: str, country: str) -> Dict | None:
        """Parse a JSON-LD Event object."""
        title = raw.get('name', '').strip()
        if not title or len(title) < 3:
            return None

        # Dates
        event_date = None
        start_time = None
        if raw.get('startDate'):
            try:
                dt = datetime.fromisoformat(raw['startDate'].replace('Z', '+00:00'))
                event_date = dt.date()
                start_time = dt.strftime('%H:%M:%S')
            except (ValueError, TypeError):
                pass

        # Duration
        duration_hours = 5.0
        if raw.get('startDate') and raw.get('endDate'):
            try:
                start_dt = datetime.fromisoformat(raw['startDate'].replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(raw['endDate'].replace('Z', '+00:00'))
                diff = (end_dt - start_dt).total_seconds() / 3600
                if 0 < diff < 24:
                    duration_hours = round(diff, 1)
            except (ValueError, TypeError):
                pass

        # Location
        location = raw.get('location', {})
        venue_name = location.get('name')
        address = location.get('address', {})
        venue_address = address.get('streetAddress') if isinstance(address, dict) else None

        # Price — find the minimum non-zero offer price, or 0 if free
        price_min = None
        offers = raw.get('offers', [])
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

        # Image
        images = raw.get('image', [])
        image_url = images[0] if isinstance(images, list) and images else (images if isinstance(images, str) else None)

        # Event URL
        event_url = raw.get('url', '')
        source_id = None
        id_match = re.search(r'/(\d+)$', event_url)
        if id_match:
            source_id = f"xceed_{id_match.group(1)}"

        # Description
        description = raw.get('description', '')

        # Age
        age_range = raw.get('typicalAgeRange', '')
        age_min = 18
        if age_range:
            age_match = re.match(r'(\d+)', age_range)
            if age_match:
                age_min = int(age_match.group(1))

        category, tags, vibe = self._classify(title, venue_name or '')

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
            'start_time': start_time or '23:00:00',
            'duration_hours': duration_hours,
            'price_min': price_min,
            'price_max': None,
            'currency': 'EUR',
            'image_url': image_url,
            'booking_url': event_url,
            'source': 'xceed',
            'source_id': source_id,
            'vibe': vibe,
            'age_min': age_min,
        }

    def _extract_card_events(self, html: str, city: str, country: str,
                             skip_ids: set = None) -> List[Dict]:
        """Extract events from HTML event cards on the listing page."""
        soup = BeautifulSoup(html, 'html.parser')
        event_links = soup.find_all('a', href=re.compile(rf'/en/{city}/event/'))

        seen = set()
        events = []
        for link in event_links:
            href = link.get('href', '')
            full_url = f"{self.BASE_URL}{href}" if href.startswith('/') else href

            # Dedup by event ID from URL
            id_match = re.search(r'/(\d+)$', href)
            event_id = f"xceed_{id_match.group(1)}" if id_match else full_url
            if event_id in seen:
                continue
            seen.add(event_id)

            if skip_ids and event_id in skip_ids:
                continue

            text = link.get_text(strip=True, separator=' | ')
            if not text:
                continue

            event = self._parse_card_text(text, full_url, city, country, link)
            if event:
                events.append(event)

        return events

    def _parse_card_text(self, text: str, url: str, city: str, country: str,
                         link_elem) -> Dict | None:
        """Parse event info from the card text: 'Day Date, Time | Title | Venue | Price'"""
        parts = [p.strip() for p in text.split('|')]
        if len(parts) < 2:
            return None

        # First part: date/time like "Sat 4 Apr, 11:59pm"
        date_str = parts[0]
        title = parts[1] if len(parts) > 1 else None
        venue_name = parts[2] if len(parts) > 2 else None
        price_str = parts[3] if len(parts) > 3 else None

        if not title or len(title) < 3:
            return None

        # Parse date
        event_date = None
        start_time = None
        date_match = re.match(r'\w+ (\d+) (\w+),?\s*(\d+:\d+\s*[ap]m)?', date_str, re.I)
        if date_match:
            day, month_str, time_str = date_match.groups()
            try:
                event_date = datetime.strptime(f"{day} {month_str} {datetime.now().year}", "%d %b %Y").date()
                # If date is in the past, assume next year
                if event_date < datetime.now().date():
                    event_date = event_date.replace(year=event_date.year + 1)
            except ValueError:
                pass
            if time_str:
                try:
                    t = datetime.strptime(time_str.strip(), "%I:%M%p")
                    start_time = t.strftime('%H:%M:%S')
                except ValueError:
                    pass

        # Parse price
        price_min = None
        if price_str:
            price_match = re.search(r'([\d,.]+)\s*€|From\s*([\d,.]+)', price_str)
            if price_match:
                p = (price_match.group(1) or price_match.group(2)).replace(',', '.')
                try:
                    price_min = float(p)
                except ValueError:
                    pass

        # Image
        img = link_elem.find('img')
        image_url = None
        if img:
            image_url = img.get('src') or img.get('data-src')

        # Source ID from URL
        source_id = None
        id_match = re.search(r'/(\d+)$', url)
        if id_match:
            source_id = f"xceed_{id_match.group(1)}"

        category, tags, vibe = self._classify(title, venue_name or '')

        return {
            'title': title,
            'description': None,
            'category': category,
            'tags': tags,
            'city': city.capitalize(),
            'country': country,
            'venue_name': venue_name,
            'venue_address': None,
            'event_date': event_date,
            'start_time': start_time or '23:00:00',
            'duration_hours': 5.0,
            'price_min': price_min,
            'price_max': None,
            'currency': 'EUR',
            'image_url': image_url,
            'booking_url': url,
            'source': 'xceed',
            'source_id': source_id,
            'vibe': vibe,
            'age_min': 18,
        }

    def _classify(self, title: str, venue: str) -> tuple:
        text = f"{title} {venue}".lower()
        if any(w in text for w in ['techno', 'tech house', 'underground']):
            return 'party', ['nightlife', 'club', 'techno'], 'Dark techno vibes'
        if any(w in text for w in ['reggaeton', 'latin', 'salsa', 'bachata']):
            return 'party', ['nightlife', 'club', 'latin'], 'Latin beats and rhythm'
        if any(w in text for w in ['indie', 'rock', 'punk']):
            return 'party', ['nightlife', 'live-music', 'indie'], 'Indie vibes'
        if any(w in text for w in ['hip hop', 'hip-hop', 'rap', 'trap']):
            return 'party', ['nightlife', 'club', 'hip-hop'], 'Hip-hop energy'
        if any(w in text for w in ['house', 'disco', 'funk']):
            return 'party', ['nightlife', 'club', 'house'], 'House music grooves'
        return 'party', ['nightlife', 'club'], 'Night out at the club'


def test_scraper():
    """Test the scraper locally"""
    print("Testing Xceed scraper...\n")

    scraper = XceedScraper()
    events = scraper.scrape_city("madrid")

    print(f"\n{'='*60}")
    print(f"Found {len(events)} events in Madrid")
    print(f"{'='*60}\n")

    for i, event in enumerate(events[:10], 1):
        print(f"Event {i}:")
        print(f"  Title: {event['title']}")
        print(f"  Venue: {event['venue_name']}")
        print(f"  Date: {event['event_date']}")
        print(f"  Start: {event['start_time']}")
        print(f"  Price: {event['price_min']}")
        print(f"  Image: {event['image_url'][:80] if event['image_url'] else None}")
        print(f"  URL: {event['booking_url']}")
        print()


if __name__ == "__main__":
    test_scraper()
