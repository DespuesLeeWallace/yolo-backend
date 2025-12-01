"""
Songkick API Scraper

Uses official Songkick API to fetch concert/live music events
API Key required (free): https://www.songkick.com/developer
"""

import requests
from datetime import datetime, date
from typing import List, Dict
import time

class SongkickScraper:
    """Scraper for Songkick concert data using official API"""
    
    BASE_URL = "https://api.songkick.com/api/3.0"
    
    def __init__(self, api_key: str):
        """
        Initialize scraper with API key
        
        Args:
            api_key: Songkick API key (get from https://www.songkick.com/developer)
        """
        if not api_key:
            raise ValueError("Songkick API key is required")
        
        self.api_key = api_key
        self.session = requests.Session()
    
    def get_city_events(self, city_name: str, max_events: int = 50) -> List[Dict]:
        """
        Get events for a city
        
        Args:
            city_name: City name (e.g., "Madrid", "Barcelona")
            max_events: Maximum number of events to return
            
        Returns:
            List of event dictionaries
        """
        try:
            # Step 1: Get metro area ID for the city
            metro_id = self._get_metro_area_id(city_name)
            if not metro_id:
                print(f"  Could not find metro area for {city_name}")
                return []
            
            # Step 2: Get events for that metro area
            events = self._get_metro_area_events(metro_id, city_name, max_events)
            
            print(f"  Found {len(events)} events")
            return events
            
        except Exception as e:
            print(f"  Error fetching {city_name} events: {e}")
            return []
    
    def _get_metro_area_id(self, city_name: str) -> int:
        """Get Songkick metro area ID for a city"""
        url = f"{self.BASE_URL}/search/locations.json"
        params = {
            "query": city_name,
            "apikey": self.api_key
        }
        
        response = self.session.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        results = data.get('resultsPage', {}).get('results', {}).get('location', [])
        
        if results and len(results) > 0:
            return results[0]['metroArea']['id']
        
        return None
    
    def _get_metro_area_events(self, metro_id: int, city_name: str, max_events: int) -> List[Dict]:
        """Get events for a metro area"""
        url = f"{self.BASE_URL}/metro_areas/{metro_id}/calendar.json"
        params = {
            "apikey": self.api_key,
            "per_page": min(max_events, 50)  # API limit is 50 per page
        }
        
        # Add small delay to respect rate limits
        time.sleep(0.5)
        
        response = self.session.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        raw_events = data.get('resultsPage', {}).get('results', {}).get('event', [])
        
        # Parse events
        events = []
        for raw_event in raw_events:
            try:
                event = self._parse_event(raw_event, city_name)
                if event:
                    events.append(event)
            except Exception as e:
                print(f"    Error parsing event: {e}")
                continue
        
        return events
    
    def _parse_event(self, raw_event: Dict, city_name: str) -> Dict:
        """Parse a Songkick event into our format"""
        
        # Extract basic info
        event_id = raw_event.get('id')
        title = raw_event.get('displayName', 'Unknown Event')
        event_type = raw_event.get('type', 'Concert')
        
        # Extract date and time
        start_info = raw_event.get('start', {})
        event_date = None
        start_time = None
        
        if start_info.get('date'):
            try:
                event_date = datetime.strptime(start_info['date'], '%Y-%m-%d').date()
            except:
                pass
        
        if start_info.get('time'):
            start_time = start_info['time']
        else:
            start_time = "20:00:00"  # Default concert time
        
        # Extract venue
        venue_info = raw_event.get('venue', {})
        venue_name = venue_info.get('displayName')
        
        # Extract location
        location_info = raw_event.get('location', {})
        city = location_info.get('city', city_name)
        
        # Extract performers/artists
        performances = raw_event.get('performance', [])
        artists = [p.get('artist', {}).get('displayName') for p in performances if p.get('artist')]
        
        # Build description
        description = None
        if artists:
            if len(artists) == 1:
                description = f"{artists[0]} live in concert"
            elif len(artists) == 2:
                description = f"{artists[0]} and {artists[1]} live"
            else:
                description = f"{artists[0]}, {artists[1]} and {len(artists)-2} more artists"
        
        # Determine category and vibe
        category = "party"  # Most concerts fit party category
        tags = ["live-music", "concert"]
        vibe = "Live music energy"
        
        # Refine based on genre or type
        title_lower = title.lower()
        if any(word in title_lower for word in ['jazz', 'blues']):
            category = "culture"
            vibe = "Intimate jazz vibes"
            tags.append("jazz")
        elif any(word in title_lower for word in ['classical', 'orchestra', 'symphony']):
            category = "culture"
            vibe = "Classical elegance"
            tags.append("classical")
        elif any(word in title_lower for word in ['indie', 'alternative']):
            category = "geeky"
            vibe = "Indie music scene"
            tags.append("indie")
        elif any(word in title_lower for word in ['metal', 'rock']):
            vibe = "High-energy rock concert"
            tags.append("rock")
        
        # Estimate price (Songkick doesn't always provide this)
        price_min = 20.0  # Typical concert price
        
        # Get country code
        country_map = {
            'madrid': 'ES', 'barcelona': 'ES',
            'lisbon': 'PT',
            'berlin': 'DE',
            'amsterdam': 'NL',
            'paris': 'FR',
            'london': 'GB'
        }
        country = country_map.get(city.lower(), 'EU')
        
        return {
            'title': title,
            'description': description,
            'category': category,
            'tags': tags,
            'city': city,
            'country': country,
            'venue_name': venue_name,
            'venue_address': None,
            'event_date': event_date,
            'start_time': start_time,
            'duration_hours': 3.0,  # Typical concert duration
            'price_min': price_min,
            'price_max': None,
            'currency': 'EUR',
            'image_url': None,
            'booking_url': raw_event.get('uri'),
            'source': 'songkick',
            'source_id': f"sk_{event_id}",
            'vibe': vibe,
            'age_min': 16  # Most concerts are all-ages or 16+
        }


def test_scraper():
    """Test the scraper locally"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    api_key = os.getenv('SONGKICK_API_KEY')
    if not api_key:
        print("Error: SONGKICK_API_KEY not set in environment")
        print("Get your API key from: https://www.songkick.com/developer")
        return
    
    print("Testing Songkick scraper...\n")
    
    scraper = SongkickScraper(api_key)
    events = scraper.get_city_events("Madrid")
    
    print(f"\n{'='*60}")
    print(f"Found {len(events)} events in Madrid")
    print(f"{'='*60}\n")
    
    for i, event in enumerate(events[:3], 1):
        print(f"Event {i}:")
        print(f"  Title: {event['title']}")
        print(f"  Venue: {event['venue_name']}")
        print(f"  Date: {event['event_date']}")
        print(f"  Category: {event['category']}")
        print(f"  Vibe: {event['vibe']}")
        print()

if __name__ == "__main__":
    test_scraper()