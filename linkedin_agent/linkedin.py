"""LinkedIn official API client (OAuth 2.0 + Posts API).

What the official API allows (and what this module implements):

* Sign in with LinkedIn (OpenID Connect)      -> openid, profile, email     (self-serve)
* Post / comment as yourself                   -> w_member_social           (self-serve, "Share on LinkedIn")
* Post as a Company Page                       -> w_organization_social     (needs Community Management API approval)

What it does NOT allow: editing profile sections (headline, About, experience)
or reading your past posts (r_member_social is closed). The agent therefore
*writes* profile copy for you to paste, and tracks post metrics you enter.
"""

from __future__ import annotations

import re
import secrets
import time
from urllib.parse import quote, urlencode

import httpx

from . import db
from .config import settings

AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
API = "https://api.linkedin.com"


class LinkedInError(RuntimeError):
    pass


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "LinkedIn-Version": settings.linkedin_api_version,
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }


# ---------------- OAuth ----------------

def authorization_url() -> str:
    if not settings.linkedin_client_id:
        raise LinkedInError("LINKEDIN_CLIENT_ID is not set. See docs: Getting started → LinkedIn app.")
    state = secrets.token_urlsafe(24)
    db.set_value("oauth_state", state)
    params = {
        "response_type": "code",
        "client_id": settings.linkedin_client_id,
        "redirect_uri": settings.redirect_uri,
        "state": state,
        "scope": " ".join(settings.linkedin_scopes),
    }
    return f"{AUTH_URL}?{urlencode(params, quote_via=quote)}"


def handle_callback(code: str, state: str) -> dict:
    expected = db.get_value("oauth_state")
    if not expected or not secrets.compare_digest(expected, state):
        raise LinkedInError("OAuth state mismatch. Please try connecting again.")
    db.delete_value("oauth_state")
    r = httpx.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.redirect_uri,
            "client_id": settings.linkedin_client_id,
            "client_secret": settings.linkedin_client_secret,
        },
        timeout=30,
    )
    if r.status_code != 200:
        raise LinkedInError(f"Token exchange failed: {r.text[:300]}")
    tok = r.json()
    tok["obtained_at"] = int(time.time())
    db.set_value("linkedin_token", tok, secret=True)
    me = userinfo(tok["access_token"])
    db.set_value("linkedin_member", me)
    return me


def _token() -> str:
    tok = db.get_value("linkedin_token")
    if not tok:
        raise LinkedInError("LinkedIn is not connected. Open the portal and click 'Connect LinkedIn'.")
    expires = tok.get("obtained_at", 0) + int(tok.get("expires_in", 0))
    if expires and time.time() > expires - 60:
        refreshed = _refresh(tok)
        if refreshed:
            return refreshed
        raise LinkedInError("LinkedIn token expired. Please reconnect LinkedIn.")
    return tok["access_token"]


def _refresh(tok: dict) -> str | None:
    rt = tok.get("refresh_token")
    if not rt:
        return None
    r = httpx.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": rt,
            "client_id": settings.linkedin_client_id,
            "client_secret": settings.linkedin_client_secret,
        },
        timeout=30,
    )
    if r.status_code != 200:
        return None
    new = r.json()
    new["obtained_at"] = int(time.time())
    new.setdefault("refresh_token", rt)
    db.set_value("linkedin_token", new, secret=True)
    return new["access_token"]


def status() -> dict:
    tok = db.get_value("linkedin_token")
    member = db.get_value("linkedin_member")
    if not tok:
        return {"connected": False, "org_enabled": settings.linkedin_org_enabled}
    expires_at = tok.get("obtained_at", 0) + int(tok.get("expires_in", 0))
    return {
        "connected": True,
        "member": member,
        "expires_in_days": max(0, int((expires_at - time.time()) / 86400)),
        "org_enabled": settings.linkedin_org_enabled,
        "organizations": db.get_value("linkedin_orgs", []),
    }


def disconnect() -> None:
    for k in ("linkedin_token", "linkedin_member", "linkedin_orgs"):
        db.delete_value(k)


def userinfo(token: str | None = None) -> dict:
    r = httpx.get(f"{API}/v2/userinfo", headers={"Authorization": f"Bearer {token or _token()}"}, timeout=30)
    if r.status_code != 200:
        raise LinkedInError(f"userinfo failed: {r.text[:300]}")
    return r.json()


def member_urn() -> str:
    member = db.get_value("linkedin_member") or {}
    sub = member.get("sub")
    if not sub:
        raise LinkedInError("LinkedIn member id unknown. Reconnect LinkedIn.")
    return f"urn:li:person:{sub}"


# ---------------- Organizations (Company Pages) ----------------

def list_admin_organizations() -> list[dict]:
    """Pages the member administers. Requires Community Management API access."""
    if not settings.linkedin_org_enabled:
        raise LinkedInError("Company Page support is off. Set LINKEDIN_ORG_ENABLED=1 after LinkedIn approves your app.")
    token = _token()
    r = httpx.get(
        f"{API}/rest/organizationAcls",
        params={"q": "roleAssignee", "role": "ADMINISTRATOR", "state": "APPROVED"},
        headers=_headers(token),
        timeout=30,
    )
    if r.status_code != 200:
        raise LinkedInError(f"organizationAcls failed: {r.text[:300]}")
    orgs = [{"urn": e["organization"]} for e in r.json().get("elements", [])]
    db.set_value("linkedin_orgs", orgs)
    return orgs


# ---------------- Posting ----------------

def create_post(text: str, author_urn: str | None = None) -> str:
    """Publish a text post. Returns the post URN (x-restli-id header)."""
    token = _token()
    author = author_urn or member_urn()
    body = {
        "author": author,
        "commentary": escape_little_text(text),
        "visibility": "PUBLIC",
        "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []},
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    r = httpx.post(f"{API}/rest/posts", headers=_headers(token), json=body, timeout=30)
    if r.status_code not in (200, 201):
        raise LinkedInError(f"Post failed ({r.status_code}): {r.text[:400]}")
    return r.headers.get("x-restli-id", "")


def create_comment(post_urn: str, text: str, actor_urn: str | None = None) -> None:
    token = _token()
    actor = actor_urn or member_urn()
    r = httpx.post(
        f"{API}/rest/socialActions/{quote(post_urn, safe='')}/comments",
        headers=_headers(token),
        json={"actor": actor, "object": post_urn, "message": {"text": text}},
        timeout=30,
    )
    if r.status_code not in (200, 201):
        raise LinkedInError(f"Comment failed ({r.status_code}): {r.text[:400]}")


_LITTLE_RESERVED = set("\\|{}@[]()<>#*_~")


_HASHTAG = re.compile(r"(?<![\w#])#([A-Za-z0-9_]+)")


def escape_little_text(text: str) -> str:
    """The Posts API 'commentary' field uses 'little text' format; reserved
    characters must be backslash-escaped or the post is truncated/rejected.
    Hashtags are converted to LinkedIn's clickable hashtag template."""
    out: list[str] = []
    pos = 0
    for m in _HASHTAG.finditer(text):
        out.append(_escape(text[pos : m.start()]))
        out.append("{hashtag|\\#|" + m.group(1) + "}")
        pos = m.end()
    out.append(_escape(text[pos:]))
    return "".join(out)


def _escape(s: str) -> str:
    return "".join(("\\" + ch) if ch in _LITTLE_RESERVED else ch for ch in s)
