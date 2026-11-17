"""Analytics from the metrics you import or enter: totals, best posting times, top posts."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from . import db

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _rate(m: dict) -> float | None:
    imp = int(m.get("impressions") or 0)
    if not imp:
        return None
    eng = int(m.get("reactions") or 0) + int(m.get("comments") or 0) + int(m.get("reposts") or 0)
    return 100 * eng / imp


def overview() -> dict:
    posts = [p for p in db.list_rows("posts", "status='published'", limit=2000) if p.get("metrics")]
    heat: dict[tuple[int, int], list[float]] = defaultdict(list)
    by_hook: dict[str, list[float]] = defaultdict(list)
    by_pillar: dict[str, list[float]] = defaultdict(list)
    series: dict[str, dict[str, int]] = defaultdict(lambda: {"impressions": 0, "engagements": 0})
    for p in posts:
        m, r = p["metrics"], _rate(p["metrics"])
        try:
            dt = datetime.fromisoformat(str(p.get("published_at") or "").replace("Z", "+00:00"))
        except ValueError:
            dt = None
        if dt:
            week = dt.strftime("%G-W%V")
            series[week]["impressions"] += int(m.get("impressions") or 0)
            series[week]["engagements"] += int(m.get("reactions") or 0) + int(m.get("comments") or 0) + int(m.get("reposts") or 0)
        if r is None:
            continue
        if dt:
            heat[(dt.weekday(), dt.hour // 3)].append(r)
        if p.get("hook_type"):
            by_hook[p["hook_type"]].append(r)
        if p.get("pillar"):
            by_pillar[p["pillar"]].append(r)
    avg = lambda xs: round(sum(xs) / len(xs), 2) if xs else None  # noqa: E731
    grid = [[avg(heat.get((d, b), [])) for b in range(8)] for d in range(7)]
    best = sorted(((v, d, b) for d, row in enumerate(grid) for b, v in enumerate(row) if v is not None), reverse=True)[:3]
    top = sorted(posts, key=lambda p: _rate(p["metrics"]) or 0, reverse=True)[:5]
    return {
        "posts_with_metrics": len(posts),
        "heatmap": {"days": DAYS, "buckets": [f"{b*3:02d}-{b*3+3:02d}h" for b in range(8)], "grid": grid},
        "best_slots": [{"day": DAYS[d], "hours": f"{b*3:02d}:00-{b*3+3:02d}:00", "rate": v} for v, d, b in best],
        "by_hook": sorted(({"name": k, "rate": avg(v), "n": len(v)} for k, v in by_hook.items()), key=lambda x: -(x["rate"] or 0)),
        "by_pillar": sorted(({"name": k, "rate": avg(v), "n": len(v)} for k, v in by_pillar.items()), key=lambda x: -(x["rate"] or 0)),
        "weekly": [{"week": k, **v} for k, v in sorted(series.items())][-12:],
        "top_posts": [{"id": p["id"], "content": p["content"][:140], "rate": round(_rate(p["metrics"]) or 0, 2), **p["metrics"]} for p in top],
    }
