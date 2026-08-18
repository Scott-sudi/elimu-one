#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Génère HANDOFF-AGENT-IA.pdf depuis le Markdown de passation."""

from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

ROOT = Path(__file__).resolve().parents[1]
MD_PATH = ROOT / "docs" / "HANDOFF-AGENT-IA.md"
OUT_PATH = ROOT / "docs" / "HANDOFF-AGENT-IA.pdf"

NAVY = colors.HexColor("#002858")
GREEN = colors.HexColor("#40a040")
MUTED = colors.HexColor("#555555")
INK = colors.HexColor("#1a1a1a")


def register_fonts() -> None:
    for name, path in (
        ("HandoffSans", r"C:\Windows\Fonts\arial.ttf"),
        ("HandoffSans-Bold", r"C:\Windows\Fonts\arialbd.ttf"),
        ("HandoffMono", r"C:\Windows\Fonts\consola.ttf"),
    ):
        p = Path(path)
        if p.exists():
            pdfmetrics.registerFont(TTFont(name, str(p)))


def build_styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "DocTitle",
            parent=base["Title"],
            fontName="HandoffSans-Bold",
            fontSize=20,
            textColor=NAVY,
            spaceAfter=14,
            leading=24,
        ),
        "meta": ParagraphStyle(
            "Meta",
            parent=base["Normal"],
            fontName="HandoffSans",
            fontSize=9,
            textColor=MUTED,
            spaceAfter=16,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontName="HandoffSans-Bold",
            fontSize=14,
            textColor=NAVY,
            spaceBefore=16,
            spaceAfter=8,
            leading=18,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName="HandoffSans-Bold",
            fontSize=12,
            textColor=GREEN,
            spaceBefore=12,
            spaceAfter=6,
            leading=15,
        ),
        "h3": ParagraphStyle(
            "H3",
            parent=base["Heading3"],
            fontName="HandoffSans-Bold",
            fontSize=10.5,
            textColor=INK,
            spaceBefore=8,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontName="HandoffSans",
            fontSize=9.5,
            leading=13,
            alignment=TA_LEFT,
            spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["Normal"],
            fontName="HandoffSans",
            fontSize=9.5,
            leading=13,
            leftIndent=14,
            bulletIndent=0,
            spaceAfter=3,
        ),
        "code": ParagraphStyle(
            "Code",
            parent=base["Code"],
            fontName="HandoffMono",
            fontSize=7.5,
            leading=10,
            leftIndent=8,
            rightIndent=8,
            backColor=colors.HexColor("#f4f6f8"),
            spaceAfter=6,
            spaceBefore=4,
        ),
    }


def escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def inline_format(text: str) -> str:
    text = escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`([^`]+)`", r'<font name="HandoffMono">\1</font>', text)
    return text


def md_to_story(md_text: str, styles) -> list:
    story = []
    in_code = False
    code_lines: list[str] = []

    for raw_line in md_text.splitlines():
        line = raw_line.rstrip()

        if line.strip().startswith("```"):
            if in_code:
                block = "<br/>".join(escape(x) for x in code_lines)
                story.append(Paragraph(block, styles["code"]))
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not line.strip():
            story.append(Spacer(1, 0.15 * cm))
            continue

        if line.strip() == "---":
            story.append(Spacer(1, 0.1 * cm))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")))
            story.append(Spacer(1, 0.1 * cm))
            continue

        if line.startswith("# "):
            story.append(Paragraph(inline_format(line[2:].strip()), styles["title"]))
            continue
        if line.startswith("## "):
            story.append(Paragraph(inline_format(line[3:].strip()), styles["h1"]))
            continue
        if line.startswith("### "):
            story.append(Paragraph(inline_format(line[4:].strip()), styles["h2"]))
            continue
        if line.startswith("#### "):
            story.append(Paragraph(inline_format(line[5:].strip()), styles["h3"]))
            continue

        if line.lstrip().startswith("- [x] "):
            story.append(Paragraph("&#9745; " + inline_format(line.split("]", 1)[1].strip()), styles["bullet"]))
            continue
        if line.lstrip().startswith("- [ ] "):
            story.append(Paragraph("&#9744; " + inline_format(line.split("]", 1)[1].strip()), styles["bullet"]))
            continue
        if line.lstrip().startswith("- "):
            story.append(Paragraph("&#8226; " + inline_format(line.lstrip()[2:].strip()), styles["bullet"]))
            continue
        if re.match(r"^\d+\.\s", line.lstrip()):
            num, rest = line.lstrip().split(".", 1)
            story.append(Paragraph(f"{num}. {inline_format(rest.strip())}", styles["bullet"]))
            continue

        if line.startswith("|") and line.endswith("|"):
            # table row -> plain text
            cells = [c.strip() for c in line.strip("|").split("|")]
            story.append(Paragraph(inline_format(" — ".join(cells)), styles["body"]))
            continue

        story.append(Paragraph(inline_format(line), styles["body"]))

    return story


def main() -> None:
    register_fonts()
    styles = build_styles()
    md_text = MD_PATH.read_text(encoding="utf-8")

    doc = SimpleDocTemplate(
        str(OUT_PATH),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="ELIMU One / ELIMU Go — Passation agent IA",
        author="CS-Elimu Project",
    )

    story = md_to_story(md_text, styles)
    doc.build(story)
    print(f"PDF genere : {OUT_PATH}")
    print(f"Source MD   : {MD_PATH}")


if __name__ == "__main__":
    main()
