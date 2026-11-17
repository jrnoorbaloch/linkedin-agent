"""Regenerate the docs site's live UI demo from the real portal.

    python tools/build_demo.py

Copies linkedin_agent/static/index.html to docs/demo/index.html, injects the
mock API (docs/demo/mock.js) and the current skill registry, and writes
docs/skills.json used by the Skills page.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from linkedin_agent import personas, skills  # noqa: E402
import shutil  # noqa: E402

demo = ROOT / "docs" / "demo"
demo.mkdir(parents=True, exist_ok=True)
registry = skills.list_skills()
(demo / "skills.js").write_text(
    "window.LA_SKILLS=" + json.dumps(registry) + ";\nwindow.LA_PROFILE_FIELDS=" + json.dumps(skills.PROFILE_FIELDS)
    + ";\nwindow.LA_PACKS=" + json.dumps(personas.list_packs()) + ";\n",
    encoding="utf-8",
)
(ROOT / "docs" / "skills.json").write_text(json.dumps(registry, indent=1), encoding="utf-8")
html = (ROOT / "linkedin_agent" / "static" / "index.html").read_text(encoding="utf-8")
inject = (
    '<meta name="robots" content="noindex">\n'
    '<script src="skills.js"></script>\n<script src="mock.js"></script>\n'
)
html = html.replace("<title>LinkedIn Agent</title>", "<title>LinkedIn Agent — Live demo</title>\n" + inject, 1)
(demo / "index.html").write_text(html, encoding="utf-8")
(demo / "static").mkdir(exist_ok=True)
shutil.copy(ROOT / "linkedin_agent" / "static" / "i18n.js", demo / "static" / "i18n.js")
print(f"demo built: {len(registry)} skills")
