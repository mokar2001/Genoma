"""
PDF Report Generator — uses ReportLab.
Phase 2: upgrade to a branded clinical-grade template.
"""

from io import BytesIO
from datetime import datetime
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from app.models.pipeline import PipelineResult


BRAND_COLOR = colors.HexColor("#4F46E5")   # indigo-600
ACCENT_COLOR = colors.HexColor("#7C3AED")  # violet-600
DANGER_COLOR = colors.HexColor("#DC2626")
WARN_COLOR = colors.HexColor("#D97706")
OK_COLOR = colors.HexColor("#059669")


def generate_pdf_report(result: PipelineResult) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title", parent=styles["Title"],
        textColor=BRAND_COLOR, fontSize=20, spaceAfter=6,
    )
    h2_style = ParagraphStyle(
        "H2", parent=styles["Heading2"],
        textColor=BRAND_COLOR, fontSize=14, spaceBefore=16, spaceAfter=6,
    )
    h3_style = ParagraphStyle(
        "H3", parent=styles["Heading3"],
        fontSize=11, spaceBefore=10, spaceAfter=4,
    )
    body = styles["BodyText"]
    small = ParagraphStyle("Small", parent=body, fontSize=8, textColor=colors.grey)

    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(Paragraph("RareDx AI — Diagnostic Report", title_style))
    story.append(Paragraph(f"Patient: <b>{result.patient_name}</b>", body))
    story.append(Paragraph(f"Session ID: {result.session_id}", small))
    story.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", small))
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND_COLOR, spaceAfter=12))

    # ── Executive Summary ─────────────────────────────────────────────────────
    story.append(Paragraph("Executive Summary", h2_style))
    story.append(Paragraph(result.summary, body))
    story.append(Paragraph(f"<b>Estimated time-to-diagnosis without AI:</b> {result.time_to_diagnosis_estimate}", body))
    story.append(Spacer(1, 0.4 * cm))

    # ── DeepRare Results ──────────────────────────────────────────────────────
    story.append(Paragraph("1. DeepRare — Disease Ranking", h2_style))
    story.append(Paragraph(
        f"Analyzed <b>{result.deeprare.total_variants_analyzed}</b> variants and "
        f"<b>{result.deeprare.phenotype_terms_matched}</b> phenotype terms.",
        body,
    ))

    for c in result.deeprare.candidates[:3]:
        story.append(Paragraph(f"#{c.rank} — {c.disease_name}", h3_style))
        data = [
            ["ORPHA", c.orpha_code, "OMIM", c.omim_id or "—"],
            ["Score", f"{c.score:.1%}", "Inheritance", c.inheritance_pattern],
            ["Prevalence", c.prevalence, "Genes", ", ".join(c.supporting_genes)],
        ]
        t = Table(data, colWidths=[3 * cm, 5 * cm, 3 * cm, 5 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F5F3FF")),
            ("TEXTCOLOR", (0, 0), (0, -1), BRAND_COLOR),
            ("TEXTCOLOR", (2, 0), (2, -1), BRAND_COLOR),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#F5F3FF")]),
        ]))
        story.append(t)
        story.append(Paragraph(c.reasoning, small))
        story.append(Spacer(1, 0.2 * cm))

    # ── ACMG Results ─────────────────────────────────────────────────────────
    story.append(Paragraph("2. ACMG Variant Classification", h2_style))
    summary_data = [
        ["Pathogenic", "Likely Pathogenic", "VUS", "Benign"],
        [
            str(result.acmg.pathogenic_count),
            str(result.acmg.likely_pathogenic_count),
            str(result.acmg.vus_count),
            str(result.acmg.benign_count),
        ],
    ]
    t2 = Table(summary_data, colWidths=[4 * cm, 4 * cm, 4 * cm, 4 * cm])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_COLOR),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    story.append(t2)
    story.append(Spacer(1, 0.3 * cm))

    for v in result.acmg.variants:
        cls_color = DANGER_COLOR if "Pathogenic" in v.classification else (WARN_COLOR if "Uncertain" in v.classification else OK_COLOR)
        story.append(Paragraph(
            f"<b>{v.gene}</b> {v.cdna_change} ({v.protein_change}) — "
            f'<font color="#{cls_color.hexval()[2:]}">{v.classification}</font>',
            body,
        ))
        story.append(Paragraph(v.recommendation, small))

    # ── AlphaFold Results ─────────────────────────────────────────────────────
    story.append(Paragraph("3. AlphaFold3 — Structural Impact", h2_style))
    for af in result.alphafold:
        story.append(Paragraph(f"{af.gene} — {af.variant}", h3_style))
        story.append(Paragraph(af.functional_summary, body))
        story.append(Paragraph(
            f"RMSD WT→Mutant: <b>{af.rmsd}Å</b> | "
            f"plDDT WT: <b>{af.wild_type_structure.plddt_score}</b> | "
            f"plDDT Mutant: <b>{af.mutant_structure.plddt_score}</b>",
            body,
        ))
        if af.pathogenicity_upgrade:
            story.append(Paragraph(
                f"⚠ Pathogenicity upgraded: {af.upgraded_from} → {af.upgraded_to}",
                ParagraphStyle("Warn", parent=body, textColor=WARN_COLOR),
            ))
        for impact in af.structural_impacts:
            story.append(Paragraph(f"• <b>{impact.impact_type}</b> [{impact.severity}]: {impact.description}", small))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 1 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    story.append(Paragraph(
        "DISCLAIMER: This report is generated by an AI-assisted research pipeline. "
        "It does not constitute a clinical diagnosis. All findings must be reviewed "
        "and validated by a qualified medical geneticist before clinical use.",
        ParagraphStyle("Disclaimer", parent=body, fontSize=7, textColor=colors.grey),
    ))

    doc.build(story)
    return buffer.getvalue()
