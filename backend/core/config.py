"""
Backend System Configuration & Security Constants
"""

import os
from dotenv import load_dotenv

load_dotenv(override=True)

APP_BUILD_ID = "runtime-query-debug-v3"
BACKEND_BUILD_ID = APP_BUILD_ID

# CORS Allowed Origins
_raw_origins = os.environ.get("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",")] if _raw_origins != "*" else ["*"]

# LLM Models
GEMMA_MODEL = os.environ.get("GEMMA_MODEL", "gemma-4-31b-it")
PLANNER_MODEL = os.environ.get("PLANNER_MODEL", "gemma-4-26b-a4b-it")
SYNTHESIS_MODEL = os.environ.get("SYNTHESIS_MODEL", "gemma-4-26b-a4b-it")
DEEP_ANALYSIS_MODEL = os.environ.get("DEEP_ANALYSIS_MODEL", "gemma-4-31b-it")
GEMINI_MODEL = GEMMA_MODEL

# Production Limits & Safety Bounds
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", 25 * 1024 * 1024))
MAX_DATAFRAME_ROWS = int(os.environ.get("MAX_DATAFRAME_ROWS", 100_000))
MAX_DATAFRAME_COLUMNS = int(os.environ.get("MAX_DATAFRAME_COLUMNS", 200))
SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL_SECONDS", 4 * 60 * 60))
MAX_SESSIONS = int(os.environ.get("MAX_SESSIONS", 50))
MAX_QUERY_CACHE_ENTRIES = int(os.environ.get("MAX_QUERY_CACHE_ENTRIES", 200))
RATE_LIMIT_MAX_REQUESTS = int(os.environ.get("RATE_LIMIT_MAX_REQUESTS", 600))
RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", 60))
MAX_JOBS = int(os.environ.get("MAX_JOBS", 200))
MAX_SANDBOX_SECONDS = int(os.environ.get("MAX_SANDBOX_SECONDS", 15))
MAX_RESULT_CHARS = int(os.environ.get("MAX_RESULT_CHARS", 15_000))
LLM_CALL_TIMEOUT_SECONDS = float(os.environ.get("LLM_CALL_TIMEOUT_SECONDS", 15.0))
DIRECT_DEADLINE_SECONDS = 15.0
DIRECT_MAX_LLM_CALLS = 1
DIRECT_SYNTHESIS_TIMEOUT_SECONDS = 12.0

# RAG Configuration
EMBED_DIM = 768
ALLOWED_DOMAINS = {"docs.google.com", "drive.google.com", "sheets.googleapis.com"}
