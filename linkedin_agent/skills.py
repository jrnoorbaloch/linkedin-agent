"""The skill registry — every LinkedIn capability the agent offers.

Each skill declares its input fields (rendered as a form in the portal and as
arguments in the MCP tool) and an instruction block that is combined with the
user's brand profile to build the LLM prompt. Add a skill by appending to
``SKILLS``; the UI, REST API and MCP server pick it up automatically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import db, llm, notify

# --------------------------------------------------------------------------
# Brand profile (voice) — the context every skill writes from
# --------------------------------------------------------------------------

PROFILE_FIELDS = [
    ("name", "Full name"),
    ("role", "Current role / title"),
    ("industry", "Industry"),
    ("audience", "Who you want to reach (ICP)"),
    ("offer", "What you offer / sell / want to be known for"),
    ("pillars", "Content pillars (comma separated, 3-5)"),
    ("tone", "Tone of voice (e.g. direct, warm, witty)"),
    ("language", "Post language (e.g. English, Urdu, Roman Urdu)"),
    ("goals", "LinkedIn goals (leads, job, hiring, authority...)"),
    ("avoid", "Words / topics to avoid"),
    ("sample_posts", "2-3 of your past posts (for voice matching)"),
    ("profile_text", "Your current LinkedIn profile text or resume"),
]


def get_brand() -> dict[str, str]:
    return db.aget("brand_profile", {}) or {}


def save_brand(data: dict[str, str]) -> dict[str, str]:
    clean = {k: str(data.get(k, "")).strip() for k, _ in PROFILE_FIELDS}
    db.aset("brand_profile", clean)
    return clean


def brand_block() -> str:
    b = get_brand()
    lines = [f"- {label}: {b[k]}" for k, label in PROFILE_FIELDS if b.get(k) and k not in ("sample_posts", "profile_text")]
    out = "USER BRAND PROFILE\n" + ("\n".join(lines) if lines else "- (not filled in yet — ask the user or keep it generic)")
    if b.get("sample_posts"):
        out += "\n\nVOICE SAMPLES (match rhythm, vocabulary and formatting — never copy):\n" + b["sample_posts"][:3000]
    stories = db.list_rows("stories", limit=15)
    if stories:
        out += "\n\nSTORY BANK (real experiences you may draw on — never invent facts):\n" + "\n".join(
            f"- [{s['id']}] {s['title']}: {s['body'][:300]}" for s in stories
        )
    return out


BASE_SYSTEM = """You are LinkedIn Agent, an expert LinkedIn ghostwriter, profile strategist and career coach.

Rules that always apply:
1. Write in the user's voice from the brand profile. Plain, specific, human. No corporate filler.
2. Never invent facts, numbers, employers, clients or results. If a detail is missing, use a clearly marked placeholder like [number] or ask.
3. Avoid AI tells: "delve", "in today's fast-paced world", "game-changer", "unlock", "elevate", "leverage", "tapestry",
   "it's not X, it's Y" reveals, stacked triads, em-dash overuse, emoji walls, and generic motivational endings.
4. LinkedIn formatting: short paragraphs (1-2 lines), white space, a hook that works before "...see more" (first ~210 chars),
   no markdown headings or **bold** (LinkedIn shows them as literal symbols), max 3 relevant hashtags at the end.
5. Put external links in the first comment, never in the post body.
6. Output only what was asked for, with no preamble.
"""


# --------------------------------------------------------------------------
# Skill definitions
# --------------------------------------------------------------------------

@dataclass
class Field:
    name: str
    label: str
    kind: str = "text"            # text | textarea | select
    options: list[str] = field(default_factory=list)
    required: bool = False
    placeholder: str = ""


@dataclass
class Skill:
    id: str
    title: str
    category: str
    description: str
    instructions: str
    fields: list[Field]
    output: str = "text"          # post | document | text
    max_tokens: int = 1800

    def schema(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "description": self.description,
            "output": self.output,
            "fields": [f.__dict__ for f in self.fields],
        }


GOALS = ["comments", "reposts", "saves", "profile visits", "leads", "followers"]
HOOKS = [
    "auto", "contrarian", "curiosity gap", "time anchor", "R.I.P.", "anaphora", "year pivot", "numbered list",
    "emotional cold open", "mistake/lesson", "before-after", "question", "myth vs reality", "named gratitude",
    "controlled A/B", "false binary", "comment gate", "behind the scenes", "data reveal", "how I / how we",
]
FORMATS = ["text post", "listicle", "story", "carousel outline", "poll", "short hot take"]

SKILLS: list[Skill] = [
    # ---------------- Content ----------------
    Skill(
        "post_writer", "Post Writer", "Content",
        "Draft a ready-to-publish LinkedIn post using a proven 2026 hook formula.",
        """Write ONE LinkedIn post.
- Pick the hook formula given (or the best one for the goal if 'auto') and name it on the first line as: HOOK: <formula>
- Then a line '---', then the post (900-1300 characters is the sweet spot unless the format says otherwise).
- End the post with a CTA that fits the engagement goal.
- After the post add '---' and 'FIRST COMMENT:' with a useful first comment (link/resource if provided, else a follow-up thought).""",
        [
            Field("topic", "Topic or idea", "textarea", required=True, placeholder="e.g. What I learned hiring my first 5 engineers"),
            Field("pillar", "Content pillar", placeholder="optional"),
            Field("goal", "Engagement goal", "select", GOALS),
            Field("hook", "Hook formula", "select", HOOKS),
            Field("format", "Format", "select", FORMATS),
            Field("link", "Link for first comment", placeholder="optional"),
        ],
        output="post",
    ),
    Skill(
        "daily_post", "Daily Post (auto)", "Content",
        "The scheduler uses this every morning: picks a pillar and an unused story, then drafts a post for approval.",
        """Choose the content pillar and angle yourself, rotating pillars and preferring an unused Story Bank item.
Return exactly:
PILLAR: <pillar>
HOOK: <formula>
---
<post>
---
FIRST COMMENT: <first comment>""",
        [Field("notes", "Extra direction for today", "textarea", placeholder="optional — trending topic, event, launch...")],
        output="post",
    ),
    Skill(
        "content_planner", "7-Day Content Planner", "Content",
        "A week of posts: pillar, format, hook, CTA, best time and daily comment targets.",
        """Create a 7-day LinkedIn plan as a Markdown table with columns:
Day | Pillar | Format | Hook formula | Working title | CTA | Post time (user's timezone) | Comment targets (3 types of accounts to engage).
Below the table: 'Weekly inbound check' — 4 bullet checks (profile headline, featured, DM readiness, lead magnet).""",
        [
            Field("theme", "Theme for the week", required=True),
            Field("timezone", "Timezone", placeholder="e.g. Asia/Karachi"),
            Field("posts_per_week", "Posts per week", "select", ["3", "4", "5", "7"]),
        ],
        output="document",
    ),
    Skill(
        "humanizer", "Humanizer & Audit", "Content",
        "Remove AI tells from a draft and score it before posting.",
        """First give an AUDIT: score /100 for hook strength, readability, specificity, voice match, AI-tell density; list the top 5 issues.
Then '---' and the REWRITTEN POST that fixes them while keeping the meaning and the user's voice.""",
        [Field("draft", "Your draft", "textarea", required=True)],
        output="post",
    ),
    Skill(
        "repurposer", "Repurposer", "Content",
        "Turn a blog, tweet thread, video transcript or newsletter into a native LinkedIn post.",
        """Rebuild the source as a native LinkedIn post: new hook before the fold, 900-1300 chars, white space, CTA.
Move any links to FIRST COMMENT. Output: post, then '---', then 'FIRST COMMENT: ...'.""",
        [
            Field("source", "Source content", "textarea", required=True),
            Field("source_type", "Source type", "select", ["blog", "tweet/thread", "YouTube transcript", "newsletter", "podcast notes", "other"]),
        ],
        output="post",
    ),
    Skill(
        "carousel", "Carousel Builder", "Content",
        "Outline an 8-10 slide document (PDF) carousel with copy for every slide.",
        """Write a LinkedIn carousel. For each slide: 'Slide N — <headline (max 8 words)>' then 1-3 short lines of body.
Slide 1 is a scroll-stopping cover, last slide is a CTA (follow / comment / DM). Then a 2-line caption post to go with it.""",
        [Field("topic", "Carousel topic", "textarea", required=True), Field("slides", "Number of slides", "select", ["6", "8", "10", "12"])],
        output="document",
    ),
    Skill(
        "poll", "Poll Creator", "Content",
        "A LinkedIn poll: question (≤140 chars), 2-4 options (≤30 chars each) and the post text.",
        "Return: QUESTION, OPTIONS (2-4, each ≤30 characters), then the short post that introduces the poll and invites comments.",
        [Field("topic", "Poll topic", required=True)],
        output="post",
    ),
    Skill(
        "hook_extractor", "Hook Extractor", "Content",
        "Reverse-engineer why a viral post worked and get a reusable template.",
        """Analyze the pasted post: which hook formula it uses (from the 20 canonical ones), why it works (3 bullets),
the structure (bullet outline), and a blank fill-in-the-blanks TEMPLATE. Then write one example adapted to the user's brand.""",
        [Field("post", "Paste the viral post", "textarea", required=True)],
    ),
    Skill(
        "article_writer", "Article / Newsletter", "Content",
        "Long-form LinkedIn article or newsletter edition (here Markdown headings are allowed).",
        """Write a LinkedIn article in Markdown: title, subtitle, 5-8 sections with H2 headings, concrete examples,
a conclusion with a CTA. 900-1500 words. Then a 3-line promo post to share it.""",
        [Field("topic", "Article topic", "textarea", required=True), Field("angle", "Angle / thesis")],
        output="document",
        max_tokens=4000,
    ),
    # ---------------- Engagement ----------------
    Skill(
        "comment_drafter", "Comment Drafter", "Engagement",
        "Thoughtful comments on someone else's post (3 variants) + a suggested reaction.",
        """Write 3 comment variants (A: add an insight, B: share a short personal experience, C: ask a sharp question).
Each 2-4 sentences, no flattery openers ("Great post!"), no pitching. Then 'REACTION:' with the best LinkedIn reaction.""",
        [Field("post", "Their post text", "textarea", required=True), Field("author", "Author name / role")],
    ),
    Skill(
        "reply_handler", "Reply Handler", "Engagement",
        "Draft replies to comments on your post — paste one or many.",
        """For each comment (separated by blank lines) write a reply that keeps the thread going (adds value or asks a follow-up).
Skip low-value comments ("Great post", emojis) with a one-line thanks. Format: '> comment' then 'Reply: ...'.""",
        [Field("post", "Your post (context)", "textarea"), Field("comments", "Comments to reply to", "textarea", required=True)],
    ),
    # ---------------- Networking ----------------
    Skill(
        "connection_note", "Connection Note", "Networking",
        "Personalized connection-request note (≤300 characters) with 2 variants.",
        "Write 2 connection notes, each under 300 characters, referencing something specific about the person. No pitch.",
        [Field("person", "Who are they? (name, headline, recent post)", "textarea", required=True), Field("reason", "Why connect?")],
    ),
    Skill(
        "dm_writer", "DM / InMail Writer", "Networking",
        "Outreach, follow-up and collaboration messages that sound human.",
        "Write the message plus one follow-up to send 4-5 days later if there is no reply. Short, specific, one clear ask.",
        [
            Field("person", "Recipient (name, role, context)", "textarea", required=True),
            Field("purpose", "Purpose", "select", ["cold outreach", "follow-up", "collaboration", "referral request", "thank you", "re-connect"]),
            Field("details", "Details to include", "textarea"),
        ],
    ),
    Skill(
        "recommendation", "Recommendation Writer", "Networking",
        "Write a recommendation for someone, or a message asking for one.",
        "If mode is 'give': a 120-180 word recommendation with one concrete story. If 'ask': a short request message with 3 suggested points they could mention.",
        [
            Field("mode", "Mode", "select", ["give", "ask"]),
            Field("person", "Person & relationship", "textarea", required=True),
            Field("highlights", "What to highlight", "textarea"),
        ],
    ),
    # ---------------- Profile ----------------
    Skill(
        "profile_optimizer", "Profile Optimizer", "Profile",
        "Full profile audit and rewrite: headline, About, Experience, Skills, Featured, banner, URL.",
        """Using the user's profile text, produce in Markdown:
1. SCORE /100 with a one-line verdict per section.
2. HEADLINE — 3 options (≤220 chars) using the formula: who you help + outcome + proof/keyword.
3. ABOUT — full rewrite (7-step: hook, who you help, problem, approach, proof, personality, CTA), ≤2,600 chars, first 2 lines must hook.
4. EXPERIENCE — rewrite each role as 3-5 result-led bullets (verb + what + metric placeholder if unknown).
5. SKILLS — top 10 keywords in priority order (recruiter search terms).
6. FEATURED — 3 items to pin and why.
7. BANNER — headline text + sub-line for the banner image.
8. CUSTOM URL suggestion and a photo checklist.
Note: these must be pasted manually — LinkedIn has no API for editing profiles.""",
        [
            Field("profile_text", "Current profile text (leave blank to use the one in Brand Profile)", "textarea"),
            Field("target", "Target (role, clients, or goal)"),
        ],
        output="document",
        max_tokens=4000,
    ),
    Skill(
        "voice_builder", "Voice Profile Builder", "Profile",
        "Analyze your past posts and write a reusable style guide for your voice.",
        """From the sample posts produce a VOICE GUIDE: sentence length, vocabulary, signature phrases, formatting habits,
emoji/hashtag habits, topics, do's & don'ts (10 bullets), and 3 example openings in this voice.""",
        [Field("samples", "Paste 3-10 of your posts", "textarea", required=True)],
        output="document",
    ),
    Skill(
        "interviewer", "Story Interviewer", "Profile",
        "Get interviewed to fill your Story Bank with real experiences that become posts.",
        """Ask the user 8 sharp interview questions about the given focus that surface concrete stories:
numbers, turning points, failures, opinions, client moments. One question per line, numbered.
If answers are provided, instead convert them into Story Bank entries: 'TITLE: ...' / 'STORY: ...' / 'POST ANGLES: 3 bullets'.""",
        [Field("focus", "Focus area", placeholder="e.g. my career switch, first startup"), Field("answers", "Your answers (optional)", "textarea")],
    ),
    # ---------------- Career ----------------
    Skill(
        "resume_builder", "Resume Builder", "Career",
        "ATS-friendly resume in Markdown from your profile (export to DOCX).",
        """Write an ATS-friendly resume in Markdown: Name & contact line placeholders, Summary (3 lines), Skills (grouped),
Experience (reverse chronological, 3-5 achievement bullets each), Education, Certifications, Projects (if any).
No tables, no columns, no icons. Use [placeholders] for missing facts.""",
        [
            Field("profile_text", "Profile / old resume (blank = Brand Profile)", "textarea"),
            Field("target_role", "Target role"),
            Field("job_description", "Job description to tailor to (optional)", "textarea"),
        ],
        output="document",
        max_tokens=4000,
    ),
    Skill(
        "cover_letter", "Cover Letter", "Career",
        "Tailored cover letter for a specific job.",
        "Write a 250-350 word cover letter: specific hook about the company, 2 proof paragraphs mapped to requirements, confident close.",
        [Field("job_description", "Job description", "textarea", required=True), Field("company", "Company name")],
        output="document",
    ),
    Skill(
        "job_match", "Job Match & Gap", "Career",
        "Compare a job description to your profile: match score, gaps and what to fix.",
        """Return: MATCH SCORE /100; MATCHED requirements; GAPS (missing keywords/skills/experience);
RESUME EDITS (exact bullet changes); PROFILE EDITS (headline/skills keywords to add); 30-day plan to close the biggest gap.""",
        [Field("job_description", "Job description", "textarea", required=True)],
        output="document",
    ),
    Skill(
        "interview_prep", "Interview Prep", "Career",
        "Likely interview questions with STAR answers drawn from your experience.",
        "List 10 likely questions (mix behavioral/technical/role-specific). For each give a STAR answer outline from the user's real experience (placeholders where unknown) and one question to ask the interviewer.",
        [Field("job_description", "Job description or role", "textarea", required=True)],
        output="document",
        max_tokens=4000,
    ),
    Skill(
        "skills_gap", "Skills Gap Planner", "Career",
        "What skills, certifications and proof you need for a target role, with a 90-day plan.",
        "Return: target-role skill map, the user's gaps, 5 recommended certifications/courses (generic names if unsure), 90-day plan with weekly milestones, and 5 post ideas to document the journey publicly.",
        [Field("target_role", "Target role", required=True)],
        output="document",
    ),
    Skill(
        "salary_negotiation", "Salary Negotiation", "Career",
        "Talking points and a script for negotiating an offer.",
        "Write: anchor strategy, 5 talking points tied to the user's value, a phone script, an email reply to the offer, and 3 non-salary asks. Not financial or legal advice.",
        [Field("offer", "Offer details", "textarea", required=True), Field("market", "Market range you know (optional)")],
        output="document",
    ),
    # ---------------- Company Page ----------------
    Skill(
        "page_post", "Company Page Post", "Company Page",
        "Brand-voice post for your Company Page (publishing needs Community Management API approval).",
        "Write a Company Page post in brand voice ('we'), 600-1000 chars, with CTA and first comment. Format like Post Writer.",
        [Field("topic", "Topic / announcement", "textarea", required=True), Field("brand_voice", "Brand voice notes")],
        output="post",
    ),
    Skill(
        "hiring_post", "Hiring Post", "Company Page",
        "Job announcement post that attracts the right candidates.",
        "Write a hiring post: hook about the mission/problem, what they'll do (3 bullets), who thrives here, perks, how to apply (link in first comment).",
        [Field("role", "Role & details", "textarea", required=True)],
        output="post",
    ),
    Skill(
        "advocacy_pack", "Employee Advocacy Pack", "Company Page",
        "Turn one company update into 3-5 personal posts employees can share in their own voice.",
        "Create 4 variants for different roles (leader, engineer, sales, new joiner). Each feels personal and different. Add a 3-bullet sharing guideline.",
        [Field("update", "Company update", "textarea", required=True)],
        output="document",
    ),
    # ---------------- Analytics ----------------
    Skill(
        "weekly_report", "Weekly Performance Report", "Analytics",
        "Analyze your posts' metrics (from the History tab) and tell you what to do next week.",
        "Analyze the metrics provided: top 3 and bottom 3 posts and why, patterns by hook/pillar/format/time, and 5 concrete actions for next week.",
        [Field("extra", "Anything else to consider", "textarea")],
        output="document",
    ),
    Skill(
        "competitor_analysis", "Competitor Analysis", "Analytics",
        "Paste a creator's recent posts and get their playbook and gaps you can own.",
        "Identify their pillars, hook patterns, formats, cadence, CTA style, and 5 gaps/angles the user can own. End with 5 post ideas.",
        [Field("posts", "Their recent posts", "textarea", required=True), Field("who", "Who is it?")],
        output="document",
    ),
]

SKILLS += [
    # ---------------- v2: Content ----------------
    Skill(
        "trend_ideas", "Trend Ideas", "Content",
        "Turn today's headlines from your RSS feeds into 5 post angles for your niche.",
        """Using the trending headlines (if any) and the user's pillars, propose 5 post ideas.
For each: the headline it reacts to, the user's angle (opinion/lesson/how-to), a hook (≤210 chars) and which pillar it fits.
Prefer angles where the user has real experience (Story Bank).""",
        [Field("focus", "Focus or niche (optional)")],
        output="document",
    ),
    Skill(
        "video_script", "Video Script", "Content",
        "A 30-90 second LinkedIn video script with hook, beats, on-screen text and caption.",
        """Write a talking-head video script: 0-3s hook line, 3-5 beats with on-screen text suggestions,
a closing CTA, approximate timing per beat, B-roll ideas, and a 2-4 line caption post with first comment.""",
        [Field("topic", "Video topic", "textarea", required=True), Field("length", "Length", "select", ["30s", "60s", "90s"])],
        output="document",
    ),
    Skill(
        "image_prompt", "Post Image Prompt", "Content",
        "Describe the ideal image for a post and write a prompt for an image model.",
        """Return: IMAGE CONCEPT (1-2 lines), PROMPT (one paragraph for an image model, no text in image unless short title,
LinkedIn 1200x1200 or 1080x1350, brand-friendly, no logos/real people), ALT TEXT (≤120 chars).""",
        [Field("post", "Post text", "textarea", required=True), Field("style", "Style", "select", ["clean illustration", "photo-realistic", "flat infographic", "3D render", "minimal typography"])],
    ),
    Skill(
        "evergreen_recycle", "Evergreen Recycler", "Content",
        "Rewrite your best-performing past posts with a fresh hook and angle.",
        "For each top past post, write a NEW version: different hook formula, updated angle, same core insight. Format like Post Writer for each, separated by '==='.",
        [Field("post", "Specific post to recycle (blank = your top posts)", "textarea")],
        output="document",
    ),
    # ---------------- v2: Persona-specific ----------------
    Skill(
        "project_showcase", "Project Showcase", "Students & Developers",
        "Turn a project, assignment, hackathon or GitHub repo into a post that recruiters notice.",
        """Write a project post: the problem, what the user built (stack/tools), one hard part and how they solved it,
the result (numbers or demo), what they learned, and a CTA (feedback / opportunities). Link (repo/demo) goes in FIRST COMMENT.""",
        [Field("project", "Project details / README", "textarea", required=True), Field("link", "Repo or demo link")],
        output="post",
    ),
    Skill(
        "open_to_work", "Open-to-Work Post", "Job Seekers",
        "A confident job-search announcement that gets referrals, not pity.",
        """Write an open-to-work post: the role(s) and location/remote, 3 proof points (wins with numbers),
what kind of team they want, an easy ask (intros/referrals), and contact info placeholder. Warm, not desperate. Also give a 2-line DM version for recruiters.""",
        [Field("roles", "Target roles & location", required=True), Field("highlights", "Top achievements", "textarea")],
        output="post",
    ),
    Skill(
        "recruiter_outreach", "Recruiter / Candidate Outreach", "Recruiters & HR",
        "Personalized InMail to a candidate (or to a recruiter) with a follow-up.",
        "Write a personalized message (≤600 chars) that references the person's background, the role's best selling point and one question. Add a 4-day follow-up.",
        [
            Field("direction", "Direction", "select", ["recruiter → candidate", "candidate → recruiter"]),
            Field("person", "Their profile summary", "textarea", required=True),
            Field("role", "Role details", "textarea"),
        ],
    ),
    Skill(
        "social_selling", "Social Selling Planner", "Sales & Freelancers",
        "Prospect research and a 14-day warm-up sequence from a pasted prospect profile.",
        """From the prospect's profile/posts: 3 likely priorities, 3 conversation angles, a 14-day plan
(day 1-5 engage on posts with comment ideas, day 6 connection note, day 9 value DM, day 14 soft ask), and SSI (Social Selling Index) tips.""",
        [Field("prospect", "Prospect profile / recent posts", "textarea", required=True), Field("offer", "What you sell")],
        output="document",
    ),
    Skill(
        "case_study_post", "Client Case Study Post", "Sales & Freelancers",
        "Turn a client win into a story post (with permission placeholders).",
        "Write a before → turning point → after story with concrete numbers, what you did (3 steps), a client quote placeholder, and a soft CTA. Note where client permission is needed.",
        [Field("project", "Client project details", "textarea", required=True)],
        output="post",
    ),
    Skill(
        "expert_explainer", "Expert Explainer", "Professionals",
        "For doctors, teachers, lawyers, engineers: explain a common question simply and responsibly.",
        """Explain the topic for a general audience: myth vs fact, 3-5 practical points, when to see a professional,
and a responsible disclaimer where relevant (medical/legal/financial). No fear-mongering, no guarantees.""",
        [Field("topic", "Topic / common question", "textarea", required=True), Field("profession", "Your profession")],
        output="post",
    ),
    Skill(
        "headline_ab", "Headline A/B Lab", "Profile",
        "10 headline variants scored for clarity, searchability and curiosity.",
        "Write 10 headline variants (≤220 chars) across styles (role-first, outcome-first, proof-first, niche, personality). Score each /10 on clarity, keywords, curiosity and recommend the top 2 to test for 2 weeks each.",
        [Field("current", "Current headline"), Field("target", "Target audience / role")],
        output="document",
    ),
]

SKILL_MAP = {s.id: s for s in SKILLS}


def list_skills() -> list[dict]:
    return [s.schema() for s in SKILLS]


def _metrics_block() -> str:
    rows = db.list_rows("posts", "status='published'", limit=40)
    if not rows:
        return "No published posts with metrics yet."
    lines = []
    for p in rows:
        m = p.get("metrics") or {}
        lines.append(
            f"- #{p['id']} {p.get('published_at','')[:10]} pillar={p.get('pillar')} hook={p.get('hook_type')} "
            f"impressions={m.get('impressions','?')} reactions={m.get('reactions','?')} comments={m.get('comments','?')} "
            f"reposts={m.get('reposts','?')} :: {p['content'][:120]!r}"
        )
    return "POST METRICS:\n" + "\n".join(lines)


def build_prompt(skill_id: str, inputs: dict[str, Any]) -> tuple[str, str]:
    skill = SKILL_MAP.get(skill_id)
    if not skill:
        raise KeyError(f"Unknown skill '{skill_id}'. Available: {', '.join(SKILL_MAP)}")
    missing = [f.label for f in skill.fields if f.required and not str(inputs.get(f.name, "")).strip()]
    if missing:
        raise ValueError("Missing required input: " + ", ".join(missing))

    system = f"{BASE_SYSTEM}\n{brand_block()}\n\nTASK: {skill.title}\n{skill.instructions}"
    parts = [f"{f.label}: {inputs[f.name]}" for f in skill.fields if str(inputs.get(f.name, "")).strip()]
    if skill_id in ("profile_optimizer", "resume_builder") and not inputs.get("profile_text"):
        parts.append("Profile text: " + (get_brand().get("profile_text") or "(none provided — use placeholders)"))
    if skill_id == "voice_builder" and not inputs.get("samples"):
        parts.append("Samples: " + get_brand().get("sample_posts", ""))
    if skill_id in ("weekly_report", "daily_post"):
        parts.append(_metrics_block())
    if skill_id in ("trend_ideas", "daily_post"):
        items = db.list_rows("trends", limit=20)
        if items:
            parts.append("TRENDING HEADLINES (from the user's feeds):\n" + "\n".join(f"- {t['title']} ({t.get('source') or ''})" for t in items))
    if skill_id == "evergreen_recycle" and not inputs.get("post"):
        best = sorted(db.list_rows("posts", "status='published'", limit=100),
                      key=lambda p: int((p.get("metrics") or {}).get("reactions") or 0) + 3 * int((p.get("metrics") or {}).get("comments") or 0), reverse=True)[:3]
        parts.append("TOP PAST POSTS:\n" + "\n---\n".join(p["content"] for p in best) if best else "No past posts — ask the user to paste one.")
    if skill_id == "daily_post":
        recent = db.list_rows("posts", limit=7)
        parts.append("RECENT POSTS (avoid repeating):\n" + "\n".join(f"- {p.get('pillar')}: {p['content'][:100]!r}" for p in recent))
    user = "\n\n".join(parts) or "Go."
    return system, user


def run(skill_id: str, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run a skill with the configured LLM. Post-type outputs are saved as drafts."""
    inputs = inputs or {}
    system, user = build_prompt(skill_id, inputs)
    skill = SKILL_MAP[skill_id]
    text = llm.complete(system, user, max_tokens=skill.max_tokens)
    result: dict[str, Any] = {"skill": skill_id, "output": text}

    if skill.output == "post":
        parsed = parse_post(text)
        target = "organization" if skill.category == "Company Page" else "member"
        post_id = db.insert(
            "posts",
            target=target,
            pillar=parsed.get("pillar") or inputs.get("pillar"),
            hook_type=parsed.get("hook") or inputs.get("hook"),
            content=parsed["post"],
            first_comment=parsed.get("first_comment"),
            status="draft",
            source="agent",
        )
        result.update(post_id=post_id, post=parsed["post"], first_comment=parsed.get("first_comment"))
        notify.emit("draft_created", db.get("posts", post_id))
    elif skill.output == "document":
        kind = {"resume_builder": "resume", "cover_letter": "cover_letter", "profile_optimizer": "profile",
                "content_planner": "plan"}.get(skill_id, "note")
        title = f"{skill.title} — {str(next(iter(inputs.values()), ''))[:60]}".strip(" —")
        result["document_id"] = db.insert("documents", kind=kind, title=title, content=text)
    return result


def parse_post(text: str) -> dict[str, str]:
    """Split LLM output of the form 'HOOK: x / --- / post / --- / FIRST COMMENT: y'."""
    meta: dict[str, str] = {}
    blocks = [b.strip() for b in text.split("\n---") if b.strip()]
    body_blocks = []
    for b in blocks:
        b = b.lstrip("-").strip()
        upper = b.upper()
        if upper.startswith("FIRST COMMENT:"):
            meta["first_comment"] = b.split(":", 1)[1].strip()
        elif all(line.split(":")[0].strip().upper() in ("HOOK", "PILLAR", "QUESTION", "OPTIONS") or not line.strip()
                 for line in b.splitlines()[:3]) and len(b) < 300 and ":" in b:
            for line in b.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip().lower()] = v.strip()
            if "question" in meta:
                body_blocks.append(b)
        else:
            body_blocks.append(b)
    meta["post"] = "\n\n".join(body_blocks).strip() or text.strip()
    return meta


# ---------------- Story bank ----------------

def add_story(title: str, body: str, tags: str = "") -> int:
    return db.insert("stories", title=title, body=body, tags=tags)
