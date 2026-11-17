"""Approval-gated publishing and the background scheduler (all workspaces)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from . import db, linkedin, notify, skills, trends

log = logging.getLogger("linkedin_agent")
_scheduler: BackgroundScheduler | None = None

DEFAULT_SCHEDULE = {
    "daily_draft_enabled": True,
    "daily_draft_time": "08:00",
    "timezone": "UTC",
    "auto_publish": False,
    "publish_time": "10:00",
    "post_days": [0, 1, 2, 3, 4],       # Mon-Fri
}


def get_schedule() -> dict:
    return {**DEFAULT_SCHEDULE, **(db.aget("schedule", {}) or {})}


def save_schedule(data: dict) -> dict:
    sched = {**get_schedule(), **{k: v for k, v in data.items() if k in DEFAULT_SCHEDULE}}
    db.aset("schedule", sched)
    start_scheduler(restart=True)
    return sched


def approve(post_id: int, scheduled_at: str | None = None, content: str | None = None) -> dict:
    post = db.get("posts", post_id)
    if not post:
        raise KeyError(f"Post {post_id} not found")
    if post["status"] == "published":
        raise PermissionError("Post is already published.")
    fields: dict = {"status": "scheduled" if scheduled_at else "approved", "scheduled_at": scheduled_at}
    if content is not None:
        fields["content"] = content
    db.update("posts", post_id, **fields)
    post = db.get("posts", post_id)
    notify.emit("scheduled" if scheduled_at else "approved", post)
    return post  # type: ignore[return-value]


def publish(post_id: int) -> dict:
    """Publish a post now. Only approved/scheduled posts can be published —
    the human approval step is enforced here, not just in the UI."""
    post = db.get("posts", post_id)
    if not post:
        raise KeyError(f"Post {post_id} not found")
    if post["status"] not in ("approved", "scheduled", "failed"):
        raise PermissionError("Post must be approved before publishing.")
    try:
        author = post.get("org_urn") if post["target"] == "organization" else None
        if post["target"] == "organization" and not author:
            raise linkedin.LinkedInError("Choose which Company Page to publish to.")
        media = None
        if post.get("media_id"):
            m = db.get("media", post["media_id"])
            if m and Path(m["path"]).exists():
                media = {"kind": m["kind"], "path": m["path"], "title": m.get("title")}
        urn = linkedin.create_post(post["content"], author_urn=author, media=media)
        if post.get("first_comment") and urn:
            try:
                linkedin.create_comment(urn, post["first_comment"], actor_urn=author)
            except linkedin.LinkedInError as e:
                log.warning("first comment failed: %s", e)
        db.update("posts", post_id, status="published", linkedin_urn=urn, published_at=db.now(), error=None)
    except Exception as e:  # noqa: BLE001
        db.update("posts", post_id, status="failed", error=str(e)[:500])
        notify.emit("failed", db.get("posts", post_id), str(e)[:300])
        raise
    post = db.get("posts", post_id)
    notify.emit("published", post, post_url(post.get("linkedin_urn")) or "")  # type: ignore[union-attr]
    return post  # type: ignore[return-value]


def post_url(urn: str | None) -> str | None:
    return f"https://www.linkedin.com/feed/update/{urn}/" if urn else None


# ---------------- background jobs ----------------

def _each_account(fn) -> None:
    for acct in db.all_accounts():
        with db.use_account(acct["id"]):
            try:
                fn()
            except Exception as e:  # noqa: BLE001
                log.error("job %s failed for account %s: %s", fn.__name__, acct["id"], e)


def _local_now(tz: str) -> datetime:
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo(tz))
    except Exception:  # noqa: BLE001
        return datetime.now(timezone.utc)


def _daily_draft_for_account() -> None:
    s = get_schedule()
    if not s.get("daily_draft_enabled"):
        return
    now = _local_now(s.get("timezone") or "UTC")
    if now.weekday() not in s.get("post_days", [0, 1, 2, 3, 4]):
        return
    if now.strftime("%H:%M") != (s.get("daily_draft_time") or "08:00"):
        return
    if db.aget("last_daily_draft") == now.date().isoformat():
        return
    db.aset("last_daily_draft", now.date().isoformat())
    if trends.get_feeds():
        trends.refresh()
    res = skills.run("daily_post", {})
    log.info("Daily draft created: post #%s (account %s)", res.get("post_id"), db.current_account())


def _auto_publish_for_account() -> None:
    s = get_schedule()
    if not s.get("auto_publish"):
        return
    now = _local_now(s.get("timezone") or "UTC")
    if now.strftime("%H:%M") != (s.get("publish_time") or "10:00") or db.aget("last_auto_publish") == now.date().isoformat():
        return
    db.aset("last_auto_publish", now.date().isoformat())
    approved = db.list_rows("posts", "status='approved'", order="id ASC", limit=1)
    if approved:
        publish(approved[0]["id"])


def _publish_due_for_account() -> None:
    now = datetime.now(timezone.utc).isoformat()
    for p in db.list_rows("posts", "status='scheduled' AND scheduled_at <= ?", (now,), order="scheduled_at ASC"):
        publish(p["id"])


def job_minutely() -> None:
    _each_account(_publish_due_for_account)
    _each_account(_daily_draft_for_account)
    _each_account(_auto_publish_for_account)


def job_telegram() -> None:
    try:
        notify.poll_telegram()
    except Exception as e:  # noqa: BLE001
        log.warning("telegram poll error: %s", e)


def job_daily_draft() -> None:  # kept for API compatibility / manual trigger
    skills.run("daily_post", {})


def start_scheduler(restart: bool = False) -> BackgroundScheduler:
    global _scheduler
    if _scheduler and restart:
        return _scheduler  # schedules are evaluated every minute from settings; nothing to rebuild
    if _scheduler:
        return _scheduler
    sch = BackgroundScheduler(timezone="UTC")
    sch.add_job(job_minutely, CronTrigger(second=5), id="minutely", max_instances=1, coalesce=True)
    sch.add_job(job_telegram, "interval", seconds=15, id="telegram", max_instances=1, coalesce=True)
    sch.start()
    _scheduler = sch
    return sch
