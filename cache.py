import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

# Default DB file sits next to this module
_DEFAULT_DB = Path(__file__).parent / "wb_cache.db"


class MemoryCache:
    """Original in-memory cache (TTL-based dict). Kept for reference / testing."""

    def __init__(self, ttl: int = 300):
        self._store: Dict[str, Tuple[Any, float]] = {}
        self._ttl = ttl

    def make_key(self, method: str, **kwargs) -> str:
        raw = json.dumps({"method": method, **kwargs}, default=str, sort_keys=True)
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        if key in self._store:
            data, ts = self._store[key]
            if time.time() - ts < self._ttl:
                return data
            del self._store[key]
        return None

    def set(self, key: str, data: Any) -> None:
        self._store[key] = (data, time.time())

    def clear(self) -> None:
        self._store.clear()

    def get_or_fetch(self, key: str, fetch_fn: Callable) -> Any:
        cached = self.get(key)
        if cached is not None:
            return cached
        data = fetch_fn()
        self.set(key, data)
        return data


class SQLiteCache:
    """
    Persistent SQLite-backed cache with the same interface as MemoryCache.

    Data survives Streamlit reruns and process restarts.
    Thread-safe (sqlite3 WAL mode + check_same_thread=False).

    Schema
    ------
    api_cache(key TEXT PK, data TEXT, expires_at REAL)
    """

    def __init__(self, ttl: int = 300, db_path: str | Path = None):
        self._ttl = ttl
        self._db_path = str(db_path or _DEFAULT_DB)
        self._init_db()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            # Существующая таблица кеша
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_cache (
                    key        TEXT PRIMARY KEY,
                    data       TEXT NOT NULL,
                    expires_at REAL NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_expires ON api_cache(expires_at)"
            )
            
            # Новая таблица для финансовых отчетов (постоянное хранение)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS financial_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_date TEXT NOT NULL,
                    nm_id INTEGER NOT NULL,
                    vendor_code TEXT,
                    subject_name TEXT,
                    brand_name TEXT,
                    supplier_oper_name TEXT,
                    retail_amount REAL DEFAULT 0,
                    for_pay REAL DEFAULT 0,
                    commission REAL DEFAULT 0,
                    delivery REAL DEFAULT 0,
                    storage REAL DEFAULT 0,
                    penalty REAL DEFAULT 0,
                    quantity INTEGER DEFAULT 0,
                    is_return BOOLEAN DEFAULT 0,
                    created_at REAL DEFAULT (strftime('%s', 'now')),
                    UNIQUE(report_date, nm_id, supplier_oper_name)
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_reports_date ON financial_reports(report_date)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_reports_nm ON financial_reports(nm_id)"
            )

    # ------------------------------------------------------------------
    # Public interface (identical to MemoryCache)
    # ------------------------------------------------------------------

    def make_key(self, method: str, **kwargs) -> str:
        raw = json.dumps({"method": method, **kwargs}, default=str, sort_keys=True)
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT data, expires_at FROM api_cache WHERE key = ?", (key,)
            ).fetchone()
        if row is None:
            return None
        if time.time() > row["expires_at"]:
            self._delete(key)
            return None
        return json.loads(row["data"])

    def set(self, key: str, data: Any) -> None:
        expires_at = time.time() + self._ttl
        serialized = json.dumps(data, default=str, ensure_ascii=False)
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO api_cache (key, data, expires_at) VALUES (?, ?, ?)",
                (key, serialized, expires_at),
            )

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM api_cache")

    def get_or_fetch(self, key: str, fetch_fn: Callable) -> Any:
        cached = self.get(key)
        if cached is not None:
            return cached
        data = fetch_fn()
        self.set(key, data)
        return data

    # ------------------------------------------------------------------
    # Extra SQLite-only methods
    # ------------------------------------------------------------------

    def _delete(self, key: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM api_cache WHERE key = ?", (key,))

    def purge_expired(self) -> int:
        """Delete expired rows. Returns number of rows removed."""
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM api_cache WHERE expires_at < ?", (time.time(),)
            )
            return cur.rowcount

    def stats(self) -> Dict[str, Any]:
        """Return cache statistics for display in the dashboard."""
        now = time.time()
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM api_cache").fetchone()[0]
            alive = conn.execute(
                "SELECT COUNT(*) FROM api_cache WHERE expires_at >= ?", (now,)
            ).fetchone()[0]
            expired = total - alive
            oldest = conn.execute(
                "SELECT MIN(expires_at) FROM api_cache WHERE expires_at >= ?", (now,)
            ).fetchone()[0]
            newest = conn.execute(
                "SELECT MAX(expires_at) FROM api_cache WHERE expires_at >= ?", (now,)
            ).fetchone()[0]
        return {
            "total_rows": total,
            "alive": alive,
            "expired": expired,
            "db_path": self._db_path,
            "oldest_expires_in": round(oldest - now, 1) if oldest else None,
            "newest_expires_in": round(newest - now, 1) if newest else None,
        }


# Drop-in replacement: all managers import APICache — now backed by SQLite
APICache = SQLiteCache
