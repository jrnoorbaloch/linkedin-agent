"""MCP server — lets Claude, Cursor or any MCP-capable LLM drive the agent.

Run:  linkedin-agent mcp            (stdio, for Claude Desktop / Claude Code)
      linkedin-agent mcp --http     (streamable HTTP on :8788)

Publishing still requires an explicit approval step (approve_post) before
publish_post will succeed, so an LLM can never post without a human-visible
approval in the tool trail.
"""

from __future__ import annotations

import json
from typing import Any

from . import analytics, db, importer, linkedin, llm, media, personas, publisher, skills, trends
from .config import settings

try:  # MCP Python SDK v2
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # MCP Python SDK v1
    from mcp.server.fastmcp import FastMCP as _Server  # type: ignore[no-redef]

INSTRUCTIONS = """LinkedIn Agent tools. Workflow for posts: run_skill (or draft_post) -> show the draft to the user ->
only after the user explicitly approves, call approve_post -> publish_post (or schedule via approve_post scheduled_at).
Profile sections cannot be edited through LinkedIn's API: give the user the rewritten text to paste."""

mcp = _Server("linkedin-agent", instructions=INSTRUCTIONS)


def _j(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, default=str)


@mcp.tool()
def status() -> str:
    """Show LinkedIn connection, configured LLM, brand-profile completeness and post counts."""
    db.init()
    posts = db.list_rows("posts", limit=500)
    return _j({
        "linkedin": linkedin.status(),
        "llm": llm.load_config().public(),
        "brand_profile": skills.get_brand(),
        "posts": {s: sum(1 for p in posts if p["status"] == s) for s in ("draft", "approved", "scheduled", "published", "failed")},
    })


@mcp.tool()
def list_skills() -> str:
    """List every LinkedIn skill (id, category, description, input fields)."""
    return _j(skills.list_skills())


@mcp.tool()
def run_skill(skill_id: str, inputs: dict[str, Any] | None = None) -> str:
    """Run a skill with the agent's configured LLM (e.g. post_writer, profile_optimizer, resume_builder,
    job_match, comment_drafter, content_planner). Post outputs are saved as drafts and return post_id."""
    db.init()
    return _j(skills.run(skill_id, inputs or {}))


@mcp.tool()
def get_skill_prompt(skill_id: str, inputs: dict[str, Any] | None = None) -> str:
    """Return the system + user prompt for a skill WITHOUT calling the agent's LLM, so the calling model
    (e.g. Claude) can write the content itself. Save the result with save_draft."""
    db.init()
    system, user = skills.build_prompt(skill_id, inputs or {})
    return _j({"system": system, "user": user})


@mcp.tool()
def save_draft(content: str, first_comment: str = "", pillar: str = "", target: str = "member", org_urn: str = "") -> str:
    """Save a post you wrote as a draft in the approval queue."""
    db.init()
    pid = db.insert("posts", content=content, first_comment=first_comment or None, pillar=pillar or None,
                    target=target, org_urn=org_urn or None, status="draft")
    return _j(db.get("posts", pid))


@mcp.tool()
def list_posts(status: str = "") -> str:
    """List posts, optionally filtered by status: draft, approved, scheduled, published, failed, rejected."""
    db.init()
    rows = db.list_rows("posts", "status=?", (status,)) if status else db.list_rows("posts", limit=50)
    return _j(rows)


@mcp.tool()
def approve_post(post_id: int, scheduled_at: str = "", content: str = "") -> str:
    """Approve a draft (ONLY after the user explicitly said yes). Optional ISO-8601 UTC scheduled_at to schedule it,
    optional content to replace the text with the user's final edit."""
    db.init()
    return _j(publisher.approve(post_id, scheduled_at or None, content or None))


@mcp.tool()
def publish_post(post_id: int) -> str:
    """Publish an approved post to LinkedIn now. Returns the live URL."""
    db.init()
    post = publisher.publish(post_id)
    post["url"] = publisher.post_url(post.get("linkedin_urn"))
    return _j(post)


@mcp.tool()
def record_metrics(post_id: int, impressions: int = 0, reactions: int = 0, comments: int = 0, reposts: int = 0) -> str:
    """Store analytics for a published post (copied from LinkedIn), used by weekly_report and the daily planner."""
    db.init()
    db.update("posts", post_id, metrics={"impressions": impressions, "reactions": reactions, "comments": comments, "reposts": reposts})
    return _j(db.get("posts", post_id))


@mcp.tool()
def get_brand_profile() -> str:
    """Read the user's brand profile (voice, audience, pillars, profile text)."""
    db.init()
    return _j(skills.get_brand())


@mcp.tool()
def update_brand_profile(fields: dict[str, str]) -> str:
    """Update brand-profile fields: name, role, industry, audience, offer, pillars, tone, language, goals, avoid,
    sample_posts, profile_text."""
    db.init()
    merged = {**skills.get_brand(), **fields}
    return _j(skills.save_brand(merged))


@mcp.tool()
def add_story(title: str, body: str, tags: str = "") -> str:
    """Add a real experience to the Story Bank (raw material for future posts)."""
    db.init()
    return _j(db.get("stories", skills.add_story(title, body, tags)))


@mcp.tool()
def list_documents(kind: str = "") -> str:
    """List saved documents (resume, cover_letter, profile, plan, note)."""
    db.init()
    return _j(db.list_rows("documents", "kind=?", (kind,)) if kind else db.list_rows("documents", limit=30))


@mcp.tool()
def save_document(kind: str, title: str, content: str) -> str:
    """Save a Markdown document (e.g. a resume you wrote) so the user can export it to DOCX from the portal."""
    db.init()
    return _j(db.get("documents", db.insert("documents", kind=kind, title=title, content=content)))


@mcp.tool()
def list_workspaces() -> str:
    """List workspaces (LinkedIn accounts/clients). Pass workspace_id to switch_workspace to act on another one."""
    db.init()
    return _j(db.all_accounts())


@mcp.tool()
def switch_workspace(workspace_id: int) -> str:
    """Switch the active workspace for the following tool calls."""
    db.init()
    if workspace_id not in {a["id"] for a in db.all_accounts()}:
        return "Unknown workspace"
    db.set_account(workspace_id)
    return f"Active workspace: {workspace_id}"


@mcp.tool()
def list_persona_packs() -> str:
    """Persona packs (student, job seeker, developer, freelancer, sales, founder, professional, recruiter)."""
    return _j(personas.list_packs())


@mcp.tool()
def apply_persona_pack(pack_id: str, overwrite: bool = False) -> str:
    """Apply a persona pack: fills pillars/tone/goals and trend feeds for the active workspace."""
    db.init()
    return _j(personas.apply_pack(pack_id, overwrite))


@mcp.tool()
def import_linkedin_export(path: str) -> str:
    """Import LinkedIn's 'Get a copy of your data' ZIP (or a CSV) from a local file path: builds the brand profile,
    profile text, voice samples and post history."""
    db.init()
    from pathlib import Path
    p = Path(path).expanduser()
    return _j(importer.import_linkedin_export([(p.name, p.read_bytes())]))


@mcp.tool()
def import_analytics_file(path: str) -> str:
    """Import LinkedIn post-analytics export (XLSX/CSV) from a local path and attach metrics to posts."""
    db.init()
    from pathlib import Path
    p = Path(path).expanduser()
    return _j(importer.import_analytics(p.name, p.read_bytes()))


@mcp.tool()
def render_carousel_pdf(text: str, theme: str = "linkedin", title: str = "Carousel") -> str:
    """Render 'Slide 1 — Title / body' text into a 1080x1350 PDF carousel. Themes: linkedin, light, dark, sunset, forest.
    Returns media id — pass it to attach_media."""
    db.init()
    return _j(media.render_carousel(text, theme, title))


@mcp.tool()
def generate_post_image(prompt: str, title: str = "") -> str:
    """Generate an image with the configured image model (Settings → Image model). Returns media id."""
    db.init()
    return _j(media.generate_image(prompt, title))


@mcp.tool()
def attach_media(post_id: int, media_id: int) -> str:
    """Attach an image or carousel PDF (media id) to a draft post."""
    db.init()
    db.update("posts", post_id, media_id=media_id)
    return _j(db.get("posts", post_id))


@mcp.tool()
def get_analytics() -> str:
    """Best posting times (heatmap), top posts, performance by hook and pillar."""
    db.init()
    return _j(analytics.overview())


@mcp.tool()
def refresh_trends() -> str:
    """Fetch the workspace's RSS feeds and return the latest headlines (input for the trend_ideas skill)."""
    db.init()
    trends.refresh()
    return _j(db.list_rows("trends", limit=20))


def main(http: bool = False) -> None:
    db.init()
    db.set_account(settings.default_account)
    if http:
        mcp.run(transport="streamable-http")
    else:
        mcp.run()
