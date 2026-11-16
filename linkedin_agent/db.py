"""SQLite storage. Secrets (API keys, OAuth tokens) are encrypted at rest."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from cryptography.fernet import Fernet

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS kv (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    secret INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target TEXT NOT NULL DEFAULT 'member',      -- member | organization
    org_urn TEXT,
    pillar TEXT,
    hook_type TEXT,
    content TEXT NOT NULL,
    first_comment TEXT,
    status TEXT NOT NULL DEFAULT 'draft',       -- draft | approved | scheduled | published | failed | rejected
    scheduled_at TEXT,
    published_at TEXT,
    linkedin_urn TEXT,
    error TEXT,
    metrics TEXT,                               -- JSON: impressions, reactions, comments, reposts
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,                         -- resume | cover_letter | profile | plan | note
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    tags TEXT,
    used_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    headline TEXT,
    url TEXT,
    notes TEXT,
    next_follow_up TEXT,
    created_at TEXT NOT NULL
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _fernet() -> Fernet:
    path = settings.key_path
    if not path.exists():
        path.write_bytes(Fernet.generate_key())
        try:
            path.chmod(0o600)
        except OSError:
            pass
    return Fernet(path.read_bytes())


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init() -> None:
    with connect() as c:
        c.executescript(SCHEMA)


# ---------- key/value settings ----------

def set_value(key: str, value: Any, secret: bool = False) -> None:
    raw = json.dumps(value)
    if secret:
        raw = _fernet().encrypt(raw.encode()).decode()
    with connect() as c:
        c.execute(
            "INSERT INTO kv(key, value, secret) VALUES(?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, secret=excluded.secret",
            (key, raw, int(secret)),
        )


def get_value(key: str, default: Any = None) -> Any:
    with connect() as c:
        row = c.execute("SELECT value, secret FROM kv WHERE key=?", (key,)).fetchone()
    if not row:
        return default
    raw = row["value"]
    if row["secret"]:
        raw = _fernet().decrypt(raw.encode()).decode()
    return json.loads(raw)


def delete_value(key: str) -> None:
    with connect() as c:
        c.execute("DELETE FROM kv WHERE key=?", (key,))


# ---------- generic row helpers ----------

def _row(r: sqlite3.Row | None) -> dict | None:
    if r is None:
        return None
    d = dict(r)
    if d.get("metrics"):
        d["metrics"] = json.loads(d["metrics"])
    return d


def insert(table: str, **fields: Any) -> int:
    fields.setdefault("created_at", now())
    if table == "posts":
        fields.setdefault("updated_at", fields["created_at"])
    if "metrics" in fields and not isinstance(fields["metrics"], (str, type(None))):
        fields["metrics"] = json.dumps(fields["metrics"])
    cols = ", ".join(fields)
    marks = ", ".join("?" for _ in fields)
    with connect() as c:
        cur = c.execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", tuple(fields.values()))
        return int(cur.lastrowid)


def update(table: str, row_id: int, **fields: Any) -> None:
    if table == "posts":
        fields["updated_at"] = now()
    if "metrics" in fields and not isinstance(fields["metrics"], (str, type(None))):
        fields["metrics"] = json.dumps(fields["metrics"])
    sets = ", ".join(f"{k}=?" for k in fields)
    with connect() as c:
        c.execute(f"UPDATE {table} SET {sets} WHERE id=?", (*fields.values(), row_id))


def get(table: str, row_id: int) -> dict | None:
    with connect() as c:
        return _row(c.execute(f"SELECT * FROM {table} WHERE id=?", (row_id,)).fetchone())


def list_rows(table: str, where: str = "", params: tuple = (), order: str = "id DESC", limit: int = 200) -> list[dict]:
    sql = f"SELECT * FROM {table}"
    if where:
        sql += f" WHERE {where}"
    sql += f" ORDER BY {order} LIMIT {int(limit)}"
    with connect() as c:
        return [_row(r) for r in c.execute(sql, params).fetchall()]  # type: ignore[misc]


def delete(table: str, row_id: int) -> None:
    with connect() as c:
        c.execute(f"DELETE FROM {table} WHERE id=?", (row_id,))
