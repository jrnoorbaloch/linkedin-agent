"""FastAPI app: REST API + LinkedIn OAuth callback + the web portal."""

from __future__ import annotations

import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response

from . import __version__, db, export, linkedin, llm, publisher, skills
from .config import settings

STATIC = Path(__file__).parent / "static"
log = logging.getLogger("linkedin_agent")


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init()
    publisher.start_scheduler()
    yield


app = FastAPI(title="LinkedIn Agent", version=__version__, lifespan=lifespan)


@app.middleware("http")
async def token_guard(request: Request, call_next):
    if settings.api_token and request.url.path.startswith("/api/"):
        supplied = request.headers.get("x-api-token") or request.cookies.get("la_token") or ""
        if not secrets.compare_digest(supplied, settings.api_token):
            return JSONResponse({"detail": "Invalid or missing API token"}, status_code=401)
    return await call_next(request)


def _err(e: Exception) -> HTTPException:
    code = 400
    if isinstance(e, KeyError):
        code = 404
    elif isinstance(e, PermissionError):
        code = 403
    elif isinstance(e, (llm.LLMError, linkedin.LinkedInError)):
        code = 502
    return HTTPException(code, str(e).strip("'\""))


# ---------------- portal ----------------

@app.get("/", response_class=HTMLResponse)
def portal() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "version": __version__}


# ---------------- LinkedIn auth ----------------

@app.get("/auth/linkedin")
def auth_start() -> RedirectResponse:
    try:
        return RedirectResponse(linkedin.authorization_url())
    except linkedin.LinkedInError as e:
        raise _err(e)


@app.get("/auth/linkedin/callback")
def auth_callback(code: str = "", state: str = "", error: str = "", error_description: str = "") -> RedirectResponse:
    if error:
        return RedirectResponse(f"/?linkedin_error={error_description or error}#settings")
    try:
        linkedin.handle_callback(code, state)
    except linkedin.LinkedInError as e:
        return RedirectResponse(f"/?linkedin_error={e}#settings")
    return RedirectResponse("/?linkedin=connected#dashboard")


@app.get("/api/linkedin/status")
def li_status() -> dict:
    return linkedin.status()


@app.post("/api/linkedin/disconnect")
def li_disconnect() -> dict:
    linkedin.disconnect()
    return {"ok": True}


@app.get("/api/linkedin/organizations")
def li_orgs() -> list[dict]:
    try:
        return linkedin.list_admin_organizations()
    except linkedin.LinkedInError as e:
        raise _err(e)


# ---------------- LLM ----------------

@app.get("/api/llm")
def llm_get() -> dict:
    return {"config": llm.load_config().public(), "presets": llm.PRESETS}


@app.post("/api/llm")
def llm_save(data: dict = Body(...)) -> dict:
    cfg = llm.save_config(
        provider=data.get("provider", "openai"),
        model=data.get("model", ""),
        api_key=data.get("api_key", ""),
        base_url=data.get("base_url", ""),
        temperature=float(data.get("temperature", 0.8)),
    )
    return cfg.public()


@app.post("/api/llm/test")
def llm_test() -> dict:
    try:
        return {"ok": True, "reply": llm.complete("Reply with exactly: OK", "ping", max_tokens=10)}
    except llm.LLMError as e:
        raise _err(e)


# ---------------- brand profile & stories ----------------

@app.get("/api/brand")
def brand_get() -> dict:
    return {"profile": skills.get_brand(), "fields": skills.PROFILE_FIELDS}


@app.post("/api/brand")
def brand_save(data: dict = Body(...)) -> dict:
    return skills.save_brand(data)


@app.get("/api/stories")
def stories_list() -> list[dict]:
    return db.list_rows("stories")


@app.post("/api/stories")
def stories_add(data: dict = Body(...)) -> dict:
    sid = skills.add_story(data.get("title", "Untitled"), data.get("body", ""), data.get("tags", ""))
    return db.get("stories", sid)  # type: ignore[return-value]


@app.delete("/api/stories/{sid}")
def stories_delete(sid: int) -> dict:
    db.delete("stories", sid)
    return {"ok": True}


# ---------------- skills ----------------

@app.get("/api/skills")
def skills_list() -> list[dict]:
    return skills.list_skills()


@app.post("/api/skills/{skill_id}")
def skills_run(skill_id: str, inputs: dict = Body(default={})) -> dict:
    try:
        return skills.run(skill_id, inputs)
    except Exception as e:  # noqa: BLE001
        raise _err(e)


# ---------------- posts ----------------

@app.get("/api/posts")
def posts_list(status: str = "") -> list[dict]:
    rows = db.list_rows("posts", "status=?", (status,)) if status else db.list_rows("posts")
    for r in rows:
        r["url"] = publisher.post_url(r.get("linkedin_urn"))
    return rows


@app.post("/api/posts")
def posts_create(data: dict = Body(...)) -> dict:
    if not data.get("content"):
        raise HTTPException(400, "content is required")
    pid = db.insert(
        "posts",
        content=data["content"],
        first_comment=data.get("first_comment"),
        pillar=data.get("pillar"),
        target=data.get("target", "member"),
        org_urn=data.get("org_urn"),
        status="draft",
    )
    return db.get("posts", pid)  # type: ignore[return-value]


@app.patch("/api/posts/{pid}")
def posts_update(pid: int, data: dict = Body(...)) -> dict:
    allowed = {k: v for k, v in data.items() if k in ("content", "first_comment", "pillar", "target", "org_urn", "metrics", "scheduled_at")}
    if data.get("status") in ("draft", "rejected"):
        allowed["status"] = data["status"]
    db.update("posts", pid, **allowed)
    return db.get("posts", pid) or {}


@app.post("/api/posts/{pid}/approve")
def posts_approve(pid: int, data: dict = Body(default={})) -> dict:
    try:
        return publisher.approve(pid, data.get("scheduled_at"), data.get("content"))
    except Exception as e:  # noqa: BLE001
        raise _err(e)


@app.post("/api/posts/{pid}/publish")
def posts_publish(pid: int) -> dict:
    try:
        post = publisher.publish(pid)
        post["url"] = publisher.post_url(post.get("linkedin_urn"))
        return post
    except Exception as e:  # noqa: BLE001
        raise _err(e)


@app.delete("/api/posts/{pid}")
def posts_delete(pid: int) -> dict:
    db.delete("posts", pid)
    return {"ok": True}


# ---------------- documents ----------------

@app.get("/api/documents")
def docs_list(kind: str = "") -> list[dict]:
    return db.list_rows("documents", "kind=?", (kind,)) if kind else db.list_rows("documents")


@app.delete("/api/documents/{did}")
def docs_delete(did: int) -> dict:
    db.delete("documents", did)
    return {"ok": True}


@app.get("/api/documents/{did}/docx")
def docs_docx(did: int) -> Response:
    d = db.get("documents", did)
    if not d:
        raise HTTPException(404, "Not found")
    name = "".join(ch if ch.isalnum() else "-" for ch in d["title"])[:60].strip("-") or "document"
    return Response(
        export.markdown_to_docx(d["content"]),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{name}.docx"'},
    )


# ---------------- contacts (mini CRM) ----------------

@app.get("/api/contacts")
def contacts_list() -> list[dict]:
    return db.list_rows("contacts", order="COALESCE(next_follow_up,'9999') ASC")


@app.post("/api/contacts")
def contacts_add(data: dict = Body(...)) -> dict:
    cid = db.insert("contacts", **{k: data.get(k) for k in ("name", "headline", "url", "notes", "next_follow_up")})
    return db.get("contacts", cid)  # type: ignore[return-value]


@app.delete("/api/contacts/{cid}")
def contacts_delete(cid: int) -> dict:
    db.delete("contacts", cid)
    return {"ok": True}


# ---------------- schedule & dashboard ----------------

@app.get("/api/schedule")
def schedule_get() -> dict:
    return publisher.get_schedule()


@app.post("/api/schedule")
def schedule_save(data: dict = Body(...)) -> dict:
    return publisher.save_schedule(data)


@app.get("/api/dashboard")
def dashboard() -> dict[str, Any]:
    posts = db.list_rows("posts", limit=500)
    count = lambda s: sum(1 for p in posts if p["status"] == s)  # noqa: E731
    published = [p for p in posts if p["status"] == "published"]
    impressions = sum(int((p.get("metrics") or {}).get("impressions") or 0) for p in published)
    reactions = sum(int((p.get("metrics") or {}).get("reactions") or 0) for p in published)
    comments = sum(int((p.get("metrics") or {}).get("comments") or 0) for p in published)
    return {
        "drafts": count("draft"),
        "approved": count("approved") + count("scheduled"),
        "published": len(published),
        "failed": count("failed"),
        "impressions": impressions,
        "engagement_rate": round(100 * (reactions + comments) / impressions, 2) if impressions else None,
        "stories": len(db.list_rows("stories", limit=1000)),
        "documents": len(db.list_rows("documents", limit=1000)),
        "linkedin": linkedin.status(),
        "llm": llm.load_config().public(),
        "brand_complete": sum(1 for v in skills.get_brand().values() if v),
        "schedule": publisher.get_schedule(),
    }
