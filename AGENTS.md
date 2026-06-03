# AGENTS.md — CSV Analyst Agent

## Project Rules

These rules are enforced for every agent session working on this project.

1. **Every endpoint must have a corresponding test in `backend/test_main.py`.**
2. **All Python functions must use type hints.**
3. **All API responses must be JSON or Server-Sent Events (SSE) — never plain text.**
4. **Run `pytest backend/` before marking any task complete.**
5. **Never hardcode secrets — API keys must be read from environment variables via `.env`.**
6. **Generated pandas code must be sandboxed — only allow safe builtins in `exec()`.**
7. **Chart outputs must be base64-encoded PNG returned in the SSE stream.**
8. **Agent steps must stream in real time via SSE — never batch all results at the end.**
9. **CORS must remain open (`allow_origins=["*"]`) for local development.**
10. **Frontend API calls must use the Vite proxy (`/upload`, `/query`) — never hardcode ports.**

## Agent Workflow

When adding a new feature:
1. Write the FastAPI endpoint in `backend/main.py`
2. Write tests in `backend/test_main.py`
3. Run `pytest backend/` — must pass before proceeding
4. Update the React frontend in `frontend/src/App.jsx` if UI changes are needed
5. Update `SAMPLE_QUESTIONS` in `App.jsx` if the feature affects what users can ask
