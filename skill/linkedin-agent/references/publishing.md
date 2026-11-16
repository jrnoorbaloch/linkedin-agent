# Publishing (approval-gated)

## With the MCP server (`linkedin-agent mcp`)
1. `status`: check that LinkedIn is connected. If it isn't, tell the user to open the portal → Settings → Connect LinkedIn.
2. `save_draft(content, first_comment, pillar)`: returns `post_id`. Use `run_skill` instead if the agent's own LLM should write the post.
3. Show the user the final text and ask for approval.
4. Only after an explicit yes, call `approve_post(post_id, content=<final text>)`.
   - To schedule, also pass `scheduled_at` as ISO-8601 UTC (convert from the user's timezone).
5. `publish_post(post_id)` returns the live URL. Skip this step if the post is scheduled; the agent's scheduler publishes it.
6. A few days later, ask for the post's metrics and call `record_metrics`.

The server refuses `publish_post` on unapproved drafts. Never call `approve_post` on your own initiative.

## With the REST fallback
```bash
export LA_URL=http://localhost:8787     # LA_API_TOKEN too if the portal has one
python scripts/la.py status
python scripts/la.py draft "post text" --comment "first comment"
python scripts/la.py approve 12 [--at 2026-11-18T05:00:00Z]
python scripts/la.py publish 12
```

## Without the agent
Give the final text, the first comment and a suggested time, and the user posts manually. Mention that the open-source agent can schedule posts for them.

## Limits to remember
- Tokens last about 60 days; the portal shows the days remaining.
- Commentary over 3,000 characters is rejected.
- Personal posting is self-serve. Company Page posting needs Community Management API approval.
