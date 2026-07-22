import os
import json
import sqlite3
import time
from typing import Any
import pandas as pd


DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DATA_DIR, "storage.db")
SESSIONS_DIR = os.path.join(DATA_DIR, "sessions")


def get_db_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DB_PATH) -> None:
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            token TEXT NOT NULL,
            filename TEXT,
            row_count INTEGER,
            col_count INTEGER,
            created_at REAL NOT NULL,
            last_accessed_at REAL NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            session_id TEXT,
            job_type TEXT NOT NULL,
            status TEXT NOT NULL,
            result_json TEXT,
            error TEXT,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS query_cache (
            cache_key TEXT PRIMARY KEY,
            session_id TEXT,
            response_json TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS models (
            session_id TEXT PRIMARY KEY,
            model_info_json TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_session(
    session_id: str,
    token: str,
    filename: str,
    df: pd.DataFrame,
    db_path: str = DB_PATH,
    sessions_dir: str = SESSIONS_DIR,
) -> None:
    init_db(db_path)
    now = time.time()
    row_count, col_count = df.shape

    os.makedirs(sessions_dir, exist_ok=True)
    parquet_path = os.path.join(sessions_dir, f"{session_id}.parquet")
    csv_path = os.path.join(sessions_dir, f"{session_id}.csv")

    try:
        df.to_parquet(parquet_path, index=False)
    except Exception:
        df.to_csv(csv_path, index=False)

    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO sessions
        (session_id, token, filename, row_count, col_count, created_at, last_accessed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (session_id, token, filename, row_count, col_count, now, now),
    )
    conn.commit()
    conn.close()


def get_session(session_id: str, db_path: str = DB_PATH) -> dict[str, Any] | None:
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)


def update_session_access(session_id: str, db_path: str = DB_PATH) -> None:
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE sessions SET last_accessed_at = ? WHERE session_id = ?",
        (time.time(), session_id),
    )
    conn.commit()
    conn.close()


def verify_token(session_id: str, token: str | None, db_path: str = DB_PATH) -> bool:
    if not token:
        return False
    session = get_session(session_id, db_path=db_path)
    if not session:
        return False
    return session.get("token") == token


def load_dataframe(
    session_id: str, sessions_dir: str = SESSIONS_DIR
) -> pd.DataFrame | None:
    parquet_path = os.path.join(sessions_dir, f"{session_id}.parquet")
    csv_path = os.path.join(sessions_dir, f"{session_id}.csv")

    if os.path.exists(parquet_path):
        try:
            return pd.read_parquet(parquet_path)
        except Exception:
            pass

    if os.path.exists(csv_path):
        try:
            return pd.read_csv(csv_path)
        except Exception:
            pass

    return None


def save_job(
    job_id: str,
    session_id: str | None,
    job_type: str,
    status: str,
    result: dict[str, Any] | None = None,
    error: str | None = None,
    db_path: str = DB_PATH,
) -> None:
    init_db(db_path)
    now = time.time()
    result_json = json.dumps(result) if result is not None else None
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO jobs
        (job_id, session_id, job_type, status, result_json, error, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (job_id, session_id, job_type, status, result_json, error, now, now),
    )
    conn.commit()
    conn.close()


def update_job(
    job_id: str,
    status: str,
    result: dict[str, Any] | None = None,
    error: str | None = None,
    db_path: str = DB_PATH,
) -> None:
    init_db(db_path)
    now = time.time()
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    if result is not None:
        result_json = json.dumps(result)
        cursor.execute(
            """
            UPDATE jobs
            SET status = ?, result_json = ?, error = ?, updated_at = ?
            WHERE job_id = ?
            """,
            (status, result_json, error, now, job_id),
        )
    else:
        cursor.execute(
            """
            UPDATE jobs
            SET status = ?, error = ?, updated_at = ?
            WHERE job_id = ?
            """,
            (status, error, now, job_id),
        )
    conn.commit()
    conn.close()


def get_job(job_id: str, db_path: str = DB_PATH) -> dict[str, Any] | None:
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    if d.get("result_json"):
        try:
            d["result"] = json.loads(d["result_json"])
        except Exception:
            d["result"] = None
    else:
        d["result"] = None
    return d


def save_model_info(
    session_id: str, model_info: dict[str, Any], db_path: str = DB_PATH
) -> None:
    init_db(db_path)
    now = time.time()
    info_json = json.dumps(model_info)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO models (session_id, model_info_json, created_at)
        VALUES (?, ?, ?)
        """,
        (session_id, info_json, now),
    )
    conn.commit()
    conn.close()


def get_model_info(
    session_id: str, db_path: str = DB_PATH
) -> dict[str, Any] | None:
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT model_info_json FROM models WHERE session_id = ?", (session_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    try:
        return json.loads(row["model_info_json"])
    except Exception:
        return None


def save_cache(
    cache_key: str, session_id: str, response_data: dict[str, Any], db_path: str = DB_PATH
) -> None:
    init_db(db_path)
    now = time.time()
    resp_json = json.dumps(response_data)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO query_cache (cache_key, session_id, response_json, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (cache_key, session_id, resp_json, now),
    )
    conn.commit()
    conn.close()


def get_cache(cache_key: str, db_path: str = DB_PATH) -> dict[str, Any] | None:
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT response_json FROM query_cache WHERE cache_key = ?", (cache_key,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    try:
        return json.loads(row["response_json"])
    except Exception:
        return None


def cleanup_old_sessions(
    ttl_seconds: int = 14400,
    db_path: str = DB_PATH,
    sessions_dir: str = SESSIONS_DIR,
) -> int:
    init_db(db_path)
    cutoff = time.time() - ttl_seconds
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT session_id FROM sessions WHERE last_accessed_at < ?", (cutoff,))
    expired = [r["session_id"] for r in cursor.fetchall()]

    for sid in expired:
        cursor.execute("DELETE FROM sessions WHERE session_id = ?", (sid,))
        cursor.execute("DELETE FROM models WHERE session_id = ?", (sid,))
        cursor.execute("DELETE FROM query_cache WHERE session_id = ?", (sid,))
        p_path = os.path.join(sessions_dir, f"{sid}.parquet")
        c_path = os.path.join(sessions_dir, f"{sid}.csv")
        if os.path.exists(p_path):
            try:
                os.remove(p_path)
            except Exception:
                pass
        if os.path.exists(c_path):
            try:
                os.remove(c_path)
            except Exception:
                pass

    conn.commit()
    conn.close()
    return len(expired)
