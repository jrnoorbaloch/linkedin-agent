"""Team accounts and roles.

Single-user mode (default): until the first user is created the portal is open
on localhost, exactly like v1. After an admin is created, everyone signs in.

Roles
* admin    — everything, including settings, LinkedIn connection, team and workspaces
* editor   — create/edit drafts, documents, stories; cannot approve or publish
* reviewer — read everything, approve / reject / schedule / publish
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from . import db

ROLES = ("admin", "editor", "reviewer")
PERMS = {
    "admin": {"read", "write", "approve", "publish", "settings", "team"},
    "editor": {"read", "write"},
    "reviewer": {"read", "approve", "publish"},
}


def hash_password(pw: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 310_000)
    return f"pbkdf2${salt.hex()}${dk.hex()}"


def check_password(pw: str, stored: str) -> bool:
    try:
        _, salt, dk = stored.split("$")
    except ValueError:
        return False
    test = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 310_000)
    return hmac.compare_digest(test.hex(), dk)


def user_count() -> int:
    with db.connect() as c:
        return int(c.execute("SELECT COUNT(*) FROM users").fetchone()[0])


def list_users() -> list[dict]:
    with db.connect() as c:
        return [dict(r) for r in c.execute("SELECT id, name, email, role, created_at FROM users ORDER BY id")]


def create_user(name: str, email: str, password: str, role: str = "editor") -> dict:
    if role not in ROLES:
        raise ValueError("Invalid role")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if user_count() == 0:
        role = "admin"  # first user is always admin
    with db.connect() as c:
        try:
            cur = c.execute("INSERT INTO users(name, email, pw_hash, role, created_at) VALUES(?,?,?,?,?)",
                            (name.strip() or email, email.strip().lower(), hash_password(password), role, db.now()))
        except Exception as e:  # sqlite3.IntegrityError
            raise ValueError("A user with that email already exists") from e
        uid = cur.lastrowid
    return {"id": uid, "name": name, "email": email.lower(), "role": role}


def delete_user(uid: int) -> None:
    with db.connect() as c:
        c.execute("DELETE FROM users WHERE id=?", (uid,))
        c.execute("DELETE FROM sessions WHERE user_id=?", (uid,))


def set_role(uid: int, role: str) -> None:
    if role not in ROLES:
        raise ValueError("Invalid role")
    with db.connect() as c:
        c.execute("UPDATE users SET role=? WHERE id=?", (role, uid))


def login(email: str, password: str) -> str:
    with db.connect() as c:
        row = c.execute("SELECT * FROM users WHERE email=?", (email.strip().lower(),)).fetchone()
    if not row or not check_password(password, row["pw_hash"]):
        raise PermissionError("Wrong email or password")
    token = secrets.token_urlsafe(32)
    exp = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    with db.connect() as c:
        c.execute("INSERT INTO sessions(token, user_id, expires_at) VALUES(?,?,?)", (token, row["id"], exp))
    return token


def logout(token: str) -> None:
    with db.connect() as c:
        c.execute("DELETE FROM sessions WHERE token=?", (token,))


def user_for_token(token: str | None) -> dict | None:
    if not token:
        return None
    with db.connect() as c:
        row = c.execute(
            "SELECT u.id, u.name, u.email, u.role, s.expires_at FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=?",
            (token,),
        ).fetchone()
    if not row or row["expires_at"] < datetime.now(timezone.utc).isoformat():
        return None
    return {k: row[k] for k in ("id", "name", "email", "role")}


def can(user: dict | None, perm: str) -> bool:
    if user is None:
        return True  # single-user mode
    return perm in PERMS.get(user["role"], set())
