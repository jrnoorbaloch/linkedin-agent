"""Images and carousel PDFs.

* ``generate_image`` — calls any OpenAI-compatible Images API (OpenAI gpt-image-1 /
  dall-e-3, or a compatible gateway) with the user's own key.
* ``save_upload`` — store an image the user uploads (base64).
* ``render_carousel`` — turns Carousel Builder output into a 1080x1350 PDF
  document ready to post as a LinkedIn document (carousel) post.
"""

from __future__ import annotations

import base64
import re
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx

from . import db, skills
from .config import settings


def media_dir() -> Path:
    d = settings.data_dir / "media"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------- image generation ----------------

@dataclass
class ImageConfig:
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-image-1"
    api_key: str = ""
    size: str = "1024x1024"

    def public(self) -> dict:
        d = asdict(self)
        d["api_key"] = ("•" * 8 + self.api_key[-4:]) if self.api_key else ""
        return d


def load_image_config() -> ImageConfig:
    data = db.get_value("image_config")
    return ImageConfig(**data) if data else ImageConfig()


def save_image_config(base_url: str = "", model: str = "", api_key: str = "", size: str = "") -> ImageConfig:
    cur = load_image_config()
    cfg = ImageConfig(base_url=(base_url or cur.base_url).rstrip("/"), model=model or cur.model,
                      api_key=api_key or cur.api_key, size=size or cur.size)
    db.set_value("image_config", asdict(cfg), secret=True)
    return cfg


def generate_image(prompt: str, title: str = "") -> dict:
    cfg = load_image_config()
    if not cfg.api_key and "localhost" not in cfg.base_url:
        raise RuntimeError("No image model configured. Settings → Image model.")
    body = {"model": cfg.model, "prompt": prompt[:3900], "size": cfg.size, "n": 1}
    if cfg.model.startswith("dall-e"):
        body["response_format"] = "b64_json"
    r = httpx.post(f"{cfg.base_url}/images/generations", json=body,
                   headers={"authorization": f"Bearer {cfg.api_key}"}, timeout=180)
    if r.status_code != 200:
        raise RuntimeError(f"Image API returned {r.status_code}: {r.text[:300]}")
    item = r.json()["data"][0]
    if item.get("b64_json"):
        data = base64.b64decode(item["b64_json"])
    else:
        data = httpx.get(item["url"], timeout=60).content
    return _store(data, "png", "image", title or prompt[:80], prompt)


def save_upload(filename: str, b64: str, title: str = "") -> dict:
    data = base64.b64decode(b64.split(",", 1)[-1])
    ext = (filename.rsplit(".", 1)[-1] or "png").lower()
    kind = "pdf" if ext == "pdf" else "image"
    if kind == "image" and ext not in ("png", "jpg", "jpeg", "gif", "webp"):
        raise ValueError("Unsupported image type")
    return _store(data, ext, kind, title or filename)


def _store(data: bytes, ext: str, kind: str, title: str, prompt: str | None = None) -> dict:
    path = media_dir() / f"{uuid.uuid4().hex}.{ext}"
    path.write_bytes(data)
    mid = db.insert("media", kind=kind, title=title, path=str(path), prompt=prompt)
    return db.get("media", mid)  # type: ignore[return-value]


# ---------------- carousel PDF ----------------

THEMES = {
    "linkedin": {"bg": "#0a66c2", "bg2": "#004182", "fg": "#ffffff", "accent": "#9fd0ff"},
    "light": {"bg": "#ffffff", "bg2": "#eef3f8", "fg": "#16191c", "accent": "#0a66c2"},
    "dark": {"bg": "#111315", "bg2": "#1d2125", "fg": "#f2f4f6", "accent": "#f5b400"},
    "sunset": {"bg": "#ff5f6d", "bg2": "#ffc371", "fg": "#ffffff", "accent": "#2b2d42"},
    "forest": {"bg": "#0f3d2e", "bg2": "#1b5e45", "fg": "#f1f7f3", "accent": "#a7f3d0"},
}

_SLIDE = re.compile(r"^\s*\**\s*slide\s*(\d+)\s*\**\s*[—\-–:.]+\s*(.*)$", re.I)


def parse_slides(text: str) -> list[dict]:
    slides: list[dict] = []
    for line in text.splitlines():
        m = _SLIDE.match(line)
        if m:
            slides.append({"title": m.group(2).strip(" *#"), "body": []})
        elif slides and line.strip() and not line.strip().lower().startswith(("caption", "---")):
            slides[-1]["body"].append(line.strip(" *-•#"))
        elif slides and line.strip().lower().startswith(("caption", "---")):
            break
    if not slides:  # fall back: paragraphs become slides
        for para in [p for p in text.split("\n\n") if p.strip()][:12]:
            ls = para.strip().splitlines()
            slides.append({"title": ls[0].strip(" *#"), "body": [x.strip(" *-•") for x in ls[1:]]})
    return slides


def render_carousel(text: str, theme: str = "linkedin", title: str = "Carousel") -> dict:
    from reportlab.lib.colors import HexColor
    from reportlab.lib.utils import simpleSplit
    from reportlab.pdfgen import canvas

    t = THEMES.get(theme, THEMES["linkedin"])
    slides = parse_slides(text)
    if not slides:
        raise ValueError("No slides found. Use the Carousel Builder output ('Slide 1 — ...').")
    brand = skills.get_brand()
    handle = brand.get("name") or ""
    W, H = 1080, 1350
    path = media_dir() / f"{uuid.uuid4().hex}.pdf"
    c = canvas.Canvas(str(path), pagesize=(W, H))
    c.setTitle(title)
    n = len(slides)
    for i, s in enumerate(slides, 1):
        cover, last = i == 1, i == n
        bg = t["bg"] if (cover or last) else t["bg2"]
        c.setFillColor(HexColor(bg))
        c.rect(0, 0, W, H, stroke=0, fill=1)
        fg = HexColor(t["fg"])
        # accent bar
        c.setFillColor(HexColor(t["accent"]))
        c.rect(90, H - 150, 120, 14, stroke=0, fill=1)
        c.setFillColor(fg)
        size = 92 if cover else 72
        y = H - 260
        for ln in simpleSplit(s["title"], "Helvetica-Bold", size, W - 180)[:5]:
            c.setFont("Helvetica-Bold", size)
            c.drawString(90, y, ln)
            y -= size * 1.12
        y -= 40
        c.setFont("Helvetica", 40)
        for para in s["body"][:6]:
            for ln in simpleSplit(para, "Helvetica", 40, W - 180)[:4]:
                c.drawString(90, y, ln)
                y -= 56
            y -= 18
        c.setFont("Helvetica-Bold", 30)
        c.drawString(90, 90, handle)
        c.setFont("Helvetica", 30)
        c.drawRightString(W - 90, 90, f"{i}/{n}" + ("   →" if not last else ""))
        c.showPage()
    c.save()
    mid = db.insert("media", kind="pdf", title=title, path=str(path))
    return db.get("media", mid)  # type: ignore[return-value]
