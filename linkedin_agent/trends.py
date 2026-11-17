"""RSS/Atom trend feeds per account (used by the Trend Ideas skill and daily post)."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

from . import db

ATOM = "{http://www.w3.org/2005/Atom}"


def get_feeds() -> list[str]:
    return db.aget("trend_feeds", []) or []


def set_feeds(feeds: list[str]) -> list[str]:
    clean = [f.strip() for f in feeds if f.strip().startswith(("http://", "https://"))]
    db.aset("trend_feeds", clean)
    return clean


def parse_feed(xml: bytes, source: str) -> list[dict]:
    root = ET.fromstring(xml)
    items = []
    for it in root.iter("item"):
        items.append({"title": (it.findtext("title") or "").strip(), "link": it.findtext("link"),
                      "summary": (it.findtext("description") or "")[:400], "published": it.findtext("pubDate"), "source": source})
    for it in root.iter(f"{ATOM}entry"):
        link = it.find(f"{ATOM}link")
        items.append({"title": (it.findtext(f"{ATOM}title") or "").strip(), "link": link.get("href") if link is not None else None,
                      "summary": (it.findtext(f"{ATOM}summary") or "")[:400], "published": it.findtext(f"{ATOM}updated"), "source": source})
    return [i for i in items if i["title"]]


def refresh(limit_per_feed: int = 8) -> dict:
    added, errors = 0, []
    seen = {t["title"] for t in db.list_rows("trends", limit=500)}
    for url in get_feeds():
        try:
            r = httpx.get(url, timeout=20, follow_redirects=True, headers={"user-agent": "LinkedInAgent/2"})
            r.raise_for_status()
            source = url.split("/")[2]
            for item in parse_feed(r.content, source)[:limit_per_feed]:
                if item["title"] not in seen:
                    db.insert("trends", **item)
                    seen.add(item["title"])
                    added += 1
        except Exception as e:  # noqa: BLE001
            errors.append(f"{url}: {e}")
    # keep the table small
    rows = db.list_rows("trends", limit=1000)
    for old in rows[150:]:
        db.delete("trends", old["id"])
    return {"added": added, "errors": errors}
