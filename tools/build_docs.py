"""Build the marketing + documentation site in docs/ (GitHub Pages).

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
from linkedin_agent import __version__, llm, personas, skills  # noqa: E402

DOCS = ROOT / "docs"
SITE = "https://jrnoorbaloch.github.io/linkedin-agent/"
REPO = "https://github.com/jrnoorbaloch/linkedin-agent"
DL = f"{REPO}/releases/latest/download/"
NAME = "LinkedIn Agent"
TAGLINE = ("Open-source AI agent for LinkedIn. Drafts a post every morning, rewrites your profile, builds your resume and "
           "publishes through LinkedIn's official API after you approve. Any LLM. Desktop, web, Docker, MCP and Claude skill.")
e = html.escape

TOP_NAV = [("features.html", "Features"), ("screens.html", "Screens"), ("personas.html", "For you"), ("docs.html", "Docs"), ("download.html", "Download")]
DOC_NAV = [
    ("Start", [("docs.html", "Overview"), ("getting-started.html", "Install & set up"), ("linkedin-app.html", "LinkedIn app"), ("models.html", "Connect any LLM")]),
    ("Use it", [("skills.html", "All skills"), ("workflows.html", "Daily workflow"), ("import-guide.html", "Import your data"), ("approvals.html", "Approvals on your phone"), ("teams.html", "Teams & workspaces")]),
    ("Build on it", [("claude.html", "Claude skill & MCP"), ("api.html", "REST API & CLI"), ("self-hosting.html", "Self-hosting")]),
    ("Help", [("faq.html", "FAQ"), ("changelog.html", "Changelog")]),
]

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=Instrument+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">')

CSS = """
:root{--ink:#0f1b33;--ink2:#17264a;--paper:#f6f7fb;--surface:#fff;--line:#e3e7f0;--text:#101828;--muted:#5b6782;--faint:#8a95ad;
--brand:#3b5bfd;--brand2:#2c47d9;--soft:#eef1ff;--ok:#12a150;--oksoft:#e7f7ee;--warn:#c97a00;--warnsoft:#fff4dc;--mint:#a5f3c5;
--display:"Bricolage Grotesque",ui-sans-serif,system-ui,sans-serif;--body:"Instrument Sans",ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--paper);color:var(--text);font:16.5px/1.65 var(--body);-webkit-font-smoothing:antialiased}
a{color:var(--brand)}img{max-width:100%;height:auto}
:focus-visible{outline:2px solid var(--brand);outline-offset:3px;border-radius:6px}
.wrap{max-width:1180px;margin:0 auto;padding:0 24px}
header.nav{position:sticky;top:0;z-index:10;background:color-mix(in srgb,var(--paper) 88%,transparent);backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
header.nav .wrap{display:flex;align-items:center;gap:28px;height:64px}
.logo{display:flex;align-items:center;gap:10px;font:700 18px var(--display);color:var(--text);text-decoration:none;letter-spacing:-.01em}
.logo img{width:30px;height:30px;border-radius:8px}
header.nav nav{display:flex;gap:4px;flex:1}
header.nav nav a{color:var(--muted);text-decoration:none;font-weight:600;font-size:15px;padding:7px 12px;border-radius:9px}
header.nav nav a:hover,header.nav nav a.on{color:var(--text);background:var(--surface)}
.btn{display:inline-flex;align-items:center;gap:8px;border-radius:11px;padding:11px 18px;font-weight:700;font-size:15px;text-decoration:none;border:1px solid var(--line);color:var(--text);background:var(--surface);white-space:nowrap}
.btn:hover{border-color:var(--faint)}
.btn.p{background:var(--brand);border-color:var(--brand);color:#fff}.btn.p:hover{background:var(--brand2)}
.btn.dark{background:var(--ink);border-color:var(--ink);color:#fff}
.btn.sm{padding:7px 13px;font-size:14px;border-radius:9px}
.btn svg{width:18px;height:18px}
h1,h2,h3{font-family:var(--display);letter-spacing:-.02em;line-height:1.08;margin:0}
.lead{font-size:20px;color:var(--muted);max-width:640px;line-height:1.55}
section{padding:96px 0}
.sec-h{max-width:720px;margin-bottom:44px}.sec-h h2{font-size:clamp(32px,4vw,48px)}.sec-h p{color:var(--muted);font-size:18.5px;margin:14px 0 0}
/* hero */
.hero{padding:72px 0 40px;overflow:hidden}
.hero-grid{display:grid;grid-template-columns:1.05fr .95fr;gap:56px;align-items:center}
.hero h1{font-size:clamp(42px,5.4vw,70px);font-weight:800;letter-spacing:-.035em;line-height:.98}
.hero .lead{margin:26px 0 30px}
.cta{display:flex;gap:12px;flex-wrap:wrap}
.trust{display:flex;gap:18px;flex-wrap:wrap;margin-top:28px;color:var(--muted);font-size:14.5px}
.trust span{display:inline-flex;gap:7px;align-items:center}.trust svg{width:16px;height:16px;color:var(--ok)}
/* signature: the post that moves through the pipeline */
.stage{position:relative;height:500px}
.post{position:absolute;inset:40px 30px auto 0;background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:18px 20px;box-shadow:0 30px 70px -30px rgba(15,27,51,.35);font:14.5px/1.5 -apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.post .h{display:flex;gap:11px;align-items:center;margin-bottom:12px}
.post .av{width:44px;height:44px;border-radius:50%;background:linear-gradient(135deg,#3b5bfd,#7c4dff);display:grid;place-items:center;color:#fff;font-weight:700}
.post .n{font-weight:700}.post .s{font-size:12.5px;color:var(--muted)}
.post .fold{border-top:1.5px dashed var(--warn);position:relative;margin:6px 0}
.post .fold span{position:absolute;right:0;top:-10px;background:#fff;color:var(--warn);font:700 11px var(--body);padding:0 6px}
.post .rest{opacity:.5}
.post .bar{display:flex;justify-content:space-around;border-top:1px solid var(--line);margin-top:12px;padding-top:9px;color:var(--muted);font-size:13px;font-weight:600}
.pipe{position:absolute;left:0;right:30px;bottom:0;display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
.pipe div{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:10px 12px;font-size:13px;color:var(--muted)}
.pipe b{display:block;color:var(--text);font-size:14px}
.pipe div.on{border-color:var(--brand);box-shadow:0 0 0 3px var(--soft)}
.stamp{position:absolute;right:6px;top:8px;font:800 15px var(--display);padding:8px 14px;border-radius:10px;transform:rotate(6deg);border:2.5px solid;background:var(--surface);opacity:0}
.stamp.draft{color:var(--warn);border-color:var(--warn)}.stamp.ok{color:var(--brand);border-color:var(--brand)}.stamp.live{color:var(--ok);border-color:var(--ok)}
@media (prefers-reduced-motion:no-preference){
 .stamp.draft{animation:s1 9s infinite}.stamp.ok{animation:s2 9s infinite}.stamp.live{animation:s3 9s infinite}
 .pipe div:nth-child(1){animation:p1 9s infinite}.pipe div:nth-child(2){animation:p2 9s infinite}.pipe div:nth-child(3){animation:p3 9s infinite}.pipe div:nth-child(4){animation:p4 9s infinite}
}
@keyframes s1{0%,30%{opacity:1;transform:rotate(6deg) scale(1)}33%,100%{opacity:0}}
@keyframes s2{0%,33%{opacity:0}36%{opacity:1;transform:rotate(6deg) scale(1.15)}38%,63%{opacity:1;transform:rotate(6deg) scale(1)}66%,100%{opacity:0}}
@keyframes s3{0%,66%{opacity:0}69%{opacity:1;transform:rotate(6deg) scale(1.15)}71%,100%{opacity:1;transform:rotate(6deg) scale(1)}}
@keyframes p1{0%,24%{border-color:var(--brand);box-shadow:0 0 0 3px var(--soft)}25%,100%{border-color:var(--line);box-shadow:none}}
@keyframes p2{0%,24%,50%,100%{border-color:var(--line);box-shadow:none}25%,49%{border-color:var(--brand);box-shadow:0 0 0 3px var(--soft)}}
@keyframes p3{0%,49%,75%,100%{border-color:var(--line);box-shadow:none}50%,74%{border-color:var(--brand);box-shadow:0 0 0 3px var(--soft)}}
@keyframes p4{0%,74%{border-color:var(--line);box-shadow:none}75%,100%{border-color:var(--ok);box-shadow:0 0 0 3px var(--oksoft)}}
/* product shot */
.frame{border-radius:18px;background:var(--ink);padding:10px;box-shadow:0 50px 100px -40px rgba(15,27,51,.5)}
.frame .dots{display:flex;gap:6px;padding:4px 6px 10px}.frame .dots i{width:10px;height:10px;border-radius:50%;background:#2b3b63}
.frame img{display:block;border-radius:10px;width:100%}
.works{display:flex;flex-wrap:wrap;gap:10px 26px;align-items:center;color:var(--muted);font-weight:600;padding:30px 0 0}
.works b{color:var(--text);font-family:var(--display);font-size:17px}
/* day timeline */
.day{display:grid;grid-template-columns:repeat(4,1fr);gap:0;border-top:2px solid var(--ink)}
.day>div{padding:22px 22px 0 0}
.day time{display:block;font:800 30px var(--display);letter-spacing:-.02em}
.day h3{font-size:19px;margin:8px 0 6px}.day p{margin:0;color:var(--muted);font-size:15.5px}
/* tabs gallery */
.gal-tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:18px}
.gal-tabs button{border:1px solid var(--line);background:var(--surface);color:var(--muted);font:600 14.5px var(--body);padding:8px 14px;border-radius:999px;cursor:pointer}
.gal-tabs button[aria-selected=true]{background:var(--ink);border-color:var(--ink);color:#fff}
.gal-cap{color:var(--muted);margin:16px 0 0;max-width:760px}
/* feature list: two columns of rows, not cards */
.flist{display:grid;grid-template-columns:repeat(2,1fr);gap:0 56px}
.flist>div{display:grid;grid-template-columns:40px 1fr;gap:14px;padding:22px 0;border-top:1px solid var(--line)}
.flist .ic{width:40px;height:40px;border-radius:11px;background:var(--soft);color:var(--brand);display:grid;place-items:center}
.flist .ic svg{width:20px;height:20px}
.flist h3{font-size:18px;margin:2px 0 4px}.flist p{margin:0;color:var(--muted);font-size:15.5px}
/* personas */
.ppl{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
.ppl a{display:block;text-decoration:none;color:var(--text);background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:20px}
.ppl a:hover{border-color:var(--brand)}
.ppl .e{font-size:30px}.ppl h3{font-size:19px;margin:10px 0 6px}.ppl p{margin:0;color:var(--muted);font-size:14.5px}
/* run-it-your-way */
.ways{display:grid;grid-template-columns:repeat(4,1fr);border:1px solid var(--line);border-radius:18px;overflow:hidden;background:var(--surface)}
.ways>div{padding:24px;border-left:1px solid var(--line)}.ways>div:first-child{border:0}
.ways h3{font-size:20px;margin-bottom:6px}.ways p{color:var(--muted);font-size:15px;margin:0 0 16px}
code{background:#eceff6;padding:.12em .4em;border-radius:6px;font-size:.88em}
pre{background:var(--ink);color:#e6ebf7;padding:18px 20px;border-radius:14px;overflow:auto;font-size:14px;line-height:1.55}
pre code{background:none;padding:0;color:inherit}
/* api honesty table */
table{width:100%;border-collapse:collapse;font-size:15.5px}th,td{text-align:left;padding:12px 14px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:13.5px;color:var(--muted);font-weight:600}
.yes{color:var(--ok);font-weight:700}.no{color:#b42318;font-weight:700}.maybe{color:var(--warn);font-weight:700}
.dark-band{background:var(--ink);color:#e6ebf7}.dark-band .sec-h p,.dark-band p{color:#aab6d3}
.dark-band h2{color:#fff}
.final{text-align:center}.final h2{font-size:clamp(36px,5vw,60px);color:#fff}.final p{font-size:19px;margin:16px auto 30px;max-width:600px}
footer{border-top:1px solid var(--line);padding:40px 0 60px;color:var(--muted);font-size:14.5px}
footer .wrap{display:grid;grid-template-columns:1.4fr repeat(3,1fr);gap:30px}
footer h4{margin:0 0 10px;color:var(--text);font-size:14px}footer a{display:block;color:var(--muted);text-decoration:none;padding:3px 0}footer a:hover{color:var(--text)}
/* docs layout */
.docs{display:grid;grid-template-columns:240px minmax(0,1fr);gap:48px;padding:40px 24px 80px;max-width:1180px;margin:0 auto}
.docs aside{position:sticky;top:84px;align-self:start;max-height:calc(100vh - 100px);overflow:auto}
.docs aside h5{font-size:13px;color:var(--faint);margin:18px 0 6px;font-weight:600}
.docs aside a{display:block;color:var(--muted);text-decoration:none;padding:5px 10px;border-radius:8px;font-weight:500;font-size:15px}
.docs aside a:hover{color:var(--text)}.docs aside a.on{background:var(--soft);color:var(--brand);font-weight:700}
.prose{max-width:760px}
.prose h1{font-size:44px;margin-bottom:10px}
.prose h2{font-size:27px;margin:48px 0 12px;padding-top:6px}
.prose h3{font-size:19px;margin:28px 0 8px}
.prose p,.prose li{color:#2c3650}
.prose .lead{margin-bottom:12px}
.note{background:var(--soft);border-left:3px solid var(--brand);padding:14px 18px;border-radius:10px;margin:18px 0}
.warn{background:var(--warnsoft);border-left-color:var(--warn)}
.shot{border-radius:14px;border:1px solid var(--line);display:block;margin:18px 0;box-shadow:0 24px 50px -30px rgba(15,27,51,.35)}
.grid2{display:grid;grid-template-columns:repeat(2,1fr);gap:18px}
.screens figure{margin:0 0 54px}.screens figcaption{margin-top:10px;color:var(--muted)}.screens figcaption b{color:var(--text);font-family:var(--display);font-size:20px;display:block}
.dlrow{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.dl{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:22px}
.dl.rec{border-color:var(--brand);box-shadow:0 0 0 4px var(--soft)}
.dl h3{font-size:21px}.dl p{color:var(--muted);font-size:15px}
.tag{display:inline-block;font-size:12.5px;font-weight:700;padding:3px 10px;border-radius:999px;background:var(--soft);color:var(--brand)}
@media (max-width:980px){.hero-grid,.flist,.grid2{grid-template-columns:1fr}.stage{height:520px}.day,.ways,.ppl,.dlrow{grid-template-columns:repeat(2,1fr)}.ways>div:nth-child(3){border-left:0}
 footer .wrap{grid-template-columns:1fr 1fr}.docs{grid-template-columns:1fr}.docs aside{position:static;max-height:none}}
@media (max-width:640px){header.nav nav{display:none}.day,.ways,.ppl,.dlrow{grid-template-columns:1fr}.ways>div{border-left:0;border-top:1px solid var(--line)}section{padding:64px 0}.post{inset:20px 0 auto 0}.pipe{right:0}}
"""

ICONS = {
    "spark": "M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6",
    "check": "M20 6 9 17l-5-5", "plug": "M9 2v6M15 2v6M6 8h12v4a6 6 0 0 1-12 0zM12 18v4",
    "shield": "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z", "cal": "M4 6h16v14H4zM4 10h16M9 3v4M15 3v4",
    "image": "M4 5h16v14H4zM4 15l5-5 4 4 3-3 4 4", "doc": "M6 3h9l5 5v13H6zM14 3v6h6", "upload": "M12 16V4M7 9l5-5 5 5M4 16v4h16v-4",
    "phone": "M7 2h10v20H7zM11 18h2", "users": "M16 19v-1a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v1M9 10a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM22 19v-1a4 4 0 0 0-3-3.9",
    "chart": "M4 20V10M10 20V4M16 20v-7M22 20H2", "globe": "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18",
    "trend": "M3 17l6-6 4 4 8-8M15 7h6v6", "box": "M21 8 12 3 3 8v8l9 5 9-5zM3 8l9 5 9-5M12 13v8", "download": "M12 4v12M7 11l5 5 5-5M4 20h16",
    "gh": "M9 19c-5 1.5-5-2.5-7-3m14 6v-3.9a3.4 3.4 0 0 0-.9-2.6c3.1-.3 6.4-1.5 6.4-7A5.4 5.4 0 0 0 20 4.8 5 5 0 0 0 19.9 1S18.7.6 16 2.5a13.4 13.4 0 0 0-7 0C6.3.6 5.1 1 5.1 1A5 5 0 0 0 5 4.8a5.4 5.4 0 0 0-1.5 3.7c0 5.4 3.3 6.6 6.4 7a3.4 3.4 0 0 0-.9 2.6V22",
    "lock": "M5 11h14v10H5zM8 11V7a4 4 0 0 1 8 0v4",
}
ic = lambda n: f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="{ICONS[n]}"/></svg>'  # noqa: E731


def head(slug: str, title: str, desc: str, kw: str, schema: dict | None) -> str:
    url = SITE + ("" if slug == "index.html" else slug)
    full = title if slug == "index.html" else f"{title} | {NAME}"
    ld = schema or {"@context": "https://schema.org", "@type": "TechArticle", "headline": title, "description": desc, "url": url,
                    "author": {"@type": "Person", "name": "jrnoorbaloch"}, "dateModified": date.today().isoformat()}
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(full)}</title>
<meta name="description" content="{e(desc)}">
<meta name="keywords" content="{e(kw)}">
<meta name="author" content="jrnoorbaloch"><meta name="robots" content="index,follow,max-image-preview:large">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website"><meta property="og:site_name" content="{NAME}"><meta property="og:title" content="{e(full)}">
<meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{url}"><meta property="og:image" content="{SITE}assets/og.png">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{e(full)}"><meta name="twitter:description" content="{e(desc)}"><meta name="twitter:image" content="{SITE}assets/og.png">
<meta name="theme-color" content="#0f1b33">
<link rel="icon" href="assets/favicon.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="assets/app-icon.png">
{FONTS}
<style>{CSS}</style>
<script type="application/ld+json">{json.dumps(ld)}</script>
</head>
<body>
<header class="nav"><div class="wrap"><a class="logo" href="index.html"><img src="assets/app-icon.png" alt="" width="30" height="30">{NAME}</a>
<nav aria-label="Main">{"".join(f'<a href="{h}" class="{"on" if h == slug else ""}">{t}</a>' for h, t in TOP_NAV)}</nav>
<a class="btn sm" href="{REPO}">{ic("gh")} GitHub</a><a class="btn sm p" href="download.html">Download</a></div></header>
"""


FOOT = f"""<footer><div class="wrap">
<div><a class="logo" href="index.html"><img src="assets/app-icon.png" alt="" width="30" height="30">{NAME}</a><p>Open-source and MIT licensed. Not affiliated with or endorsed by LinkedIn Corporation.</p></div>
<div><h4>Product</h4><a href="features.html">Features</a><a href="screens.html">Screens</a><a href="personas.html">Persona packs</a><a href="demo/">Live demo</a><a href="download.html">Download</a></div>
<div><h4>Docs</h4><a href="getting-started.html">Install</a><a href="skills.html">Skills</a><a href="claude.html">Claude & MCP</a><a href="api.html">API</a><a href="faq.html">FAQ</a></div>
<div><h4>Project</h4><a href="{REPO}">GitHub</a><a href="{REPO}/releases">Releases</a><a href="{REPO}/issues">Issues</a><a href="changelog.html">Changelog</a><a href="sitemap.xml">Sitemap</a></div>
</div></footer>
</body></html>
"""


def page(slug, title, desc, body, kw="", schema=None):
    (DOCS / slug).write_text(head(slug, title, desc, kw or KW, schema) + body + FOOT, encoding="utf-8")


def doc(slug, title, desc, body, kw=""):
    side = "".join(f"<h5>{g}</h5>" + "".join(f'<a href="{h}" class="{"on" if h == slug else ""}">{t}</a>' for h, t in items) for g, items in DOC_NAV)
    page(slug, title, desc, f'<div class="docs"><aside aria-label="Documentation">{side}</aside><article class="prose">{body}</article></div>', kw)


KW = ("LinkedIn AI agent, LinkedIn automation, AI LinkedIn post generator, LinkedIn post scheduler, LinkedIn profile optimizer, "
      "AI resume builder, LinkedIn content calendar, MCP server, Claude skill, open source, self-hosted")

SCREENS = [
    ("dashboard", "Dashboard", "Today's draft in a real LinkedIn preview, the dashed line where “see more” cuts in, what's scheduled next, your best posting slots and a setup checklist."),
    ("queue", "Approval queue", "A board with Drafts, Approved, Scheduled and Published. Nothing reaches LinkedIn until someone approves it."),
    ("editor", "Post editor", "Edit with a live preview and a character count, attach an image or PDF carousel, schedule, or copy a review link for a client."),
    ("create", "Skill gallery", "Every skill, grouped by what you're trying to do, with the skills for your persona pack shown first."),
    ("post-writer", "Post Writer", "Pick a topic, goal, hook formula and format. The draft lands in your queue with a first comment."),
    ("calendar", "Calendar", "Month view of scheduled and published posts. Drag a post to another day to move it."),
    ("analytics", "Analytics", "Impressions by week, an engagement heatmap by weekday and hour, and results by hook formula and pillar."),
    ("media", "Media studio", "Generate images with your own image model, upload your own, and turn carousel text into a branded PDF."),
    ("trends", "Trends", "Headlines from your RSS feeds, each one a click away from a post with your take."),
    ("packs", "Persona packs", "Eight ready-made setups: students, job seekers, developers, freelancers, sales, founders, experts and recruiters."),
    ("import", "Import", "Drop LinkedIn's own data export to fill your brand profile, voice samples and post history in one go."),
    ("integrations", "Notifications & integrations", "Approve drafts from Telegram or WhatsApp, post updates to Slack, send webhooks to Zapier, subscribe in Google Calendar."),
    ("workspaces", "Workspaces", "One per LinkedIn account: you, your Company Page, every client. Each with its own queue, brand and schedule."),
    ("team", "Team & roles", "Admins, editors who write, reviewers who approve and publish."),
    ("settings-model", "Bring your own model", "OpenAI, Claude, Gemini, Groq, OpenRouter, DeepSeek, any OpenAI-compatible endpoint or a local Ollama model."),
    ("brand", "Brand profile", "The voice, audience and pillars every skill writes from."),
    ("stories", "Story bank", "Real moments and numbers, so posts are built from your experience instead of invented."),
    ("network", "Network", "A small CRM for the people you're building relationships with, with follow-up dates."),
    ("documents", "Documents", "Resumes, cover letters, profile rewrites and plans, with Word export."),
    ("schedule", "Daily routine", "Choose the draft time, posting days and whether approved posts publish on their own."),
    ("dashboard-dark", "Dark mode", "Every screen has a dark theme that follows your system or your choice."),
    ("queue-urdu", "Five languages, right-to-left included", "English, Urdu, Hindi, Arabic and Spanish. Urdu and Arabic switch the whole layout to right-to-left."),
]


def build() -> None:
    reg = skills.list_skills()
    cats: dict[str, list[dict]] = {}
    for s in reg:
        cats.setdefault(s["category"], []).append(s)
    packs = personas.list_packs()

    # ------------------------------------------------------------- HOME
    gal_tabs = [s for s in SCREENS if s[0] in ("dashboard", "queue", "editor", "calendar", "analytics", "media", "packs", "integrations")]
    home = f"""
<main>
<div class="hero"><div class="wrap hero-grid">
 <div>
  <h1>Your LinkedIn, written for you. Posted only when you say so.</h1>
  <p class="lead">{NAME} drafts a post every morning in your voice, rewrites your profile, builds your resume and publishes through LinkedIn's official API once you approve. Use any AI model. Free and open source.</p>
  <div class="cta"><a class="btn p" href="download.html">{ic("download")} Download for free</a><a class="btn" href="demo/">Try the live demo</a></div>
  <div class="trust"><span>{ic("check")} Official LinkedIn API</span><span>{ic("check")} Runs on your computer</span><span>{ic("check")} No account to create</span></div>
 </div>
 <div class="stage" aria-label="A post moving from draft to approved to published">
  <div class="post"><div class="h"><div class="av">A</div><div><div class="n">Ayesha Khan</div><div class="s">Head of Growth · B2B SaaS</div></div></div>
   <div>We ran 41 onboarding experiments last quarter.<br><br>38 failed.<br><br>The 3 that worked had one thing in common: they removed a step instead of adding a feature.</div>
   <div class="fold"><span>…see more</span></div><div class="rest">→ Killed the “invite your team” screen (+18% activation)<br>→ Pre-filled the first project (+11%)</div>
   <div class="bar"><span>👍 Like</span><span>💬 Comment</span><span>🔁 Repost</span></div>
   <span class="stamp draft">Draft</span><span class="stamp ok">Approved</span><span class="stamp live">Published</span></div>
  <div class="pipe"><div><b>08:00</b>Drafted</div><div><b>08:06</b>Approved on phone</div><div><b>09:30</b>Scheduled</div><div><b>09:30</b>Live on LinkedIn</div></div>
 </div>
</div>
<div class="wrap"><div class="frame" style="margin-top:56px"><div class="dots"><i></i><i></i><i></i></div><img src="assets/screens/dashboard.png" alt="LinkedIn Agent dashboard with today's draft in a LinkedIn-style preview, stats and best posting times" width="2160" height="1350"></div>
<div class="works"><span>Works with</span><b>OpenAI</b><b>Claude</b><b>Gemini</b><b>Groq</b><b>OpenRouter</b><b>DeepSeek</b><b>Ollama</b><span>and any OpenAI-compatible API</span></div></div>
</div>

<section><div class="wrap">
 <div class="sec-h"><h2>What a day looks like</h2><p>Set it up once. After that, your part takes about a minute.</p></div>
 <div class="day">
  <div><time>08:00</time><h3>A draft is waiting</h3><p>Written from your pillars, your real stories and today's headlines in your field.</p></div>
  <div><time>08:06</time><h3>You approve it</h3><p>In the app, or straight from Telegram or WhatsApp. Edit first if you like.</p></div>
  <div><time>09:30</time><h3>It goes live</h3><p>Published at your best time, with the first comment added for you.</p></div>
  <div><time>Fri</time><h3>You see what worked</h3><p>Import LinkedIn's analytics and get a weekly report with next week's plan.</p></div>
 </div>
</div></section>

<section style="padding-top:0"><div class="wrap">
 <div class="sec-h"><h2>See every screen</h2><p>A desktop app, a web portal, the same modern interface. Light and dark, five languages.</p></div>
 <div class="gal-tabs" role="tablist">{"".join(f'<button role="tab" aria-selected="{"true" if i == 0 else "false"}" data-shot="{k}" data-cap="{e(c)}">{e(t)}</button>' for i, (k, t, c) in enumerate(gal_tabs))}</div>
 <div class="frame"><div class="dots"><i></i><i></i><i></i></div><img id="galimg" src="assets/screens/{gal_tabs[0][0]}.png" alt="{e(gal_tabs[0][1])} screen" width="2160" height="1350"></div>
 <p class="gal-cap" id="galcap">{e(gal_tabs[0][2])}</p>
 <p><a href="screens.html">All {len(SCREENS)} screens</a></p>
</div></section>

<section style="padding-top:0"><div class="wrap">
 <div class="sec-h"><h2>Everything you do on LinkedIn, in one place</h2><p>{len(reg)} skills across content, engagement, networking, your profile, your career and your company page.</p></div>
 <div class="flist">
  <div><span class="ic">{ic("spark")}</span><div><h3>Posts that sound like you</h3><p>20 proven hook formulas, a humanizer that strips AI tells, and a preview that shows exactly where LinkedIn cuts to “see more”.</p></div></div>
  <div><span class="ic">{ic("shield")}</span><div><h3>Nothing posts without approval</h3><p>Enforced in the app, the API and the MCP server. Share a review link with a client who doesn't have an account.</p></div></div>
  <div><span class="ic">{ic("upload")}</span><div><h3>Set up in one drop</h3><p>Import LinkedIn's own data export. Your profile, experience, skills and past posts become your brand profile and voice.</p></div></div>
  <div><span class="ic">{ic("image")}</span><div><h3>Images and carousels</h3><p>Generate images with your own model and turn any outline into a branded PDF carousel, posted as a document.</p></div></div>
  <div><span class="ic">{ic("phone")}</span><div><h3>Approve from your phone</h3><p>Drafts arrive in Telegram with Approve and Reject buttons, or on WhatsApp where you reply APPROVE.</p></div></div>
  <div><span class="ic">{ic("cal")}</span><div><h3>Calendar and scheduling</h3><p>Drag posts between days and subscribe in Google Calendar. The scheduler posts at your best times.</p></div></div>
  <div><span class="ic">{ic("doc")}</span><div><h3>Profile, resume and job search</h3><p>Headline A/B lab, full profile rewrite, ATS resume with Word export, cover letters, job match and interview prep.</p></div></div>
  <div><span class="ic">{ic("users")}</span><div><h3>Teams, clients and Company Pages</h3><p>A workspace per account, roles for writers and reviewers, and Company Page posting once LinkedIn approves your app.</p></div></div>
  <div><span class="ic">{ic("chart")}</span><div><h3>Know your best time to post</h3><p>An engagement heatmap by weekday and hour, plus what's working by hook formula and pillar.</p></div></div>
  <div><span class="ic">{ic("plug")}</span><div><h3>Built for AI agents too</h3><p>An MCP server for Claude, Cursor and any agent, a Claude skill with every playbook, and a REST API.</p></div></div>
 </div>
 <p style="margin-top:26px"><a href="features.html">All features</a> · <a href="skills.html">All {len(reg)} skills</a></p>
</div></section>

<section style="padding-top:0"><div class="wrap">
 <div class="sec-h"><h2>Made for whoever you are</h2><p>Pick a persona pack and the agent starts with the right pillars, skills and trend feeds.</p></div>
 <div class="ppl">{"".join(f'<a href="personas.html#{p["id"]}"><span class="e">{p["emoji"]}</span><h3>{e(p["name"])}</h3><p>{e(p["description"])}</p></a>' for p in packs)}</div>
</div></section>

<section style="padding-top:0"><div class="wrap">
 <div class="sec-h"><h2>Run it your way</h2><p>Same app, same data, four ways in.</p></div>
 <div class="ways">
  <div><h3>Desktop app</h3><p>Install on Windows, macOS or Linux and it opens in its own window.</p><a class="btn sm p" href="download.html">Download</a></div>
  <div><h3>Python</h3><p>One command, then open the portal in your browser.</p><pre style="padding:10px 12px;font-size:12.5px"><code>pip install git+{REPO.replace("https://", "https://")}</code></pre></div>
  <div><h3>Docker or cloud</h3><p>Self-host for a team, or deploy to Render or Railway.</p><a class="btn sm" href="self-hosting.html">Self-hosting guide</a></div>
  <div><h3>Claude and MCP</h3><p>Use every skill from Claude, Claude Code, Cursor or any MCP client.</p><a class="btn sm" href="claude.html">Connect an agent</a></div>
 </div>
</div></section>

<section style="padding-top:0"><div class="wrap">
 <div class="sec-h"><h2>Straight about what LinkedIn allows</h2><p>No scraping and no browser bots, so your account isn't put at risk.</p></div>
 <table><tr><th>What you want</th><th>Status</th><th>How {NAME} handles it</th></tr>
 <tr><td>Post as yourself, with images or PDF carousels</td><td class="yes">Yes</td><td>Official “Share on LinkedIn” access, which any developer app gets</td></tr>
 <tr><td>Add the first comment</td><td class="yes">Yes</td><td>Posted automatically right after your post</td></tr>
 <tr><td>Post as a Company Page</td><td class="maybe">After approval</td><td>LinkedIn's Community Management API. Apply once, then switch it on</td></tr>
 <tr><td>Edit your profile</td><td class="no">No API</td><td>The agent writes every section and you paste it in</td></tr>
 <tr><td>Read your analytics</td><td class="no">Restricted</td><td>Import LinkedIn's analytics export and the agent learns from it</td></tr>
 <tr><td>Send DMs and connection requests</td><td class="no">No API</td><td>The agent drafts them and you send them</td></tr></table>
</div></section>

<section class="dark-band"><div class="wrap final"><h2>Write less. Post more. Stay in charge.</h2><p>Free, open source and private by default. Your keys and your data stay on your machine.</p>
 <div class="cta" style="justify-content:center"><a class="btn p" href="download.html">{ic("download")} Download {NAME}</a><a class="btn" href="{REPO}" style="background:transparent;color:#fff;border-color:#3a4a73">{ic("gh")} Star on GitHub</a></div></div></section>
</main>
<script>
const tabs=[...document.querySelectorAll('[data-shot]')],img=document.getElementById('galimg'),cap=document.getElementById('galcap');
tabs.forEach(b=>b.addEventListener('click',()=>{{tabs.forEach(x=>x.setAttribute('aria-selected',x===b));img.src='assets/screens/'+b.dataset.shot+'.png';img.alt=b.textContent+' screen';cap.textContent=b.dataset.cap;}}));
</script>"""
    page("index.html", f"{NAME}: open-source AI agent for LinkedIn posts, profile & resume", TAGLINE, home,
         schema={"@context": "https://schema.org", "@type": "SoftwareApplication", "name": NAME, "applicationCategory": "BusinessApplication",
                 "operatingSystem": "Windows, macOS, Linux, Docker", "description": TAGLINE, "url": SITE, "softwareVersion": __version__,
                 "license": "https://opensource.org/licenses/MIT", "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
                 "downloadUrl": SITE + "download.html", "screenshot": SITE + "assets/screens/dashboard.png", "codeRepository": REPO})

    # ------------------------------------------------------------- FEATURES
    groups = [
        ("Write", [("Daily draft", "Every posting day at your chosen time, a post is drafted from a pillar you haven't used lately, an unused story and today's headlines."),
                   ("Post Writer with 20 hook formulas", "Contrarian, time anchor, data reveal, R.I.P., anaphora and 15 more, chosen by your goal: comments, reposts, saves or leads."),
                   ("Humanizer and audit", "Scores a draft out of 100 and rewrites it without the phrases that make posts sound machine-written."),
                   ("Carousels, polls, articles and video scripts", "From one topic to a slide-by-slide carousel, a poll, a long-form article or a 60-second script."),
                   ("Repurposer and evergreen recycler", "Turn a blog, thread or transcript into a native post, or bring back your best posts with a new hook.")]),
        ("Approve and publish", [("Approval queue", "Drafts, Approved, Scheduled and Published on one board. The API refuses to publish anything unapproved."),
                   ("Live LinkedIn preview", "See your post the way LinkedIn shows it, with the dashed line where “see more” cuts in."),
                   ("Client review links", "Send a signed link that works for 14 days. The client approves or asks for changes without an account."),
                   ("Phone approvals", "Telegram buttons or WhatsApp replies move a draft to approved."),
                   ("Calendar", "Drag to reschedule, and subscribe from Google Calendar, Outlook or Apple Calendar.")]),
        ("Media", [("Image generation", "Uses your own OpenAI-compatible image model. A skill writes the prompt and alt text for you."),
                   ("PDF carousel builder", "Five themes, 1080×1350 slides, your name and page numbers, uploaded to LinkedIn as a document post."),
                   ("Your own uploads", "Attach any image or PDF from your computer.")]),
        ("Profile and career", [("Profile Optimizer", "Score, three headline options, a seven-step About section, result-led experience bullets, skills, Featured and banner copy."),
                   ("Headline A/B lab", "Ten scored headline variants and a two-week test plan."),
                   ("Resume, cover letter and job match", "ATS-friendly resume with Word export, tailored letters and a gap analysis against any job description."),
                   ("Interview prep and salary negotiation", "Likely questions with STAR answers from your real experience, and a negotiation script.")]),
        ("Grow and learn", [("Import from LinkedIn", "Your data export fills the brand profile, voice samples and post history. Your analytics export fills the metrics."),
                   ("Analytics", "Weekly impressions, a weekday-by-hour heatmap, and results by hook formula and pillar."),
                   ("Trends", "RSS headlines from your field, each turned into a post angle in one click."),
                   ("Story bank and interviewer", "The agent interviews you and keeps your real stories, so posts never invent facts.")]),
        ("Teams and agencies", [("Workspaces", "One per LinkedIn account, each with its own brand, LinkedIn connection, queue and schedule."),
                   ("Roles", "Admins, editors who write, reviewers who approve and publish."),
                   ("Company Pages and advocacy", "Page posts, hiring posts, and one update turned into personal posts for every teammate."),
                   ("Webhooks, Slack, CSV", "Send every event to Zapier, Make or n8n, post to Slack, export to Sheets.")]),
        ("Everywhere", [("Desktop app", "Windows installer, macOS app and Linux build, opening in a native window."),
                   ("Any model", "OpenAI, Claude, Gemini, Groq, OpenRouter, DeepSeek, Ollama or any compatible endpoint."),
                   ("Claude skill, subagent and MCP server", "Every skill available to Claude, Claude Code, Cursor and other agents."),
                   ("Five languages", "English, Urdu, Hindi, Arabic and Spanish, with right-to-left layouts.")]),
    ]
    feat = f'<main><div class="wrap" style="padding-top:60px"><div class="sec-h"><h1 style="font-size:clamp(40px,5vw,64px)">Features</h1><p>Everything in {NAME} {__version__}.</p></div>'
    for g, items in groups:
        feat += f'<h2 style="font-size:30px;margin:46px 0 4px">{g}</h2><div class="flist">' + "".join(
            f'<div><span class="ic">{ic("check")}</span><div><h3>{e(t)}</h3><p>{e(d)}</p></div></div>' for t, d in items) + "</div>"
    feat += f'<p style="margin:50px 0 90px"><a class="btn p" href="download.html">Download</a> <a class="btn" href="screens.html">See the screens</a></p></div></main>'
    page("features.html", "Features", f"All features of {NAME}: daily AI drafts, approval queue, images and PDF carousels, profile optimizer, resume builder, analytics, teams, desktop app and MCP.", feat)

    # ------------------------------------------------------------- SCREENS
    scr = f'<main><div class="wrap screens" style="padding-top:60px"><div class="sec-h"><h1 style="font-size:clamp(40px,5vw,64px)">Screens</h1><p>Every screen of the app, as it looks after you install it. <a href="demo/">Open the live demo</a> to click through them yourself.</p></div>'
    for k, t, c in SCREENS:
        scr += f'<figure id="{k}"><div class="frame"><div class="dots"><i></i><i></i><i></i></div><img loading="lazy" src="assets/screens/{k}.png" alt="{e(t)} screen of {NAME}" width="2160" height="1350"></div><figcaption><b>{e(t)}</b>{e(c)}</figcaption></figure>'
    scr += '<figure id="mobile"><div style="max-width:340px"><img class="shot" loading="lazy" src="assets/screens/mobile.png" alt="LinkedIn Agent on a phone" width="780" height="1688"></div><figcaption><b>On your phone</b>The portal works on small screens too, for checking the queue on the go.</figcaption></figure></div></main>'
    page("screens.html", "Screens", f"Screenshots of every {NAME} screen: dashboard, approval queue, post editor, calendar, analytics, media studio, persona packs, import, integrations, team and settings.", scr)

    # ------------------------------------------------------------- PERSONAS
    per = '<main><div class="wrap" style="padding-top:60px"><div class="sec-h"><h1 style="font-size:clamp(40px,5vw,64px)">Made for you</h1><p>Each persona pack sets your content pillars, tone and goals, adds trend feeds, and puts the skills you need first. Apply one from the Packs screen.</p></div>'
    titles = {s["id"]: s["title"] for s in reg}
    for p in packs:
        per += f'''<section id="{p["id"]}" style="padding:36px 0;border-top:1px solid var(--line)"><div class="grid2" style="align-items:start"><div><span style="font-size:40px">{p["emoji"]}</span><h2 style="font-size:32px;margin-top:8px">{e(p["name"])}</h2><p class="lead" style="font-size:18px">{e(p["description"])}</p></div>
<div><h3>Pillars</h3><p>{e(p["pillars"])}</p><h3>Skills you'll use most</h3><p>{", ".join(e(titles.get(s, s)) for s in p["skills"])}</p><h3>A typical week</h3><p>{e(" → ".join(p["week"]))}</p></div></div></section>'''
    per += '<p style="margin:30px 0 90px"><a class="btn p" href="download.html">Download</a></p></div></main>'
    page("personas.html", "For students, job seekers, developers, freelancers, sales, founders, experts and recruiters",
         f"{NAME} persona packs: ready-made LinkedIn strategies and skills for students, job seekers, developers, freelancers, sales, founders, doctors and teachers, and recruiters.", per)

    # ------------------------------------------------------------- DOWNLOAD
    dl = f"""<main><div class="wrap" style="padding:60px 24px 90px">
<div class="sec-h"><h1 style="font-size:clamp(40px,5vw,64px)">Download {NAME}</h1><p>Free and open source. Version {__version__}. Your data stays on your computer.</p></div>
<div class="dlrow">
 <div class="dl" data-os="win"><span class="tag" hidden>Recommended for you</span><h3>Windows</h3><p>Windows 10 or 11. An installer that adds a Start menu shortcut.</p><a class="btn p" href="{DL}LinkedIn-Agent-Setup.exe">{ic("download")} Download installer</a><p><a href="{DL}LinkedIn-Agent-Windows-portable.zip">Portable ZIP</a></p></div>
 <div class="dl" data-os="mac"><span class="tag" hidden>Recommended for you</span><h3>macOS</h3><p>macOS 12 or later, Apple silicon. Open the DMG and drag to Applications.</p><a class="btn p" href="{DL}LinkedIn-Agent-macOS.dmg">{ic("download")} Download for Mac</a><p class="faint" style="font-size:13.5px">First launch: right-click the app and choose Open.</p></div>
 <div class="dl" data-os="linux"><span class="tag" hidden>Recommended for you</span><h3>Linux</h3><p>x86-64. Extract and run. Opens in your browser.</p><a class="btn p" href="{DL}LinkedIn-Agent-Linux.tar.gz">{ic("download")} Download for Linux</a></div>
</div>
<div class="note" style="margin-top:26px">Installers are built automatically for each release on GitHub. If a link says “Not found”, the build for the newest version is still running. <a href="{REPO}/releases">See all releases</a> or install with Python below.</div>
<h2 style="font-size:30px;margin:50px 0 12px">Other ways to install</h2>
<div class="grid2"><div><h3>Python 3.10+</h3><pre><code>pip install git+{REPO}
linkedin-agent serve        # web portal
linkedin-agent-desktop      # native window</code></pre></div>
<div><h3>Docker</h3><pre><code>docker run -d -p 8787:8787 -v la-data:/data \\
  --env-file .env ghcr.io/jrnoorbaloch/linkedin-agent</code></pre></div></div>
<h2 style="font-size:30px;margin:50px 0 12px">After installing</h2>
<p>Follow <a href="getting-started.html">Install & set up</a>: connect a model, import your LinkedIn data, choose a pack, connect LinkedIn. It takes about ten minutes.</p>
</div></main>
<script>
const ua=navigator.userAgent, os=/Win/.test(ua)?"win":/Mac/.test(ua)?"mac":/Linux/.test(ua)?"linux":"";
const c=document.querySelector('[data-os="'+os+'"]'); if(c){{c.classList.add('rec');c.querySelector('.tag').hidden=false;}}
</script>"""
    page("download.html", "Download for Windows, macOS and Linux", f"Download {NAME} {__version__} for Windows, macOS and Linux, or install with pip or Docker. Free and open source.", dl,
         kw="download LinkedIn agent, LinkedIn automation app Windows, LinkedIn scheduler Mac, LinkedIn AI desktop app")

    # ------------------------------------------------------------- DOCS PAGES
    doc("docs.html", "Documentation", f"How to install, set up and use {NAME}.", f"""
<h1>Documentation</h1><p class="lead">{NAME} is an AI agent for LinkedIn that runs on your computer or your server. It writes in your voice with the model you choose, and publishes through LinkedIn's official API after you approve.</p>
<h2>How it fits together</h2>
<p>One engine holds your workspaces, brand profiles, story bank, queue and schedule in a local database, with keys and tokens encrypted. Four ways in all share it:</p>
<ul><li><b>Desktop app and web portal</b>: the interface shown on <a href="screens.html">Screens</a>.</li><li><b>MCP server</b>: tools for Claude, Cursor and any MCP client.</li><li><b>Claude skill and subagent</b>: playbooks that tell Claude how to do LinkedIn well.</li><li><b>REST API and CLI</b>: for scripts and automations.</li></ul>
<h2>Start here</h2><ol><li><a href="getting-started.html">Install & set up</a></li><li><a href="linkedin-app.html">Create your LinkedIn app</a></li><li><a href="models.html">Connect a model</a></li><li><a href="import-guide.html">Import your LinkedIn data</a></li><li><a href="workflows.html">Learn the daily workflow</a></li></ol>""")

    doc("getting-started.html", "Install & set up", f"Install {NAME} on Windows, macOS, Linux, with pip or Docker, and set it up in ten minutes.", f"""
<h1>Install & set up</h1><p class="lead">About ten minutes from download to your first approved post.</p>
<h2>1. Install</h2>
<p><b>Desktop app:</b> get the installer for your system from <a href="download.html">Download</a>. It opens in its own window.</p>
<p><b>Python:</b></p><pre><code>pip install git+{REPO}
linkedin-agent serve          # open http://localhost:8787</code></pre>
<p><b>Docker:</b> see <a href="self-hosting.html">Self-hosting</a>.</p>
<h2>2. Connect a model</h2><p>Settings → Language model. Pick a provider, paste your key, then click <i>Test connection</i>. Details: <a href="models.html">Connect any LLM</a>.</p>
<h2>3. Import your LinkedIn data</h2><p>Import → drop LinkedIn's data export ZIP. Your brand profile, profile text, voice samples and post history fill in. See <a href="import-guide.html">Import your data</a>.</p>
<h2>4. Pick a persona pack</h2><p>Packs → choose the one that fits you. See <a href="personas.html">persona packs</a>.</p>
<h2>5. Connect LinkedIn</h2><p>Create your LinkedIn developer app (<a href="linkedin-app.html">step-by-step</a>), add its keys to <code>.env</code>, then Settings → LinkedIn → Connect.</p>
<h2>6. Draft, approve, publish</h2><p>Dashboard → <i>Draft today's post</i>. Review it in the editor, then approve, schedule, or publish now.</p>
<h2>Configuration</h2><table><tr><th>Variable</th><th>Default</th><th>Purpose</th></tr>
<tr><td><code>LA_HOST</code> / <code>LA_PORT</code></td><td>127.0.0.1 / 8787</td><td>Where the portal listens</td></tr>
<tr><td><code>LA_BASE_URL</code></td><td>http://localhost:8787</td><td>Public URL when hosted. Used for OAuth, review links and webhooks</td></tr>
<tr><td><code>LA_API_TOKEN</code></td><td>none</td><td>Requires a token for the API. Recommended on servers</td></tr>
<tr><td><code>LA_DATA_DIR</code></td><td>~/.linkedin-agent</td><td>Database, media and encryption key</td></tr>
<tr><td><code>LA_ACCOUNT</code></td><td>1</td><td>Default workspace for the MCP server</td></tr>
<tr><td><code>LINKEDIN_CLIENT_ID</code> / <code>_SECRET</code></td><td>none</td><td>Your LinkedIn app</td></tr>
<tr><td><code>LINKEDIN_API_VERSION</code></td><td>202608</td><td>The LinkedIn-Version header</td></tr>
<tr><td><code>LINKEDIN_ORG_ENABLED</code></td><td>0</td><td>Company Page posting, after approval</td></tr></table>""")

    doc("linkedin-app.html", "Create your LinkedIn app", "Step-by-step: create a LinkedIn developer app with Sign In with LinkedIn and Share on LinkedIn, and connect it to LinkedIn Agent.", """
<h1>Create your LinkedIn app</h1><p class="lead">The agent posts through your own LinkedIn developer app. Personal posting needs no review.</p>
<ol><li>Go to <a href="https://www.linkedin.com/developers/apps">linkedin.com/developers/apps</a> and click <b>Create app</b>. Link it to a LinkedIn Page you admin. A small placeholder page works.</li>
<li>Open the <b>Products</b> tab and add <b>Sign In with LinkedIn using OpenID Connect</b> and <b>Share on LinkedIn</b>.</li>
<li>Open the <b>Auth</b> tab and add the redirect URL <code>http://localhost:8787/auth/linkedin/callback</code>. On a server, use your <code>LA_BASE_URL</code> followed by <code>/auth/linkedin/callback</code>.</li>
<li>Copy the Client ID and Client Secret into <code>.env</code>:</li></ol>
<pre><code>LINKEDIN_CLIENT_ID=your-client-id
LINKEDIN_CLIENT_SECRET=your-client-secret</code></pre>
<p>Restart the app, then Settings → LinkedIn → <b>Connect LinkedIn</b>. Access lasts about 60 days, and the app shows how many days are left.</p>
<h2>Company Pages</h2><p>Request the <b>Community Management API</b> product for your app. After LinkedIn approves it, set <code>LINKEDIN_ORG_ENABLED=1</code>, reconnect, and use Settings → LinkedIn → Load my pages.</p>
<div class="note">Each workspace connects its own LinkedIn account, so one app can serve you and your clients.</div>""")

    preset_rows = "".join(f"<tr><td>{k}</td><td><code>{v['base_url'] or 'your URL'}</code></td><td><code>{v['model'] or '–'}</code></td></tr>" for k, v in llm.PRESETS.items())
    doc("models.html", "Connect any LLM", "Use OpenAI, Claude, Gemini, Groq, OpenRouter, DeepSeek, Ollama or any OpenAI-compatible model with LinkedIn Agent.", f"""
<h1>Connect any LLM</h1><p class="lead">Settings → Language model. Keys are encrypted on your machine.</p>
<table><tr><th>Provider</th><th>Base URL</th><th>Example model</th></tr>{preset_rows}</table>
<p>Choose <b>custom</b> for any OpenAI-compatible endpoint, such as LM Studio, vLLM, Together, Mistral or Azure OpenAI. For a fully local setup, install <a href="https://ollama.com">Ollama</a> and pick <b>ollama</b>.</p>
<h2>Image model</h2><p>The Media studio uses any OpenAI-compatible Images API, for example <code>gpt-image-1</code> or <code>dall-e-3</code>. Set it in Settings → Language model → Image model.</p>
<h2>From Claude or another agent</h2><p>When an agent drives LinkedIn Agent over MCP, it can write the text itself with <code>get_skill_prompt</code> and <code>save_draft</code>. No model key is needed in that case.</p>""")

    rows = ""
    for c, items in cats.items():
        rows += f'<h2 id="{c.lower().replace(" ", "-").replace("&", "and")}">{e(c)}</h2><table><tr><th style="width:26%">Skill</th><th>What it does</th></tr>' + "".join(
            f'<tr><td><b>{e(s["title"])}</b><br><code>{s["id"]}</code></td><td>{e(s["description"])}</td></tr>' for s in items) + "</table>"
    doc("skills.html", "All skills", f"The {len(reg)} skills in {NAME}: post writer, hooks, humanizer, carousel, video script, profile optimizer, headline A/B, resume, job match, interview prep, social selling, recruiter outreach and more.",
        f'<h1>All skills</h1><p class="lead">{len(reg)} skills. Each one is in the app (Create), over MCP (<code>run_skill</code>), in the CLI (<code>linkedin-agent run &lt;id&gt;</code>) and in the Claude skill.</p>{rows}'
        '<h2>Add your own</h2><p>Append a <code>Skill(...)</code> to <code>SKILLS</code> in <code>linkedin_agent/skills.py</code>. The app form, the API and the MCP tool pick it up automatically.</p>')

    doc("workflows.html", "Daily workflow", "The LinkedIn Agent daily routine: morning draft, approval, scheduling, publishing and the weekly review.", """
<h1>Daily workflow</h1><p class="lead">The routine the agent is built around.</p>
<h2>Every posting day</h2><ol><li><b>Draft time (08:00 by default):</b> the agent refreshes your trend feeds and drafts a post from a pillar you haven't used lately, an unused story, and your recent posts so it doesn't repeat itself.</li>
<li><b>You get notified</b> in Telegram, WhatsApp or Slack if you've connected one.</li><li><b>You review</b> in the editor or on your phone: edit, add media, then approve.</li><li><b>It publishes</b> at the time you scheduled, or at your publish time if auto-publish is on. The first comment follows.</li></ol>
<h2>Every week</h2><ol><li>Import LinkedIn's analytics export.</li><li>Run the Weekly Performance Report.</li><li>Run the 7-Day Content Planner with what you learned.</li><li>Spend 15 minutes a day commenting, with Comment Drafter's help.</li></ol>
<h2>Settings that shape it</h2><p>Settings → Schedule: draft time, timezone, posting days, auto-publish and publish time. Drafts never publish by themselves. Only approved posts do.</p>""")

    doc("import-guide.html", "Import your data", "Import your LinkedIn data export and post analytics into LinkedIn Agent.", """
<h1>Import your data</h1><p class="lead">The fastest way to set up, and the only way to get analytics, since LinkedIn doesn't share them with apps.</p>
<h2>Your LinkedIn data export</h2><ol><li>On LinkedIn: Settings → Data privacy → <b>Get a copy of your data</b>.</li><li>Choose the larger archive, which includes your posts. LinkedIn emails a link, usually within a day.</li><li>In the app: Import → drop the ZIP.</li></ol>
<p>The agent reads <code>Profile</code>, <code>Positions</code>, <code>Education</code>, <code>Certifications</code>, <code>Skills</code> and <code>Shares</code>. It fills your name, headline, industry and full profile text, picks your longest recent posts as voice samples, and adds your past posts to History.</p>
<h2>Post analytics</h2><ol><li>On LinkedIn: Me → Posts & activity → Analytics.</li><li>Click <b>Export</b> and download the XLSX.</li><li>In the app: Import → drop the file.</li></ol>
<p>Rows are matched to your posts by URL. Unmatched rows are added to history so they count toward your best posting times.</p>
<div class="note">Files are processed on your machine. Nothing is uploaded anywhere.</div>""")

    doc("approvals.html", "Approvals on your phone", "Approve LinkedIn drafts from Telegram or WhatsApp, share client review links, and send updates to Slack and webhooks.", """
<h1>Approvals on your phone</h1><p class="lead">Settings → Notifications & integrations.</p>
<h2>Telegram</h2><ol><li>Message <b>@BotFather</b>, create a bot and copy its token.</li><li>Send your bot any message, then find your chat ID (for example with <b>@userinfobot</b>).</li><li>Paste both, turn it on, and save.</li></ol>
<p>Each new draft arrives with <b>Approve</b> and <b>Reject</b> buttons. This works on a laptop too. No public URL is needed.</p>
<h2>WhatsApp</h2><ol><li>Set up the WhatsApp Cloud API in Meta for Developers and copy the phone number ID and an access token.</li><li>Enter them with your own WhatsApp number and a verify word of your choice.</li><li>Point the webhook to <code>LA_BASE_URL/webhooks/whatsapp</code>. This needs a public URL, so see <a href="self-hosting.html">Self-hosting</a>.</li></ol>
<p>Reply <code>APPROVE 12</code> or <code>REJECT 12 too long</code>. Only messages from your number are accepted.</p>
<h2>Client review links</h2><p>In the post editor, click <b>Share for review</b>. The link is signed, lasts 14 days, and lets anyone with it approve or ask for changes. Their note shows up on the post.</p>
<h2>Slack, webhooks, calendar</h2><p>Slack gets updates through an incoming webhook. Webhooks send JSON for every event to Zapier, Make or n8n. The private calendar link shows scheduled and published posts in Google Calendar, Outlook or Apple Calendar.</p>""")

    doc("teams.html", "Teams & workspaces", "Use LinkedIn Agent for multiple LinkedIn accounts, clients and Company Pages, with admin, editor and reviewer roles.", """
<h1>Teams & workspaces</h1>
<h2>Workspaces</h2><p>A workspace is one LinkedIn account: you, your Company Page, or a client. Each has its own brand profile, story bank, queue, media, LinkedIn connection, schedule and notifications. Switch from the top of the sidebar.</p>
<h2>Team sign-in</h2><p>Out of the box the app is in single-user mode. Settings → Team → <b>Create the admin account</b> turns on sign-in. Then add teammates with a temporary password.</p>
<table><tr><th>Role</th><th>Can</th></tr><tr><td>Admin</td><td>Everything, including settings, LinkedIn connections, workspaces and team</td></tr>
<tr><td>Editor</td><td>Write and edit drafts, documents, stories and media</td></tr><tr><td>Reviewer</td><td>Approve, schedule, reject and publish</td></tr></table>
<p>For clients without an account, use review links (see <a href="approvals.html">Approvals</a>).</p>""")

    tools = ["status", "list_skills", "run_skill", "get_skill_prompt", "save_draft", "list_posts", "approve_post", "publish_post", "attach_media",
             "render_carousel_pdf", "generate_post_image", "record_metrics", "get_analytics", "refresh_trends", "get_brand_profile", "update_brand_profile",
             "add_story", "list_documents", "save_document", "list_persona_packs", "apply_persona_pack", "import_linkedin_export", "import_analytics_file",
             "list_workspaces", "switch_workspace"]
    doc("claude.html", "Claude skill & MCP", "Use LinkedIn Agent from Claude, Claude Code, Cursor or any MCP client: Claude skill, subagent and MCP server setup.", f"""
<h1>Claude skill, subagent & MCP</h1><p class="lead">Let your AI assistant run your LinkedIn, with the same approval gate.</p>
<h2>Claude skill</h2><p>One skill that bundles every playbook (hooks, writing, humanizer, profile, career, engagement, networking, company page, analytics, publishing) and routes each request to the right one.</p>
<ul><li><b>Claude apps:</b> download <a href="downloads/linkedin-agent-skill.zip">linkedin-agent-skill.zip</a>, then Settings → Capabilities → Skills → Upload.</li><li><b>Claude Code:</b> <code>cp -r skill/linkedin-agent ~/.claude/skills/</code></li></ul>
<h2>Subagent (Claude Code)</h2><pre><code>cp agents/linkedin-agent.md ~/.claude/agents/</code></pre><p>Then ask: “Use the linkedin-agent subagent to plan and draft my week.”</p>
<h2>MCP server</h2><pre><code>{{"mcpServers": {{"linkedin-agent": {{"command": "linkedin-agent", "args": ["mcp"]}}}}}}</code></pre>
<p>Claude Code: <code>claude mcp add linkedin-agent -- linkedin-agent mcp</code>. Over HTTP: <code>linkedin-agent mcp --http</code>.</p>
<h3>{len(tools)} tools</h3><p>{", ".join(f"<code>{t}</code>" for t in tools)}</p>
<div class="note"><code>publish_post</code> refuses anything that hasn't been approved, and the skill tells the model to approve only after you say yes to the exact text.</div>""")

    eps = [("GET", "/api/dashboard", "Counts, upcoming posts, best slots"), ("GET/POST", "/api/skills[/{id}]", "List skills, or run one"),
           ("GET/POST", "/api/posts", "List (status, start, end) or create a draft"), ("PATCH/DELETE", "/api/posts/{id}", "Edit, attach media, set metrics, delete"),
           ("POST", "/api/posts/{id}/approve", "Approve, or schedule with scheduled_at"), ("POST", "/api/posts/{id}/publish", "Publish an approved post"),
           ("POST", "/api/posts/{id}/share", "Create a signed client review link"), ("GET/POST", "/api/media, /api/media/upload|generate|carousel", "Images and PDF carousels"),
           ("POST", "/api/import/linkedin, /api/import/analytics", "Import exports (base64 files)"), ("GET/POST", "/api/packs[/{id}]", "Persona packs"),
           ("GET/POST", "/api/trends, /api/trends/feeds|refresh", "Trend feeds"), ("GET", "/api/analytics", "Heatmap, top posts, by hook and pillar"),
           ("GET/POST", "/api/accounts", "Workspaces (send X-Account header to choose one)"), ("GET/POST", "/api/team, /api/auth/*", "Users, roles, sign-in"),
           ("GET/POST", "/api/integrations", "Telegram, WhatsApp, Slack, webhooks, calendar link"), ("GET", "/calendar/{acct}/{token}.ics", "Calendar subscription"),
           ("GET", "/api/export/posts.csv", "CSV export"), ("GET/POST", "/api/brand, /api/stories, /api/contacts, /api/documents", "Library"),
           ("GET/POST", "/api/llm, /api/image-model, /api/schedule", "Settings")]
    doc("api.html", "REST API & CLI", "LinkedIn Agent REST API and CLI reference.", f"""
<h1>REST API & CLI</h1><p class="lead">The app is a thin layer over this API. Interactive OpenAPI docs are at <code>/docs</code> on your install.</p>
<p>Authentication: send <code>X-API-Token</code> if <code>LA_API_TOKEN</code> is set, or sign in for a session cookie in team mode. Choose a workspace with <code>X-Account: 2</code>.</p>
<table><tr><th>Method</th><th>Path</th><th>Purpose</th></tr>{"".join(f"<tr><td><code>{m}</code></td><td><code>{e(p)}</code></td><td>{e(d)}</td></tr>" for m, p, d in eps)}</table>
<h2>Example</h2><pre><code>curl -X POST localhost:8787/api/skills/post_writer -H 'content-type: application/json' \\
  -d '{{"topic":"What 100 sales calls taught me","goal":"comments"}}'
curl -X POST localhost:8787/api/posts/12/approve -H 'content-type: application/json' -d '{{}}'
curl -X POST localhost:8787/api/posts/12/publish</code></pre>
<h2>CLI</h2><pre><code>linkedin-agent serve [--host 0.0.0.0 --port 8787]
linkedin-agent-desktop
linkedin-agent mcp [--http]
linkedin-agent skills
linkedin-agent run post_writer -i topic="Hiring lessons" -i goal=comments</code></pre>""")

    doc("self-hosting.html", "Self-hosting", "Self-host LinkedIn Agent with Docker, Render or Railway, for teams, agencies and phone approvals.", f"""
<h1>Self-hosting</h1><p class="lead">Run it on a server for a team, for clients, or so WhatsApp approvals have a public URL.</p>
<h2>Docker</h2><pre><code>git clone {REPO} && cd linkedin-agent
cp .env.example .env      # set LA_BASE_URL, LA_API_TOKEN, LinkedIn keys
docker compose up -d</code></pre>
<p>Or use the published image: <code>ghcr.io/jrnoorbaloch/linkedin-agent:latest</code>. Data lives in the <code>/data</code> volume.</p>
<h2>One-click deploys</h2><p><a class="btn sm" href="https://render.com/deploy?repo={REPO}">Deploy to Render</a> <a class="btn sm" href="https://railway.app/new/template?template={REPO}">Deploy to Railway</a></p>
<p>Both read the Dockerfile. Add a persistent disk at <code>/data</code>, then set the environment variables.</p>
<h2>Checklist</h2><ul><li>Serve it over HTTPS behind a reverse proxy (Caddy, Nginx, or the platform's).</li><li>Set <code>LA_BASE_URL</code> to the public URL and add <code>LA_BASE_URL/auth/linkedin/callback</code> to your LinkedIn app.</li>
<li>Create the admin account (Settings → Team) or set <code>LA_API_TOKEN</code>.</li><li>Back up <code>/data</code>. It holds the database and the encryption key.</li></ul>""")

    faqs = [
        ("Is this allowed by LinkedIn?", "It uses only LinkedIn's official, documented APIs, through your own developer app and with your OAuth consent. It doesn't scrape, automate a browser, or send messages or connection requests. Follow LinkedIn's User Agreement and API terms as usual."),
        ("Why can't it update my profile automatically?", "LinkedIn has no public API for editing profiles. The Profile Optimizer writes every section for you to paste in."),
        ("Will it post without me?", "No. Only approved posts are published. Drafts never are, and the API refuses to publish an unapproved post. Auto-publish is off by default and only ever publishes approved posts."),
        ("Which AI models work?", "OpenAI, Anthropic Claude, Google Gemini, Groq, OpenRouter, DeepSeek, Mistral, Together, LM Studio, Ollama and anything with an OpenAI-compatible API."),
        ("Where is my data?", "In a local database in LA_DATA_DIR (~/.linkedin-agent by default). Keys and tokens are encrypted with a key that never leaves your machine. Only your model provider and LinkedIn receive anything."),
        ("Can I manage clients or a Company Page?", "Yes. Create a workspace per account. Company Page posting needs LinkedIn's Community Management API approval for your app."),
        ("How do I get analytics?", "LinkedIn restricts analytics for apps, so export them from LinkedIn and import the file. The app then shows your best times and what's working."),
        ("Does it work in Urdu, Hindi or Arabic?", "The interface is available in English, Urdu, Hindi, Arabic and Spanish. Set the post language in your brand profile, and any capable model will write in it."),
        ("Is it free?", "Yes, and MIT licensed. You pay only your model provider for usage, or nothing if you run a local model."),
    ]
    doc("faq.html", "FAQ", f"Frequently asked questions about {NAME}: LinkedIn rules, profile editing, approvals, models, privacy, clients, analytics and languages.",
        "<h1>FAQ</h1>" + "".join(f"<h3>{e(q)}</h3><p>{e(a)}</p>" for q, a in faqs))
    # FAQPage schema on the FAQ page
    faq_html = (DOCS / "faq.html").read_text(encoding="utf-8")
    faq_ld = json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]})
    (DOCS / "faq.html").write_text(faq_html.replace("</head>", f'<script type="application/ld+json">{faq_ld}</script>\n</head>', 1), encoding="utf-8")

    doc("changelog.html", "Changelog", f"What's new in {NAME}.", f"""
<h1>Changelog</h1>
<h2>2.0.0</h2><ul>
<li>Desktop app for Windows, macOS and Linux, plus automatic installer builds.</li><li>New interface: approval board, post editor with LinkedIn preview, calendar with drag-to-reschedule, command palette, dark mode, five languages with right-to-left support.</li>
<li>Import from LinkedIn's data export and analytics export.</li><li>Eight persona packs and 11 new skills ({len(reg)} in total).</li><li>Image generation, uploads and PDF carousels, posted with LinkedIn's Images and Documents APIs.</li>
<li>Analytics heatmap, best slots, and results by hook and pillar.</li><li>Trend feeds.</li><li>Workspaces for several accounts, team sign-in with roles, and client review links.</li>
<li>Approvals from Telegram and WhatsApp, plus Slack, webhooks, a calendar subscription and CSV export.</li><li>11 new MCP tools, Docker image on GHCR, Render and Railway configs, CI.</li></ul>
<h2>0.1.0</h2><ul><li>First release: web portal, 28 skills, approval-gated publishing, MCP server, Claude skill.</li></ul>""")

    # ------------------------------------------------------------- 404, sitemap, robots
    page("404.html", "Page not found", "Page not found.", '<main><div class="wrap" style="padding:120px 24px"><h1 style="font-size:56px">That page isn\'t here.</h1><p class="lead">It may have moved in version 2.</p><p><a class="btn p" href="index.html">Go to the home page</a> <a class="btn" href="docs.html">Open the docs</a></p></div></main>')
    pages = [h for h, _ in TOP_NAV] + [h for _, items in DOC_NAV for h, _ in items]
    today = date.today().isoformat()
    (DOCS / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + f"  <url><loc>{SITE}</loc><lastmod>{today}</lastmod><priority>1.0</priority></url>\n"
        + "".join(f"  <url><loc>{SITE}{h}</loc><lastmod>{today}</lastmod><priority>{'0.9' if h in ('download.html', 'features.html') else '0.7'}</priority></url>\n" for h in dict.fromkeys(pages))
        + "</urlset>\n", encoding="utf-8")
    (DOCS / "robots.txt").write_text(f"User-agent: *\nAllow: /\nDisallow: /demo/\nSitemap: {SITE}sitemap.xml\n", encoding="utf-8")
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")
    (DOCS / "assets" / "favicon.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='9' fill='#3b5bfd'/><path d='M9 22V10h3v9.5h6V22z' fill='white'/><circle cx='22' cy='12' r='2.6' fill='#a5f3c5'/></svg>", encoding="utf-8")
    for old in ("portal.html", "skills.json"):
        (DOCS / old).unlink(missing_ok=True)
    print("docs built:", len(set(pages)) + 1, "pages")


if __name__ == "__main__":
    build()
