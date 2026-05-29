# CLAUDE.md — Cocktail Recommendation LangGraph Agent

## Project overview

This project is a LangGraph-based AI agent that ingests user data from multiple sources and
produces personalized cocktail recommendations. The agent uses a typed StateGraph with parallel
ingestion, an LLM-powered profile builder and recommender, conditional clarification routing,
and a persistent memory store for cross-session personalization.

A **FastAPI application** wraps the agent, exposing it as an HTTP service with REST endpoints
for recommendations, clarification responses, feedback submission, and session management.

---

## Repo structure

```
cocktail-agent/
├── CLAUDE.md
├── .env
├── src/
│   ├── api/
│   │   ├── main.py           # FastAPI app factory and lifespan
│   │   ├── routers/
│   │   │   ├── recommendations.py   # POST /recommend, POST /clarify
│   │   │   ├── feedback.py          # POST /feedback
│   │   │   └── sessions.py          # GET /sessions/{user_id}
│   │   ├── schemas.py        # Pydantic request/response models for the API layer
│   │   ├── dependencies.py   # FastAPI dependency injection (graph, checkpointer)
│   │   └── middleware.py     # Auth, CORS, request-ID logging
│   ├── graph.py              # StateGraph definition and compilation
│   ├── state.py              # Typed state schema (Pydantic)
│   ├── nodes/
│   │   ├── ingest.py         # Parallel data-fetching tool node
│   │   ├── profile_builder.py
│   │   ├── preference_extractor.py
│   │   ├── constraint_checker.py
│   │   ├── recommender.py
│   │   ├── clarify.py
│   │   └── output.py
│   ├── tools/
│   │   ├── spotify.py        # Spotipy wrapper
│   │   ├── weather.py        # OpenWeatherMap or similar
│   │   └── pantry.py         # Any inventory source
│   ├── memory/
│   │   └── checkpointer.py   # SQLite (dev) / Postgres (prod) setup
│   └── prompts/
│       ├── profile.py
│       ├── recommender.py
│       └── clarify.py
```

---

## FastAPI layer

### App factory (`src/api/main.py`)

The FastAPI app is created in a factory function and uses a `lifespan` context manager to
initialise the compiled graph and checkpointer once at startup and tear them down gracefully
on shutdown.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.graph import build_graph
from src.memory.checkpointer import get_checkpointer
from src.api.routers import recommendations, feedback, sessions

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.checkpointer = get_checkpointer()
    app.state.graph = build_graph(app.state.checkpointer)
    yield
    await app.state.checkpointer.aclose()

def create_app() -> FastAPI:
    app = FastAPI(title="Cocktail Agent", version="1.0.0", lifespan=lifespan)
    app.include_router(recommendations.router, prefix="/v1")
    app.include_router(feedback.router, prefix="/v1")
    app.include_router(sessions.router, prefix="/v1")
    return app

app = create_app()
```

Launch with:
```bash
uvicorn src.api.main:app --reload --port 8000
```

---

### API schemas (`src/api/schemas.py`)

Keep API request/response models **separate** from the internal `AgentState`. They are the
public contract; `AgentState` is an implementation detail.

```python
# Request bodies
class RecommendRequest(BaseModel):
    user_id: str
    thread_id: str | None = None   # omit to start a new session
    context_override: dict | None = None   # optional one-off signal overrides

class ClarifyRequest(BaseModel):
    user_id: str
    thread_id: str
    answer: str

class FeedbackRequest(BaseModel):
    user_id: str
    thread_id: str
    cocktail_name: str
    rating: Literal["up", "down"]
    notes: str | None = None

# Response bodies
class CocktailOut(BaseModel):
    name: str
    ingredients: list[str]
    method: str
    flavor_notes: list[str]
    why_this_works: str

class RecommendResponse(BaseModel):
    thread_id: str
    recommendations: list[CocktailOut]
    confidence_score: float
    rationale: str
    needs_clarification: bool
    clarification_question: str | None = None

class FeedbackResponse(BaseModel):
    accepted: bool

class SessionSummary(BaseModel):
    user_id: str
    session_count: int
    last_run_at: str | None
    top_preferences: dict
```

---

### Endpoints

#### `POST /v1/recommend`

Runs the full agent graph for a user. Returns recommendations or, when confidence is low, a
clarification question instead. The `thread_id` in the response must be stored by the client
and sent back to `/v1/clarify` if `needs_clarification` is `true`.

```
POST /v1/recommend
Content-Type: application/json

{ "user_id": "u_123", "thread_id": null }

→ 200 RecommendResponse
```

#### `POST /v1/clarify`

Submits the user's answer to a clarification question and reruns the `recommender` node. The
graph resumes from the saved checkpoint; it does not re-ingest sources.

```
POST /v1/clarify
{ "user_id": "u_123", "thread_id": "t_abc", "answer": "something citrusy" }

→ 200 RecommendResponse   (needs_clarification will always be false here)
```

#### `POST /v1/feedback`

Appends a thumbs-up/down to the session state so the agent can personalise future runs.

```
POST /v1/feedback
{ "user_id": "u_123", "thread_id": "t_abc", "cocktail_name": "Negroni", "rating": "up" }

→ 200 FeedbackResponse
```

#### `GET /v1/sessions/{user_id}`

Returns a lightweight summary of the user's history (session count, last run timestamp,
inferred top preferences). Does not run the graph.

```
GET /v1/sessions/u_123

→ 200 SessionSummary
```

---

### Dependency injection (`src/api/dependencies.py`)

Graph and checkpointer are attached to `app.state` at startup and retrieved via FastAPI
dependencies so they can be easily mocked in tests.

```python
from fastapi import Request
from src.graph import CompiledGraph
from src.memory.checkpointer import Checkpointer

def get_graph(request: Request) -> CompiledGraph:
    return request.app.state.graph

def get_checkpointer(request: Request) -> Checkpointer:
    return request.app.state.checkpointer
```

Import and use in routers with `Depends(get_graph)`. Never instantiate the graph inside a
request handler.

---

### Middleware (`src/api/middleware.py`)

Register the following middleware in order in `create_app`:

1. **CORS** — configure `allow_origins` from `CORS_ORIGINS` env var (comma-separated list).
   Default to `["*"]` in development only.
2. **Request ID** — generate a UUID per request, attach as `X-Request-ID` response header, and
   inject into the `loguru` context so every log line carries it.
3. **Auth** — validate a `Bearer` token against `API_KEY` env var. Skip auth for `/docs`,
   `/openapi.json`, and `/healthz`. Return `401` with a plain JSON error body on failure.

Do not use third-party auth libraries unless agreed. A simple `HTTPBearer` dependency is enough
for v1.

---

### Error handling

Define a global exception handler in `main.py` for the following cases:

| Exception | HTTP status | Notes |
|---|---|---|
| `SourceUnavailableError` | 503 | At least one source failed; recommendations may be degraded. Include a `degraded: true` flag in the response. |
| `GraphExecutionError` | 500 | Unrecoverable graph error. Log at `ERROR` level with full traceback. |
| `ValueError` (validation) | 422 | FastAPI handles Pydantic validation automatically; add a handler for manual raises. |
| `KeyError` / unexpected | 500 | Catch-all. Log and return a generic error body — never expose internals. |

All error responses use this shape:
```json
{ "error": "human-readable message", "request_id": "..." }
```

---

## Core architecture

### State schema (`src/state.py`)

The graph state is a `TypedDict` (or Pydantic model). All nodes read from and write to this
object. Key fields:

```python
class AgentState(TypedDict):
    user_id: str
    thread_id: str
    raw_sources: dict[str, Any]        # Raw API payloads, keyed by source name
    user_profile: UserProfile | None   # Synthesized mood/occasion/vibe
    preferences: Preferences | None    # Spirit, flavor, ABV, style preferences
    constraints: Constraints | None    # Allergies, ingredients on hand, ABV limits
    recommendations: list[Cocktail]    # Final ranked list
    confidence_score: float            # Recommender's self-assessed confidence (0–1)
    clarification_question: str | None # Set by clarify node if needed
    clarification_answer: str | None   # User's response if clarification happened
    session_clarification_used: bool   # Cap clarification to one round per session
    session_count: int                 # How many times this user has run the agent
    feedback: list[Feedback]           # Past thumbs up/down on recommendations
```

Never add untyped fields to state. If you need to pass something between nodes, add it to the
schema first. `thread_id` is required — the API layer always generates or passes one through.

### Graph topology (`src/graph.py`)

```
ingest (parallel fan-out)
  → profile_builder
  → preference_extractor
  → constraint_checker
  → recommender
  → [conditional] clarify  (if confidence < CLARIFY_THRESHOLD)
  → output
```

The conditional edge after `recommender` checks `state["confidence_score"]`. If below the
threshold (default `0.65`, configurable via env), route to `clarify`. After clarification, loop
back to `recommender` once, then always proceed to `output` regardless of confidence.

Cap clarification at one round per session via `session_clarification_used: bool` in state.

### Ingestion node (`src/nodes/ingest.py`)

All source fetches run concurrently via `asyncio.gather`. Each tool returns a normalized dict.
If a source fails, log the error and continue — the agent should degrade gracefully, not crash.

```python
async def ingest_node(state: AgentState) -> AgentState:
    results = await asyncio.gather(
        fetch_spotify(state["user_id"]),
        fetch_gmail(state["user_id"]),
        fetch_calendar(state["user_id"]),
        fetch_weather(state["user_id"]),
        return_exceptions=True,
    )
    # Filter out exceptions, log them, store the rest
    ...
```

---

## LLM usage

### Model

Use `claude-sonnet-4-20250514` for all LLM calls via OpenRouter. Do not hardcode the model
string in node files — import it from `src/config.py`:

```python
# src/config.py
LLM_MODEL = os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5")
CLARIFY_THRESHOLD = float(os.getenv("CLARIFY_THRESHOLD", "0.65"))
```

### OpenRouter setup

All LLM calls go through OpenRouter via LangChain's `ChatOpenAI` with a custom `base_url`:

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model=LLM_MODEL,
    openai_api_key=os.environ["OPENROUTER_API_KEY"],
    openai_api_base="https://openrouter.ai/api/v1",
    default_headers={
        "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", ""),
        "X-Title": os.getenv("OPENROUTER_SITE_NAME", "cocktail-agent"),
    },
)
```

### Structured output

The `recommender` node must return structured output via `with_structured_output`:

```python
class RecommenderOutput(BaseModel):
    recommendations: list[Cocktail]   # Max 3, ranked by fit
    confidence_score: float           # 0.0–1.0
    rationale: str                    # One sentence explaining the top pick
```

`Cocktail` includes: `name`, `ingredients`, `method`, `flavor_notes`, `why_this_works`.

### Prompt files (`src/prompts/`)

Keep all system prompts in `src/prompts/` as Python string constants — not inline in node files.
Version with a comment at the top: `# prompt-version: 1.0`. Increment on every update.

---

## Memory and checkpointing

Use `SqliteSaver` locally and `PostgresSaver` in production. Connection strings come from env
vars only. The checkpointer persists the full `AgentState` per `(user_id, thread_id)`.

On subsequent sessions, load the previous state and merge `feedback` and `session_count` before
running the graph. The API layer is responsible for generating a stable `thread_id` per session
and passing it to `graph.ainvoke`.

Patterns to maintain across sessions:
- `session_count` — increment each run; reduces clarification frequency over time
- `feedback` — append after each session when the user rates recommendations
- `preferences` — update incrementally; never fully overwrite

---

## Data source tools (`src/tools/`)

Each tool must implement:

```python
async def fetch_{source}(user_id: str) -> dict[str, Any]:
    """Returns normalized source data or raises SourceUnavailableError."""
```

Every source returns a dict with at least:

```python
{
    "source": str,        # e.g. "spotify"
    "fetched_at": str,    # ISO 8601 UTC
    "signals": dict,      # source-specific signals
    "confidence": float,  # 0–1, how reliable/fresh this data is
}
```

Wrap every external call in `try/except` that raises `SourceUnavailableError` (defined in
`src/tools/base.py`). The ingest node catches these — it never re-raises.

---

## Testing

- Use `pytest` with `pytest-asyncio` for async tests.
- Mock all external API calls. Store fixtures in `tests/fixtures/{source}/`.
- Each node has a unit test that passes a hand-crafted `AgentState` and asserts on the returned
  state delta.
- Graph integration test (`tests/test_graph.py`) runs a full end-to-end pass with all sources
  mocked; asserts `recommendations` is non-empty and well-formed.
- **API tests** (`tests/api/`) use `httpx.AsyncClient` with the FastAPI `TestClient` (or
  `ASGITransport`). Mock `get_graph` and `get_checkpointer` dependencies via `app.dependency_overrides`.
  Cover: happy-path recommendation, clarification flow, feedback persistence, auth rejection (401),
  and at least one degraded-source scenario (503).

```bash
pytest tests/ -v
```

---

## Environment variables

```bash
# LLM
LLM_MODEL=claude-sonnet-4-20250514
OPENROUTER_API_KEY=...
OPENROUTER_SITE_URL=...
OPENROUTER_SITE_NAME=cocktail-agent

# Graph tuning
CLARIFY_THRESHOLD=0.65

# Data sources
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
OPENWEATHER_API_KEY=...

# Memory
DATABASE_URL=sqlite:///./dev.db   # Use postgres:// in prod

# API
API_KEY=...                        # Bearer token validated by auth middleware
CORS_ORIGINS=http://localhost:3000 # Comma-separated; defaults to * in dev only
PORT=8000
```

Copy `.env.example` to `.env` before running locally. Never commit `.env`.

---

## Running the service

```bash
# Install dependencies
pip install -r requirements.txt

# Run dev server with reload
uvicorn src.api.main:app --reload --port 8000

# Run in production (example with gunicorn + uvicorn workers)
gunicorn src.api.main:app -k uvicorn.workers.UvicornWorker --workers 4 --bind 0.0.0.0:8000
```

Interactive API docs are available at `http://localhost:8000/docs` (Swagger UI) and
`http://localhost:8000/redoc` (ReDoc) in non-production environments. Disable both by setting
`docs_url=None, redoc_url=None` in `create_app` when `ENV=production`.

---

## Coding conventions

- All nodes and route handlers are `async`. No synchronous blocking calls anywhere in the
  request path.
- Type-annotate everything. Run `mypy src/` before committing.
- Use `loguru` for logging. Log at `DEBUG` for per-source fetch results, `INFO` for node
  transitions and HTTP requests, `WARNING` for source failures, `ERROR` for unrecoverable errors.
- Format with `ruff format` and lint with `ruff check`. CI will fail without this.
- Keep node files under ~150 lines. Extract helpers into `src/nodes/utils/`.
- Keep router files under ~100 lines. Extract business logic into service functions in
  `src/api/services/` — routers should only handle HTTP concerns (parsing, status codes, errors).

---

## What not to do

- Do not add `print()` statements — use the logger.
- Do not call the LLM more than once per node. If you think you need two calls, propose a new
  node instead.
- Do not store raw API credentials or tokens in state — only derived signals.
- Do not hardcode user IDs, cocktail names, or flavor profiles. Everything user-specific comes
  from state or memory.
- Do not silently swallow exceptions in node code. Either handle them explicitly or let them
  propagate to the graph's error boundary, then to the API's global exception handlers.
- Do not modify `state.py` without updating the corresponding fixture in `tests/fixtures/state/`
  **and** the relevant API schema in `src/api/schemas.py`.
- Do not put business logic in router files. Routers handle HTTP; service functions handle logic.
- Do not expose internal field names, stack traces, or `AgentState` structure in API error
  responses.