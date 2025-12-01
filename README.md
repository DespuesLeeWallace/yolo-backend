# YOLO Event Scrapers

Automated event scrapers for the YOLO app. Collects nightlife, concerts, and cultural experiences from across Europe.

## Features

- 🎵 **Resident Advisor** - Electronic music & nightlife
- 🎸 **Songkick** - Live concerts & music events  
- 🎟️ **Fever** - Unique experiences & exhibitions
- 🤖 **Automated** - Runs every 6 hours via GitHub Actions
- 📊 **Monitoring** - Logs all scraper runs to database

## Cities Covered

- Madrid, Spain
- Barcelona, Spain
- Lisbon, Portugal
- Berlin, Germany
- Amsterdam, Netherlands

## Quick Start

### Prerequisites

- Python 3.11+
- UV (recommended) or pip
- PostgreSQL database (Supabase)

### Setup with UV (Recommended - 10x faster!)

```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone/create project
cd yolo-scrapers

# Install dependencies (UV handles venv automatically)
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your DATABASE_URL

# Run scrapers
uv run python main.py
```

**See [UV-SETUP.md](UV-SETUP.md) for detailed UV guide.**

### Setup with pip (Alternative)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure and run
cp .env.example .env
python main.py
```

## Project Structure

```
yolo-scrapers/
├── main.py                  # Entry point - runs all scrapers
├── pyproject.toml           # Dependencies (UV/pip)
├── requirements.txt         # Dependencies (pip only)
│
├── src/
│   ├── database.py          # Database operations
│   └── scrapers/
│       ├── resident_advisor.py
│       ├── songkick.py
│       └── fever.py
│
├── .github/workflows/
│   └── scrape.yml           # GitHub Actions automation
│
├── .env.example             # Environment template
└── UV-SETUP.md              # UV setup guide
```

## Environment Variables

Create `.env` file:

```env
# Required: Database connection
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres

# Optional: Songkick API key (free from songkick.com/developer)
SONGKICK_API_KEY=your-api-key-here
```

**Note:** Resident Advisor and Fever don't require API keys.

## Usage

### Run All Scrapers

```bash
# With UV
uv run python main.py

# With pip
python main.py
```

### Test Individual Scrapers

```bash
# With UV
uv run python src/scrapers/resident_advisor.py
uv run python src/scrapers/songkick.py
uv run python src/scrapers/fever.py

# With pip
python src/scrapers/resident_advisor.py
```

### Using Project Scripts (UV only)

```bash
uv run scrape              # Run all scrapers
uv run test-ra             # Test Resident Advisor
uv run test-sk             # Test Songkick
uv run test-fever          # Test Fever
```

## Automation

### GitHub Actions

The scrapers run automatically every 6 hours via GitHub Actions.

**Setup:**

1. Push code to GitHub
2. Add secrets in repo settings:
   - `DATABASE_URL` (required)
   - `SONGKICK_API_KEY` (optional)
3. Enable GitHub Actions
4. Done! Check Actions tab for runs

**Manual trigger:**
- Go to Actions tab → Scrape Events → Run workflow

## Data Output

Scrapers write to PostgreSQL database:

### Events Table
```sql
- id, title, description
- category (party/culture/adventure/relax/geeky)
- city, country, venue_name
- event_date, start_time, duration_hours
- price_min, price_max, currency
- booking_url, source, source_id
- vibe (generated description)
```

### Scraper Runs Table
```sql
- scraper_name, started_at, finished_at
- status (success/failed)
- events_found, events_new
- error_message
```

## Expected Output

Each scrape run typically collects:
- **Resident Advisor:** ~20-30 events per city
- **Songkick:** ~15-25 events per city
- **Fever:** ~10-20 events per city

**Total:** 150-250 events across 5 cities

## Adding New Cities

Edit `main.py`:

```python
cities = [
    ("madrid", "ES"),
    ("barcelona", "ES"),
    ("lisbon", "PT"),
    ("berlin", "DE"),
    ("amsterdam", "NL"),
    ("paris", "FR"),        # Add new city
    ("london", "GB"),       # Add new city
]
```

## Adding New Scrapers

1. Create `src/scrapers/new_source.py`
2. Implement `scrape_city()` method
3. Add to `main.py`:
   ```python
   def run_new_source(db: DatabaseManager):
       scraper = NewSourceScraper()
       events = scraper.scrape_city("Madrid")
       db.save_events(events)
   ```
4. Test locally, then push!

## Troubleshooting

### No events found
- Check if source websites are accessible
- HTML structure may have changed (update selectors)
- Check rate limits

### Database connection fails
- Verify DATABASE_URL is correct
- Check Supabase project is running
- Ensure IP is allowed (Supabase settings)

### Songkick returns nothing
- Verify SONGKICK_API_KEY is set
- Check API key is valid
- Free tier: 300 requests/day

### GitHub Actions fails
- Check secrets are configured
- Review workflow logs
- Test locally first

## Development

### With UV

```bash
# Add dependency
uv add httpx

# Run with auto-reload (install nodemon)
nodemon --exec "uv run python main.py" --ext py

# Format code
uv run black .

# Lint
uv run ruff check .
```

### With pip

```bash
# Add dependency
pip install httpx
pip freeze > requirements.txt

# Run
python main.py
```

## Performance

- **Full scrape:** ~2-3 minutes (5 cities, 3 sources)
- **Memory usage:** ~50-100 MB
- **Network:** ~5-10 MB data transfer
- **Database writes:** ~200-300 inserts/updates

## Rate Limiting

Scrapers implement respectful rate limiting:
- 1-3 second delays between requests
- Rotating user agents
- Exponential backoff on errors

## Monitoring

Check scraper health:
- GitHub Actions runs every 6 hours
- Email notifications on failure
- Database logs all runs
- Review `scraper_runs` table

## License

Private project - All rights reserved

## Contributing

1. Test changes locally
2. Run all scrapers successfully
3. Check database for correct data
4. Push to feature branch
5. Create pull request

## Support

For issues or questions:
- Check UV-SETUP.md for UV-specific help
- Review QUICK-START-REVISED.md for setup
- Check GitHub Actions logs for errors

---

**Built with ❤️ for YOLO**

Stop overthinking. Start living. 🚀