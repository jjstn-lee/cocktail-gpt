# Cocktail GPT - Quick Start Guide

## Overview

This LangGraph-based AI agent generates personalized cocktail recommendations by analyzing:
- **Spotify data** (music taste, mood, energy level)
- **Weather conditions** (temperature, condition, forecast)
- *(Future)* Gmail/Calendar data for occasion and schedule context

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example env file:
```bash
cp .env.example .env
```

Edit `.env` and add your API credentials:

```bash
# Required for Spotify data
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret

# Required for Weather data
OPENWEATHER_API_KEY=your_openweathermap_api_key

# Optional: LLM for recommendations (future)
OPENROUTER_API_KEY=your_openrouter_key
LLM_MODEL=anthropic/claude-sonnet-4-5
```

**Get API Credentials:**
- **Spotify**: https://developer.spotify.com/dashboard
- **OpenWeatherMap**: https://openweathermap.org/api
- **OpenRouter**: https://openrouter.ai/

### 3. Run the Integration Test (No credentials needed)

This demonstrates the full data flow with mocked data:

```bash
python test_integration.py
```

Output shows:
- ✅ Both Spotify and Weather sources ingesting concurrently
- 📊 Signal extraction from each source
- 📁 Results saved to `integration_test_results.json`

## Usage

### Test with Mocked Data (Recommended First)

```bash
python test_integration.py
```

This uses realistic mock data and doesn't require API credentials. Perfect for understanding the data flow.

### Run with Real APIs (Requires Credentials)

```bash
# Use default test user
python main.py

# Or specify a user
python main.py your_user_id
```

This will:
1. Fetch your Spotify data (requires OAuth approval on first run)
2. Fetch current weather (defaults to NYC, customize with DEFAULT_LAT/DEFAULT_LON)
3. Ingest both sources concurrently
4. Save results to `results.json`

## Current Implementation Status

✅ **Completed:**
- `src/tools/spotify.py` - Spotify API wrapper with OAuth
- `src/tools/weather.py` - OpenWeatherMap API wrapper
- `src/nodes/ingest.py` - Parallel data ingestion node
- Full test coverage (46 tests)

🚧 **In Progress / TODO:**
- Profile builder node (synthesize mood/occasion/vibe)
- Preference extractor node (extract spirit/flavor preferences)
- Constraint checker node (allergies, max ABV, etc.)
- Recommender node (LLM-powered cocktail recommendations)
- Clarify node (conditional edge for low confidence)
- Output node (format recommendations)

## Project Structure

```
cocktail-gpt/
├── main.py                 # Entry point for live API execution
├── test_integration.py     # Integration test with mocked data
├── CLAUDE.md              # Architecture & coding standards
├── src/
│   ├── state.py           # TypedDict state schema
│   ├── tools/
│   │   ├── base.py        # SourcePayload, SourceUnavailableError
│   │   ├── spotify.py     # ✅ Spotify data fetching
│   │   └── weather.py     # ✅ Weather data fetching
│   └── nodes/
│       ├── ingest.py      # ✅ Parallel source ingestion
│       └── (others TBD)
└── tests/
    ├── test_weather.py    # 15 weather tests
    ├── test_spotify.py    # 20 spotify tests
    └── test_ingest.py     # 11 ingest tests
```

## Data Flow

```
START
  ↓
INGEST NODE (Runs in parallel)
  ├── fetch_spotify(user_id)
  │   └── Returns: audio signals, genres, playback, playlists
  └── fetch_weather(user_id)
      └── Returns: current conditions, 12-hr forecast
  ↓
raw_sources = {
  "spotify": {signals, confidence: 0.92},
  "weather": {signals, confidence: 0.75}
}
  ↓
[FUTURE NODES - Not yet implemented]
PROFILE BUILDER → PREFERENCE EXTRACTOR → CONSTRAINT CHECKER
  ↓
RECOMMENDER (generates cocktail recommendations)
  ↓
CLARIFY (if confidence < 0.65)
  ↓
OUTPUT (final recommendations)
```

## Key Features

### Graceful Degradation
If one data source fails:
```python
# Both sources are fetched concurrently with return_exceptions=True
results = await asyncio.gather(
    fetch_spotify(user_id),
    fetch_weather(user_id),
    return_exceptions=True,
)
# If Spotify fails, Weather still processes and vice versa
```

### Type Safety
- Full type annotations with `mypy --strict`
- Pydantic models for state
- TypedDict for graph state

### Async Throughout
- All I/O operations are async
- Concurrent source fetching
- Non-blocking integration with LangGraph

## Development

### Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_weather.py -v

# Run with coverage
pytest tests/ --cov=src
```

### Code Quality

```bash
# Type checking (strict mode)
mypy src/ --strict

# Formatting
ruff format src/ tests/

# Linting
ruff check src/ tests/
```

### Add a New Data Source

1. Create `src/tools/new_source.py`
2. Implement `async def fetch_new_source(user_id: str) -> SourcePayload`
3. Return normalized signals dict with confidence score
4. Add tests in `tests/test_new_source.py`
5. Import and add to `src/nodes/ingest.py` gather

Example:
```python
# src/tools/example.py
async def fetch_example(user_id: str) -> SourcePayload:
    # Fetch data from API
    data = await my_api.get(user_id)

    # Extract normalized signals
    signals = extract_signals(data)

    # Return standardized payload
    return SourcePayload(
        source="example",
        fetched_at=datetime.now(timezone.utc).isoformat(),
        signals=signals,
        confidence=0.85,
    )
```

Then in `src/nodes/ingest.py`:
```python
from src.tools.example import fetch_example

results = await asyncio.gather(
    fetch_spotify(user_id),
    fetch_weather(user_id),
    fetch_example(user_id),  # ADD HERE
    return_exceptions=True,
)
```

## Troubleshooting

### "Missing SPOTIFY_CLIENT_ID"
- Get credentials at https://developer.spotify.com/dashboard
- Add to `.env` file
- OAuth will prompt on first run

### "Missing OPENWEATHER_API_KEY"
- Get free API key at https://openweathermap.org/api
- Add to `.env` file

### Spotify OAuth not completing
- Make sure SPOTIFY_REDIRECT_URI matches your app settings
- Clear `.spotify_cache_*` files to reset auth
- Check browser for OAuth prompt

### Tests failing
- Run `pytest tests/ -v` to see detailed output
- Most require no credentials (they mock external APIs)
- Weather and Spotify tests mock HTTP calls

## Next Steps

1. **Try the integration test** (no credentials needed):
   ```bash
   python test_integration.py
   ```

2. **Set up real API credentials** in `.env`:
   - Spotify: OAuth-based (browser prompt on first run)
   - Weather: Just needs API key

3. **Run with real data**:
   ```bash
   python main.py your_user_id
   ```

4. **Implement the remaining nodes** (see CLAUDE.md for architecture)

## Architecture Notes

- **State**: TypedDict with typed fields; never add untyped fields
- **Async/Await**: All I/O is async; use `asyncio.gather` for concurrency
- **Error Handling**: `SourceUnavailableError` for expected failures; log and continue
- **Confidence**: 0.0–1.0 score indicating data quality/freshness
- **Signals**: Normalized dict structure from each source for downstream nodes

See `CLAUDE.md` for full architecture and coding standards.

## Questions?

- Check `CLAUDE.md` for architecture and conventions
- Review existing tests in `tests/` for usage patterns
- See inline code comments for implementation details
