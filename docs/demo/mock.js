/* In-browser mock of the LinkedIn Agent REST API, used by the live demo on the docs site.
   Nothing leaves the browser; generated text is canned sample output. */
(function () {
  window.LA_DEMO = true;
  const now = () => new Date().toISOString().slice(0, 19);
  const days = n => new Date(Date.now() - n * 864e5).toISOString().slice(0, 19);
  let nextId = 20;

  const skills = window.LA_SKILLS || [];
  const brand = {
    name: "Ayesha Khan", role: "Head of Growth at a B2B SaaS startup", industry: "SaaS / Marketing",
    audience: "Founders and marketing leads at early-stage B2B startups", offer: "Product-led growth playbooks",
    pillars: "PLG, hiring growth teams, founder-led sales, experiments", tone: "Direct, warm, numbers-first",
    language: "English", goals: "Inbound leads and speaking invites", avoid: "Hustle culture, buzzwords",
    sample_posts: "", profile_text: "",
  };
  const posts = [
    { id: 11, target: "member", pillar: "Experiments", hook_type: "data reveal", status: "draft", created_at: now(),
      content: "We ran 41 onboarding experiments last quarter.\n\n38 failed.\n\nThe 3 that worked had one thing in common: they removed a step instead of adding a feature.\n\n→ Killed the \"invite your team\" screen (+18% activation)\n→ Pre-filled the first project (+11%)\n→ Moved pricing after the aha moment (+9% trial-to-paid)\n\nYour onboarding doesn't need more. It needs less.\n\nWhat's one step you could delete this week?\n\n#ProductLedGrowth #SaaS",
      first_comment: "Full experiment log (anonymized) in our newsletter: https://example.com/plg" },
    { id: 10, target: "member", pillar: "Hiring", hook_type: "mistake/lesson", status: "scheduled", scheduled_at: days(-1), created_at: days(1),
      content: "I hired my first growth marketer for the wrong skill.\n\nI optimized for channel expertise. What we needed was someone who could run 5 cheap experiments a week and kill 4 of them without ego.\n\nHere's the interview question I use now…" },
    { id: 9, target: "member", pillar: "PLG", hook_type: "contrarian", status: "published", published_at: days(2), created_at: days(3), linkedin_urn: "urn:li:share:demo1",
      metrics: { impressions: 18420, reactions: 412, comments: 96, reposts: 31 },
      content: "Unpopular opinion: your free trial is too long.\n\nWe cut ours from 30 days to 7. Conversions went up 22%…" },
    { id: 8, target: "member", pillar: "Founder-led sales", hook_type: "time anchor", status: "published", published_at: days(5), created_at: days(6), linkedin_urn: "urn:li:share:demo2",
      metrics: { impressions: 9310, reactions: 188, comments: 41, reposts: 9 },
      content: "2 years ago I sent 300 cold emails and booked 2 calls.\n\nLast month: 40 emails, 11 calls…" },
  ];
  const documents = [
    { id: 3, kind: "resume", title: "Resume Builder — Head of Growth", created_at: days(1),
      content: "# Ayesha Khan\n[City] · [email] · linkedin.com/in/ayeshakhan\n\n## Summary\nGrowth leader who scaled a B2B SaaS from $1M to $6M ARR through product-led onboarding and experiment culture.\n\n## Experience\n### Head of Growth — [Company] (2023–present)\n- Built a 6-person growth team running 5+ experiments per week\n- Lifted activation 34% by removing 3 onboarding steps\n- Grew self-serve revenue from 20% to 55% of new ARR\n\n## Skills\nProduct-led growth · Experimentation · Lifecycle marketing · SQL · Amplitude · Team building" },
    { id: 2, kind: "profile", title: "Profile Optimizer — B2B SaaS founders", created_at: days(4),
      content: "## Score: 64/100\n\n## Headline options\n1. Head of Growth | I help B2B SaaS founders turn free users into paying customers | PLG · Onboarding · Experiments\n2. Scaling B2B SaaS with product-led growth ($1M → $6M ARR) | Head of Growth\n3. Growth leader for early-stage SaaS | Activation, onboarding & pricing experiments\n\n## About (rewrite)\nMost SaaS onboarding loses 60% of signups before they see any value…" },
  ];
  const stories = [
    { id: 1, title: "Cut the free trial from 30 to 7 days", body: "Q2 2025. Conversions +22%, support tickets -15%. Board was nervous.", tags: "pricing, experiments", created_at: days(9) },
    { id: 2, title: "First growth hire didn't work out", body: "Hired for channel expertise, needed experiment velocity. Parted ways after 5 months.", tags: "hiring, mistake", created_at: days(7) },
    { id: 3, title: "Spoke at SaaStock", body: "First keynote, 400 people, talked about killing onboarding steps.", tags: "speaking", created_at: days(3) },
  ];
  const contacts = [
    { id: 1, name: "Bilal Ahmed", headline: "Founder, Fintech startup", url: "", notes: "Met at SaaStock; interested in PLG audit", next_follow_up: new Date().toISOString().slice(0, 10), created_at: days(2) },
    { id: 2, name: "Sara Malik", headline: "VP Marketing", url: "", notes: "Podcast collab idea", next_follow_up: new Date(Date.now() + 5 * 864e5).toISOString().slice(0, 10), created_at: days(1) },
  ];
  let llm = { provider: "anthropic", format: "anthropic", base_url: "https://api.anthropic.com/v1", model: "claude-sonnet-5-5", api_key: "••••••••a1b2", temperature: 0.8 };
  let schedule = { daily_draft_enabled: true, daily_draft_time: "08:00", timezone: "Asia/Karachi", auto_publish: false, publish_time: "10:00" };
  const presets = { openai: { format: "openai", base_url: "https://api.openai.com/v1", model: "gpt-4.1-mini" }, anthropic: { format: "anthropic", base_url: "https://api.anthropic.com/v1", model: "claude-sonnet-5-5" }, gemini: { format: "openai", base_url: "https://generativelanguage.googleapis.com/v1beta/openai", model: "gemini-2.5-flash" }, groq: { format: "openai", base_url: "https://api.groq.com/openai/v1", model: "llama-3.3-70b-versatile" }, openrouter: { format: "openai", base_url: "https://openrouter.ai/api/v1", model: "openai/gpt-4.1-mini" }, deepseek: { format: "openai", base_url: "https://api.deepseek.com/v1", model: "deepseek-chat" }, ollama: { format: "openai", base_url: "http://localhost:11434/v1", model: "llama3.1" }, custom: { format: "openai", base_url: "", model: "" } };
  const member = { name: "Ayesha Khan", given_name: "Ayesha", sub: "demo" };

  const sample = {
    post: "Your onboarding has a step nobody needs.\n\nI know because we had four.\n\nLast quarter we deleted the \"invite your team\" screen. Activation went up 18% in two weeks.\n\nNo new feature. No redesign. Just one less thing between a signup and the moment they get value.\n\nHere's the test I now run on every step:\n→ Does this help the user see value faster?\n→ If we removed it, who would complain?\n→ Can we ask for it later instead?\n\nIf the answers are no, nobody, yes, it goes.\n\nWhich step in your onboarding would fail this test?\n\n#ProductLedGrowth #SaaS",
    comment: "I wrote up the full experiment (with the numbers) here: [link]",
    doc: "## Demo output\n\nThis is the live demo, so this is sample text. Install LinkedIn Agent and connect your own LLM to generate real content from your brand profile.\n\n| Day | Pillar | Format | Hook |\n|---|---|---|---|\n| Mon | PLG | Text | Data reveal |\n| Tue | Hiring | Story | Mistake/lesson |\n| Wed | Experiments | Carousel | Numbered list |\n| Thu | Founder-led sales | Poll | Controlled A/B |\n| Fri | PLG | Hot take | Contrarian |",
  };

  const json = v => JSON.parse(JSON.stringify(v));
  const delay = ms => new Promise(r => setTimeout(r, ms));
  const withUrl = p => ({ ...p, url: p.linkedin_urn ? "https://www.linkedin.com/" : null });

  window.LA_MOCK = async function (path, opts = {}) {
    const method = opts.method || "GET", body = opts.body || {};
    const [p, qs] = path.split("?"); const q = new URLSearchParams(qs || "");
    await delay(method === "GET" ? 60 : 350);
    let m;
    if (p === "/api/health") return { ok: true, version: "0.1.0" };
    if (p === "/api/dashboard") {
      const pub = posts.filter(x => x.status === "published");
      const imp = pub.reduce((a, x) => a + (x.metrics?.impressions || 0), 0);
      const eng = pub.reduce((a, x) => a + (x.metrics?.reactions || 0) + (x.metrics?.comments || 0), 0);
      return { drafts: posts.filter(x => x.status === "draft").length, approved: posts.filter(x => ["approved", "scheduled"].includes(x.status)).length,
        published: pub.length, failed: 0, impressions: imp, engagement_rate: imp ? +(100 * eng / imp).toFixed(2) : null,
        stories: stories.length, documents: documents.length, linkedin: { connected: true, member, expires_in_days: 52, org_enabled: false },
        llm, brand_complete: 10, schedule };
    }
    if (p === "/api/skills") return json(skills);
    if ((m = p.match(/^\/api\/skills\/(\w+)$/))) {
      const s = skills.find(x => x.id === m[1]);
      await delay(900);
      if (s.output === "post") { const id = nextId++; posts.unshift({ id, target: "member", pillar: body.pillar || "PLG", hook_type: body.hook && body.hook !== "auto" ? body.hook : "curiosity gap", status: "draft", content: sample.post, first_comment: sample.comment, created_at: now() });
        return { skill: s.id, output: "HOOK: curiosity gap\n---\n" + sample.post + "\n---\nFIRST COMMENT: " + sample.comment, post_id: id, post: sample.post }; }
      if (s.output === "document") { const id = nextId++; documents.unshift({ id, kind: "note", title: s.title + " (demo)", content: sample.doc, created_at: now() }); return { skill: s.id, output: sample.doc, document_id: id }; }
      return { skill: s.id, output: "A) Love that you measured activation, not signups. We saw the same: removing steps beat adding features every time.\n\nB) We deleted our team-invite step last year and activation jumped 18%. Biggest surprise: nobody missed it.\n\nC) How did you decide which step to test first?\n\nREACTION: Insightful" };
    }
    if (p === "/api/posts" && method === "GET") return json(posts.filter(x => !q.get("status") || x.status === q.get("status")).map(withUrl));
    if (p === "/api/posts" && method === "POST") { const id = nextId++; posts.unshift({ id, target: "member", status: "draft", created_at: now(), ...body }); return { id }; }
    if ((m = p.match(/^\/api\/posts\/(\d+)(\/\w+)?$/))) {
      const post = posts.find(x => x.id == m[1]); const act = m[2];
      if (method === "DELETE") { posts.splice(posts.indexOf(post), 1); return { ok: true }; }
      if (method === "PATCH") { Object.assign(post, body); return post; }
      if (act === "/approve") { Object.assign(post, { status: body.scheduled_at ? "scheduled" : "approved", scheduled_at: body.scheduled_at || null }, body.content ? { content: body.content } : {}); return post; }
      if (act === "/publish") { Object.assign(post, { status: "published", published_at: now(), linkedin_urn: "urn:li:share:demo" + post.id }); return withUrl(post); }
    }
    if (p === "/api/documents") return json(documents);
    if ((m = p.match(/^\/api\/documents\/(\d+)$/))) { documents.splice(documents.findIndex(d => d.id == m[1]), 1); return { ok: true }; }
    if (p === "/api/stories" && method === "GET") return json(stories);
    if (p === "/api/stories") { stories.unshift({ id: nextId++, created_at: now(), ...body }); return {}; }
    if ((m = p.match(/^\/api\/stories\/(\d+)$/))) { stories.splice(stories.findIndex(d => d.id == m[1]), 1); return { ok: true }; }
    if (p === "/api/contacts" && method === "GET") return json(contacts);
    if (p === "/api/contacts") { contacts.unshift({ id: nextId++, created_at: now(), ...body }); return {}; }
    if ((m = p.match(/^\/api\/contacts\/(\d+)$/))) { contacts.splice(contacts.findIndex(d => d.id == m[1]), 1); return { ok: true }; }
    if (p === "/api/brand" && method === "GET") return { profile: brand, fields: window.LA_PROFILE_FIELDS };
    if (p === "/api/brand") { Object.assign(brand, body); return brand; }
    if (p === "/api/llm" && method === "GET") return { config: llm, presets };
    if (p === "/api/llm") { llm = { ...llm, ...body, api_key: "••••••••demo" }; return llm; }
    if (p === "/api/llm/test") return { ok: true, reply: "OK (demo)" };
    if (p === "/api/linkedin/status") return { connected: true, member, expires_in_days: 52, org_enabled: false };
    if (p === "/api/schedule" && method === "GET") return schedule;
    if (p === "/api/schedule") { schedule = { ...schedule, ...body }; return schedule; }
    throw new Error("Demo mode: " + p + " is not available");
  };
})();
