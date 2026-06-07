# CLAUDE.md — Cocktail Recommendation LangGraph Agent

## Project overview

This project is a LangGraph-based AI agent that ingests user data from multiple sources and
produces personalized cocktail recommendations. It is currently a work in progress, so do not assume that everything you see in this repo is runs correctly or adheres to the conventions below.

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