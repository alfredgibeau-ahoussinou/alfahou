from __future__ import annotations

from datetime import datetime
from pathlib import Path

from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from alfahou.core.config import settings


class PDFEngine:
    """Compose un PDF à partir du texte (et optionnellement d'une image) générés par AlfAhou."""

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
            topMargin=2 * cm,
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
            spaceAfter=12,
            textColor="#0E2A24",
        )
        meta_style = ParagraphStyle(
            "AlfMeta",
            parent=styles["Normal"],
            fontSize=10,
            alignment=TA_CENTER,
            textColor="#4A635C",
            spaceAfter=24,
        )
        body_style = ParagraphStyle(
            "AlfBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=11,
            leading=16,
            alignment=TA_JUSTIFY,
            spaceAfter=10,
        )

        story = [
            Paragraph(title.replace("\n", "<br/>"), title_style),
            Paragraph(author, meta_style),
        ]
        if image_path and image_path.exists():
            img = RLImage(str(image_path), width=12 * cm, height=12 * cm)
            story.append(img)
            story.append(Spacer(1, 0.6 * cm))

        for para in body.split("\n"):
            p = para.strip()
            if not p:
                story.append(Spacer(1, 0.3 * cm))
                continue
            story.append(Paragraph(p.replace("&", "&amp;").replace("<", "&lt;"), body_style))

        doc.build(story)
        return out
