"""
Database Manager for YOLO Scrapers

Handles all database operations including:
- Connection management
- Saving events (with duplicate detection)
- Logging scraper runs
"""

import os
from datetime import datetime
from typing import List, Dict, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

class DatabaseManager:
    """Manages database connections and operations"""

    def __init__(self):
        """Initialize database connection"""
        # database_url = os.getenv('DATABASE_URL')
        #
        # if not database_url:
        #     raise ValueError("DATABASE_URL environment variable not set")
        #
        # # Create engine
        # self.engine = create_engine(
        #     database_url,
        #     pool_pre_ping=True,  # Verify connections before using
        #     echo=False  # Set to True for SQL debugging
        # )
        #
        # # Create session factory
        # self.SessionLocal = sessionmaker(
        #     autocommit=False,
        #     autoflush=False,
        #     bind=self.engine
        # )
        pass

    def get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()

    def save_events(self, events: List[Dict]) -> Tuple[int, int]:
        """
        Save events to database with duplicate detection

        Args:
            events: List of event dictionaries

        Returns:
            Tuple of (new_count, updated_count)
        """
        session = self.get_session()
        new_count = 0
        updated_count = 0

        try:
            for event_data in events:
                try:
                    # Check if event exists by source_id
                    if event_data.get('source_id'):
                        result = session.execute(
                            text("SELECT id FROM events WHERE source_id = :source_id"),
                            {"source_id": event_data['source_id']}
                        ).fetchone()

                        if result:
                            # Update existing event
                            event_id = result[0]
                            update_query = text("""
                                UPDATE events SET
                                    title = :title,
                                    description = :description,
                                    category = :category,
                                    tags = :tags,
                                    city = :city,
                                    country = :country,
                                    venue_name = :venue_name,
                                    event_date = :event_date,
                                    start_time = :start_time,
                                    duration_hours = :duration_hours,
                                    price_min = :price_min,
                                    price_max = :price_max,
                                    currency = :currency,
                                    image_url = :image_url,
                                    booking_url = :booking_url,
                                    vibe = :vibe,
                                    updated_at = :updated_at,
                                    age_min = :age_min
                                WHERE id = :id
                            """)

                            session.execute(update_query, {
                                **event_data,
                                'id': event_id,
                                'updated_at': datetime.now()
                            })
                            updated_count += 1
                        else:
                            # Insert new event
                            self._insert_event(session, event_data)
                            new_count += 1
                    else:
                        # No source_id, always insert (might create duplicates)
                        self._insert_event(session, event_data)
                        new_count += 1

                except IntegrityError as e:
                    # Duplicate source_id, skip
                    session.rollback()
                    continue
                except Exception as e:
                    print(f"Error saving event '{event_data.get('title', 'Unknown')}': {e}")
                    session.rollback()
                    continue

            session.commit()

        except Exception as e:
            print(f"Database error: {e}")
            session.rollback()
            raise
        finally:
            session.close()

        return new_count, updated_count

    def _insert_event(self, session: Session, event_data: Dict):
        """Insert a new event into the database"""
        insert_query = text("""
            INSERT INTO events (
                title, description, category, tags, city, country,
                venue_name, venue_address, event_date, start_time,
                duration_hours, price_min, price_max, currency,
                image_url, booking_url, source, source_id, vibe,
                age_min, is_active, created_at, updated_at
            ) VALUES (
                :title, :description, :category, :tags, :city, :country,
                :venue_name, :venue_address, :event_date, :start_time,
                :duration_hours, :price_min, :price_max, :currency,
                :image_url, :booking_url, :source, :source_id, :vibe,
                :age_min, :is_active, :created_at, :updated_at
            )
        """)

        session.execute(insert_query, {
            **event_data,
            'is_active': True,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        })

    def log_scraper_run(self, scraper_name: str, started_at: datetime,
                        finished_at: datetime, status: str,
                        events_found: int = 0, events_new: int = 0,
                        error_message: str = None):
        """Log a scraper run to the database"""
        session = self.get_session()

        try:
            insert_query = text("""
                INSERT INTO scraper_runs (
                    scraper_name, started_at, finished_at, status,
                    events_found, events_new, error_message, created_at
                ) VALUES (
                    :scraper_name, :started_at, :finished_at, :status,
                    :events_found, :events_new, :error_message, :created_at
                )
            """)

            session.execute(insert_query, {
                'scraper_name': scraper_name,
                'started_at': started_at,
                'finished_at': finished_at,
                'status': status,
                'events_found': events_found,
                'events_new': events_new,
                'error_message': error_message,
                'created_at': datetime.now()
            })

            session.commit()

        except Exception as e:
            print(f"Failed to log scraper run: {e}")
            session.rollback()
        finally:
            session.close()

    def deactivate_old_events(self, days_old: int = 1):
        """
        Mark events as inactive if their date has passed

        Args:
            days_old: Number of days in the past to consider old
        """
        session = self.get_session()

        try:
            update_query = text("""
                UPDATE events
                SET is_active = FALSE
                WHERE event_date < CURRENT_DATE - INTERVAL ':days days'
                AND is_active = TRUE
            """)

            result = session.execute(update_query, {'days': days_old})
            session.commit()

            print(f"Deactivated {result.rowcount} old events")

        except Exception as e:
            print(f"Failed to deactivate old events: {e}")
            session.rollback()
        finally:
            session.close()