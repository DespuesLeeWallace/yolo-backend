-- YOLO Events Database Schema
-- Run this in the Supabase SQL Editor (https://supabase.com/dashboard → SQL Editor)

CREATE TABLE IF NOT EXISTS events (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL,
    tags JSONB DEFAULT '[]',
    city TEXT NOT NULL,
    country TEXT,
    venue_name TEXT,
    venue_address TEXT,
    event_date DATE,
    start_time TEXT,
    duration_hours NUMERIC,
    price_min NUMERIC,
    price_max NUMERIC,
    currency TEXT DEFAULT 'EUR',
    image_url TEXT,
    booking_url TEXT,
    source TEXT NOT NULL,
    source_id TEXT UNIQUE,
    vibe TEXT,
    age_min INTEGER DEFAULT 18,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS scraper_runs (
    id BIGSERIAL PRIMARY KEY,
    scraper_name TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL,
    events_found INTEGER DEFAULT 0,
    events_new INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_events_active_date ON events (is_active, event_date);
CREATE INDEX IF NOT EXISTS idx_events_city ON events (city);
CREATE INDEX IF NOT EXISTS idx_events_category ON events (category);
CREATE INDEX IF NOT EXISTS idx_events_source_id ON events (source_id);

-- Enable Row Level Security (required by Supabase)
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE scraper_runs ENABLE ROW LEVEL SECURITY;

-- Allow anonymous read/write access (anon key)
-- Adjust these policies based on your security needs
CREATE POLICY "Allow anonymous read events" ON events FOR SELECT USING (true);
CREATE POLICY "Allow anonymous insert events" ON events FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow anonymous update events" ON events FOR UPDATE USING (true);
CREATE POLICY "Allow anonymous read scraper_runs" ON scraper_runs FOR SELECT USING (true);
CREATE POLICY "Allow anonymous insert scraper_runs" ON scraper_runs FOR INSERT WITH CHECK (true);
