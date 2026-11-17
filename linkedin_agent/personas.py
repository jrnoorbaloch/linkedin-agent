"""Persona packs — ready-made setups so anyone can start in one click.

Applying a pack fills empty brand-profile fields (pillars, tone, goals), sets
suggested RSS feeds for Trend Ideas, and highlights the skills that matter most.
"""

from __future__ import annotations

from . import db, skills

PACKS: list[dict] = [
    {
        "id": "student", "emoji": "🎓", "name": "Students & Freshers",
        "description": "Land internships and your first job by documenting what you learn and build.",
        "pillars": "Projects I built, What I'm learning, Internship/campus life, Career lessons",
        "tone": "Curious, humble, energetic", "goals": "Internships, first job, recruiter visibility",
        "skills": ["project_showcase", "post_writer", "resume_builder", "connection_note", "skills_gap", "interview_prep"],
        "feeds": ["https://news.ycombinator.com/rss", "https://www.freecodecamp.org/news/rss/"],
        "week": ["Learning log", "Project showcase", "Lesson from a mistake", "Resource list", "Career question poll"],
    },
    {
        "id": "job_seeker", "emoji": "💼", "name": "Job Seekers",
        "description": "Get referrals and recruiter messages with a sharp profile and proof-of-work posts.",
        "pillars": "Wins & results, Industry opinions, Job search lessons, Skills in action",
        "tone": "Confident, specific, warm", "goals": "Interviews, referrals, recruiter inbound",
        "skills": ["open_to_work", "profile_optimizer", "headline_ab", "job_match", "cover_letter", "recruiter_outreach"],
        "feeds": [],
        "week": ["Win story", "Industry take", "Open-to-work / ask", "How I solved X", "Thank-you / gratitude"],
    },
    {
        "id": "developer", "emoji": "💻", "name": "Developers & Engineers",
        "description": "Turn your code, repos and debugging stories into authority content.",
        "pillars": "Things I built, Debugging stories, Tools & stack, Engineering opinions, Career in tech",
        "tone": "Direct, practical, a little nerdy", "goals": "Job offers, freelance clients, open-source users",
        "skills": ["project_showcase", "carousel", "hook_extractor", "article_writer", "trend_ideas", "resume_builder"],
        "feeds": ["https://news.ycombinator.com/rss", "https://github.blog/feed/", "https://dev.to/feed"],
        "week": ["Build log", "Debugging story", "Tool comparison carousel", "Hot take", "Repo showcase"],
    },
    {
        "id": "freelancer", "emoji": "🧑‍💻", "name": "Freelancers & Agencies",
        "description": "Attract clients with case studies, process posts and a profile that sells.",
        "pillars": "Client results, My process, Mistakes clients make, Behind the scenes, Offers",
        "tone": "Helpful, confident, results-first", "goals": "Inbound leads, client trust, referrals",
        "skills": ["case_study_post", "social_selling", "profile_optimizer", "dm_writer", "carousel", "content_planner"],
        "feeds": [],
        "week": ["Case study", "Process carousel", "Common mistake", "Behind the scenes", "Soft offer"],
    },
    {
        "id": "sales", "emoji": "📈", "name": "Sales & Business Development",
        "description": "Warm up prospects with social selling and raise your SSI.",
        "pillars": "Customer problems, Industry insights, Wins & lessons, Buyer education",
        "tone": "Consultative, curious, no hard pitch", "goals": "Meetings booked, pipeline, SSI",
        "skills": ["social_selling", "comment_drafter", "connection_note", "dm_writer", "case_study_post", "weekly_report"],
        "feeds": [],
        "week": ["Buyer problem", "Insight/data", "Customer story", "Myth vs reality", "Question poll"],
    },
    {
        "id": "founder", "emoji": "🚀", "name": "Founders & Creators",
        "description": "Build in public, grow an audience and turn it into customers and hires.",
        "pillars": "Building in public, Lessons & failures, Industry POV, Team & hiring, Product",
        "tone": "Honest, opinionated, story-driven", "goals": "Followers, customers, hiring, investors",
        "skills": ["post_writer", "content_planner", "hiring_post", "advocacy_pack", "evergreen_recycle", "competitor_analysis"],
        "feeds": ["https://techcrunch.com/feed/"],
        "week": ["Build-in-public update", "Failure lesson", "Contrarian take", "Team story", "Product insight"],
    },
    {
        "id": "professional", "emoji": "🩺", "name": "Doctors, Teachers & Experts",
        "description": "Share expertise simply and responsibly to build trust in your field.",
        "pillars": "Myths vs facts, Practical tips, Stories from practice, Field news explained",
        "tone": "Clear, kind, trustworthy", "goals": "Reputation, patients/students/clients, speaking",
        "skills": ["expert_explainer", "post_writer", "carousel", "video_script", "profile_optimizer", "trend_ideas"],
        "feeds": [],
        "week": ["Myth vs fact", "Practical tips carousel", "Story from practice", "News explained", "Q&A poll"],
    },
    {
        "id": "recruiter", "emoji": "🧲", "name": "Recruiters & HR",
        "description": "Employer branding, hiring posts and candidate outreach that gets replies.",
        "pillars": "Open roles, Culture stories, Hiring tips for candidates, Market insights",
        "tone": "Warm, transparent, helpful", "goals": "Qualified applicants, employer brand",
        "skills": ["hiring_post", "recruiter_outreach", "advocacy_pack", "page_post", "post_writer", "interview_prep"],
        "feeds": [],
        "week": ["Open role", "Culture story", "Candidate tip", "Market insight", "Team spotlight"],
    },
]

PACK_MAP = {p["id"]: p for p in PACKS}


def list_packs() -> list[dict]:
    titles = {s.id: s.title for s in skills.SKILLS}
    return [{**p, "skill_titles": [titles.get(s, s) for s in p["skills"]]} for p in PACKS]


def apply_pack(pack_id: str, overwrite: bool = False) -> dict:
    pack = PACK_MAP.get(pack_id)
    if not pack:
        raise KeyError(f"Unknown pack '{pack_id}'")
    brand = skills.get_brand()
    for field in ("pillars", "tone", "goals"):
        if overwrite or not brand.get(field):
            brand[field] = pack[field]
    skills.save_brand(brand)
    feeds = db.aget("trend_feeds", []) or []
    for f in pack["feeds"]:
        if f not in feeds:
            feeds.append(f)
    db.aset("trend_feeds", feeds)
    db.aset("persona", pack_id)
    with db.connect() as c:
        c.execute("UPDATE accounts SET persona=? WHERE id=?", (pack_id, db.current_account()))
    return {"brand": brand, "feeds": feeds, "pack": pack}
