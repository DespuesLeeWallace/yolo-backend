"""
Resident Advisor Scraper

Scrapes electronic music events from Resident Advisor (ra.co)
Best coverage for nightlife/club events across Europe
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict
import re
import time
import random
import brotli

class ResidentAdvisorScraper:
    """Scraper for Resident Advisor events"""
    
    BASE_URL = "https://ra.co"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.google.com/',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def scrape_city(self, city: str, country: str = "ES") -> List[Dict]:
        """
        Scrape events for a specific city
        
        Args:
            city: City name (e.g., 'madrid', 'barcelona')
            country: Country code (e.g., 'ES' for Spain)
        
        Returns:
            List of event dictionaries
        """
        events = []
        
        # RA uses city URLs like: /events/es/madrid
        url = f"{self.BASE_URL}/events/{country.lower()}/{city.lower()}"
        
        try:
            # Add delay to be respectful
            time.sleep(random.uniform(1, 2))
            
            response = self.session.get(url, timeout=15)
            print(f"Status code: {response.status_code}")
            print(f"Headers: {response.headers}\n")
            try:
                # Try to use response.text (should work if brotli is installed)
                html = response.text
                print(f"First 500 chars of response.text:\n{html[:500]}\n")
            except Exception as e:
                # Fallback: manual brotli decode
                print(f"Error decoding response.text: {e}, trying manual brotli decode...")
                html = brotli.decompress(response.content).decode('utf-8')
                print(f"First 500 chars of manually decoded html:\n{html[:500]}\n")
            response.raise_for_status()
            
            soup = BeautifulSoup(html, 'html.parser')

            # Find event listings
            # Note: RA's exact selectors may change, adjust as needed
            event_items = soup.find_all('div', attrs={'data-testid': 'event-upcoming-card'})
            # Fallback: try different selectors
            if not event_items:
                event_items = soup.find_all('article')

            if not event_items:
                print(f"⚠️  No events found for {city} (selector might need updating)")
                return events
            
            for item in event_items[:50]:  # Limit to 50 events per city
                try:
                    event = self._parse_event(item, city, country)
                    if event and event.get('title'):
                        events.append(event)
                except Exception as e:
                    print(f"  Error parsing event: {e}")
                    continue
            
            print(f"  Found {len(events)} events")
            
        except requests.RequestException as e:
            print(f"  ✗ Network error: {e}")
        except Exception as e:
            print(f"  ✗ Unexpected error: {e}")
        
        return events
    
    def _parse_event(self, item, city: str, country: str) -> Dict:
        """Parse a single event from HTML"""
        
        # Extract title
        title_elem = item.find(['h3', 'h4', 'h2'])
        if not title_elem:
            # Try finding any link with text
            title_elem = item.find('a', string=True)
        
        title = title_elem.get_text(strip=True) if title_elem else None
        if not title or len(title) < 3:
            return None
        
        # Extract venue
        venue_elem = item.find(string=re.compile(r'venue|club|sala', re.I))
        if not venue_elem:
            venue_elem = item.find(class_=re.compile(r'venue|location', re.I))
        venue = venue_elem.get_text(strip=True) if venue_elem else None
        
        # Extract date
        date_elem = item.find('time')
        event_date = None
        if date_elem and date_elem.get('datetime'):
            try:
                date_str = date_elem.get('datetime')
                event_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
            except:
                pass
        
        # If no structured date, try to parse from text
        if not event_date:
            date_text = item.get_text()
            # Look for patterns like "15 Dec" or "December 15"
            # This is a simplified parser, can be improved
            pass
        
        # Extract link and ID
        link_elem = item.find('a', href=re.compile(r'/events/'))
        event_url = None
        source_id = None
        if link_elem:
            href = link_elem.get('href')
            if href:
                event_url = f"{self.BASE_URL}{href}" if href.startswith('/') else href
                # Extract ID from URL like /events/12345-event-name
                match = re.search(r'/events/(\d+)', href)
                if match:
                    source_id = f"ra_{match.group(1)}"
        
        # Extract price if available
        price_min = None
        price_text = item.find(string=re.compile(r'€|EUR|free', re.I))
        if price_text:
            text = price_text.lower()
            if 'free' in text:
                price_min = 0.0
            else:
                price_match = re.search(r'€?(\d+)', text)
                if price_match:
                    price_min = float(price_match.group(1))
        
        # Default if no price found
        if price_min is None:
            price_min = 15.0  # Typical RA event price
        
        # Auto-classify and generate vibe
        category = "party"
        tags = ["electronic", "nightlife"]
        vibe = "Electronic music in an underground atmosphere"
        
        title_lower = title.lower()
        if any(word in title_lower for word in ['techno', 'tech house']):
            vibe = "Dark techno vibes, industrial energy"
            tags.append("techno")
        elif any(word in title_lower for word in ['house', 'deep house']):
            vibe = "House music, uplifting beats"
            tags.append("house")
        elif any(word in title_lower for word in ['drum', 'bass', 'dnb', 'd&b']):
            vibe = "High-energy drum and bass"
            tags.append("drum-and-bass")
        elif any(word in title_lower for word in ['ambient', 'experimental']):
            vibe = "Experimental sounds, mind-expanding"
            tags.append("experimental")
        
        return {
            'title': title,
            'description': None,
            'category': category,
            'tags': tags,
            'city': city.capitalize(),
            'country': country,
            'venue_name': venue,
            'venue_address': None,
            'event_date': event_date,
            'start_time': "23:00:00",  # Default club time
            'duration_hours': 5.0,
            'price_min': price_min,
            'price_max': None,
            'currency': 'EUR',
            'image_url': None,
            'booking_url': event_url,
            'source': 'resident_advisor',
            'source_id': source_id,
            'vibe': vibe,
            'age_min': 18
        }


def test_scraper():
    """Test the scraper locally"""
    print("Testing Resident Advisor scraper...\n")
    
    scraper = ResidentAdvisorScraper()
    events = scraper.scrape_city("madrid", "ES")
    
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