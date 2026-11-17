"""Notifications and phone approvals.

Channels (configured per account in Settings → Integrations):
* Telegram — draft arrives with ✅ Approve / ✏️ Reject buttons; tapping them acts
  on the post (polling, so it works on localhost).
* WhatsApp — via the WhatsApp Cloud API: the draft is sent to your number; reply
  "APPROVE 12" / "REJECT 12" (webhook: /webhooks/whatsapp).
* Slack — incoming webhook message.
* Webhooks — JSON POST to any URL (Zapier, Make, n8n, Notion/Sheets automations).
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time

import httpx

from . import db

log = logging.getLogger("linkedin_agent")

EVENTS = ("draft_created", "approved", "scheduled", "published", "failed", "review_feedback")


def get_config() -> dict:
    return db.aget("notify", {}) or {}


def save_config(data: dict) -> dict:
    cur = get_config()
    for ch in ("telegram", "whatsapp", "slack"):
        if ch in data:
            merged = {**cur.get(ch, {}), **{k: v for k, v in data[ch].items() if v not in (None, "") or k == "enabled"}}
            cur[ch] = merged
    if "webhooks" in data:
        cur["webhooks"] = [u for u in data["webhooks"] if str(u).startswith(("http://", "https://"))]
    if "events" in data:
        cur["events"] = [e for e in data["events"] if e in EVENTS]
    db.aset("notify", cur, secret=True)
    return public_config()


def public_config() -> dict:
    cfg = get_config()
    mask = lambda s: ("•" * 6 + str(s)[-4:]) if s else ""  # noqa: E731
    out = {k: dict(v) for k, v in cfg.items() if isinstance(v, dict)}
    for ch, key in (("telegram", "bot_token"), ("whatsapp", "access_token")):
        if out.get(ch, {}).get(key):
            out[ch][key] = mask(out[ch][key])
    out["webhooks"] = cfg.get("webhooks", [])
    out["events"] = cfg.get("events", list(EVENTS))
    return out


def review_url(post_id: int) -> str:
    from .config import settings

    return f"{settings.base_url.rstrip('/')}/review/{sign_review(post_id)}"


def sign_review(post_id: int, days: int = 14) -> str:
    exp = int(time.time()) + days * 86400
    payload = f"{db.current_account()}.{post_id}.{exp}"
    sig = hmac.new(db.secret_key(), payload.encode(), hashlib.sha256).hexdigest()[:24]
    return f"{payload}.{sig}"


def verify_review(token: str) -> tuple[int, int]:
    try:
        acct, pid, exp, sig = token.split(".")
    except ValueError as e:
        raise PermissionError("Invalid review link") from e
    good = hmac.new(db.secret_key(), f"{acct}.{pid}.{exp}".encode(), hashlib.sha256).hexdigest()[:24]
    if not hmac.compare_digest(good, sig) or int(exp) < time.time():
        raise PermissionError("Review link is invalid or expired")
    return int(acct), int(pid)


def emit(event: str, post: dict | None = None, extra: str = "") -> None:
    """Fire an event to all configured channels. Never raises."""
    cfg = get_config()
    if event not in cfg.get("events", EVENTS):
        return
    text = _format(event, post, extra)
    try:
        tg = cfg.get("telegram", {})
        if tg.get("enabled") and tg.get("bot_token") and tg.get("chat_id"):
            markup = None
            if event == "draft_created" and post:
                markup = {"inline_keyboard": [[{"text": "✅ Approve", "callback_data": f"approve:{db.current_account()}:{post['id']}"},
                                               {"text": "✏️ Reject", "callback_data": f"reject:{db.current_account()}:{post['id']}"}]]}
            telegram_send(tg["bot_token"], tg["chat_id"], text, markup)
        wa = cfg.get("whatsapp", {})
        if wa.get("enabled") and wa.get("access_token") and wa.get("phone_number_id") and wa.get("to"):
            wa_text = text + (f"\n\nReply APPROVE {post['id']} or REJECT {post['id']}" if event == "draft_created" and post else "")
            httpx.post(f"https://graph.facebook.com/v21.0/{wa['phone_number_id']}/messages",
                       headers={"authorization": f"Bearer {wa['access_token']}"},
                       json={"messaging_product": "whatsapp", "to": wa["to"], "type": "text", "text": {"body": wa_text[:4000]}}, timeout=20)
        sl = cfg.get("slack", {})
        if sl.get("enabled") and sl.get("webhook_url"):
            httpx.post(sl["webhook_url"], json={"text": text}, timeout=15)
        for url in cfg.get("webhooks", []):
            httpx.post(url, json={"event": event, "account_id": db.current_account(), "post": post, "message": text}, timeout=15)
    except Exception as e:  # noqa: BLE001
        log.warning("notification failed: %s", e)


def _format(event: str, post: dict | None, extra: str) -> str:
    head = {"draft_created": "📝 New LinkedIn draft ready for review", "approved": "✅ Post approved",
            "scheduled": "🗓 Post scheduled", "published": "🚀 Post published", "failed": "⚠️ Publishing failed",
            "review_feedback": "💬 Reviewer feedback"}[event]
    if not post:
        return f"{head}\n{extra}".strip()
    body = post.get("content", "")
    if len(body) > 900:
        body = body[:900] + "…"
    lines = [f"{head} (#{post['id']})", "", body]
    if extra:
        lines += ["", extra]
    if event == "draft_created":
        lines += ["", f"Review: {review_url(post['id'])}"]
    return "\n".join(lines)


def telegram_send(token: str, chat_id: str, text: str, markup: dict | None = None) -> None:
    payload: dict = {"chat_id": chat_id, "text": text[:4000], "disable_web_page_preview": True}
    if markup:
        payload["reply_markup"] = markup
    httpx.post(f"https://api.telegram.org/bot{token}/sendMessage", json=payload, timeout=20)


def poll_telegram() -> int:
    """Process Approve/Reject button taps for every account with Telegram enabled."""
    from . import publisher

    handled = 0
    for acct in db.all_accounts():
        with db.use_account(acct["id"]):
            tg = get_config().get("telegram", {})
            if not (tg.get("enabled") and tg.get("bot_token")):
                continue
            offset = db.aget("tg_offset", 0)
            try:
                r = httpx.get(f"https://api.telegram.org/bot{tg['bot_token']}/getUpdates",
                              params={"offset": offset, "timeout": 0, "allowed_updates": '["callback_query"]'}, timeout=20)
                updates = r.json().get("result", [])
            except Exception as e:  # noqa: BLE001
                log.warning("telegram poll failed: %s", e)
                continue
            for u in updates:
                db.aset("tg_offset", u["update_id"] + 1)
                cq = u.get("callback_query")
                if not cq or str(cq.get("message", {}).get("chat", {}).get("id")) != str(tg.get("chat_id")):
                    continue
                action, a_id, pid = (cq.get("data") or "x:0:0").split(":")
                if int(a_id) != acct["id"]:
                    continue
                msg = handle_remote_action(action, int(pid))
                httpx.post(f"https://api.telegram.org/bot{tg['bot_token']}/answerCallbackQuery",
                           json={"callback_query_id": cq["id"], "text": msg}, timeout=15)
                handled += 1
    return handled


def handle_remote_action(action: str, post_id: int, note: str = "") -> str:
    from . import publisher

    try:
        if action == "approve":
            publisher.approve(post_id)
            return f"Post #{post_id} approved ✅"
        if action == "reject":
            db.update("posts", post_id, status="rejected", review_note=note or None)
            return f"Post #{post_id} rejected"
    except Exception as e:  # noqa: BLE001
        return f"Could not {action} #{post_id}: {e}"
    return "Unknown action"
