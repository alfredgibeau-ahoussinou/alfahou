"""Compose un PDF soigné (texte LLM + couverture image optionnelle)."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image as RLImage
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

from alfahou.core.config import settings


class PDFEngine:
    def generate(
        self,
        title: str,
        body: str,
        image_path: Path | None = None,
        author: str = "AlfAhou — Alfred Ahoussinou",
    ) -> Path:
        out = settings.outputs_dir / f"pdf_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        doc = SimpleDocTemplate(
            str(out),
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=1.8 * cm,
            bottomMargin=2 * cm,
            title=title,
            author=author,
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "AlfTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=28,
            alignment=TA_CENTER,
            spaceAfter=8,
            textColor="#1a1c1e",
        )
        meta_style = ParagraphStyle(
            "AlfMeta",
            parent=styles["Normal"],
            fontSize=10,
            alignment=TA_CENTER,
            textColor="#6e6a63",
            spaceAfter=16,
        )
        h2_style = ParagraphStyle(
            "AlfH2",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=18,
            textColor="#2a2e32",
            spaceBefore=10,
            spaceAfter=6,
            alignment=TA_LEFT,
        )
        body_style = ParagraphStyle(
            "AlfBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=11,
            leading=16,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
            textColor="#222",
        )
        bullet_style = ParagraphStyle(
            "AlfBullet",
            parent=body_style,
            leftIndent=14,
            bulletIndent=0,
            spaceAfter=4,
        )

        story = [
            Paragraph(_esc(title), title_style),
            Paragraph(_esc(author), meta_style),
            HRFlowable(width="100%", thickness=0.6, color="#d4b896", spaceAfter=14),
        ]
        if image_path and image_path.exists():
            try:
                img = RLImage(str(image_path), width=14 * cm, height=9 * cm, kind="proportional")
                story.append(img)
                story.append(Spacer(1, 0.7 * cm))
            except Exception:
                pass

        for block in _split_blocks(body):
            if block["type"] == "h":
                story.append(Paragraph(_esc(block["text"]), h2_style))
            elif block["type"] == "li":
                story.append(Paragraph(f"• {_esc(block['text'])}", bullet_style))
            elif block["type"] == "p":
                story.append(Paragraph(_esc(block["text"]), body_style))
            else:
                story.append(Spacer(1, 0.25 * cm))

        doc.build(story)
        return out


def _esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )


def _split_blocks(body: str) -> list[dict]:
    blocks: list[dict] = []
    for raw in body.split("\n"):
        line = raw.strip()
        if not line:
            blocks.append({"type": "sp", "text": ""})
            continue
        if line.startswith("## "):
            blocks.append({"type": "h", "text": line[3:].strip()})
        elif line.startswith("# "):
            blocks.append({"type": "h", "text": line[2:].strip()})
        elif re.match(r"^[-*•]\s+", line):
            blocks.append({"type": "li", "text": re.sub(r"^[-*•]\s+", "", line)})
        elif re.match(r"^\d+\.\s+", line):
            blocks.append({"type": "li", "text": re.sub(r"^\d+\.\s+", "", line)})
        else:
            # markdown bold léger
            text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", line)
            blocks.append({"type": "p", "text": text})
    return blocks
