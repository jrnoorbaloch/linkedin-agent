"""FastAPI app: REST API, LinkedIn OAuth, review links, webhooks and the web portal."""

from __future__ import annotations

import base64
import csv
import html
import io
import logging
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import Body, Depends, FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import (FileResponse, HTMLResponse, JSONResponse, PlainTextResponse,
                               RedirectResponse, Response)

from . import (__version__, analytics, auth, db, export, importer, linkedin, llm, media, notify,
               personas, publisher, skills, trends)
from .config import settings

STATIC = Path(__file__).parent / "static"
log = logging.getLogger("linkedin_agent")


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init()
    if not settings.disable_scheduler:
        publisher.start_scheduler()
    yield


app = FastAPI(title="LinkedIn Agent", version=__version__, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")

PUBLIC_PATHS = ("/api/health", "/api/auth/", "/api/i18n")


# ---------------- request context: user + workspace ----------------

async def ctx(request: Request) -> dict | None:
    """Resolve the user (or single-user mode) and activate the requested workspace."""
    user: dict | None = None
    api_tok = request.headers.get("x-api-token") or ""
    if settings.api_token and api_tok and secrets.compare_digest(api_tok, settings.api_token):
        user = {"id": 0, "name": "API token", "email": "", "role": "admin"}
    else:
        user = auth.user_for_token(request.cookies.get("la_session") or request.headers.get("authorization", "").removeprefix("Bearer ").strip())
    needs_login = auth.user_count() > 0 or bool(settings.api_token)
    if needs_login and user is None and not request.url.path.startswith(PUBLIC_PATHS):
        raise HTTPException(401, "Sign in required")
    acct = request.headers.get("x-account") or request.query_params.get("account") or "1"
    ids = {a["id"] for a in db.all_accounts()}
    db.set_account(int(acct) if acct.isdigit() and int(acct) in ids else 1)
    request.state.user = user
    return user


def need(perm: str):
    async def check(request: Request, user: dict | None = Depends(ctx)) -> dict | None:
        if not auth.can(user, perm):
            raise HTTPException(403, f"Your role can't do this ({perm}).")
        return user
    return check


R, W, A, P, S, T = (need(p) for p in ("read", "write", "approve", "publish", "settings", "team"))


def _err(e: Exception) -> HTTPException:
    code = 400
    if isinstance(e, KeyError):
        code = 404
    elif isinstance(e, PermissionError):
        code = 403
    elif isinstance(e, (llm.LLMError, linkedin.LinkedInError)):
        code = 502
    return HTTPException(code, str(e).strip("'\""))


def _b64files(data: dict) -> list[tuple[str, bytes]]:
    files = data.get("files") or [data]
    out = []
    for f in files:
        if not f.get("content"):
            continue
        out.append((f.get("name", "upload"), base64.b64decode(f["content"].split(",", 1)[-1])))
    if not out:
        raise HTTPException(400, "No file content received")
    return out


# ---------------- portal ----------------

@app.get("/", response_class=HTMLResponse)
def portal() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "version": __version__}


# ---------------- auth & team ----------------

@app.get("/api/auth/me")
async def me(request: Request) -> dict:
    user = auth.user_for_token(request.cookies.get("la_session"))
    return {"user": user, "team_mode": auth.user_count() > 0, "api_token_required": bool(settings.api_token)}


@app.post("/api/auth/setup")
def auth_setup(data: dict = Body(...)) -> JSONResponse:
    if auth.user_count() > 0:
        raise HTTPException(403, "Already set up — ask an admin to invite you.")
    try:
        auth.create_user(data.get("name", ""), data.get("email", ""), data.get("password", ""), "admin")
        token = auth.login(data["email"], data["password"])
    except ValueError as e:
        raise HTTPException(400, str(e))
    resp = JSONResponse({"ok": True})
    resp.set_cookie("la_session", token, httponly=True, samesite="lax", max_age=30 * 86400)
    return resp


@app.post("/api/auth/login")
def auth_login(data: dict = Body(...)) -> JSONResponse:
    try:
        token = auth.login(data.get("email", ""), data.get("password", ""))
    except PermissionError as e:
        raise HTTPException(401, str(e))
    resp = JSONResponse({"ok": True})
    resp.set_cookie("la_session", token, httponly=True, samesite="lax", max_age=30 * 86400)
    return resp


@app.post("/api/auth/logout")
def auth_logout(request: Request) -> JSONResponse:
    auth.logout(request.cookies.get("la_session") or "")
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("la_session")
    return resp


@app.get("/api/team")
def team_list(_: Any = Depends(T)) -> dict:
    return {"users": auth.list_users(), "roles": auth.ROLES}


@app.post("/api/team")
def team_add(data: dict = Body(...), _: Any = Depends(T)) -> dict:
    try:
        return auth.create_user(data.get("name", ""), data.get("email", ""), data.get("password", ""), data.get("role", "editor"))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.patch("/api/team/{uid}")
def team_role(uid: int, data: dict = Body(...), _: Any = Depends(T)) -> dict:
    auth.set_role(uid, data.get("role", "editor"))
    return {"ok": True}


@app.delete("/api/team/{uid}")
def team_delete(uid: int, user: Any = Depends(T)) -> dict:
    if user and user.get("id") == uid:
        raise HTTPException(400, "You can't remove yourself.")
    auth.delete_user(uid)
    return {"ok": True}


# ---------------- workspaces ----------------

@app.get("/api/accounts")
def accounts_list(_: Any = Depends(R)) -> list[dict]:
    out = []
    for a in db.all_accounts():
        with db.use_account(a["id"]):
            m = db.aget("linkedin_member") or {}
            out.append({**a, "linkedin_name": m.get("name"), "picture": m.get("picture"), "drafts": db.count("posts", "status='draft'")})
    return out


@app.post("/api/accounts")
def accounts_add(data: dict = Body(...), _: Any = Depends(T)) -> dict:
    aid = db.insert("accounts", name=data.get("name") or "New workspace", color=data.get("color") or "#7c3aed")
    return {"id": aid}


@app.patch("/api/accounts/{aid}")
def accounts_rename(aid: int, data: dict = Body(...), _: Any = Depends(T)) -> dict:
    with db.connect() as c:
        c.execute("UPDATE accounts SET name=COALESCE(?,name), color=COALESCE(?,color) WHERE id=?", (data.get("name"), data.get("color"), aid))
    return {"ok": True}


@app.delete("/api/accounts/{aid}")
def accounts_delete(aid: int, _: Any = Depends(T)) -> dict:
    if aid == 1:
        raise HTTPException(400, "The first workspace can't be deleted.")
    with db.connect() as c:
        for t in db.SCOPED_TABLES:
            c.execute(f"DELETE FROM {t} WHERE account_id=?", (aid,))
        c.execute("DELETE FROM kv WHERE key LIKE ?", (f"a{aid}:%",))
        c.execute("DELETE FROM accounts WHERE id=?", (aid,))
    return {"ok": True}


# ---------------- LinkedIn auth ----------------

@app.get("/auth/linkedin")
async def auth_start(request: Request, _: Any = Depends(S)) -> RedirectResponse:
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
def li_status(_: Any = Depends(R)) -> dict:
    return linkedin.status()


@app.post("/api/linkedin/disconnect")
def li_disconnect(_: Any = Depends(S)) -> dict:
    linkedin.disconnect()
    return {"ok": True}


@app.get("/api/linkedin/organizations")
def li_orgs(_: Any = Depends(S)) -> list[dict]:
    try:
        return linkedin.list_admin_organizations()
    except linkedin.LinkedInError as e:
        raise _err(e)


# ---------------- LLM & image model ----------------

@app.get("/api/llm")
def llm_get(_: Any = Depends(R)) -> dict:
    return {"config": llm.load_config().public(), "presets": llm.PRESETS, "image": media.load_image_config().public()}


@app.post("/api/llm")
def llm_save(data: dict = Body(...), _: Any = Depends(S)) -> dict:
    cfg = llm.save_config(provider=data.get("provider", "openai"), model=data.get("model", ""),
                          api_key=data.get("api_key", ""), base_url=data.get("base_url", ""),
                          temperature=float(data.get("temperature", 0.8)))
    return cfg.public()


@app.post("/api/llm/test")
def llm_test(_: Any = Depends(R)) -> dict:
    try:
        return {"ok": True, "reply": llm.complete("Reply with exactly: OK", "ping", max_tokens=10)}
    except llm.LLMError as e:
        raise _err(e)


@app.post("/api/image-model")
def image_model_save(data: dict = Body(...), _: Any = Depends(S)) -> dict:
    return media.save_image_config(data.get("base_url", ""), data.get("model", ""), data.get("api_key", ""), data.get("size", "")).public()


# ---------------- brand, packs, import ----------------

@app.get("/api/brand")
def brand_get(_: Any = Depends(R)) -> dict:
    return {"profile": skills.get_brand(), "fields": skills.PROFILE_FIELDS, "persona": db.aget("persona")}


@app.post("/api/brand")
def brand_save(data: dict = Body(...), _: Any = Depends(W)) -> dict:
    return skills.save_brand(data)


@app.get("/api/packs")
def packs_list(_: Any = Depends(R)) -> dict:
    return {"packs": personas.list_packs(), "active": db.aget("persona")}


@app.post("/api/packs/{pack_id}")
def packs_apply(pack_id: str, data: dict = Body(default={}), _: Any = Depends(W)) -> dict:
    try:
        return personas.apply_pack(pack_id, overwrite=bool(data.get("overwrite")))
    except KeyError as e:
        raise _err(e)


@app.post("/api/import/linkedin")
def import_linkedin(data: dict = Body(...), _: Any = Depends(W)) -> dict:
    try:
        return importer.import_linkedin_export(_b64files(data))
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"Could not read the export: {e}")


@app.post("/api/import/analytics")
def import_analytics(data: dict = Body(...), _: Any = Depends(W)) -> dict:
    name, raw = _b64files(data)[0]
    try:
        return importer.import_analytics(name, raw)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"Could not read analytics file: {e}")


# ---------------- stories ----------------

@app.get("/api/stories")
def stories_list(_: Any = Depends(R)) -> list[dict]:
    return db.list_rows("stories")


@app.post("/api/stories")
def stories_add(data: dict = Body(...), _: Any = Depends(W)) -> dict:
    sid = skills.add_story(data.get("title", "Untitled"), data.get("body", ""), data.get("tags", ""))
    return db.get("stories", sid)  # type: ignore[return-value]


@app.delete("/api/stories/{sid}")
def stories_delete(sid: int, _: Any = Depends(W)) -> dict:
    db.delete("stories", sid)
    return {"ok": True}


# ---------------- skills ----------------

@app.get("/api/skills")
def skills_list(_: Any = Depends(R)) -> list[dict]:
    return skills.list_skills()


@app.post("/api/skills/{skill_id}")
def skills_run(skill_id: str, inputs: dict = Body(default={}), _: Any = Depends(W)) -> dict:
    try:
        return skills.run(skill_id, inputs)
    except Exception as e:  # noqa: BLE001
        raise _err(e)


# ---------------- posts ----------------

def _decorate(p: dict) -> dict:
    p["url"] = publisher.post_url(p.get("linkedin_urn"))
    if p.get("media_id"):
        m = db.get("media", p["media_id"])
        p["media"] = {"id": m["id"], "kind": m["kind"], "title": m.get("title"), "url": f"/media/{m['id']}"} if m else None
    return p


@app.get("/api/posts")
def posts_list(status: str = "", start: str = "", end: str = "", _: Any = Depends(R)) -> list[dict]:
    where, params = [], []
    if status:
        where.append("status IN (%s)" % ",".join("?" * len(status.split(","))))
        params += status.split(",")
    if start and end:
        where.append("COALESCE(scheduled_at, published_at, created_at) BETWEEN ? AND ?")
        params += [start, end]
    rows = db.list_rows("posts", " AND ".join(where), tuple(params), limit=1000)
    return [_decorate(r) for r in rows]


@app.post("/api/posts")
def posts_create(data: dict = Body(...), _: Any = Depends(W)) -> dict:
    if not data.get("content"):
        raise HTTPException(400, "content is required")
    pid = db.insert("posts", content=data["content"], first_comment=data.get("first_comment"), pillar=data.get("pillar"),
                    target=data.get("target", "member"), org_urn=data.get("org_urn"), media_id=data.get("media_id"),
                    status="draft", source="manual")
    return _decorate(db.get("posts", pid))  # type: ignore[arg-type]


@app.patch("/api/posts/{pid}")
def posts_update(pid: int, data: dict = Body(...), user: Any = Depends(W)) -> dict:
    allowed = {k: v for k, v in data.items() if k in ("content", "first_comment", "pillar", "target", "org_urn", "metrics", "media_id")}
    if "scheduled_at" in data:
        post = db.get("posts", pid) or {}
        if post.get("status") == "scheduled" and not auth.can(user, "approve"):
            raise HTTPException(403, "Only reviewers can reschedule approved posts.")
        allowed["scheduled_at"] = data["scheduled_at"]
    if data.get("status") in ("draft", "rejected"):
        allowed["status"] = data["status"]
    db.update("posts", pid, **allowed)
    return _decorate(db.get("posts", pid) or {})


@app.post("/api/posts/{pid}/approve")
def posts_approve(pid: int, data: dict = Body(default={}), _: Any = Depends(A)) -> dict:
    try:
        return _decorate(publisher.approve(pid, data.get("scheduled_at"), data.get("content")))
    except Exception as e:  # noqa: BLE001
        raise _err(e)


@app.post("/api/posts/{pid}/publish")
def posts_publish(pid: int, _: Any = Depends(P)) -> dict:
    try:
        return _decorate(publisher.publish(pid))
    except Exception as e:  # noqa: BLE001
        raise _err(e)


@app.post("/api/posts/{pid}/share")
def posts_share(pid: int, _: Any = Depends(W)) -> dict:
    if not db.get("posts", pid):
        raise HTTPException(404, "Not found")
    return {"url": notify.review_url(pid)}


@app.delete("/api/posts/{pid}")
def posts_delete(pid: int, _: Any = Depends(W)) -> dict:
    db.delete("posts", pid)
    return {"ok": True}


# ---------------- client review links ----------------

REVIEW_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>Review post · LinkedIn Agent</title>
<style>body{{margin:0;font-family:Inter,-apple-system,Segoe UI,Roboto,sans-serif;background:#f5f6f8;color:#0f172a}}
.w{{max-width:620px;margin:40px auto;padding:0 16px}}.c{{background:#fff;border-radius:16px;box-shadow:0 1px 3px rgba(0,0,0,.08),0 0 0 1px #e5e7eb;padding:24px}}
.t{{white-space:pre-wrap;line-height:1.6;font-size:15px}}.m{{color:#64748b;font-size:13px}}textarea{{width:100%;box-sizing:border-box;border:1px solid #e2e8f0;border-radius:10px;padding:10px;font:inherit;min-height:80px}}
button{{border:0;border-radius:999px;padding:10px 20px;font-weight:600;font-size:14px;cursor:pointer;margin-right:8px}}.a{{background:#0a66c2;color:#fff}}.r{{background:#f1f5f9;color:#0f172a}}
.s{{padding:12px 16px;border-radius:10px;background:#ecfdf5;color:#047857;font-weight:600;margin-bottom:16px}}img{{max-width:100%;border-radius:12px;margin-top:12px}}</style></head>
<body><div class="w"><p class="m">LinkedIn Agent · post #{id} for review</p>{msg}<div class="c"><div class="t">{content}</div>{media}
{fc}</div>{form}</div></body></html>"""


@app.get("/review/{token}", response_class=HTMLResponse)
def review_page(token: str, done: str = "") -> HTMLResponse:
    try:
        acct, pid = notify.verify_review(token)
    except PermissionError as e:
        return HTMLResponse(f"<h3 style='font-family:sans-serif'>{html.escape(str(e))}</h3>", status_code=403)
    with db.use_account(acct):
        p = db.get("posts", pid)
        if not p:
            return HTMLResponse("<h3>Post not found</h3>", status_code=404)
        med = ""
        if p.get("media_id") and (m := db.get("media", p["media_id"])) and m["kind"] == "image":
            med = f'<img src="/review/{token}/media" alt="">'
        open_ = p["status"] in ("draft", "failed")
        form = (f"""<form method="post" style="margin-top:16px"><textarea name="note" placeholder="Optional note for the author"></textarea>
<p><button class="a" name="action" value="approve">Approve</button><button class="r" name="action" value="reject">Request changes</button></p></form>""" if open_ else "")
        msg = {"approve": '<div class="s">Thanks, the post is approved.</div>', "reject": '<div class="s">Thanks, your feedback was sent.</div>'}.get(done, "")
        if not open_ and not msg:
            msg = f'<div class="s">Status: {html.escape(p["status"])}</div>'
        fc = f'<p class="m">First comment: {html.escape(p["first_comment"])}</p>' if p.get("first_comment") else ""
        return HTMLResponse(REVIEW_HTML.format(id=pid, content=html.escape(p["content"]), media=med, fc=fc, form=form, msg=msg))


@app.get("/review/{token}/media")
def review_media(token: str) -> FileResponse:
    acct, pid = notify.verify_review(token)
    with db.use_account(acct):
        p = db.get("posts", pid) or {}
        m = db.get("media", p.get("media_id") or 0)
    if not m:
        raise HTTPException(404)
    return FileResponse(m["path"])


@app.post("/review/{token}")
async def review_submit(token: str, request: Request) -> RedirectResponse:
    acct, pid = notify.verify_review(token)
    form = dict((k, v[0] if isinstance(v, list) else v) for k, v in
                __import__("urllib.parse", fromlist=["parse_qs"]).parse_qs((await request.body()).decode()).items())
    action, note = form.get("action", ""), form.get("note", "")[:1000]
    with db.use_account(acct):
        p = db.get("posts", pid)
        if p and p["status"] in ("draft", "failed"):
            if action == "approve":
                db.update("posts", pid, review_note=note or None)
                publisher.approve(pid)
            elif action == "reject":
                db.update("posts", pid, status="rejected", review_note=note or "Changes requested")
                notify.emit("review_feedback", db.get("posts", pid), note)
    return RedirectResponse(f"/review/{token}?done={action}", status_code=303)


# ---------------- WhatsApp webhook ----------------

@app.get("/webhooks/whatsapp")
def wa_verify(request: Request) -> PlainTextResponse:
    q = request.query_params
    for a in db.all_accounts():
        with db.use_account(a["id"]):
            wa = notify.get_config().get("whatsapp", {})
            if wa.get("verify_token") and q.get("hub.verify_token") == wa["verify_token"]:
                return PlainTextResponse(q.get("hub.challenge", ""))
    raise HTTPException(403, "Verification failed")


@app.post("/webhooks/whatsapp")
def wa_incoming(payload: dict = Body(...)) -> dict:
    try:
        msg = payload["entry"][0]["changes"][0]["value"]["messages"][0]
        sender, text = msg["from"], (msg.get("text", {}).get("body") or "").strip()
    except (KeyError, IndexError):
        return {"ok": True}
    parts = text.split()
    if len(parts) < 2 or parts[0].lower() not in ("approve", "reject") or not parts[1].lstrip("#").isdigit():
        return {"ok": True}
    for a in db.all_accounts():
        with db.use_account(a["id"]):
            wa = notify.get_config().get("whatsapp", {})
            if wa.get("enabled") and wa.get("to", "").lstrip("+") == sender.lstrip("+"):
                notify.handle_remote_action(parts[0].lower(), int(parts[1].lstrip("#")), " ".join(parts[2:]))
                break
    return {"ok": True}


# ---------------- media & carousel ----------------

@app.get("/api/media")
def media_list(_: Any = Depends(R)) -> list[dict]:
    return [{**m, "url": f"/media/{m['id']}"} for m in db.list_rows("media")]


@app.get("/media/{mid}")
async def media_file(mid: int, request: Request, _: Any = Depends(R)) -> FileResponse:
    m = db.get("media", mid)
    if not m or not Path(m["path"]).exists():
        raise HTTPException(404)
    return FileResponse(m["path"])


@app.post("/api/media/upload")
def media_upload(data: dict = Body(...), _: Any = Depends(W)) -> dict:
    try:
        m = media.save_upload(data.get("name", "upload.png"), data["content"], data.get("title", ""))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, str(e))
    return {**m, "url": f"/media/{m['id']}"}


@app.post("/api/media/generate")
def media_generate(data: dict = Body(...), _: Any = Depends(W)) -> dict:
    try:
        m = media.generate_image(data.get("prompt", ""), data.get("title", ""))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, str(e))
    return {**m, "url": f"/media/{m['id']}"}


@app.post("/api/media/carousel")
def media_carousel(data: dict = Body(...), _: Any = Depends(W)) -> dict:
    text = data.get("text") or ""
    if data.get("document_id"):
        d = db.get("documents", int(data["document_id"]))
        text = d["content"] if d else text
    try:
        m = media.render_carousel(text, data.get("theme", "linkedin"), data.get("title") or "Carousel")
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, str(e))
    return {**m, "url": f"/media/{m['id']}"}


@app.delete("/api/media/{mid}")
def media_delete(mid: int, _: Any = Depends(W)) -> dict:
    m = db.get("media", mid)
    if m:
        Path(m["path"]).unlink(missing_ok=True)
        db.delete("media", mid)
    return {"ok": True}


# ---------------- trends ----------------

@app.get("/api/trends")
def trends_get(_: Any = Depends(R)) -> dict:
    return {"feeds": trends.get_feeds(), "items": db.list_rows("trends", limit=60)}


@app.post("/api/trends/feeds")
def trends_feeds(data: dict = Body(...), _: Any = Depends(W)) -> dict:
    return {"feeds": trends.set_feeds(data.get("feeds", []))}


@app.post("/api/trends/refresh")
def trends_refresh(_: Any = Depends(W)) -> dict:
    return trends.refresh()


# ---------------- documents ----------------

@app.get("/api/documents")
def docs_list(kind: str = "", _: Any = Depends(R)) -> list[dict]:
    return db.list_rows("documents", "kind=?", (kind,)) if kind else db.list_rows("documents")


@app.delete("/api/documents/{did}")
def docs_delete(did: int, _: Any = Depends(W)) -> dict:
    db.delete("documents", did)
    return {"ok": True}


@app.get("/api/documents/{did}/docx")
def docs_docx(did: int, _: Any = Depends(R)) -> Response:
    d = db.get("documents", did)
    if not d:
        raise HTTPException(404, "Not found")
    name = "".join(ch if ch.isalnum() else "-" for ch in d["title"])[:60].strip("-") or "document"
    return Response(export.markdown_to_docx(d["content"]),
                    media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f'attachment; filename="{name}.docx"'})


# ---------------- contacts ----------------

@app.get("/api/contacts")
def contacts_list(_: Any = Depends(R)) -> list[dict]:
    return db.list_rows("contacts", order="COALESCE(next_follow_up,'9999') ASC")


@app.post("/api/contacts")
def contacts_add(data: dict = Body(...), _: Any = Depends(W)) -> dict:
    cid = db.insert("contacts", **{k: data.get(k) for k in ("name", "headline", "url", "notes", "next_follow_up")})
    return db.get("contacts", cid)  # type: ignore[return-value]


@app.delete("/api/contacts/{cid}")
def contacts_delete(cid: int, _: Any = Depends(W)) -> dict:
    db.delete("contacts", cid)
    return {"ok": True}


# ---------------- integrations ----------------

@app.get("/api/integrations")
def integrations_get(_: Any = Depends(S)) -> dict:
    tok = db.aget("ics_token")
    if not tok:
        tok = secrets.token_urlsafe(18)
        db.aset("ics_token", tok)
    return {"notify": notify.public_config(), "events": notify.EVENTS,
            "ics_url": f"{settings.base_url.rstrip('/')}/calendar/{db.current_account()}/{tok}.ics",
            "csv_url": "/api/export/posts.csv", "whatsapp_webhook": f"{settings.base_url.rstrip('/')}/webhooks/whatsapp"}


@app.post("/api/integrations")
def integrations_save(data: dict = Body(...), _: Any = Depends(S)) -> dict:
    return notify.save_config(data)


@app.post("/api/integrations/test")
def integrations_test(_: Any = Depends(S)) -> dict:
    notify.emit("approved", None, "Test message from LinkedIn Agent ✅")
    return {"ok": True}


@app.get("/calendar/{aid}/{token}.ics")
def calendar_ics(aid: int, token: str) -> Response:
    with db.use_account(aid):
        if not secrets.compare_digest(db.aget("ics_token") or "-", token):
            raise HTTPException(404)
        rows = db.list_rows("posts", "status IN ('scheduled','approved','published')", limit=500)
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//LinkedIn Agent//EN", "X-WR-CALNAME:LinkedIn posts"]
    for p in rows:
        when = p.get("scheduled_at") or p.get("published_at")
        if not when:
            continue
        try:
            dt = datetime.fromisoformat(str(when).replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            continue
        summ = p["content"].splitlines()[0][:70].replace(",", "\\,").replace(";", "\\;")
        desc = p["content"][:900].replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")
        lines += ["BEGIN:VEVENT", f"UID:post-{aid}-{p['id']}@linkedin-agent", f"DTSTAMP:{dt:%Y%m%dT%H%M%SZ}",
                  f"DTSTART:{dt:%Y%m%dT%H%M%SZ}", f"DTEND:{(dt + timedelta(minutes=15)):%Y%m%dT%H%M%SZ}",
                  f"SUMMARY:[{p['status']}] {summ}", f"DESCRIPTION:{desc}", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return Response("\r\n".join(lines), media_type="text/calendar")


@app.get("/api/export/posts.csv")
def export_csv(_: Any = Depends(R)) -> Response:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "status", "pillar", "hook", "scheduled_at", "published_at", "url", "impressions", "reactions", "comments", "reposts", "content"])
    for p in db.list_rows("posts", limit=5000):
        m = p.get("metrics") or {}
        w.writerow([p["id"], p["status"], p.get("pillar"), p.get("hook_type"), p.get("scheduled_at"), p.get("published_at"),
                    publisher.post_url(p.get("linkedin_urn")), m.get("impressions"), m.get("reactions"), m.get("comments"), m.get("reposts"), p["content"]])
    return Response(buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="linkedin-posts.csv"'})


# ---------------- schedule, analytics, dashboard ----------------

@app.get("/api/schedule")
def schedule_get(_: Any = Depends(R)) -> dict:
    return publisher.get_schedule()


@app.post("/api/schedule")
def schedule_save(data: dict = Body(...), _: Any = Depends(S)) -> dict:
    return publisher.save_schedule(data)


@app.get("/api/analytics")
def analytics_get(_: Any = Depends(R)) -> dict:
    return analytics.overview()


@app.get("/api/dashboard")
def dashboard(_: Any = Depends(R)) -> dict[str, Any]:
    posts = db.list_rows("posts", limit=2000)
    cnt = lambda s: sum(1 for p in posts if p["status"] == s)  # noqa: E731
    published = [p for p in posts if p["status"] == "published"]
    impressions = sum(int((p.get("metrics") or {}).get("impressions") or 0) for p in published)
    eng = sum(int((p.get("metrics") or {}).get(k) or 0) for p in published for k in ("reactions", "comments", "reposts"))
    upcoming = sorted([p for p in posts if p["status"] == "scheduled"], key=lambda p: p.get("scheduled_at") or "")[:3]
    return {
        "drafts": cnt("draft"), "approved": cnt("approved") + cnt("scheduled"), "published": len(published), "failed": cnt("failed"),
        "impressions": impressions, "engagement_rate": round(100 * eng / impressions, 2) if impressions else None,
        "stories": db.count("stories"), "documents": db.count("documents"), "media": db.count("media"),
        "linkedin": linkedin.status(), "llm": llm.load_config().public(),
        "brand_complete": sum(1 for v in skills.get_brand().values() if v), "schedule": publisher.get_schedule(),
        "persona": db.aget("persona"), "upcoming": [_decorate(p) for p in upcoming],
        "recent_drafts": [_decorate(p) for p in posts if p["status"] == "draft"][:3],
        "best_slots": analytics.overview()["best_slots"],
    }
