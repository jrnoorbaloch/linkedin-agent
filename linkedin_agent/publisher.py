"""Approval-gated publishing and the daily scheduler."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from . import db, linkedin, skills

log = logging.getLogger("linkedin_agent")
_scheduler: BackgroundScheduler | None = None

DEFAULT_SCHEDULE = {
    "daily_draft_enabled": True,
    "daily_draft_time": "08:00",      # when the agent drafts today's post
    "timezone": "UTC",
    "auto_publish": False,             # if True, approved posts without a time go out at publish_time
    "publish_time": "10:00",
}


def get_schedule() -> dict:
    return {**DEFAULT_SCHEDULE, **(db.get_value("schedule", {}) or {})}


def save_schedule(data: dict) -> dict:
    sched = {**get_schedule(), **{k: v for k, v in data.items() if k in DEFAULT_SCHEDULE}}
    db.set_value("schedule", sched)
    start_scheduler(restart=True)
    return sched


def approve(post_id: int, scheduled_at: str | None = None, content: str | None = None) -> dict:
    post = db.get("posts", post_id)
    if not post:
        raise KeyError(f"Post {post_id} not found")
    fields: dict = {"status": "scheduled" if scheduled_at else "approved", "scheduled_at": scheduled_at}
    if content is not None:
        fields["content"] = content
    db.update("posts", post_id, **fields)
    return db.get("posts", post_id)  # type: ignore[return-value]


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
        urn = linkedin.create_post(post["content"], author_urn=author)
        if post.get("first_comment") and urn:
            try:
                linkedin.create_comment(urn, post["first_comment"], actor_urn=author)
            except linkedin.LinkedInError as e:  # post is live; comment failure is non-fatal
                log.warning("first comment failed: %s", e)
        db.update("posts", post_id, status="published", linkedin_urn=urn,
                  published_at=db.now(), error=None)
    except Exception as e:  # noqa: BLE001
        db.update("posts", post_id, status="failed", error=str(e)[:500])
        raise
    return db.get("posts", post_id)  # type: ignore[return-value]


def post_url(urn: str | None) -> str | None:
    return f"https://www.linkedin.com/feed/update/{urn}/" if urn else None


# ---------------- background jobs ----------------

def job_daily_draft() -> None:
    try:
        res = skills.run("daily_post", {})
        log.info("Daily draft created: post #%s", res.get("post_id"))
    except Exception as e:  # noqa: BLE001
        log.error("Daily draft failed: %s", e)


def job_publish_due() -> None:
    now = datetime.now(timezone.utc).isoformat()
    for p in db.list_rows("posts", "status='scheduled' AND scheduled_at <= ?", (now,), order="scheduled_at ASC"):
        try:
            publish(p["id"])
            log.info("Published scheduled post #%s", p["id"])
        except Exception as e:  # noqa: BLE001
            log.error("Publishing #%s failed: %s", p["id"], e)


def job_auto_publish() -> None:
    if not get_schedule().get("auto_publish"):
        return
    approved = db.list_rows("posts", "status='approved'", order="id ASC", limit=1)
    if approved:
        try:
            publish(approved[0]["id"])
        except Exception as e:  # noqa: BLE001
            log.error("Auto-publish failed: %s", e)


def start_scheduler(restart: bool = False) -> BackgroundScheduler:
    global _scheduler
    if _scheduler and restart:
        _scheduler.shutdown(wait=False)
        _scheduler = None
    if _scheduler:
        return _scheduler
    s = get_schedule()
    tz = s.get("timezone") or "UTC"
    sch = BackgroundScheduler(timezone=tz)
    if s.get("daily_draft_enabled"):
        h, m = (s.get("daily_draft_time") or "08:00").split(":")
        sch.add_job(job_daily_draft, CronTrigger(hour=int(h), minute=int(m), timezone=tz), id="daily_draft")
    ph, pm = (s.get("publish_time") or "10:00").split(":")
    sch.add_job(job_auto_publish, CronTrigger(hour=int(ph), minute=int(pm), timezone=tz), id="auto_publish")
    sch.add_job(job_publish_due, "interval", minutes=1, id="publish_due")
    sch.start()
    _scheduler = sch
    return sch
