"""SQLite storage with workspaces (multi-account).

* Every content table carries ``account_id``; helpers scope reads/writes to the
  active account automatically (``use_account`` / ``current_account``).
* Secrets (API keys, OAuth tokens) are Fernet-encrypted at rest.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Iterator

from cryptography.fernet import Fernet

from .config import settings

SCOPED_TABLES = {"posts", "documents", "stories", "contacts", "media", "trends"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS kv (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    secret INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    persona TEXT,
    color TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    pw_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'editor',        -- admin | editor | reviewer
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL DEFAULT 1,
    target TEXT NOT NULL DEFAULT 'member',
    org_urn TEXT,
    pillar TEXT,
    hook_type TEXT,
    content TEXT NOT NULL,
    first_comment TEXT,
    media_id INTEGER,
    status TEXT NOT NULL DEFAULT 'draft',       -- draft | approved | scheduled | published | failed | rejected
    scheduled_at TEXT,
    published_at TEXT,
    linkedin_urn TEXT,
    error TEXT,
    review_note TEXT,
    source TEXT,                                -- agent | import | manual
    metrics TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL DEFAULT 1,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL DEFAULT 1,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    tags TEXT,
    used_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL DEFAULT 1,
    name TEXT NOT NULL,
    headline TEXT,
    url TEXT,
    notes TEXT,
    next_follow_up TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL DEFAULT 1,
    kind TEXT NOT NULL,                         -- image | pdf
    title TEXT,
    path TEXT NOT NULL,
    prompt TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS trends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL DEFAULT 1,
    source TEXT,
    title TEXT NOT NULL,
    link TEXT,
    summary TEXT,
    published TEXT,
    created_at TEXT NOT NULL
);
"""

# Columns added after v0.1 — applied to existing databases on start-up.
MIGRATIONS = {
    "posts": {"account_id": "INTEGER NOT NULL DEFAULT 1", "media_id": "INTEGER", "review_note": "TEXT", "source": "TEXT"},
    "documents": {"account_id": "INTEGER NOT NULL DEFAULT 1"},
    "stories": {"account_id": "INTEGER NOT NULL DEFAULT 1"},
    "contacts": {"account_id": "INTEGER NOT NULL DEFAULT 1"},
}

_account: ContextVar[int] = ContextVar("account", default=1)


def current_account() -> int:
    return _account.get()


@contextmanager
def use_account(account_id: int) -> Iterator[None]:
    tok = _account.set(int(account_id))
    try:
        yield
    finally:
        _account.reset(tok)


def set_account(account_id: int) -> None:
    _account.set(int(account_id))


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


def secret_key() -> bytes:
    """Stable per-install secret used for signing review links."""
    _fernet()
    return settings.key_path.read_bytes()


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
        for table, cols in MIGRATIONS.items():
            have = {r["name"] for r in c.execute(f"PRAGMA table_info({table})")}
            for col, ddl in cols.items():
                if col not in have:
                    c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
        if not c.execute("SELECT 1 FROM accounts LIMIT 1").fetchone():
            c.execute("INSERT INTO accounts(name, color, created_at) VALUES(?,?,?)", ("My LinkedIn", "#0a66c2", now()))
    # Move v0.1 single-account keys into account 1.
    for k in ("brand_profile", "linkedin_token", "linkedin_member", "linkedin_orgs", "schedule"):
        with connect() as c:
            row = c.execute("SELECT value, secret FROM kv WHERE key=?", (k,)).fetchone()
            if row:
                c.execute("INSERT OR IGNORE INTO kv(key, value, secret) VALUES(?,?,?)", (f"a1:{k}", row["value"], row["secret"]))
                c.execute("DELETE FROM kv WHERE key=?", (k,))


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


# Account-scoped key/value helpers
def aset(key: str, value: Any, secret: bool = False) -> None:
    set_value(f"a{current_account()}:{key}", value, secret)


def aget(key: str, default: Any = None) -> Any:
    return get_value(f"a{current_account()}:{key}", default)


def adelete(key: str) -> None:
    delete_value(f"a{current_account()}:{key}")


# ---------- generic row helpers ----------

def _row(r: sqlite3.Row | None) -> dict | None:
    if r is None:
        return None
    d = dict(r)
    if d.get("metrics"):
        try:
            d["metrics"] = json.loads(d["metrics"])
        except (TypeError, ValueError):
            d["metrics"] = {}
    return d


def _scope(table: str, where: str, params: tuple) -> tuple[str, tuple]:
    if table in SCOPED_TABLES:
        clause = "account_id=?"
        where = f"({where}) AND {clause}" if where else clause
        params = (*params, current_account())
    return where, params


def insert(table: str, **fields: Any) -> int:
    fields.setdefault("created_at", now())
    if table in SCOPED_TABLES:
        fields.setdefault("account_id", current_account())
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
    if not fields:
        return
    if table == "posts":
        fields["updated_at"] = now()
    if "metrics" in fields and not isinstance(fields["metrics"], (str, type(None))):
        fields["metrics"] = json.dumps(fields["metrics"])
    sets = ", ".join(f"{k}=?" for k in fields)
    where, params = _scope(table, "id=?", (row_id,))
    with connect() as c:
        c.execute(f"UPDATE {table} SET {sets} WHERE {where}", (*fields.values(), *params))


def get(table: str, row_id: int) -> dict | None:
    where, params = _scope(table, "id=?", (row_id,))
    with connect() as c:
        return _row(c.execute(f"SELECT * FROM {table} WHERE {where}", params).fetchone())


def list_rows(table: str, where: str = "", params: tuple = (), order: str = "id DESC", limit: int = 200) -> list[dict]:
    where, params = _scope(table, where, params)
    sql = f"SELECT * FROM {table}"
    if where:
        sql += f" WHERE {where}"
    sql += f" ORDER BY {order} LIMIT {int(limit)}"
    with connect() as c:
        return [_row(r) for r in c.execute(sql, params).fetchall()]  # type: ignore[misc]


def count(table: str, where: str = "", params: tuple = ()) -> int:
    where, params = _scope(table, where, params)
    with connect() as c:
        return int(c.execute(f"SELECT COUNT(*) FROM {table}" + (f" WHERE {where}" if where else ""), params).fetchone()[0])


def delete(table: str, row_id: int) -> None:
    where, params = _scope(table, "id=?", (row_id,))
    with connect() as c:
        c.execute(f"DELETE FROM {table} WHERE {where}", params)


def all_accounts() -> list[dict]:
    with connect() as c:
        return [dict(r) for r in c.execute("SELECT * FROM accounts ORDER BY id").fetchall()]
