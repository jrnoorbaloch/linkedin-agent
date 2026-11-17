---
name: linkedin-agent
description: All-in-one LinkedIn assistant. Use whenever the user wants to write, plan, humanize or schedule a LinkedIn post, carousel, poll or article; rewrite or audit their LinkedIn profile (headline, About, experience, skills, banner); build a resume, cover letter or interview prep from their profile; draft comments, replies, connection notes, DMs or recommendations; run a Company Page or employee advocacy; or review LinkedIn performance. Can publish through the self-hosted LinkedIn Agent (MCP or REST) after explicit user approval.
---

# LinkedIn Agent

One skill that covers the whole LinkedIn workflow: **content → engagement → networking → profile → career → company page → analytics**, plus approval-gated publishing through the open-source [LinkedIn Agent](https://github.com/jrnoorbaloch/linkedin-agent).

## 0. Ground rules (always)

1. **Voice first.** Before writing anything, get the user's brand profile: name, role, audience, offer, 3-5 content pillars, tone, language, and 1-3 sample posts. Sources, in order: the `get_brand_profile` MCP tool → `scripts/la.py brand` → ask the user (max 4 short questions). Save answers with `update_brand_profile` when available.
2. **Never invent facts** (numbers, employers, clients, results). Use `[placeholder]` or ask. Prefer real stories from the Story Bank (`references/interviewer.md`).
3. **No AI tells.** Run every draft through the checklist in `references/humanizer.md` before showing it.
4. **LinkedIn formatting.** Hook inside the first ~210 characters (before "…see more"), 1-2 line paragraphs, no Markdown bold/headings in posts, max 3 hashtags at the end, links go in the first comment.
5. **Approval gate.** Never publish, schedule, comment or send anything without the user's explicit "yes" to that exact text. Show the final draft, then ask.
6. **API reality.** LinkedIn's official API can post and comment (as the member; as a Company Page only after Community Management API approval). It **cannot** edit profiles, read your past posts, send DMs or connection requests. For those, produce the copy and tell the user where to paste it.

## 1. Route the request

| User wants… | Read | Output |
|---|---|---|
| A post / hook / "write about X" | `references/post-writing.md`, `references/hooks.md` | 1 post (+ optional A/B hook), first comment |
| Week/month plan, posting cadence | `references/content-planning.md` | Markdown table plan |
| Make a draft sound human / audit before posting | `references/humanizer.md` | Score + rewrite |
| Turn blog/video/tweet into a post | `references/post-writing.md` § Repurpose | Native post |
| Carousel, poll, article/newsletter | `references/formats.md` | Slide copy / poll / article |
| Learn from a viral post | `references/hooks.md` § Extract | Formula + template |
| Comment on someone's post / reply to comments | `references/engagement.md` | 3 variants / reply batch |
| Connection note, DM, recommendation | `references/networking.md` | Message + follow-up |
| Profile review or rewrite | `references/profile.md` | Section-by-section rewrite to paste |
| Resume, cover letter, job match, interview, salary | `references/career.md` | Markdown doc (DOCX via portal) |
| Interview me / build my story bank / voice profile | `references/interviewer.md` | Questions → stories / voice guide |
| Company Page, hiring post, employee advocacy | `references/company-page.md` | Page post / pack |
| Performance, what's working, competitors | `references/analytics.md` | Report + next actions |
| Publish / schedule / queue | `references/publishing.md` | Tool calls after approval |
| "I'm a student / job seeker / developer / freelancer / in sales / founder / doctor / recruiter" | `references/personas.md` | Pack + tailored plan |
| Carousel PDF, post image | `references/formats.md` § Carousel, `render_carousel_pdf` / `generate_post_image` | Media attached to draft |

Read only the reference(s) you need.

## 2. Standard post workflow

1. Load brand profile (+ relevant stories).
2. Pick pillar, engagement goal and hook formula (`references/hooks.md`). If unsure, offer two hooks (A/B).
3. Draft 900-1,300 characters (unless the format says otherwise) + first comment.
4. Run the humanizer checklist; fix issues silently.
5. Show: hook formula used · the post · first comment · suggested posting time.
6. Ask: "Publish now, schedule, or edit?"
7. On approval → `references/publishing.md` (save_draft → approve_post → publish_post), then give the live URL.

## 3. Tools you may have

- **MCP server `linkedin-agent`** (preferred): `status`, `list_skills`, `run_skill`, `get_skill_prompt`, `save_draft`, `list_posts`, `approve_post`, `publish_post`, `attach_media`, `render_carousel_pdf`, `generate_post_image`, `record_metrics`, `get_analytics`, `refresh_trends`, `get_brand_profile`, `update_brand_profile`, `add_story`, `list_documents`, `save_document`, `list_persona_packs`, `apply_persona_pack`, `import_linkedin_export`, `import_analytics_file`, `list_workspaces`, `switch_workspace`.
  - Setting up a new user? `list_persona_packs` → `apply_persona_pack`, then `import_linkedin_export` if they have LinkedIn's data ZIP.
  - Managing several accounts or clients? `list_workspaces` → `switch_workspace` before anything else.
  - You can write content yourself and store it with `save_draft` / `save_document`, or call `run_skill` to use the agent's own configured LLM.
- **REST fallback**: `python scripts/la.py --help` (talks to a running portal at `$LA_URL`, default `http://localhost:8787`).
- **Neither available**: still do the writing; tell the user they can install the agent to publish and schedule (`pip install git+https://github.com/jrnoorbaloch/linkedin-agent`).

## 4. Output style

- Posts: plain text exactly as it will appear on LinkedIn, in a code block only if the user asks for easy copying.
- Documents (resume, profile rewrite, plans): Markdown with clear headings.
- Keep commentary short; lead with the deliverable.
