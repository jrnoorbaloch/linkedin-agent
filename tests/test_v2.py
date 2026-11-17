import base64
import io
import os
import tempfile
import zipfile

os.environ.setdefault("LA_DATA_DIR", tempfile.mkdtemp())
os.environ["LA_DISABLE_SCHEDULER"] = "1"

from fastapi.testclient import TestClient  # noqa: E402

from linkedin_agent import db, linkedin, llm, media, notify  # noqa: E402
from linkedin_agent.server import app  # noqa: E402


def fake_complete(system, user, **kw):
    return "HOOK: contrarian\n---\nA post body.\n---\nFIRST COMMENT: link"


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def make_export() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("Profile.csv", "First Name,Last Name,Headline,Summary,Industry,Geo Location\nNoor,Baloch,Growth Engineer,I build things,Software,Karachi\n")
        z.writestr("Positions.csv", "Company Name,Title,Description,Location,Started On,Finished On\nAcme,Engineer,Shipped stuff,Karachi,Jan 2022,\n")
        z.writestr("Skills.csv", "Name\nPython\nGrowth\n")
        z.writestr("Shares.csv", 'Date,ShareLink,ShareCommentary,SharedUrl,MediaUrl,Visibility\n2025-03-01 09:00:00,https://www.linkedin.com/feed/update/urn%3Ali%3Ashare%3A123,"My first imported post, with a comma",,,PUBLIC\n')
    return buf.getvalue()


def test_import_packs_carousel_and_isolation(monkeypatch):
    monkeypatch.setattr(llm, "complete", fake_complete)
    with TestClient(app) as c:
        aid = c.post("/api/accounts", json={"name": "Import test"}).json()["id"]
        c.headers.update({"x-account": str(aid)})
        r = c.post("/api/import/linkedin", json={"name": "export.zip", "content": b64(make_export())}).json()
        assert r["posts_imported"] == 1 and r["brand"]["name"] == "Noor Baloch"
        assert "Python" in r["brand"]["profile_text"]
        assert c.post("/api/packs/developer", json={}).json()["brand"]["pillars"].startswith("Things I built")
        # carousel pdf
        m = c.post("/api/media/carousel", json={"text": "Slide 1 — Big idea\nLine one\nSlide 2 — Step two\nDo this"}).json()
        assert m["kind"] == "pdf" and c.get(m["url"]).content[:4] == b"%PDF"
        # another workspace is isolated
        other = c.post("/api/accounts", json={"name": "Client B"}).json()["id"]
        assert c.get("/api/posts", headers={"x-account": str(other)}).json() == []
        assert len(c.get("/api/posts").json()) == 1
        # analytics import (CSV) matches the imported post by URN
        csv = "Post URL,Post publish date,Impressions,Reactions,Comments,Reposts\nhttps://www.linkedin.com/feed/update/urn:li:share:123,2025-03-01,1000,40,8,2\n"
        a = c.post("/api/import/analytics", json={"name": "a.csv", "content": b64(csv.encode())}).json()
        assert a["updated"] == 1
        ov = c.get("/api/analytics").json()
        assert ov["posts_with_metrics"] == 1 and ov["best_slots"]


def test_review_link_and_publish_with_media(monkeypatch):
    monkeypatch.setattr(llm, "complete", fake_complete)
    sent = {}
    monkeypatch.setattr(linkedin, "create_post", lambda text, author_urn=None, media=None: sent.update(media=media) or "urn:li:share:9")
    monkeypatch.setattr(linkedin, "create_comment", lambda *a, **k: None)
    with TestClient(app) as c:
        pid = c.post("/api/skills/post_writer", json={"topic": "x"}).json()["post_id"]
        img = c.post("/api/media/upload", json={"name": "a.png", "content": b64(b"\x89PNG\r\n\x1a\nfake")}).json()
        c.patch(f"/api/posts/{pid}", json={"media_id": img["id"]})
        url = c.post(f"/api/posts/{pid}/share").json()["url"]
        token = url.rsplit("/", 1)[-1]
        assert "Approve" in c.get(f"/review/{token}").text
        c.post(f"/review/{token}", content="action=approve&note=lgtm", headers={"content-type": "application/x-www-form-urlencoded"})
        assert db.get("posts", pid)["status"] == "approved"
        res = c.post(f"/api/posts/{pid}/publish").json()
        assert res["status"] == "published" and sent["media"]["kind"] == "image"
        # tampered token rejected
        assert c.get(f"/review/{token[:-2]}xx").status_code == 403


def test_team_roles():
    with TestClient(app) as c:
        assert c.post("/api/auth/setup", json={"name": "Admin", "email": "a@x.com", "password": "password123"}).status_code == 200
        c.post("/api/team", json={"name": "Ed", "email": "ed@x.com", "password": "password123", "role": "editor"})
    with TestClient(app) as anon:
        assert anon.get("/api/posts").status_code == 401
        anon.post("/api/auth/login", json={"email": "ed@x.com", "password": "password123"})
        pid = anon.post("/api/posts", json={"content": "editor draft"}).json()["id"]
        assert anon.post(f"/api/posts/{pid}/approve", json={}).status_code == 403   # editors can't approve
        assert anon.post("/api/llm", json={"provider": "openai"}).status_code == 403  # nor change settings
    # clean up so other tests run in single-user mode
    with db.connect() as conn:
        conn.execute("DELETE FROM users")
        conn.execute("DELETE FROM sessions")


def test_ics_and_trend_parser():
    with TestClient(app) as c:
        info = c.get("/api/integrations").json()
        path = "/" + info["ics_url"].split("/", 3)[3]
        assert c.get(path).text.startswith("BEGIN:VCALENDAR")
    from linkedin_agent import trends
    items = trends.parse_feed(b"<rss><channel><item><title>AI news</title><link>http://x</link></item></channel></rss>", "x")
    assert items[0]["title"] == "AI news"


def test_slides_parser():
    s = media.parse_slides("Slide 1 — Hello\nworld\nSlide 2: Next\nmore\nCaption: hi")
    assert [x["title"] for x in s] == ["Hello", "Next"]


def test_review_signature_roundtrip():
    tok = notify.sign_review(5)
    assert notify.verify_review(tok) == (1, 5)
