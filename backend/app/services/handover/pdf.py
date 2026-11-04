"""ReportLab PDF renderer for handover documents.

Brand colors: navy #101827, blue #4169E1, teal #20BFA9.
Markdown-lite parsing: "## " → sub-heading, "- " → bullet, **bold** inline,
blank line → paragraph break. Verification badges rendered as colored text.
Page numbers in the footer.
"""
from __future__ import annotations

import io
import re

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate,
                                Paragraph, Spacer)

NAVY = colors.HexColor("#101827")
BLUE = colors.HexColor("#4169E1")
TEAL = colors.HexColor("#20BFA9")

BADGE_COLORS = {
    "verified": TEAL,
    "supported": TEAL,
    "approved": TEAL,
    "inferred": BLUE,
    "unresolved": colors.HexColor("#D97706"),
    "unverified": colors.HexColor("#D97706"),
    "conflicting": colors.HexColor("#DC2626"),
    "pending": colors.HexColor("#6B7280"),
    "rejected": colors.HexColor("#DC2626"),
}


def _escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _inline(s: str) -> str:
    """Escape and convert **bold** to <b>."""
    s = _escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return s


def _badge(s: str) -> str:
    """Convert [STATUS] tokens to colored <b>[STATUS]</b> text."""
    def repl(m):
        word = m.group(1).lower()
        color = BADGE_COLORS.get(word, NAVY)
        return (f'<font color="#{color.hexval()[2:]}"><b>[{m.group(1).upper()}]</b></font>')
    return re.sub(r"\[(Verified|Inferred|Unresolved|Unverified|Conflicting|"
                  r"Supported|Approved|Pending|Rejected|Open|Mitigated|Closed|HIGH|MEDIUM|LOW|CRITICAL)\]",
                  repl, s, flags=re.IGNORECASE)


def _parse_content(content: str, styles: dict) -> list:
    """Parse markdown-lite content into flowables."""
    flowables: list = []
    paragraphs: list[str] = []

    def flush_para():
        if paragraphs:
            text = " ".join(paragraphs)
            flowables.append(Paragraph(_badge(_inline(text)), styles["body"]))
            paragraphs.clear()

    for raw_line in (content or "").splitlines():
        line = raw_line.rstrip()
        if line.startswith("## "):
            flush_para()
            flowables.append(Paragraph(_badge(_inline(line[3:])), styles["subhead"]))
        elif line.startswith("- "):
            flush_para()
            flowables.append(Paragraph(f"&#8226;&nbsp;&nbsp;{_badge(_inline(line[2:]))}",
                                       styles["bullet"]))
        elif not line.strip():
            flush_para()
            flowables.append(Spacer(1, 3 * mm))
        else:
            paragraphs.append(line.strip())
    flush_para()
    if not flowables:
        flowables.append(Paragraph(_inline(content or ""), styles["body"]))
    return flowables


def _make_styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("ca_title", parent=base["Title"], fontName="Helvetica-Bold",
                                fontSize=26, leading=32, textColor=NAVY, spaceAfter=6),
        "subtitle": ParagraphStyle("ca_subtitle", parent=base["Normal"], fontName="Helvetica",
                                   fontSize=12, leading=16, textColor=BLUE),
        "meta": ParagraphStyle("ca_meta", parent=base["Normal"], fontName="Helvetica",
                               fontSize=10, leading=14, textColor=NAVY),
        "section": ParagraphStyle("ca_section", parent=base["Heading1"], fontName="Helvetica-Bold",
                                  fontSize=14, leading=18, textColor=NAVY,
                                  spaceBefore=8, spaceAfter=4),
        "subhead": ParagraphStyle("ca_subhead", parent=base["Heading2"], fontName="Helvetica-Bold",
                                  fontSize=11, leading=14, textColor=BLUE,
                                  spaceBefore=6, spaceAfter=2),
        "body": ParagraphStyle("ca_body", parent=base["Normal"], fontName="Helvetica",
                               fontSize=9.5, leading=13, textColor=NAVY,
                               spaceAfter=4),
        "bullet": ParagraphStyle("ca_bullet", parent=base["Normal"], fontName="Helvetica",
                                 fontSize=9.5, leading=13, textColor=NAVY,
                                 leftIndent=12, spaceAfter=2),
        "footer": ParagraphStyle("ca_footer", parent=base["Normal"], fontName="Helvetica",
                                 fontSize=8, leading=10, textColor=colors.HexColor("#6B7280")),
    }


class _PageNumberCanvasMixin:
    """Draw footer page numbers + brand rule on every page."""

    def _end_page(self):
        canvas = self.canv
        page_no = canvas.getPageNumber()
        canvas.saveState()
        canvas.setStrokeColor(TEAL)
        canvas.setLineWidth(1.2)
        canvas.line(20 * mm, 16 * mm, A4[0] - 20 * mm, 16 * mm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#6B7280"))
        canvas.drawString(20 * mm, 11 * mm, "CONTINUITY AI - Project Knowledge Handover")
        canvas.drawRightString(A4[0] - 20 * mm, 11 * mm, f"Page {page_no}")
        canvas.restoreState()


def render_pdf(handover: dict, project_name: str) -> bytes:
    """Render a handover (dict with sections/audience/version/generated_at)
    to PDF bytes."""
    styles = _make_styles()
    buf = io.BytesIO()

    class Doc(BaseDocTemplate, _PageNumberCanvasMixin):
        def handle_pageEnd(self):
            self._end_page()
            super().handle_pageEnd()

    doc = Doc(buf, pagesize=A4,
              leftMargin=20 * mm, rightMargin=20 * mm,
              topMargin=18 * mm, bottomMargin=20 * mm,
              title=f"CONTINUITY AI Handover — {project_name}")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame])])

    story: list = []
    # Title page block
    story.append(Paragraph("CONTINUITY AI", styles["subtitle"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(_escape(project_name), styles["title"]))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(
        f"<b>Generated:</b> {handover.get('generated_at', '')}", styles["meta"]))
    story.append(Paragraph(
        f"<b>Version:</b> {handover.get('version', 1)}", styles["meta"]))
    story.append(Paragraph(
        f"<b>Audience:</b> {handover.get('audience', 'general')}", styles["meta"]))
    story.append(Paragraph(
        f"<b>Status:</b> {handover.get('status', 'generated')}", styles["meta"]))
    story.append(Spacer(1, 10 * mm))

    for section in handover.get("sections", []):
        story.append(Paragraph(_escape(section.get("title", "")), styles["section"]))
        story.extend(_parse_content(section.get("content", ""), styles))
        story.append(Spacer(1, 5 * mm))

    doc.build(story)
    return buf.getvalue()