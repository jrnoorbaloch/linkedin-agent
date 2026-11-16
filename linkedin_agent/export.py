"""Export Markdown documents (resume, cover letter, plans) to .docx."""

from __future__ import annotations

import io
import re

from docx import Document
from docx.shared import Pt


def markdown_to_docx(markdown: str) -> bytes:
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)
    for raw in markdown.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        m = re.match(r"^(#{1,4})\s+(.*)", line)
        if m:
            doc.add_heading(_strip(m.group(2)), level=min(len(m.group(1)), 3))
        elif re.match(r"^\s*[-*•]\s+", line):
            _rich(doc.add_paragraph(style="List Bullet"), re.sub(r"^\s*[-*•]\s+", "", line))
        elif re.match(r"^\s*\d+[.)]\s+", line):
            _rich(doc.add_paragraph(style="List Number"), re.sub(r"^\s*\d+[.)]\s+", "", line))
        elif set(line.strip()) <= {"-", "|", ":", " "}:
            continue
        else:
            _rich(doc.add_paragraph(), line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _strip(s: str) -> str:
    return re.sub(r"\*\*|__|`", "", s)


def _rich(par, text: str) -> None:
    for i, part in enumerate(re.split(r"\*\*(.+?)\*\*", text)):
        run = par.add_run(part.replace("`", ""))
        run.bold = i % 2 == 1
