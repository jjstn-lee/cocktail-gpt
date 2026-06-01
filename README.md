# Cocktail GPT - Monorepo

A personalized cocktail recommendation system using LangGraph and FastAPI.

## Project Structure

```
cocktail-gpt/
├── backend/              # FastAPI + LangGraph backend
│   ├── src/
│   │   ├── api/         # FastAPI routes, schemas, middleware
│   │   ├── nodes/       # LangGraph nodes
│   │   ├── storage/     # UserStore (JSON persistence)
│   │   ├── tools/       # Data source integrations
│   │   ├── memory/      # State checkpointing
│   │   └── prompts/     # LLM prompts
│   ├── tests/           # Unit & integration tests
│   ├── data/            # User data (data/users/*.json)
│   ├── .venv/           # Python virtual environment
│   └── .env             # Environment configuration
│
├── CLAUDE.md            # Project specification & architecture
└── README.md            # This file
```

## Getting Started

### Backend

```bash
cd backend

# Activate virtual environment
source .venv/bin/activate

# Set environment variables
export API_KEY=your_secret_key
export OPENROUTER_API_KEY=your_openrouter_key

# Start the server
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

API docs available at: `http://localhost:8000/docs`

### API Endpoints

**Profile Management:**
- `POST /api/update/profile` - Update user preferences
- `POST /api/update/constraints` - Update user constraints
- `GET /api/profile/{user_id}` - Get saved profile

**Recommendations:**
- `POST /api/recommend` - Get cocktail recommendations
- `POST /v1/recommend` - Alternative endpoint (legacy)

**Health:**
- `GET /healthz` - Health check (no auth required)

### Testing

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

## Key Features

- **LangGraph Agent**: StateGraph with parallel ingestion and conditional routing
- **User Personalization**: Preferences and constraints persisted in JSON files
- **Smart Merging**: User-set values override LLM inference; LLM fills blanks
- **State Checkpointing**: Session memory with LangGraph checkpointer
- **FastAPI**: REST API with Bearer token auth, CORS, request IDs

## Environment Variables

```bash
# LLM
LLM_MODEL=anthropic/claude-sonnet-4-5
OPENROUTER_API_KEY=...
OPENROUTER_SITE_URL=...
OPENROUTER_SITE_NAME=cocktail-agent

# API
API_KEY=...                    # Bearer token
CORS_ORIGINS=http://localhost:3000

# Data Sources
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
OPENWEATHER_API_KEY=...

# Database
DATABASE_URL=sqlite:///./dev.db
```

## Architecture

### Graph Topology
```
ingest (parallel fan-out)
  ↓
profile_builder
  ↓
preference_extractor [merge with stored prefs]
  ↓
constraint_checker [merge with stored constraints]
  ↓
recommender
  ↓
[conditional] clarify (if confidence < 0.65)
  ↓
output
```

### State Schema
- `user_id`, `thread_id`: Session identification
- `preferences`, `constraints`: User data (from profile or UserStore)
- `recommendations`: Top cocktails ranked by fit
- `rationale`: Explanation for top pick
- `confidence_score`: Recommender's confidence (0-1)
- `clarification_question`: If more info needed

### UserStore
- Stores preferences and constraints in `data/users/{user_id}.json`
- Provides atomic merge-on-write for partial updates
- Seeded into graph state at recommendation start

For detailed architecture, see [CLAUDE.md](./CLAUDE.md)

## Frontend

_Coming soon: Next.js frontend will be added to this monorepo._
