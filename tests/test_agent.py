import os
import tempfile

os.environ.setdefault("LA_DATA_DIR", tempfile.mkdtemp())
os.environ["LA_DISABLE_SCHEDULER"] = "1"

from fastapi.testclient import TestClient  # noqa: E402

from linkedin_agent import db, linkedin, llm, skills  # noqa: E402
from linkedin_agent.server import app  # noqa: E402


def fake_complete(system, user, **kw):
    assert "USER BRAND PROFILE" in system
    return "HOOK: contrarian\n---\nMost advice about hiring is wrong.\n\nHere's what worked.\n---\nFIRST COMMENT: Link: https://example.com"


def test_registry_has_unique_ids():
    ids = [s.id for s in skills.SKILLS]
    assert len(ids) == len(set(ids)) and len(ids) >= 25


def test_parse_post():
    p = skills.parse_post(fake_complete("USER BRAND PROFILE", ""))
    assert p["hook"] == "contrarian"
    assert p["post"].startswith("Most advice")
    assert p["first_comment"].startswith("Link")


def test_little_text_escaping():
    out = linkedin.escape_little_text("Hello (world) #AI and @me")
    assert "\\(" in out and "{hashtag|\\#|AI}" in out and "\\@" in out


def test_secrets_encrypted():
    db.init()
    llm.save_config("openai", api_key="sk-secret-1234")
    with db.connect() as c:
        raw = c.execute("SELECT value FROM kv WHERE key='llm_config'").fetchone()[0]
    assert "sk-secret" not in raw
    assert llm.load_config().api_key == "sk-secret-1234"
    assert llm.load_config().public()["api_key"].endswith("1234")


def test_api_flow(monkeypatch):
    monkeypatch.setattr(llm, "complete", fake_complete)
    published = {}
    monkeypatch.setattr(linkedin, "create_post", lambda text, author_urn=None, media=None: published.setdefault("urn", "urn:li:share:1"))
    monkeypatch.setattr(linkedin, "create_comment", lambda *a, **k: None)
    with TestClient(app) as c:
        assert c.get("/api/health").json()["ok"]
        assert c.post("/api/brand", json={"name": "Noor", "pillars": "AI, careers"}).status_code == 200
        r = c.post("/api/skills/post_writer", json={"topic": "hiring"}).json()
        pid = r["post_id"]
        # publishing before approval is refused
        assert c.post(f"/api/posts/{pid}/publish").status_code == 403
        assert c.post(f"/api/posts/{pid}/approve", json={}).json()["status"] == "approved"
        res = c.post(f"/api/posts/{pid}/publish").json()
        assert res["status"] == "published" and res["url"].endswith("urn:li:share:1/")
        assert c.post("/api/skills/post_writer", json={}).status_code == 400  # missing topic
        d = c.post("/api/skills/resume_builder", json={"target_role": "PM"}).json()
        assert c.get(f"/api/documents/{d['document_id']}/docx").status_code == 200
        assert c.get("/api/dashboard").json()["published"] == 1
        assert "<title>LinkedIn Agent</title>" in c.get("/").text


def test_mcp_tools_registered():
    from linkedin_agent import mcp_server
    import asyncio
    tools = asyncio.run(mcp_server.mcp.list_tools())
    names = {t.name for t in tools}
    assert {"run_skill", "approve_post", "publish_post", "get_skill_prompt"} <= names
