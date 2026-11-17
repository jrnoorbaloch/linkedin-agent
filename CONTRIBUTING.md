# Contributing

Thanks for helping make LinkedIn Agent better!

## Set up
```bash
git clone https://github.com/jrnoorbaloch/linkedin-agent && cd linkedin-agent
pip install -e '.[dev,desktop]'
pytest -q
LA_DATA_DIR=./data linkedin-agent serve
```

## Add a skill
Append a `Skill(...)` to `SKILLS` in `linkedin_agent/skills.py`. The portal, REST API and MCP server pick it up automatically. If it's for a specific audience, add it to a pack in `linkedin_agent/personas.py`.

## Add a language
Add a block to `linkedin_agent/static/i18n.js`. Set `rtl: true` for right-to-left scripts.

## Docs site
`docs/` is generated: run `python tools/build_demo.py && python tools/build_docs.py`.

## Ground rules
- Only LinkedIn's official APIs. No scraping, no browser automation of linkedin.com.
- Publishing must stay approval-gated.
- Keep secrets out of logs and the UI.
