"""
Resident Advisor Scraper

Scrapes electronic music events from Resident Advisor (ra.co)
Uses their GraphQL API via curl_cffi to bypass DataDome bot protection.
"""

from curl_cffi import requests
from datetime import datetime, date
from typing import List, Dict
import re
import time
import random


# RA area IDs (found via GraphQL areas query)
AREA_IDS = {
    'madrid': 41,
    'barcelona': 20,
    'lisbon': 53,
    'berlin': 34,
    'amsterdam': 29,
    'copenhagen': 402,
    'paris': 44,
    'london': 13,
    'prague': 451,
    'milan': 347,
    'vienna': 450,
}

COUNTRY_CODES = {
    'madrid': 'ES',
    'barcelona': 'ES',
    'lisbon': 'PT',
    'berlin': 'DE',
    'amsterdam': 'NL',
    'copenhagen': 'DK',
    'paris': 'FR',
    'london': 'GB',
    'prague': 'CZ',
    'milan': 'IT',
    'vienna': 'AT',
}

CURRENCIES = {
    'DK': 'DKK',
    'GB': 'GBP',
    'CZ': 'CZK',
}

GRAPHQL_URL = "https://ra.co/graphql"

EVENT_LISTINGS_QUERY = """
query GET_EVENT_LISTINGS($filters: FilterInputDtoInput, $pageSize: Int, $page: Int) {
  eventListings(filters: $filters, pageSize: $pageSize, page: $page, sort: { attending: { priority: 1, order: DESCENDING } }) {
    data {
      id
      event {
        id
        title
        date
        startTime
        endTime
        venue {
          id
          name
          address
        }
        images {
          filename
        }
        contentUrl
        pick {
          blurb
        }
      }
    }
    totalResults
  }
}
"""


class ResidentAdvisorScraper:
    """Scraper for Resident Advisor events using their GraphQL API"""

    BASE_URL = "https://ra.co"

    def __init__(self):
        self.session = requests.Session()

    def scrape_city(self, city: str, country: str = None, days_ahead: int = 14, page_size: int = 50) -> List[Dict]:
        """
        Scrape events for a specific city via RA's GraphQL API.

        Args:
            city: City name (e.g., 'madrid', 'barcelona')
            country: Country code — ignored, looked up from city name
            days_ahead: How many days ahead to fetch
            page_size: Max events per request (RA caps at ~50)

        Returns:
            List of event dictionaries
        """
        city_lower = city.lower()
        area_id = AREA_IDS.get(city_lower)
        if area_id is None:
            print(f"  Unknown city: {city}. Known cities: {list(AREA_IDS.keys())}")
            return []

        country_code = COUNTRY_CODES[city_lower]
        today = date.today()
        end_date = date(today.year, today.month + (1 if today.month < 12 else 0), today.day) if days_ahead > 28 else date.fromordinal(today.toordinal() + days_ahead)

        print(f"  Fetching RA events for {city.title()} (area {area_id}), {today} to {end_date}")

        payload = {
            'operationName': 'GET_EVENT_LISTINGS',
            'query': EVENT_LISTINGS_QUERY,
            'variables': {
                'filters': {
                    'areas': {'eq': area_id},
                    'listingDate': {
                        'gte': today.isoformat(),
                        'lte': end_date.isoformat(),
                    },
                },
                'pageSize': page_size,
                'page': 1,
            },
        }

        try:
            time.sleep(random.uniform(0.5, 1.5))
            response = self.session.post(GRAPHQL_URL, json=payload, impersonate='chrome', timeout=15)
            response.raise_for_status()
            data = response.json()

            if 'errors' in data:
                print(f"  GraphQL errors: {data['errors']}")
                return []

            listings = data.get('data', {}).get('eventListings', {}).get('data', [])
            total = data.get('data', {}).get('eventListings', {}).get('totalResults', 0)
            print(f"  Got {len(listings)} of {total} total events")

            events = []
            for listing in listings:
                event = self._parse_event(listing, city_lower, country_code)
                if event and event.get('title'):
                    events.append(event)

            print(f"  Parsed {len(events)} events")
            return events

        except Exception as e:
            print(f"  Error fetching {city}: {e}")
            return []

    def _parse_event(self, listing: Dict, city: str, country: str) -> Dict | None:
        """Parse a GraphQL event listing into our standard format."""
        raw = listing.get('event', {})
        if not raw:
            return None

        title = raw.get('title', '').strip()
        if not title or len(title) < 3:
            return None

        # Parse dates
        event_date = None
        start_time = None
        end_time_str = None
        if raw.get('date'):
            try:
                event_date = datetime.fromisoformat(raw['date']).date()
            except (ValueError, TypeError):
                pass
        if raw.get('startTime'):
            try:
                start_time = datetime.fromisoformat(raw['startTime']).strftime('%H:%M:%S')
            except (ValueError, TypeError):
                start_time = '23:00:00'
        if raw.get('endTime'):
            try:
                end_time_str = raw['endTime']
            except (ValueError, TypeError):
                pass

        # Calculate duration
        duration_hours = 5.0
        if raw.get('startTime') and raw.get('endTime'):
            try:
                start_dt = datetime.fromisoformat(raw['startTime'])
                end_dt = datetime.fromisoformat(raw['endTime'])
                diff = (end_dt - start_dt).total_seconds() / 3600
                if diff > 0:
                    duration_hours = round(diff, 1)
            except (ValueError, TypeError):
                pass

        # Venue
        venue = raw.get('venue', {}) or {}
        venue_name = venue.get('name')
        venue_address = venue.get('address')

        # Image
        images = raw.get('images', []) or []
        image_url = images[0].get('filename') if images else None

        # Event URL
        content_url = raw.get('contentUrl', '')
        event_url = f"{self.BASE_URL}{content_url}" if content_url else None
        source_id = None
        if raw.get('id'):
            source_id = f"ra_{raw['id']}"

        # Blurb from pick
        description = None
        pick = raw.get('pick')
        if pick and pick.get('blurb'):
            description = pick['blurb']

        # Classify
        category, tags, vibe = self._classify(title)

        return {
            'title': title,
            'description': description,
            'category': category,
            'tags': tags,
            'city': city.capitalize(),
            'country': country,
            'venue_name': venue_name,
            'venue_address': venue_address,
            'event_date': event_date,
            'start_time': start_time or '23:00:00',
            'duration_hours': duration_hours,
            'price_min': 15.0,
            'price_max': None,
            'currency': CURRENCIES.get(country, 'EUR'),
            'image_url': image_url,
            'booking_url': event_url,
            'source': 'resident_advisor',
            'source_id': source_id,
            'vibe': vibe,
            'age_min': 18,
        }

    def _classify(self, title: str) -> tuple:
        title_lower = title.lower()
        if any(w in title_lower for w in ['techno', 'tech house']):
            return 'party', ['electronic', 'nightlife', 'techno'], 'Dark techno vibes, industrial energy'
        if any(w in title_lower for w in ['house', 'deep house']):
            return 'party', ['electronic', 'nightlife', 'house'], 'House music, uplifting beats'
        if any(w in title_lower for w in ['drum', 'bass', 'dnb', 'd&b']):
            return 'party', ['electronic', 'nightlife', 'drum-and-bass'], 'High-energy drum and bass'
        if any(w in title_lower for w in ['ambient', 'experimental']):
            return 'party', ['electronic', 'nightlife', 'experimental'], 'Experimental sounds, mind-expanding'
        return 'party', ['electronic', 'nightlife'], 'Electronic music in an underground atmosphere'


def test_scraper():
    """Test the scraper locally"""
    print("Testing Resident Advisor scraper...\n")

    scraper = ResidentAdvisorScraper()
    events = scraper.scrape_city("madrid")

    print(f"\n{'='*60}")
    print(f"Found {len(events)} events in Madrid")
    print(f"{'='*60}\n")

    for i, event in enumerate(events[:5], 1):
        print(f"Event {i}:")
        print(f"  Title: {event['title']}")
        print(f"  Venue: {event['venue_name']}")
        print(f"  Date: {event['event_date']}")
        print(f"  Start: {event['start_time']}")
        print(f"  Duration: {event['duration_hours']}h")
        print(f"  Image: {event['image_url']}")
        print(f"  URL: {event['booking_url']}")
        print(f"  Vibe: {event['vibe']}")
        print()


if __name__ == "__main__":
    test_scraper()
