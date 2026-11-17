"""Import from LinkedIn's own data export and analytics export.

1. Profile & history — LinkedIn → Settings → Data privacy → "Get a copy of your data".
   Upload the ZIP (or individual CSVs). We read Profile, Positions, Skills,
   Education, Certifications and Shares, then build the brand profile, the
   profile text used by Profile Optimizer / Resume Builder, voice samples, and
   your post history.
2. Analytics — LinkedIn → your posts → Analytics → Export (XLSX/CSV). We match
   rows to posts by URL/URN (or create history rows) and store the metrics.
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
from typing import Any

from . import db, skills


def _read_csv(data: bytes) -> list[dict[str, str]]:
    text = data.decode("utf-8-sig", errors="replace")
    lines = text.splitlines()
    # Some LinkedIn CSVs start with "Notes:" preamble lines — skip until a header with commas.
    start = 0
    for i, line in enumerate(lines[:10]):
        if line.count(",") >= 1 and not line.lower().startswith("notes"):
            start = i
            break
    return list(csv.DictReader(io.StringIO("\n".join(lines[start:]))))


def _files_from_upload(name: str, data: bytes) -> dict[str, bytes]:
    if name.lower().endswith(".zip") or data[:2] == b"PK" and not name.lower().endswith(".xlsx"):
        out = {}
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for info in z.infolist():
                if info.filename.lower().endswith(".csv"):
                    out[info.filename.split("/")[-1]] = z.read(info)
        return out
    return {name.split("/")[-1]: data}


def import_linkedin_export(files: list[tuple[str, bytes]]) -> dict[str, Any]:
    found: dict[str, bytes] = {}
    for name, data in files:
        found.update(_files_from_upload(name, data))
    get = lambda key: next((v for k, v in found.items() if k.lower().startswith(key.lower())), None)  # noqa: E731

    brand = skills.get_brand()
    summary: dict[str, Any] = {"files": sorted(found), "posts_imported": 0}
    lines: list[str] = []

    if (raw := get("Profile.csv")) and (rows := _read_csv(raw)):
        p = rows[0]
        name = f"{p.get('First Name', '')} {p.get('Last Name', '')}".strip()
        brand["name"] = brand.get("name") or name
        brand["role"] = brand.get("role") or p.get("Headline", "")
        brand["industry"] = brand.get("industry") or p.get("Industry", "")
        lines += [f"Name: {name}", f"Headline: {p.get('Headline', '')}", f"Location: {p.get('Geo Location', '')}",
                  f"Industry: {p.get('Industry', '')}", "", "About:", p.get("Summary", "")]
        summary["profile"] = True

    if (raw := get("Positions.csv")) and (rows := _read_csv(raw)):
        lines += ["", "Experience:"]
        for r in rows:
            lines.append(f"- {r.get('Title', '')} at {r.get('Company Name', '')} ({r.get('Started On', '')} – {r.get('Finished On', '') or 'present'})")
            if r.get("Description"):
                lines.append("  " + r["Description"].replace("\n", " ")[:600])
        summary["positions"] = len(rows)

    if (raw := get("Education.csv")) and (rows := _read_csv(raw)):
        lines += ["", "Education:"] + [f"- {r.get('Degree Name', '')} {r.get('Notes', '')}, {r.get('School Name', '')} ({r.get('Start Date', '')}–{r.get('End Date', '')})" for r in rows]

    if (raw := get("Certifications.csv")) and (rows := _read_csv(raw)):
        lines += ["", "Certifications:"] + [f"- {r.get('Name', '')} ({r.get('Authority', '')})" for r in rows]

    if (raw := get("Skills.csv")) and (rows := _read_csv(raw)):
        lines += ["", "Skills: " + ", ".join(r.get("Name", "") for r in rows if r.get("Name"))]
        summary["skills"] = len(rows)

    if lines:
        brand["profile_text"] = "\n".join(lines).strip()

    if (raw := get("Shares.csv")) and (rows := _read_csv(raw)):
        texts = []
        existing = {p["content"][:200] for p in db.list_rows("posts", limit=5000)}
        for r in rows:
            text = (r.get("ShareCommentary") or "").replace('""', '"').strip().strip('"')
            if not text or text[:200] in existing:
                continue
            date = (r.get("Date") or "").replace(" ", "T")
            db.insert("posts", content=text, status="published", published_at=date or None, source="import",
                      linkedin_urn=_urn_from_url(r.get("ShareLink", "")))
            texts.append(text)
            summary["posts_imported"] += 1
        if texts and not brand.get("sample_posts"):
            longest = sorted(texts[:30], key=len, reverse=True)[:3]
            brand["sample_posts"] = "\n\n---\n\n".join(longest)

    skills.save_brand(brand)
    summary["brand"] = brand
    return summary


_URN = re.compile(r"(urn:li:(?:activity|share|ugcPost):\d+)")


def _urn_from_url(url: str) -> str | None:
    from urllib.parse import unquote

    url = unquote(url or "")
    m = _URN.search(url)
    if m:
        return m.group(1)
    m = re.search(r"activity-(\d+)", url or "")
    return f"urn:li:activity:{m.group(1)}" if m else None


def import_analytics(name: str, data: bytes) -> dict[str, Any]:
    """Accepts LinkedIn's post-analytics export (XLSX) or any CSV with similar columns."""
    rows: list[dict[str, Any]] = []
    if name.lower().endswith(".xlsx"):
        import openpyxl

        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        for ws in wb.worksheets:
            grid = [list(r) for r in ws.iter_rows(values_only=True)]
            hdr_i = next((i for i, r in enumerate(grid[:15]) if r and any(isinstance(c, str) and "url" in c.lower() for c in r)), None)
            if hdr_i is None:
                continue
            hdr = [str(c or "").strip() for c in grid[hdr_i]]
            for r in grid[hdr_i + 1:]:
                if r and any(r):
                    rows.append(dict(zip(hdr, r)))
            if rows:
                break
    else:
        rows = _read_csv(data)

    def pick(row: dict, *words: str) -> Any:
        for k, v in row.items():
            if k and all(w in str(k).lower() for w in words):
                return v
        return None

    updated = created = 0
    posts = db.list_rows("posts", limit=5000)
    by_urn = {p["linkedin_urn"].split(":")[-1]: p for p in posts if p.get("linkedin_urn")}
    for r in rows:
        url = str(pick(r, "url") or "")
        urn = _urn_from_url(url)
        num = lambda *w: int(float(pick(r, *w) or 0))  # noqa: E731
        metrics = {"impressions": num("impression"), "reactions": num("reaction") or num("engagement"),
                   "comments": num("comment"), "reposts": num("repost") or num("share")}
        target = by_urn.get(urn.split(":")[-1]) if urn else None
        if target:
            db.update("posts", target["id"], metrics=metrics)
            updated += 1
        elif url:
            date = pick(r, "date")
            db.insert("posts", content=f"(imported from analytics) {url}", status="published", source="import",
                      linkedin_urn=urn, published_at=str(date) if date else None, metrics=metrics)
            created += 1
    return {"rows": len(rows), "updated": updated, "created": created}
