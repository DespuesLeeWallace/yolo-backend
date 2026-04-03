"""
Database Manager for YOLO Scrapers

Uses Supabase Python client (same credentials as the frontend).
Handles saving events with duplicate detection and logging scraper runs.
"""

import os
from datetime import datetime, date
from typing import List, Dict, Tuple
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv('.env.local')

class DatabaseManager:
    """Manages database operations via Supabase."""

    def __init__(self):
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_ANON_KEY')
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env.local")
        self.client: Client = create_client(url, key)

    def save_events(self, events: List[Dict]) -> Tuple[int, int]:
        """
        Save events to database with duplicate detection via source_id.

        Returns:
            Tuple of (new_count, updated_count)
        """
        new_count = 0
        updated_count = 0

        for event_data in events:
            try:
                row = self._event_to_row(event_data)
                source_id = row.get('source_id')

                if source_id:
                    # Check if exists
                    existing = (
                        self.client.table('events')
                        .select('id')
                        .eq('source_id', source_id)
                        .execute()
                    )

                    if existing.data:
                        # Update
                        row['updated_at'] = datetime.now().isoformat()
                        (
                            self.client.table('events')
                            .update(row)
                            .eq('source_id', source_id)
                            .execute()
                        )
                        updated_count += 1
                    else:
                        # Insert
                        row['is_active'] = True
                        row['created_at'] = datetime.now().isoformat()
                        row['updated_at'] = datetime.now().isoformat()
                        self.client.table('events').insert(row).execute()
                        new_count += 1
                else:
                    # No source_id — always insert
                    row['is_active'] = True
                    row['created_at'] = datetime.now().isoformat()
                    row['updated_at'] = datetime.now().isoformat()
                    self.client.table('events').insert(row).execute()
                    new_count += 1

            except Exception as e:
                print(f"  Error saving event '{event_data.get('title', '?')}': {e}")
                continue

        return new_count, updated_count

    def log_scraper_run(self, scraper_name: str, started_at: datetime,
                        finished_at: datetime, status: str,
                        events_found: int = 0, events_new: int = 0,
                        error_message: str = None):
        """Log a scraper run to the database."""
        try:
            self.client.table('scraper_runs').insert({
                'scraper_name': scraper_name,
                'started_at': started_at.isoformat(),
                'finished_at': finished_at.isoformat(),
                'status': status,
                'events_found': events_found,
                'events_new': events_new,
                'error_message': error_message,
                'created_at': datetime.now().isoformat(),
            }).execute()
        except Exception as e:
            print(f"  Failed to log scraper run: {e}")

    def deactivate_old_events(self, days_old: int = 1):
        """Mark events as inactive if their date has passed."""
        try:
            cutoff = date.today().isoformat()
            result = (
                self.client.table('events')
                .update({'is_active': False})
                .eq('is_active', True)
                .lt('event_date', cutoff)
                .execute()
            )
            count = len(result.data) if result.data else 0
            print(f"  Deactivated {count} old events")
        except Exception as e:
            print(f"  Failed to deactivate old events: {e}")

    def _event_to_row(self, event_data: Dict) -> Dict:
        """Convert scraper event dict to a database row, serializing non-JSON types."""
        row = {}
        for key, value in event_data.items():
            if isinstance(value, (date, datetime)):
                row[key] = value.isoformat()
            elif isinstance(value, list):
                row[key] = value
            else:
                row[key] = value
        return row
