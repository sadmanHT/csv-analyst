"""
Two-Level In-Memory Session & Data Cache
"""

import time
import pandas as pd
from typing import Any
from backend.core.config import MAX_QUERY_CACHE_ENTRIES

def _dataset_fingerprint(df: pd.DataFrame) -> str:
    """Lightweight fingerprint for cache invalidation."""
    cols = "|".join(str(c) for c in df.columns)
    dtypes = "|".join(str(v) for v in df.dtypes)
    sample = pd.util.hash_pandas_object(df.head(50), index=True).sum()
    return f"{df.shape[0]}x{df.shape[1]}:{cols}:{dtypes}:{int(sample)}"

def _norm_text(text: str) -> str:
    return " ".join(text.lower().strip().split())

class TwoLevelCache:
    """Two-level in-memory cache for dataset profiles and query responses."""

    def __init__(self, max_entries: int = MAX_QUERY_CACHE_ENTRIES):
        self.max_entries = max_entries
        self._query_cache: dict[str, dict[str, Any]] = {}
        self._profile_cache: dict[str, dict[str, Any]] = {}

    def get_query_key(self, session_id: str, category: str, question: str, df: pd.DataFrame) -> str:
        return f"{session_id}:{category}:{_norm_text(question)}:{_dataset_fingerprint(df)}"

    def get_query(self, key: str) -> dict[str, Any] | None:
        return self._query_cache.get(key)

    def set_query(self, key: str, value: dict[str, Any]) -> None:
        self._query_cache[key] = value
        while len(self._query_cache) > self.max_entries:
            oldest = next(iter(self._query_cache))
            self._query_cache.pop(oldest, None)

    def get_profile(self, session_id: str) -> dict[str, Any] | None:
        return self._profile_cache.get(session_id)

    def set_profile(self, session_id: str, profile: dict[str, Any]) -> None:
        self._profile_cache[session_id] = profile

    def invalidate_session(self, session_id: str) -> None:
        self._profile_cache.pop(session_id, None)
        for key in list(self._query_cache.keys()):
            if key.startswith(f"{session_id}:"):
                self._query_cache.pop(key, None)

# Shared cache instance
cache_service = TwoLevelCache()
