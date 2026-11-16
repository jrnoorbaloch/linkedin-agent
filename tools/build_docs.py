"""Build the static documentation site in docs/ (served by GitHub Pages).

    python tools/build_demo.py && python tools/build_docs.py
"""
from __future__ import annotations

import html
import json
import pathlib
import sys
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from linkedin_agent import __version__, skills  # noqa: E402

DOCS = ROOT / "docs"
SITE = "https://jrnoorbaloch.github.io/linkedin-agent/"
REPO = "https://github.com/jrnoorbaloch/linkedin-agent"
NAME = "LinkedIn Agent"
TAGLINE = "Open-source AI agent for LinkedIn: daily posts, profile optimization, resumes and approval-gated publishing — bring your own LLM."

NAV = [
    ("index.html", "Home"),
    ("getting-started.html", "Get started"),
    ("portal.html", "Web portal"),
    ("skills.html", "Skills"),
    ("claude.html", "Claude & MCP"),
    ("api.html", "API"),
    ("faq.html", "FAQ"),
]

CSS = """
:root{--bg:#fbfaf8;--panel:#fff;--ink:#16191c;--muted:#5b636c;--line:#e7e4de;--brand:#0a66c2;--brand-2:#004182;--soft:#eaf2fb;--code:#f3f1ec;
font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
@media (prefers-color-scheme:dark){:root{--bg:#0f1113;--panel:#171a1d;--ink:#e9ebee;--muted:#9ba4ad;--line:#2a2f34;--brand:#5aa8ee;--brand-2:#8cc2f5;--soft:#14253a;--code:#1d2125}}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);line-height:1.65;font-size:16px}
a{color:var(--brand)}
header{position:sticky;top:0;z-index:5;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
.bar{max-width:1120px;margin:0 auto;display:flex;align-items:center;gap:22px;padding:12px 22px}
.brand{display:flex;gap:9px;align-items:center;font-weight:750;color:var(--ink);text-decoration:none}
.brand b{display:grid;place-items:center;width:30px;height:30px;border-radius:8px;background:#0a66c2;color:#fff;font-size:12px}
.bar nav{display:flex;gap:4px;flex-wrap:wrap;flex:1}
.bar nav a{color:var(--muted);text-decoration:none;padding:6px 10px;border-radius:8px;font-size:14.5px;font-weight:500}
.bar nav a:hover,.bar nav a.on{color:var(--ink);background:var(--code)}
.gh{font-size:14px;font-weight:600;text-decoration:none;border:1px solid var(--line);padding:6px 12px;border-radius:999px;color:var(--ink)}
main{max-width:1120px;margin:0 auto;padding:40px 22px 80px}
.doc{max-width:820px}
h1{font-size:clamp(30px,4.6vw,52px);line-height:1.1;letter-spacing:-.02em;margin:.2em 0 .35em}
h2{font-size:26px;letter-spacing:-.01em;margin:2em 0 .5em;padding-top:.3em}
h3{font-size:18px;margin:1.6em 0 .4em}
.lead{font-size:19px;color:var(--muted);max-width:720px}
.cta{display:flex;gap:12px;flex-wrap:wrap;margin:26px 0}
.btn{display:inline-block;padding:11px 20px;border-radius:999px;font-weight:650;text-decoration:none;border:1px solid var(--line);color:var(--ink);background:var(--panel)}
.btn.p{background:#0a66c2;border-color:#0a66c2;color:#fff}
.btn:hover{filter:brightness(1.05)}
.shot{border-radius:14px;border:1px solid var(--line);box-shadow:0 20px 50px -20px rgba(0,0,0,.25);width:100%;height:auto;display:block;margin:18px 0}
.grid{display:grid;gap:16px;grid-template-columns:repeat(auto-fill,minmax(240px,1fr))}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px 18px 14px}
.card h3{margin:0 0 6px;font-size:16px}.card p{margin:0;color:var(--muted);font-size:14.5px}
.ico{font-size:22px}
code{background:var(--code);padding:.1em .38em;border-radius:5px;font-size:.9em}
pre{background:var(--code);padding:16px 18px;border-radius:12px;overflow:auto;font-size:14px;line-height:1.5;border:1px solid var(--line)}
pre code{background:none;padding:0}
table{width:100%;border-collapse:collapse;font-size:14.5px;margin:12px 0}th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:12.5px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
.note{background:var(--soft);border-left:3px solid var(--brand);padding:12px 16px;border-radius:8px;margin:16px 0}
.tag{display:inline-block;font-size:12px;font-weight:600;background:var(--code);padding:2px 9px;border-radius:999px;color:var(--muted);margin:2px}
.yes{color:#0b7a46;font-weight:700}.no{color:#b42318;font-weight:700}
.arch{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:18px 0}
.arch div{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px;text-align:center;font-weight:600}
.arch small{display:block;font-weight:400;color:var(--muted)}
.core{grid-column:1/-1;background:var(--soft)!important;border-color:var(--brand)!important}
footer{border-top:1px solid var(--line);color:var(--muted);font-size:14px}
footer .bar{flex-wrap:wrap}
iframe.demo{width:100%;height:760px;border:1px solid var(--line);border-radius:14px;background:var(--panel)}
@media(max-width:760px){.bar nav{display:none}.arch{grid-template-columns:1fr}iframe.demo{height:620px}}
"""


def page(slug: str, title: str, description: str, body: str, *, doc: bool = True, keywords: str = "", schema: dict | None = None) -> None:
    url = SITE + ("" if slug == "index.html" else slug)
    full_title = title if slug == "index.html" else f"{title} · {NAME}"
    nav = "".join(f'<a href="{h}" class="{"on" if h == slug else ""}">{t}</a>' for h, t in NAV)
    ld = schema or {
        "@context": "https://schema.org", "@type": "TechArticle", "headline": title, "description": description,
        "url": url, "author": {"@type": "Person", "name": "jrnoorbaloch"}, "dateModified": date.today().isoformat(),
    }
    out = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(full_title)}</title>
<meta name="description" content="{html.escape(description)}">
<meta name="keywords" content="{html.escape(keywords or 'LinkedIn agent, LinkedIn AI, LinkedIn automation, AI LinkedIn post generator, LinkedIn profile optimizer, resume builder, MCP server, Claude skill, open source')}">
<meta name="author" content="jrnoorbaloch">
<meta name="robots" content="index,follow">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{NAME}">
<meta property="og:title" content="{html.escape(full_title)}">
<meta property="og:description" content="{html.escape(description)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}assets/og.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{html.escape(full_title)}">
<meta name="twitter:description" content="{html.escape(description)}">
<meta name="twitter:image" content="{SITE}assets/og.png">
<meta name="theme-color" content="#0a66c2">
<link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<style>{CSS}</style>
<script type="application/ld+json">{json.dumps(ld)}</script>
</head>
<body>
<header><div class="bar"><a class="brand" href="index.html"><b>LA</b>{NAME}</a><nav>{nav}</nav><a class="gh" href="{REPO}">★ GitHub</a></div></header>
<main><div class="{'doc' if doc else ''}">
{body}
</div></main>
<footer><div class="bar"><span>{NAME} v{__version__} · MIT License · Not affiliated with LinkedIn Corporation.</span><span style="flex:1"></span><a href="{REPO}">GitHub</a><a href="{REPO}/issues">Issues</a><a href="sitemap.xml">Sitemap</a></div></footer>
</body>
</html>
"""
    (DOCS / slug).write_text(out, encoding="utf-8")


# ----------------------------------------------------------------- pages

def build() -> None:
    reg = skills.list_skills()
    cats: dict[str, list[dict]] = {}
    for s in reg:
        cats.setdefault(s["category"], []).append(s)

    icons = {"Content": "✍️", "Engagement": "💬", "Networking": "🤝", "Profile": "🎯", "Career": "💼", "Company Page": "🏢", "Analytics": "📈"}

    # ---------- Home
    feature_cards = "".join(
        f'<div class="card"><div class="ico">{i}</div><h3>{t}</h3><p>{d}</p></div>' for i, t, d in [
            ("🗓️", "A post every morning", "The scheduler drafts today's post from your pillars and Story Bank. You approve; it publishes."),
            ("🔌", "Any LLM", "OpenAI, Claude, Gemini, Groq, OpenRouter, DeepSeek or a local Ollama model. Your key, your machine."),
            ("✅", "Approval-gated", "Nothing is posted without your OK, enforced in the API, the MCP server and the Claude skill."),
            ("🎯", "Profile optimizer", "Headline, About, Experience, Skills, Featured and banner rewrites ready to paste."),
            ("📄", "Resumes & cover letters", "ATS-friendly resumes tailored to a job description, exported to Word."),
            ("🧩", "Claude skill + MCP", "Use it from Claude, Claude Code, Cursor or any MCP client. Or just the web portal."),
            ("🏢", "Company Pages", "Page posts, hiring posts and employee-advocacy packs (with LinkedIn's Community Management API)."),
            ("🔒", "Self-hosted & private", "SQLite on your machine, API keys and tokens encrypted at rest. MIT licensed."),
        ])
    cat_tags = " ".join(f'<span class="tag">{icons.get(c,"")} {c} · {len(v)}</span>' for c, v in cats.items())
    page("index.html", f"{NAME} — open-source AI agent for LinkedIn posts, profile & resume",
         TAGLINE,
         f"""
<p class="tag">Open source · Self-hosted · v{__version__}</p>
<h1>Your LinkedIn, on autopilot. With you in control.</h1>
<p class="lead">{NAME} drafts a post every day, rewrites your profile, builds your resume and publishes through LinkedIn's official API, using <b>any LLM you choose</b>. Run it as a web portal, an MCP server, or a Claude skill.</p>
<div class="cta"><a class="btn p" href="getting-started.html">Get started in 5 minutes →</a><a class="btn" href="demo/">Try the live UI demo</a><a class="btn" href="{REPO}">View on GitHub</a></div>
<img class="shot" src="assets/ui-dashboard.png" alt="LinkedIn Agent web portal dashboard showing drafts, published posts, engagement rate and setup checklist" width="2040" height="1290">
<h2>Everything LinkedIn, in one agent</h2>
<p>{len(reg)} skills across {len(cats)} areas: {cat_tags}</p>
<div class="grid">{feature_cards}</div>
<h2>How it fits together</h2>
<div class="arch">
 <div>🖥️ Web portal<small>for you, in the browser</small></div>
 <div>🧩 MCP server<small>for Claude, Cursor, any agent</small></div>
 <div>📚 Claude skill<small>playbooks + workflows</small></div>
 <div class="core">⚙️ Core engine: skill registry · your LLM · approval queue · scheduler · LinkedIn API · encrypted SQLite</div>
</div>
<h2>Install</h2>
<pre><code>pip install git+{REPO}
linkedin-agent serve        # open http://localhost:8787</code></pre>
<p>or with Docker: <code>docker compose up -d</code>. Full guide: <a href="getting-started.html">Getting started</a>.</p>
<h2>Honest about LinkedIn's API</h2>
<table><tr><th>Capability</th><th>Status</th><th>How</th></tr>
<tr><td>Post as yourself</td><td class="yes">Yes</td><td>Self-serve "Share on LinkedIn" (<code>w_member_social</code>)</td></tr>
<tr><td>First comment on your post</td><td class="yes">Yes</td><td>Same permission</td></tr>
<tr><td>Post as a Company Page</td><td class="yes">With approval</td><td>Community Management API (<code>w_organization_social</code>)</td></tr>
<tr><td>Edit your profile</td><td class="no">No API</td><td>Agent writes the copy, you paste it</td></tr>
<tr><td>Read post analytics</td><td class="no">Restricted</td><td>Paste metrics in History; the agent learns from them</td></tr>
<tr><td>DMs / connection requests</td><td class="no">No API</td><td>Agent drafts, you send</td></tr></table>
<p>No scraping, no browser bots, no account risk. <a href="faq.html">Read the FAQ</a>.</p>
""", doc=False,
         schema={"@context": "https://schema.org", "@type": "SoftwareApplication", "name": NAME, "applicationCategory": "BusinessApplication",
                 "operatingSystem": "Windows, macOS, Linux, Docker", "description": TAGLINE, "url": SITE, "license": "https://opensource.org/licenses/MIT",
                 "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}, "softwareVersion": __version__,
                 "codeRepository": REPO})

    # ---------- Getting started
    page("getting-started.html", "Getting started", "Install LinkedIn Agent, create a LinkedIn developer app, connect any LLM and publish your first approved post.",
         f"""
<h1>Getting started</h1>
<p class="lead">About 5 minutes: install, create a LinkedIn app, connect an LLM, fill your brand profile, approve your first post.</p>

<h2 id="install">1. Install</h2>
<h3>Option A — pip (Python 3.10+)</h3>
<pre><code>pip install git+{REPO}
cp .env.example .env     # or create .env, see step 2
linkedin-agent serve     # → http://localhost:8787</code></pre>
<h3>Option B — Docker</h3>
<pre><code>git clone {REPO}.git
cd linkedin-agent
cp .env.example .env
docker compose up -d     # → http://localhost:8787 (data in ./data)</code></pre>

<h2 id="linkedin-app">2. Create a LinkedIn developer app</h2>
<ol>
<li>Go to <a href="https://www.linkedin.com/developers/apps">linkedin.com/developers/apps</a> → <b>Create app</b>. It must be linked to a LinkedIn Page (any page you admin; a placeholder page is fine).</li>
<li><b>Products</b> tab → add <b>Sign In with LinkedIn using OpenID Connect</b> and <b>Share on LinkedIn</b>. Both are self-serve, with no review.</li>
<li><b>Auth</b> tab → add the redirect URL <code>http://localhost:8787/auth/linkedin/callback</code> (or <code>LA_BASE_URL</code> + <code>/auth/linkedin/callback</code> if hosted).</li>
<li>Copy the Client ID and Client Secret into <code>.env</code>:</li>
</ol>
<pre><code>LINKEDIN_CLIENT_ID=your-client-id
LINKEDIN_CLIENT_SECRET=your-client-secret</code></pre>
<p>Restart, open <b>Settings → Connect LinkedIn</b>, and approve. Access tokens last about 60 days; the dashboard shows how many days remain.</p>
<div class="note"><b>Company Pages:</b> request the <b>Community Management API</b> product for your app. After LinkedIn approves it, set <code>LINKEDIN_ORG_ENABLED=1</code>, reconnect, and use <i>Settings → Load my pages</i>.</div>

<h2 id="llm">3. Connect any LLM</h2>
<p>In <b>Settings → Language model</b>, pick a provider, paste your key, and click <i>Test connection</i>. Keys are encrypted on disk.</p>
<table><tr><th>Provider</th><th>Base URL (auto-filled)</th><th>Example model</th></tr>
{''.join(f"<tr><td>{k}</td><td><code>{v['base_url'] or 'your OpenAI-compatible URL'}</code></td><td><code>{v['model'] or '—'}</code></td></tr>" for k, v in __import__('linkedin_agent.llm', fromlist=['PRESETS']).PRESETS.items())}
</table>
<p>Any OpenAI-compatible endpoint works with <b>custom</b>: LM Studio, vLLM, Together, Mistral, Azure OpenAI and others. For a fully local setup, run <a href="https://ollama.com">Ollama</a> and choose <b>ollama</b>.</p>

<h2 id="brand">4. Fill your brand profile</h2>
<p>Every skill writes from it: role, audience, offer, 3-5 content pillars, tone, language, two or three past posts and your profile text. Add a few real experiences to the <b>Story Bank</b>, or use <i>Create → Story Interviewer</i>.</p>

<h2 id="first-post">5. Draft, approve, publish</h2>
<ol><li>Dashboard → <b>Draft today's post now</b> (or Create → Post Writer).</li>
<li>Review it in the <b>Approval queue</b>: edit, then <b>Approve</b>, or pick a time and <b>Schedule</b>.</li>
<li><b>Publish now</b> posts it and adds your first comment. The live link opens.</li></ol>

<h2 id="daily">6. Turn on the daily routine</h2>
<p><b>Settings → Daily schedule</b>: set the draft time and your timezone (e.g. <code>Asia/Karachi</code>). Optionally enable <i>auto-publish</i>, which posts the oldest <b>approved</b> post each day at your publish time. Drafts are never auto-published.</p>

<h2 id="config">Configuration reference</h2>
<table><tr><th>Variable</th><th>Default</th><th>Purpose</th></tr>
<tr><td><code>LA_HOST</code> / <code>LA_PORT</code></td><td>127.0.0.1 / 8787</td><td>Where the portal listens</td></tr>
<tr><td><code>LA_BASE_URL</code></td><td>http://localhost:8787</td><td>Public URL when hosted (used for the OAuth redirect)</td></tr>
<tr><td><code>LA_API_TOKEN</code></td><td>—</td><td>Protects <code>/api/*</code>. Recommended when not on localhost</td></tr>
<tr><td><code>LA_DATA_DIR</code></td><td>~/.linkedin-agent</td><td>SQLite database + encryption key</td></tr>
<tr><td><code>LINKEDIN_CLIENT_ID</code> / <code>_SECRET</code></td><td>—</td><td>Your LinkedIn app</td></tr>
<tr><td><code>LINKEDIN_API_VERSION</code></td><td>202608</td><td><code>LinkedIn-Version</code> header (YYYYMM)</td></tr>
<tr><td><code>LINKEDIN_ORG_ENABLED</code></td><td>0</td><td>Company Page features (after approval)</td></tr></table>
""", keywords="install LinkedIn agent, LinkedIn developer app setup, LinkedIn OAuth, Share on LinkedIn API, connect OpenAI Claude Gemini Ollama")

    # ---------- Portal tour
    shots = [
        ("ui-dashboard.png", "Dashboard", "Drafts waiting, approved/scheduled and published counts, engagement rate, a setup checklist, today's schedule, and one-click <i>Draft today's post</i>."),
        ("ui-create.png", "Create", f"All {len(reg)} skills, grouped by category. Each opens a form generated from the skill registry."),
        ("ui-post-writer.png", "Post Writer", "Pick a topic, goal, hook formula and format. The result lands in the approval queue with its first comment."),
        ("ui-queue.png", "Approval queue", "Edit inline with a live character count, approve, schedule for a date and time, or reject. Approved posts get <i>Publish now</i>."),
        ("ui-history.png", "History & metrics", "Published posts with links. Enter impressions, reactions, comments and reposts so the weekly report and daily planner learn what works."),
        ("ui-settings.png", "Settings", "Choose an LLM provider and model, connect or disconnect LinkedIn, enable Company Pages, set the daily schedule, and copy the MCP config."),
    ]
    page("portal.html", "Web portal tour", "A tour of the LinkedIn Agent web portal: dashboard, skill forms, approval queue, history, documents, story bank, network CRM, brand profile and settings.",
         "<h1>Web portal</h1><p class=\"lead\">A local web app at <code>http://localhost:8787</code>. Light and dark mode, mobile friendly. <a href=\"demo/\">Open the live demo</a> to click around with sample data.</p>"
         + "".join(f'<h2>{t}</h2><p>{d}</p><img class="shot" loading="lazy" src="assets/{f}" alt="LinkedIn Agent {t} screen" width="2040" height="1290">' for f, t, d in shots)
         + """<h2>Library screens</h2>
<ul><li><b>Documents</b>: resumes, cover letters, profile rewrites and plans. Copy or download as <b>.docx</b>.</li>
<li><b>Story bank</b>: real experiences the agent draws from, so it doesn't invent.</li>
<li><b>Network</b>: a mini CRM with follow-up dates, plus quick links to the Connection Note and DM writers.</li>
<li><b>Brand profile</b>: your voice, audience, pillars, sample posts and profile text.</li></ul>
<h2>Live demo</h2><iframe class="demo" src="demo/#create" title="LinkedIn Agent live demo" loading="lazy"></iframe>""",
         keywords="LinkedIn agent dashboard, LinkedIn post approval queue, LinkedIn content scheduler UI")

    # ---------- Skills
    rows = ""
    for c, items in cats.items():
        rows += f'<h2 id="{c.lower().replace(" ", "-")}">{icons.get(c, "")} {c}</h2><table><tr><th style="width:24%">Skill</th><th>What it does</th><th style="width:26%">Inputs</th></tr>'
        for s in items:
            ins = ", ".join(f["label"] + (" *" if f["required"] else "") for f in s["fields"]) or "—"
            rows += f'<tr><td><b>{html.escape(s["title"])}</b><br><code>{s["id"]}</code></td><td>{html.escape(s["description"])}</td><td>{html.escape(ins)}</td></tr>'
        rows += "</table>"
    page("skills.html", "All skills", f"The {len(reg)} LinkedIn skills in LinkedIn Agent: post writer, hooks, humanizer, carousel, comments, connection notes, profile optimizer, resume builder, job match, interview prep, company pages and analytics.",
         f"""<h1>Skills</h1><p class="lead">{len(reg)} skills. Every one is available in the portal (<i>Create</i>), over MCP (<code>run_skill</code>), from the CLI (<code>linkedin-agent run &lt;id&gt;</code>), and as playbooks in the Claude skill.</p>
<p>{' '.join(f'<a class="tag" href="#{c.lower().replace(" ", "-")}">{icons.get(c,"")} {c}</a>' for c in cats)}</p>
{rows}
<h2 id="add-your-own">Add your own skill</h2>
<p>Append a <code>Skill(...)</code> to <code>SKILLS</code> in <code>linkedin_agent/skills.py</code>. The portal form, REST endpoint and MCP tool pick it up automatically.</p>
<pre><code>Skill(
    "event_recap", "Event Recap", "Content",
    "Turn notes from an event into a post.",
    "Write a post recapping the event: 3 takeaways, one photo idea, thank the hosts.",
    [Field("notes", "Your notes", "textarea", required=True)],
    output="post",
)</code></pre>""",
         keywords="LinkedIn post writer AI, LinkedIn hook formulas, LinkedIn humanizer, LinkedIn carousel generator, LinkedIn profile optimizer, ATS resume builder, job match, interview prep, LinkedIn comment generator")

    # ---------- Claude & MCP
    tool_rows = "".join(f"<tr><td><code>{n}</code></td><td>{d}</td></tr>" for n, d in [
        ("status", "LinkedIn connection, LLM, brand profile, post counts"),
        ("list_skills", "All skills with their input fields"),
        ("run_skill", "Run a skill with the agent's own LLM (drafts are saved)"),
        ("get_skill_prompt", "Get the skill's prompt so the calling model writes the content itself"),
        ("save_draft", "Put a post you wrote into the approval queue"),
        ("list_posts", "List posts by status"),
        ("approve_post", "Approve or schedule a draft, only after the user says yes"),
        ("publish_post", "Publish an approved post and return its URL"),
        ("record_metrics", "Store impressions, reactions, comments and reposts"),
        ("get_brand_profile / update_brand_profile", "Read or update voice, audience and pillars"),
        ("add_story", "Add to the Story Bank"),
        ("list_documents / save_document", "Resumes, cover letters, plans"),
    ])
    page("claude.html", "Use with Claude, Claude Code & any MCP client", "Install the LinkedIn Agent Claude skill and subagent, and connect the MCP server to Claude Desktop, Claude Code, Cursor or any MCP-compatible LLM.",
         f"""<h1>Claude skill, subagent & MCP</h1>
<p class="lead">Three ways for an AI assistant to use the agent. Combine them for the best result.</p>

<h2 id="skill">1. The Claude skill</h2>
<p><code>skill/linkedin-agent/</code> is a single skill that bundles every playbook (hooks, post writing, humanizer, profile, career, engagement, networking, company page, analytics, publishing) and routes each request to the right one. It works on its own: Claude writes everything. With the MCP server connected, it can also queue and publish.</p>
<pre><code>skill/linkedin-agent/
├── SKILL.md              # routing, ground rules, workflows
├── references/           # 13 playbooks, loaded only when needed
└── scripts/la.py         # stdlib REST client for the portal</code></pre>
<h3>Install</h3>
<ul>
<li><b>Claude apps (claude.ai / desktop):</b> download <a href="downloads/linkedin-agent-skill.zip"><code>linkedin-agent-skill.zip</code></a>, then go to <i>Settings → Capabilities → Skills → Upload skill</i>.</li>
<li><b>Claude Code:</b> <code>cp -r skill/linkedin-agent ~/.claude/skills/</code> (personal) or <code>.claude/skills/</code> (project).</li>
</ul>

<h2 id="subagent">2. The subagent (Claude Code)</h2>
<p><code>agents/linkedin-agent.md</code> defines a LinkedIn manager subagent with routines for the daily post, weekly plan, profile and career overhaul, and weekly review.</p>
<pre><code>cp agents/linkedin-agent.md ~/.claude/agents/
# then: "Use the linkedin-agent subagent to plan and draft my week"</code></pre>

<h2 id="mcp">3. The MCP server</h2>
<p>Any MCP client can drive the agent: Claude Desktop, Claude Code, Cursor, Windsurf, or your own agent.</p>
<h3>Claude Desktop / Cursor (<code>mcpServers</code> config)</h3>
<pre><code>{{
  "mcpServers": {{
    "linkedin-agent": {{ "command": "linkedin-agent", "args": ["mcp"] }}
  }}
}}</code></pre>
<h3>Claude Code</h3>
<pre><code>claude mcp add linkedin-agent -- linkedin-agent mcp</code></pre>
<h3>Remote / HTTP</h3>
<pre><code>linkedin-agent mcp --http      # streamable HTTP transport</code></pre>
<div class="note">The MCP server and the portal share the same database (<code>LA_DATA_DIR</code>). Connect LinkedIn once in the portal and both can use it.</div>
<h3>Tools</h3><table><tr><th>Tool</th><th>Purpose</th></tr>{tool_rows}</table>

<h2 id="safety">Approval gate</h2>
<p><code>publish_post</code> refuses any post that hasn't been approved. The skill and the subagent both instruct the model to call <code>approve_post</code> only after you explicitly say yes to the exact text.</p>
""", keywords="Claude skill LinkedIn, Claude Code subagent, MCP server LinkedIn, Model Context Protocol LinkedIn, Cursor MCP LinkedIn")

    # ---------- API
    eps = [
        ("GET", "/api/health", "Version check"), ("GET", "/api/dashboard", "Counts, LinkedIn and LLM status, schedule"),
        ("GET", "/api/skills", "Skill registry"), ("POST", "/api/skills/{id}", "Run a skill; body is the input fields"),
        ("GET", "/api/posts?status=", "List posts"), ("POST", "/api/posts", "Create draft {content, first_comment, pillar, target, org_urn}"),
        ("PATCH", "/api/posts/{id}", "Edit, set metrics, or set status to draft/rejected"), ("POST", "/api/posts/{id}/approve", "{scheduled_at?, content?}"),
        ("POST", "/api/posts/{id}/publish", "Publish (approved only)"), ("DELETE", "/api/posts/{id}", "Delete"),
        ("GET", "/api/documents", "List documents"), ("GET", "/api/documents/{id}/docx", "Download as Word"),
        ("GET/POST", "/api/brand", "Brand profile"), ("GET/POST/DELETE", "/api/stories", "Story Bank"),
        ("GET/POST/DELETE", "/api/contacts", "Network CRM"), ("GET/POST", "/api/llm", "LLM provider config"), ("POST", "/api/llm/test", "Ping the model"),
        ("GET/POST", "/api/schedule", "Daily draft and auto-publish settings"), ("GET", "/api/linkedin/status", "Connection status"),
        ("GET", "/api/linkedin/organizations", "Pages you admin (Community Management API)"), ("GET", "/auth/linkedin", "Start OAuth"),
    ]
    page("api.html", "REST API & CLI reference", "REST API and CLI reference for LinkedIn Agent: skills, posts, approval, publishing, documents, brand profile, schedule.",
         f"""<h1>REST API & CLI</h1>
<p class="lead">The portal is a thin UI over this API. Interactive OpenAPI docs are served at <code>/docs</code> on your instance.</p>
<p>If <code>LA_API_TOKEN</code> is set, send it as the <code>X-API-Token</code> header.</p>
<table><tr><th>Method</th><th>Path</th><th>Description</th></tr>{''.join(f'<tr><td><code>{m}</code></td><td><code>{html.escape(p)}</code></td><td>{html.escape(d)}</td></tr>' for m, p, d in eps)}</table>
<h2>Example</h2>
<pre><code>curl -X POST localhost:8787/api/skills/post_writer \\
  -H 'content-type: application/json' \\
  -d '{{"topic":"What I learned from 100 sales calls","goal":"comments"}}'

curl -X POST localhost:8787/api/posts/12/approve -d '{{}}' -H 'content-type: application/json'
curl -X POST localhost:8787/api/posts/12/publish</code></pre>
<h2>CLI</h2>
<pre><code>linkedin-agent serve [--host 0.0.0.0 --port 8787]
linkedin-agent mcp [--http]
linkedin-agent skills
linkedin-agent run post_writer -i topic="Hiring lessons" -i goal=comments</code></pre>
""", keywords="LinkedIn agent API, LinkedIn post API wrapper, LinkedIn automation REST API")

    # ---------- FAQ
    faqs = [
        ("Is this allowed by LinkedIn?", "It only uses LinkedIn's official, documented APIs with your own developer app and OAuth consent: posting as yourself (and as a Page once approved). It does not scrape, automate a browser, or send messages or connection requests. As always, follow LinkedIn's User Agreement and API terms."),
        ("Why can't it update my profile automatically?", "LinkedIn offers no public API for editing profile sections. The Profile Optimizer writes the headline, About, experience bullets and more so you can paste them in."),
        ("Which LLMs work?", "Anything OpenAI-compatible (OpenAI, Gemini, Groq, OpenRouter, DeepSeek, Mistral, Together, LM Studio, Ollama) plus Anthropic Claude natively. From Claude or another MCP client, the calling model can also write content itself via get_skill_prompt + save_draft."),
        ("Will it post without me?", "Only posts you approved. Drafts are never published, and the API refuses to publish an unapproved post. Auto-publish is off by default."),
        ("Where is my data?", "In a SQLite file in LA_DATA_DIR on your machine. LLM keys and LinkedIn tokens are encrypted with a local key. Nothing goes anywhere except your LLM provider and LinkedIn."),
        ("Can I post to my Company Page?", "Yes, after LinkedIn approves the Community Management API for your app and you're a Page admin. Set LINKEDIN_ORG_ENABLED=1."),
        ("Can I see analytics?", "LinkedIn restricts post analytics for self-serve apps. Enter the numbers in History (or via the record_metrics tool) and the weekly report will analyze them."),
        ("Can I host it for my team or clients?", "Yes. Deploy the Docker image behind HTTPS, set LA_BASE_URL and LA_API_TOKEN, and add the public callback URL to your LinkedIn app. The current version is single-user, so run one instance per person."),
    ]
    page("faq.html", "FAQ", "Frequently asked questions about LinkedIn Agent: LinkedIn API limits and terms, privacy, supported LLMs, Company Pages, analytics and hosting.",
         "<h1>FAQ</h1>" + "".join(f"<h3>{html.escape(q)}</h3><p>{html.escape(a)}</p>" for q, a in faqs),
         schema={"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
             {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]},
         keywords="LinkedIn API limits, is LinkedIn automation allowed, LinkedIn profile API, LinkedIn Community Management API")

    # ---------- 404, sitemap, robots, favicon, nojekyll
    page("404.html", "Page not found", "Page not found.", '<h1>Page not found</h1><p><a href="index.html">← Back home</a></p>')
    pages = [h for h, _ in NAV]
    today = date.today().isoformat()
    (DOCS / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{SITE}{'' if h == 'index.html' else h}</loc><lastmod>{today}</lastmod><priority>{'1.0' if h == 'index.html' else '0.8'}</priority></url>\n" for h in pages)
        + "</urlset>\n", encoding="utf-8")
    (DOCS / "robots.txt").write_text(f"User-agent: *\nAllow: /\nDisallow: /demo/\nSitemap: {SITE}sitemap.xml\n", encoding="utf-8")
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")
    (DOCS / "assets" / "favicon.svg").write_text(
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='8' fill='#0a66c2'/>"
        "<text x='16' y='21.5' font-size='13' font-family='Arial' font-weight='700' fill='white' text-anchor='middle'>LA</text></svg>", encoding="utf-8")
    print("docs built:", ", ".join(pages))


if __name__ == "__main__":
    build()
