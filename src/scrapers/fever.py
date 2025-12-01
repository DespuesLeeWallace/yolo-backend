"""
Fever Scraper

Scrapes unique experiences, exhibitions, and cultural events from Fever
Uses their hidden public API
"""

import requests
from datetime import datetime
from typing import List, Dict
import time
import random

class FeverScraper:
    """Scraper for Fever experiences"""
    
    # Fever's public API endpoint
    API_URL = "https://feverup.com/m/api/v2/events"
    
    # City IDs (found by inspecting network requests on feverup.com)
    CITY_IDS = {
        'Madrid': 10,
        'Barcelona': 4,
        'Lisbon': 28,
        'Berlin': 74,
        'Amsterdam': 69,
        'Paris': 2,
        'London': 1
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json'
        })
    
    def scrape_city(self, city_id: int, city_name: str, limit: int = 30) -> List[Dict]:
        """
        Scrape Fever events for a city
        
        Args:
            city_id: Fever's internal city ID
            city_name: City name for our database
            limit: Maximum number of events to fetch
            
        Returns:
            List of event dictionaries
        """
        events = []
        
        try:
            # Add delay to be respectful
            time.sleep(random.uniform(1, 2))
            
            params = {
                'city_id': city_id,
                'page': 1,
                'page_size': limit
            }
            
            response = self.session.get(self.API_URL, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            raw_events = data.get('data', [])
            
            for raw_event in raw_events:
                try:
                    event = self._parse_event(raw_event, city_name)
                    if event and event.get('title'):
                        events.append(event)
                except Exception as e:
                    print(f"    Error parsing event: {e}")
                    continue
            
            print(f"  Found {len(events)} events")
            
        except requests.RequestException as e:
            print(f"  Network error: {e}")
        except Exception as e:
            print(f"  Unexpected error: {e}")
        
        return events
    
    def _parse_event(self, raw_event: Dict, city_name: str) -> Dict:
        """Parse a Fever event into our format"""
        
        # Extract basic info
        event_id = raw_event.get('id')
        title = raw_event.get('title', 'Unknown Event')
        description = raw_event.get('description', '')
        
        # Extract dates
        start_date_str = raw_event.get('start_date')
        end_date_str = raw_event.get('end_date')
        
        event_date = None
        if start_date_str:
            try:
                event_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00')).date()
            except:
                pass
        
        # Extract pricing
        price_info = raw_event.get('price', {})
        price_min = None
        price_max = None
        
        if isinstance(price_info, dict):
            price_min = price_info.get('min')
            price_max = price_info.get('max')
        
        # Default pricing if not available
        if price_min is None:
            price_min = 15.0
        
        # Extract location
        location_info = raw_event.get('location', {})
        venue_name = location_info.get('name')
        venue_address = location_info.get('address')
        
        # Extract images
        images = raw_event.get('images', [])
        image_url = images[0] if images else None
        
        # Build booking URL
        slug = raw_event.get('slug', '')
        booking_url = f"https://feverup.com/m/{slug}" if slug else None
        
        # Classify event
        category, tags, vibe = self._classify_event(title, description)
        
        # Get country code
        country_map = {
            'madrid': 'ES', 'barcelona': 'ES',
            'lisbon': 'PT',
            'berlin': 'DE',
            'amsterdam': 'NL',
            'paris': 'FR',
            'london': 'GB'
        }
        country = country_map.get(city_name.lower(), 'EU')
        
        return {
            'title': title,
            'description': description[:500] if description else None,  # Limit length
            'category': category,
            'tags': tags,
            'city': city_name,
            'country': country,
            'venue_name': venue_name,
            'venue_address': venue_address,
            'event_date': event_date,
            'start_time': "19:00:00",  # Default evening time
            'duration_hours': 2.0,
            'price_min': price_min,
            'price_max': price_max,
            'currency': 'EUR',
            'image_url': image_url,
            'booking_url': booking_url,
            'source': 'fever',
            'source_id': f"fever_{event_id}",
            'vibe': vibe,
            'age_min': 12  # Most Fever events are family-friendly
        }
    
    def _classify_event(self, title: str, description: str) -> tuple:
        """
        Classify event into category, tags, and vibe
        
        Returns:
            (category, tags, vibe)
        """
        text = f"{title} {description}".lower()
        
        # Culture indicators
        if any(word in text for word in ['museum', 'exhibition', 'gallery', 'art', 'van gogh', 
                                          'immersive', 'theatre', 'opera', 'ballet']):
            return 'culture', ['art', 'exhibition'], 'Immersive cultural experience'
        
        # Adventure indicators
        if any(word in text for word in ['escape', 'tour', 'adventure', 'experience', 'explore']):
            return 'adventure', ['experience', 'unique'], 'Unique adventure experience'
        
        # Relax indicators
        if any(word in text for word in ['spa', 'wellness', 'brunch', 'rooftop', 'sunset', 'wine']):
            return 'relax', ['leisure', 'chill'], 'Relaxing experience'
        
        # Party indicators
        if any(word in text for word in ['party', 'club', 'night', 'dj', 'live music', 'concert']):
            return 'party', ['nightlife', 'music'], 'Vibrant nightlife'
        
        # Geeky indicators
        if any(word in text for word in ['gaming', 'tech', 'science', 'interactive', 'virtual reality']):
            return 'geeky', ['tech', 'interactive'], 'Interactive tech experience'
        
        # Default to culture (most Fever events are cultural)
        return 'culture', ['experience'], 'Curated cultural experience'


def test_scraper():
    """Test the scraper locally"""
    print("Testing Fever scraper...\n")
    
    scraper = FeverScraper()
    events = scraper.scrape_city(10, "Madrid")  # Madrid = city_id 10
    
    print(f"\n{'='*60}")
    print(f"Found {len(events)} events in Madrid")
    print(f"{'='*60}\n")
    
    for i, event in enumerate(events[:3], 1):
        print(f"Event {i}:")
        print(f"  Title: {event['title']}")
        print(f"  Venue: {event['venue_name']}")
        print(f"  Date: {event['event_date']}")
        print(f"  Price: €{event['price_min']}")
        print(f"  Category: {event['category']}")
        print(f"  Tags: {', '.join(event['tags'])}")
        print(f"  Vibe: {event['vibe']}")
        print()

if __name__ == "__main__":
    test_scraper()