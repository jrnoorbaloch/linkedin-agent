/* In-browser mock of the LinkedIn Agent v2 REST API for the live demo. Nothing leaves the browser. */
(function () {
  window.LA_DEMO = true;
  const iso = (dDays, h = 9, m = 0) => { const d = new Date(); d.setDate(d.getDate() + dDays); d.setHours(h, m, 0, 0); return d.toISOString(); };
  let nextId = 40;
  const skills = window.LA_SKILLS || [];
  const brand = {
    name: "Ayesha Khan", role: "Head of Growth at a B2B SaaS startup · PLG nerd", industry: "SaaS / Marketing",
    audience: "Founders and marketing leads at early-stage B2B startups", offer: "Product-led growth playbooks and advisory",
    pillars: "PLG, Hiring growth teams, Founder-led sales, Experiments", tone: "Direct, warm, numbers-first", language: "English",
    goals: "Inbound leads and speaking invites", avoid: "Hustle culture, buzzwords", sample_posts: "", profile_text: "Head of Growth at Northwind (2023–present)…",
  };
  const P = (o) => ({ target: "member", first_comment: null, media_id: null, review_note: null, metrics: null, scheduled_at: null, published_at: null, linkedin_urn: null, ...o });
  const posts = [
    P({ id: 31, pillar: "Experiments", hook_type: "data reveal", status: "draft", created_at: iso(0, 7, 58), source: "agent",
      content: "We ran 41 onboarding experiments last quarter.\n\n38 failed.\n\nThe 3 that worked had one thing in common: they removed a step instead of adding a feature.\n\n→ Killed the \"invite your team\" screen (+18% activation)\n→ Pre-filled the first project (+11%)\n→ Moved pricing after the aha moment (+9% trial-to-paid)\n\nYour onboarding doesn't need more. It needs less.\n\nWhat's one step you could delete this week?\n\n#ProductLedGrowth #SaaS",
      first_comment: "Full experiment log (anonymised) in this week's newsletter: https://example.com/plg", media_id: 3 }),
    P({ id: 30, pillar: "Hiring", hook_type: "mistake/lesson", status: "draft", created_at: iso(-1, 8), review_note: "Love it. Can we add one line on what the interview question actually is?",
      content: "I hired my first growth marketer for the wrong skill.\n\nI optimised for channel expertise. What we needed was someone who could run 5 cheap experiments a week and kill 4 of them without ego.\n\nHere's the interview question I use now…" }),
    P({ id: 29, pillar: "Founder-led sales", hook_type: "time anchor", status: "approved", created_at: iso(-1, 9),
      content: "2 years ago I sent 300 cold emails and booked 2 calls.\n\nLast month: 40 emails, 11 calls.\n\nThe difference wasn't the copy. It was who I wrote to." }),
    P({ id: 28, pillar: "PLG", hook_type: "contrarian", status: "scheduled", scheduled_at: iso(1, 9, 30), created_at: iso(-2), media_id: 2,
      content: "Unpopular opinion: your free trial is too long.\n\nWe cut ours from 30 days to 7. Conversions went up 22%.\n\nSwipe through the 6 changes we made 👇" }),
    P({ id: 27, pillar: "Experiments", hook_type: "numbered list", status: "scheduled", scheduled_at: iso(3, 8, 45), created_at: iso(-2),
      content: "5 growth experiments you can run this week with zero engineering time:" }),
    P({ id: 26, pillar: "PLG", hook_type: "contrarian", status: "published", published_at: iso(-2, 9), created_at: iso(-3), linkedin_urn: "urn:li:share:1",
      metrics: { impressions: 18420, reactions: 412, comments: 96, reposts: 31 }, content: "Stop asking for a credit card on day one.\n\nWe removed it and paid conversions went up, not down." }),
    P({ id: 25, pillar: "Founder-led sales", hook_type: "time anchor", status: "published", published_at: iso(-5, 8), created_at: iso(-6), linkedin_urn: "urn:li:share:2",
      metrics: { impressions: 9310, reactions: 188, comments: 41, reposts: 9 }, content: "The best sales call I ever had started with me saying \"I don't think we're a fit.\"" }),
    P({ id: 24, pillar: "Hiring", hook_type: "story", status: "published", published_at: iso(-9, 13), created_at: iso(-10), linkedin_urn: "urn:li:share:3",
      metrics: { impressions: 6120, reactions: 95, comments: 22, reposts: 4 }, content: "Our best hire had zero marketing experience." }),
    P({ id: 23, pillar: "Experiments", hook_type: "data reveal", status: "published", published_at: iso(-12, 9), created_at: iso(-13), linkedin_urn: "urn:li:share:4",
      metrics: { impressions: 12880, reactions: 301, comments: 77, reposts: 19 }, content: "We A/B tested 12 pricing pages. The winner had fewer words." }),
    P({ id: 22, pillar: "PLG", hook_type: "how I", status: "published", published_at: iso(-16, 17), created_at: iso(-17), linkedin_urn: "urn:li:share:5",
      metrics: { impressions: 4410, reactions: 61, comments: 9, reposts: 2 }, content: "How we got to 1,000 self-serve signups a month." }),
    P({ id: 21, pillar: "Founder-led sales", hook_type: "question", status: "published", published_at: iso(-19, 8), created_at: iso(-20), linkedin_urn: "urn:li:share:6",
      metrics: { impressions: 7720, reactions: 140, comments: 58, reposts: 6 }, content: "Founders: who writes your cold emails?" }),
    P({ id: 20, pillar: "Hiring", hook_type: "contrarian", status: "published", published_at: iso(-23, 10), created_at: iso(-24), linkedin_urn: "urn:li:share:7",
      metrics: { impressions: 5230, reactions: 88, comments: 17, reposts: 3 }, content: "Don't hire a Head of Growth before product-market fit." }),
  ];
  const svg = (bg, fg, t) => "data:image/svg+xml;utf8," + encodeURIComponent(`<svg xmlns='http://www.w3.org/2000/svg' width='1080' height='1350'><rect width='100%' height='100%' fill='${bg}'/><rect x='90' y='150' width='120' height='14' fill='${fg}' opacity='.6'/><text x='90' y='330' font-family='Arial' font-weight='700' font-size='88' fill='${fg}'>${t}</text></svg>`);
  const media = [
    { id: 3, kind: "image", title: "Onboarding funnel illustration", url: svg("#eef1ff", "#3b5bfd", "Less is more"), created_at: iso(0) },
    { id: 2, kind: "pdf", title: "Carousel — 7-day trial", url: "#", created_at: iso(-2) },
    { id: 1, kind: "image", title: "Pricing page chart", url: svg("#0f1b33", "#a5f3c5", "+22%"), created_at: iso(-4) },
  ];
  const documents = [
    { id: 3, kind: "resume", title: "Resume Builder — Head of Growth", created_at: iso(-1),
      content: "# Ayesha Khan\n[City] · [email] · linkedin.com/in/ayeshakhan\n\n## Summary\nGrowth leader who scaled a B2B SaaS from $1M to $6M ARR through product-led onboarding and an experiment culture.\n\n## Experience\n### Head of Growth — Northwind (2023–present)\n- Built a 6-person growth team running 5+ experiments a week\n- Lifted activation 34% by removing 3 onboarding steps\n- Grew self-serve revenue from 20% to 55% of new ARR" },
    { id: 2, kind: "profile", title: "Profile Optimizer — B2B SaaS founders", created_at: iso(-4),
      content: "## Score: 64/100\n\n## Headline options\n1. Head of Growth | I help B2B SaaS founders turn free users into paying customers | PLG · Onboarding\n2. Scaling B2B SaaS with product-led growth ($1M → $6M ARR)\n3. Growth leader for early-stage SaaS | Activation, onboarding & pricing experiments" },
    { id: 1, kind: "note", title: "Carousel Builder — 7-day trial", created_at: iso(-3), content: "Slide 1 — Your free trial is too long\nWe cut ours from 30 to 7 days\nSlide 2 — Conversions went up 22%\nUrgency beats time" },
  ];
  const stories = [
    { id: 1, title: "Cut the free trial from 30 to 7 days", body: "Q2 2025. Conversions +22%, support tickets −15%. The board was nervous.", tags: "pricing, experiments", created_at: iso(-9) },
    { id: 2, title: "First growth hire didn't work out", body: "Hired for channel expertise, needed experiment speed. Parted ways after 5 months.", tags: "hiring, mistake", created_at: iso(-7) },
    { id: 3, title: "First keynote at SaaStock", body: "400 people. Talked about deleting onboarding steps.", tags: "speaking", created_at: iso(-3) },
  ];
  const contacts = [
    { id: 1, name: "Bilal Ahmed", headline: "Founder, fintech startup", url: "", notes: "Met at SaaStock. Interested in a PLG audit.", next_follow_up: iso(0).slice(0, 10), created_at: iso(-2) },
    { id: 2, name: "Sara Malik", headline: "VP Marketing", url: "", notes: "Podcast collab idea", next_follow_up: iso(5).slice(0, 10), created_at: iso(-1) },
    { id: 3, name: "Omar Siddiqui", headline: "Seed investor", url: "", notes: "Wants intros to PLG founders", next_follow_up: iso(9).slice(0, 10), created_at: iso(-1) },
  ];
  const trends = [
    { id: 1, title: "Product-led sales is eating traditional SaaS sales", source: "saastr.com", link: "#" },
    { id: 2, title: "Why onboarding checklists are making a comeback", source: "lennysnewsletter.com", link: "#" },
    { id: 3, title: "AI agents start handling first-line customer support", source: "techcrunch.com", link: "#" },
    { id: 4, title: "Free trials vs. freemium: new benchmark data for 2026", source: "openviewpartners.com", link: "#" },
    { id: 5, title: "LinkedIn rolls out new creator analytics", source: "news.linkedin.com", link: "#" },
  ];
  let feeds = ["https://techcrunch.com/feed/", "https://www.saastr.com/feed/"];
  let accounts = [{ id: 1, name: "Ayesha Khan", color: "#3b5bfd", persona: "founder", linkedin_name: "Ayesha Khan" }, { id: 2, name: "Northwind (Page)", color: "#12a150", persona: "recruiter", linkedin_name: null }, { id: 3, name: "Client: Bilal", color: "#c97a00", persona: "sales", linkedin_name: "Bilal Ahmed" }];
  let llm = { provider: "anthropic", format: "anthropic", base_url: "https://api.anthropic.com/v1", model: "claude-sonnet-5-5", api_key: "••••••••a1b2", temperature: 0.8 };
  let image = { base_url: "https://api.openai.com/v1", model: "gpt-image-1", api_key: "••••••••9f3c", size: "1024x1024" };
  let schedule = { daily_draft_enabled: true, daily_draft_time: "08:00", timezone: "Asia/Karachi", auto_publish: false, publish_time: "10:00", post_days: [0, 1, 2, 3, 4] };
  let persona = "founder";
  const presets = { openai: { format: "openai", base_url: "https://api.openai.com/v1", model: "gpt-4.1-mini" }, anthropic: { format: "anthropic", base_url: "https://api.anthropic.com/v1", model: "claude-sonnet-5-5" }, gemini: { format: "openai", base_url: "https://generativelanguage.googleapis.com/v1beta/openai", model: "gemini-2.5-flash" }, groq: { format: "openai", base_url: "https://api.groq.com/openai/v1", model: "llama-3.3-70b-versatile" }, openrouter: { format: "openai", base_url: "https://openrouter.ai/api/v1", model: "openai/gpt-4.1-mini" }, deepseek: { format: "openai", base_url: "https://api.deepseek.com/v1", model: "deepseek-chat" }, ollama: { format: "openai", base_url: "http://localhost:11434/v1", model: "llama3.1" }, custom: { format: "openai", base_url: "", model: "" } };
  const member = { name: "Ayesha Khan", given_name: "Ayesha", sub: "demo" };
  const packs = (window.LA_PACKS || []);
  let notifyCfg = { telegram: { enabled: true, bot_token: "••••••3f9a", chat_id: "987654321" }, whatsapp: { enabled: false }, slack: { enabled: true, webhook_url: "https://hooks.slack.com/services/T000/B000/XXXX" }, webhooks: ["https://hooks.zapier.com/hooks/catch/123/abc"], events: ["draft_created", "approved", "scheduled", "published", "failed", "review_feedback"] };
  const team = [{ id: 1, name: "Ayesha Khan", email: "ayesha@northwind.io", role: "admin" }, { id: 2, name: "Hamza Ali", email: "hamza@northwind.io", role: "editor" }, { id: 3, name: "Sana Iqbal", email: "sana@client.com", role: "reviewer" }];

  const sample = {
    post: "Your onboarding has a step nobody needs.\n\nI know because we had four.\n\nLast quarter we deleted the \"invite your team\" screen. Activation went up 18% in two weeks.\n\nNo new feature. No redesign. Just one less thing between a signup and the moment they get value.\n\nHere's the test I now run on every step:\n→ Does this help the user see value faster?\n→ If we removed it, who would complain?\n→ Can we ask for it later instead?\n\nIf the answers are no, nobody, yes, it goes.\n\nWhich step in your onboarding would fail this test?\n\n#ProductLedGrowth #SaaS",
    comment: "I wrote up the full experiment (with the numbers) here: [link]",
    doc: "## Demo output\n\nThis is the live demo, so this is sample text. Install LinkedIn Agent and connect your own model to generate real content from your brand profile.\n\n| Day | Pillar | Format | Hook |\n|---|---|---|---|\n| Mon | PLG | Text | Data reveal |\n| Tue | Hiring | Story | Mistake/lesson |\n| Wed | Experiments | Carousel | Numbered list |\n| Thu | Founder-led sales | Poll | Controlled A/B |\n| Fri | PLG | Hot take | Contrarian |",
  };
  const json = v => JSON.parse(JSON.stringify(v));
  const delay = ms => new Promise(r => setTimeout(r, ms));
  const deco = p => { const o = { ...p, url: p.linkedin_urn ? "https://www.linkedin.com/" : null }; const m = media.find(x => x.id === p.media_id); if (m) o.media = { id: m.id, kind: m.kind, title: m.title, url: m.url }; return o; };
  const rate = m => m && m.impressions ? 100 * ((m.reactions || 0) + (m.comments || 0) + (m.reposts || 0)) / m.impressions : null;

  function analytics() {
    const pub = posts.filter(p => p.status === "published" && p.metrics);
    const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], grid = days.map(() => Array(8).fill(null));
    const base = [[null, null, 4.1, 3.6, 2.9, 2.2, null, null], [null, null, 4.8, 3.9, 3.1, 2.6, 1.9, null], [null, null, 3.9, 3.4, 2.7, 2.4, null, null], [null, null, 4.3, 3.7, 3.3, 2.1, 1.7, null], [null, null, 3.2, 2.8, 2.2, 1.9, null, null], [null, null, null, 1.8, 1.6, null, null, null], [null, null, null, 1.5, 1.9, null, null, null]];
    base.forEach((r, i) => r.forEach((v, j) => grid[i][j] = v));
    const by = k => { const g = {}; pub.forEach(p => { (g[p[k]] = g[p[k]] || []).push(rate(p.metrics)); }); return Object.entries(g).map(([name, v]) => ({ name, n: v.length, rate: +(v.reduce((a, b) => a + b, 0) / v.length).toFixed(2) })).sort((a, b) => b.rate - a.rate); };
    const weekly = [6120, 8840, 7730, 12880, 9310, 18420, 15200, 21300].map((v, i) => ({ week: "2026-W" + (39 + i), impressions: v, engagements: Math.round(v * 0.035) }));
    return { posts_with_metrics: pub.length, heatmap: { days, buckets: ["00-03h", "03-06h", "06-09h", "09-12h", "12-15h", "15-18h", "18-21h", "21-24h"], grid },
      best_slots: [{ day: "Tue", hours: "06:00-09:00", rate: 4.8 }, { day: "Thu", hours: "06:00-09:00", rate: 4.3 }, { day: "Mon", hours: "06:00-09:00", rate: 4.1 }],
      by_hook: by("hook_type"), by_pillar: by("pillar"), weekly,
      top_posts: pub.map(p => ({ id: p.id, content: p.content.slice(0, 120), rate: +rate(p.metrics).toFixed(2), ...p.metrics })).sort((a, b) => b.rate - a.rate).slice(0, 5) };
  }

  window.LA_MOCK = async function (path, opts = {}) {
    const method = opts.method || "GET", body = opts.body || {};
    const [p, qs] = path.split("?"); const q = new URLSearchParams(qs || "");
    await delay(method === "GET" ? 40 : 300);
    let m;
    if (p === "/api/health") return { ok: true, version: "2.0.0" };
    if (p === "/api/auth/me") return { user: { name: "Ayesha Khan", role: "admin" }, team_mode: true };
    if (p === "/api/accounts" && method === "GET") return json(accounts.map(a => ({ ...a, drafts: a.id === 1 ? posts.filter(x => x.status === "draft").length : a.id === 3 ? 2 : 0 })));
    if (p === "/api/accounts" && method === "POST") { const id = nextId++; accounts.push({ id, name: body.name, color: body.color || "#7c4dff" }); return { id }; }
    if ((m = p.match(/^\/api\/accounts\/(\d+)$/))) { if (method === "DELETE") accounts = accounts.filter(a => a.id != m[1]); else Object.assign(accounts.find(a => a.id == m[1]), body); return { ok: true }; }
    if (p === "/api/dashboard") {
      const pub = posts.filter(x => x.status === "published"); const imp = pub.reduce((a, x) => a + (x.metrics?.impressions || 0), 0);
      const eng = pub.reduce((a, x) => a + (x.metrics?.reactions || 0) + (x.metrics?.comments || 0) + (x.metrics?.reposts || 0), 0);
      return { drafts: posts.filter(x => x.status === "draft").length, approved: posts.filter(x => ["approved", "scheduled"].includes(x.status)).length, published: pub.length, failed: 0,
        impressions: imp, engagement_rate: +(100 * eng / imp).toFixed(2), stories: stories.length, documents: documents.length, media: media.length,
        linkedin: { connected: true, member, expires_in_days: 52, org_enabled: false }, llm, brand_complete: 10, schedule, persona,
        upcoming: posts.filter(x => x.status === "scheduled").map(deco), recent_drafts: posts.filter(x => x.status === "draft").map(deco), best_slots: analytics().best_slots };
    }
    if (p === "/api/skills") return json(skills);
    if ((m = p.match(/^\/api\/skills\/(\w+)$/))) {
      const s = skills.find(x => x.id === m[1]); await delay(800);
      if (s.output === "post") { const id = nextId++; posts.unshift(P({ id, pillar: body.pillar || "PLG", hook_type: body.hook && body.hook !== "auto" ? body.hook : "curiosity gap", status: "draft", content: sample.post, first_comment: sample.comment, created_at: new Date().toISOString() }));
        return { skill: s.id, output: sample.post, post_id: id, post: sample.post, first_comment: sample.comment }; }
      if (s.output === "document") { const id = nextId++; documents.unshift({ id, kind: "note", title: s.title + " (demo)", content: sample.doc, created_at: new Date().toISOString() }); return { skill: s.id, output: sample.doc, document_id: id }; }
      return { skill: s.id, output: "A) Love that you measured activation, not signups. We saw the same: removing steps beat adding features every time.\n\nB) We deleted our team-invite step last year and activation jumped 18%. Biggest surprise: nobody missed it.\n\nC) How did you decide which step to test first?\n\nREACTION: Insightful" };
    }
    if (p === "/api/posts" && method === "GET") {
      let rows = posts; const st = q.get("status"); if (st) rows = rows.filter(x => st.split(",").includes(x.status));
      if (q.get("start")) { const a = q.get("start"), b = q.get("end"); rows = rows.filter(x => { const w = x.scheduled_at || x.published_at || x.created_at; return w >= a && w <= b; }); }
      return json(rows.map(deco));
    }
    if (p === "/api/posts" && method === "POST") { const id = nextId++; posts.unshift(P({ id, status: "draft", created_at: new Date().toISOString(), ...body })); return deco(posts[0]); }
    if ((m = p.match(/^\/api\/posts\/(\d+)(\/\w+)?$/))) {
      const post = posts.find(x => x.id == m[1]); const act = m[2];
      if (method === "DELETE") { posts.splice(posts.indexOf(post), 1); return { ok: true }; }
      if (method === "PATCH") { Object.assign(post, body); return deco(post); }
      if (act === "/approve") { Object.assign(post, { status: body.scheduled_at ? "scheduled" : "approved", scheduled_at: body.scheduled_at || null }, body.content ? { content: body.content } : {}); return deco(post); }
      if (act === "/publish") { Object.assign(post, { status: "published", published_at: new Date().toISOString(), linkedin_urn: "urn:li:share:demo" + post.id }); return deco(post); }
      if (act === "/share") return { url: location.origin + "/review/demo-" + post.id };
    }
    if (p === "/api/documents") return json(documents);
    if ((m = p.match(/^\/api\/documents\/(\d+)$/))) { documents.splice(documents.findIndex(d => d.id == m[1]), 1); return { ok: true }; }
    if (p === "/api/stories" && method === "GET") return json(stories);
    if (p === "/api/stories") { stories.unshift({ id: nextId++, created_at: new Date().toISOString(), ...body }); return {}; }
    if ((m = p.match(/^\/api\/stories\/(\d+)$/))) { stories.splice(stories.findIndex(d => d.id == m[1]), 1); return { ok: true }; }
    if (p === "/api/contacts" && method === "GET") return json(contacts);
    if (p === "/api/contacts") { contacts.unshift({ id: nextId++, created_at: new Date().toISOString(), ...body }); return {}; }
    if ((m = p.match(/^\/api\/contacts\/(\d+)$/))) { contacts.splice(contacts.findIndex(d => d.id == m[1]), 1); return { ok: true }; }
    if (p === "/api/brand" && method === "GET") return { profile: brand, fields: window.LA_PROFILE_FIELDS, persona };
    if (p === "/api/brand") { Object.assign(brand, body); return brand; }
    if (p === "/api/packs") return { packs: json(packs), active: persona };
    if ((m = p.match(/^\/api\/packs\/(\w+)$/))) { persona = m[1]; return { brand }; }
    if (p === "/api/llm" && method === "GET") return { config: llm, presets, image };
    if (p === "/api/llm") { llm = { ...llm, ...body, api_key: "••••••••demo" }; return llm; }
    if (p === "/api/llm/test") return { ok: true, reply: "OK (demo)" };
    if (p === "/api/image-model") { image = { ...image, ...body, api_key: "••••••••demo" }; return image; }
    if (p === "/api/linkedin/status") return { connected: true, configured: true, member, expires_in_days: 52, org_enabled: false };
    if (p === "/api/schedule" && method === "GET") return schedule;
    if (p === "/api/schedule") { schedule = { ...schedule, ...body }; return schedule; }
    if (p === "/api/analytics") return analytics();
    if (p === "/api/media") return json(media);
    if (p === "/api/media/carousel") { const id = nextId++; media.unshift({ id, kind: "pdf", title: body.title || "Carousel", url: "#", created_at: new Date().toISOString() }); return media[0]; }
    if (p === "/api/media/generate" || p === "/api/media/upload") { const id = nextId++; await delay(700); media.unshift({ id, kind: "image", title: (body.prompt || body.title || "Image").slice(0, 40), url: svg("#fff4dc", "#c97a00", "New image"), created_at: new Date().toISOString() }); return media[0]; }
    if ((m = p.match(/^\/api\/media\/(\d+)$/))) { media.splice(media.findIndex(d => d.id == m[1]), 1); return { ok: true }; }
    if (p === "/api/trends") return { feeds, items: json(trends) };
    if (p === "/api/trends/feeds") { feeds = body.feeds.filter(Boolean); return { feeds }; }
    if (p === "/api/trends/refresh") return { added: 0, errors: [] };
    if (p === "/api/integrations" && method === "GET") return { notify: notifyCfg, events: ["draft_created", "approved", "scheduled", "published", "failed", "review_feedback"], ics_url: "http://localhost:8787/calendar/1/•••••.ics", csv_url: "#", whatsapp_webhook: "https://your-domain/webhooks/whatsapp" };
    if (p === "/api/integrations") { Object.assign(notifyCfg, body); return notifyCfg; }
    if (p === "/api/integrations/test") return { ok: true };
    if (p === "/api/team" && method === "GET") return { users: team, roles: ["admin", "editor", "reviewer"] };
    if (p.startsWith("/api/team")) return { ok: true };
    if (p.startsWith("/api/import/linkedin")) { await delay(900); return { posts_imported: 128, positions: 6, skills: 34, brand }; }
    if (p.startsWith("/api/import/analytics")) { await delay(700); return { rows: 42, updated: 39, created: 3 }; }
    if (p === "/api/auth/logout") return { ok: true };
    throw new Error("Not available in the demo");
  };
})();
