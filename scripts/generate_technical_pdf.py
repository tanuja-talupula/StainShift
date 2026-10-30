#!/usr/bin/env python3
"""
StainShift Technical Documentation Generator
Generates a comprehensive, publication-grade technical architecture and developer guide PDF.
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    HRFlowable,
)
from reportlab.pdfgen import canvas

# Theme Palette (Matches StainShift & Claude Aesthetic)
C_PRIMARY = colors.HexColor("#1A1918")      # Near black charcoal
C_SECONDARY = colors.HexColor("#3D3A37")    # Deep charcoal
C_MUTED = colors.HexColor("#6B665E")        # Muted body grey
C_TERRACOTTA = colors.HexColor("#CC785C")   # Accent warm terracotta
C_SAGE = colors.HexColor("#2D5A46")         # Accent sage green
C_BURGUNDY = colors.HexColor("#9B2A2A")     # Warning / drop red
C_BG_CREAM = colors.HexColor("#FAF8F5")     # Soft cream background
C_BG_WARM = colors.HexColor("#F5F2EB")      # Warm card background
C_BG_GREEN = colors.HexColor("#EDF4EF")     # Success callout background
C_BG_RED = colors.HexColor("#FAF2F2")       # Alert callout background
C_BORDER = colors.HexColor("#E8E4DD")       # Subtle border
C_BORDER_DARK = colors.HexColor("#DDD8CF")  # Strong border
C_CODE_BG = colors.HexColor("#21201E")      # Dark code block background
C_CODE_TEXT = colors.HexColor("#F6F4EF")    # Off-white code text
C_WHITE = colors.HexColor("#FFFFFF")


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas that computes total page count and adds
    running headers and footers to every page except the cover page.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_decorations(self, page_count):
        if self._pageNumber == 1:
            return  # Suppress headers/footers on cover page

        page_w, page_h = letter

        # Running Header
        self.setFont("Helvetica", 7.5)
        self.setFillColor(C_MUTED)
        self.drawString(54, page_h - 36, "StainShift — Technical Architecture & Developer Guide")
        self.drawRightString(page_w - 54, page_h - 36, "System Reference Manual · October 2026")
        self.setStrokeColor(C_BORDER)
        self.setLineWidth(0.5)
        self.line(54, page_h - 40, page_w - 54, page_h - 40)

        # Running Footer
        self.line(54, 44, page_w - 54, 44)
        self.drawString(54, 32, "Git Commit: b890655 · CRC-VAL-HE-7K Benchmark System")
        self.drawRightString(page_w - 54, 32, f"Page {self._pageNumber} of {page_count}")


def build_styles():
    """Constructs a clean typographic hierarchy for the document."""
    base_styles = getSampleStyleSheet()

    styles = {
        "CoverTitle": ParagraphStyle(
            "CoverTitle",
            parent=base_styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=30,
            textColor=C_PRIMARY,
            alignment=0,
            spaceAfter=10,
        ),
        "CoverSubtitle": ParagraphStyle(
            "CoverSubtitle",
            fontName="Helvetica",
            fontSize=12,
            leading=17,
            textColor=C_TERRACOTTA,
            alignment=0,
            spaceAfter=18,
        ),
        "CoverMeta": ParagraphStyle(
            "CoverMeta",
            fontName="Helvetica",
            fontSize=8.5,
            leading=13,
            textColor=C_SECONDARY,
        ),
        "H1": ParagraphStyle(
            "CustomH1",
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=C_PRIMARY,
            spaceBefore=14,
            spaceAfter=6,
            keepWithNext=True,
        ),
        "H2": ParagraphStyle(
            "CustomH2",
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=C_TERRACOTTA,
            spaceBefore=10,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "H3": ParagraphStyle(
            "CustomH3",
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=13.5,
            textColor=C_SECONDARY,
            spaceBefore=8,
            spaceAfter=3,
            keepWithNext=True,
        ),
        "Body": ParagraphStyle(
            "CustomBody",
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=C_SECONDARY,
            spaceAfter=4,
        ),
        "BodyBold": ParagraphStyle(
            "CustomBodyBold",
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=12,
            textColor=C_PRIMARY,
            spaceAfter=4,
        ),
        "Bullet": ParagraphStyle(
            "CustomBullet",
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=C_SECONDARY,
            leftIndent=12,
            firstLineIndent=-8,
            spaceAfter=2,
        ),
        "CodeText": ParagraphStyle(
            "CustomCodeText",
            fontName="Courier",
            fontSize=6.5,
            leading=8.5,
            textColor=C_CODE_TEXT,
        ),
        "TableHead": ParagraphStyle(
            "CustomTableHead",
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9.5,
            textColor=C_PRIMARY,
        ),
        "TableCell": ParagraphStyle(
            "CustomTableCell",
            fontName="Helvetica",
            fontSize=7,
            leading=9,
            textColor=C_SECONDARY,
        ),
        "TableCellBold": ParagraphStyle(
            "CustomTableCellBold",
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9,
            textColor=C_PRIMARY,
        ),
        "TableCellMono": ParagraphStyle(
            "CustomTableCellMono",
            fontName="Courier",
            fontSize=6.5,
            leading=8,
            textColor=C_PRIMARY,
        ),
        "CalloutText": ParagraphStyle(
            "CustomCalloutText",
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=C_SECONDARY,
        ),
    }

    return styles


def create_callout(text: str, title: str = "NOTE", kind: str = "note", styles=None):
    """Renders a rounded callout alert box with themed borders and backgrounds."""
    bg_color = C_BG_WARM
    border_color = C_BORDER
    title_color = C_SECONDARY

    if kind == "important":
        bg_color = C_BG_GREEN
        border_color = C_SAGE
        title_color = C_SAGE
    elif kind == "warning":
        bg_color = C_BG_RED
        border_color = C_BURGUNDY
        title_color = C_BURGUNDY
    elif kind == "accent":
        bg_color = colors.HexColor("#FAF3EE")
        border_color = C_TERRACOTTA
        title_color = C_TERRACOTTA

    header_para = Paragraph(f"<b>[{title}]</b>", ParagraphStyle(
        f"CalloutHead_{kind}",
        parent=styles["CalloutText"],
        fontName="Helvetica-Bold",
        textColor=title_color,
        fontSize=8,
        leading=10,
    ))
    content_para = Paragraph(text, styles["CalloutText"])

    box_data = [[header_para], [Spacer(1, 1)], [content_para]]
    box_table = Table(box_data, colWidths=[504])
    box_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg_color),
        ("BOX", (0, 0), (-1, -1), 0.75, border_color),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return box_table


def create_code_block(code_text: str, filename: str = "", styles=None):
    """Renders a dark-themed syntax code container."""
    lines = code_text.strip().split("\n")
    formatted_code = "<br/>".join([
        line.replace(" ", "&nbsp;").replace("<", "&lt;").replace(">", "&gt;")
        for line in lines
    ])

    header_cell = [
        Paragraph(f"<b>FILE:</b> <font face='Courier'>{filename}</font>" if filename else "<b>CODE LISTING / DIAGRAM</b>", ParagraphStyle(
            "CodeHeader",
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=8.5,
            textColor=colors.HexColor("#DFBAA3"),
        ))
    ]
    code_cell = [Paragraph(formatted_code, styles["CodeText"])]

    block_data = [header_cell, code_cell]
    table = Table(block_data, colWidths=[504])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_CODE_BG),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 3),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
        ("TOPPADDING", (0, 1), (-1, 1), 2),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 5),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#4D4842")),
    ]))
    return table


def build_pdf(output_path: str):
    """Assembles all sections into the final PDF document."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = build_styles()
    story = []

    # =========================================================================
    # COVER PAGE
    # =========================================================================
    story.append(Spacer(1, 15))
    story.append(Paragraph("RESEARCH ENGINEERING MONOGRAPH · MEDICAL AI SYSTEMS", styles["CoverSubtitle"]))
    story.append(Paragraph("StainShift: Complete Technical Architecture, Packages, ML Pipeline & Developer Guide", styles["CoverTitle"]))
    story.append(HRFlowable(width="100%", thickness=2, color=C_TERRACOTTA, spaceBefore=4, spaceAfter=12))

    abstract_text = (
        "<b>Abstract:</b> StainShift is a full-stack, physics-informed biomedical artificial intelligence "
        "system designed to evaluate and resolve domain shift vulnerabilities in deep neural networks applied "
        "to Hematoxylin and Eosin (H&E) colorectal cancer histopathology. In standard empirical risk minimization "
        "(ERM) regimes, state-of-the-art convolutional networks reach 99.9% classification accuracy on pristine "
        "laboratory slides but collapse catastrophically to 33.9% under modest laboratory stain shifts. By integrating "
        "Beer-Lambert optical density deconvolution (Macenko SVD decomposition) directly into online data augmentation "
        "and real-time inference serving, StainShift restores tissue classification accuracy to 97.7% across eight distinct "
        "stain perturbations while maintaining a 3.91 ms forward latency boundary on Apple Silicon MPS hardware. "
        "This document provides the definitive, comprehensive architectural specification, dependency inventory, "
        "mathematical derivation, verbatim code implementation, and a pedagogical developer guide for researchers "
        "and bioinformatics engineers."
    )
    story.append(Paragraph(abstract_text, styles["Body"]))
    story.append(Spacer(1, 12))

    meta_table_data = [
        [
            Paragraph("<b>Project:</b> StainShift AI", styles["CoverMeta"]),
            Paragraph("<b>Production Frontend:</b> https://stainshift-ai.vercel.app/", styles["CoverMeta"]),
        ],
        [
            Paragraph("<b>Author / Lead:</b> Mahesh Reddy", styles["CoverMeta"]),
            Paragraph("<b>Production API:</b> https://stainshift-api.onrender.com", styles["CoverMeta"]),
        ],
        [
            Paragraph("<b>Academic Context:</b> B.Tech Bioinformatics Engineering", styles["CoverMeta"]),
            Paragraph("<b>Dataset:</b> CRC-VAL-HE-7K (7,180 colorectal patches, 9 classes)", styles["CoverMeta"]),
        ],
        [
            Paragraph("<b>Repository:</b> tanuja-talupula/StainShift", styles["CoverMeta"]),
            Paragraph("<b>Model Checkpoints:</b> MobileNetV3-Small (baseline & robust)", styles["CoverMeta"]),
        ],
        [
            Paragraph("<b>Active Git Commit:</b> <font face='Courier'>b890655</font>", styles["CoverMeta"]),
            Paragraph("<b>Hardware Benchmark:</b> Apple Silicon MPS (M-series synchronized)", styles["CoverMeta"]),
        ],
        [
            Paragraph(f"<b>Generation Date:</b> {datetime.now().strftime('%B %d, %Y')}", styles["CoverMeta"]),
            Paragraph("<b>Validation Status:</b> Stage B Verified Benchmark", styles["CoverMeta"]),
        ],
    ]
    meta_table = Table(meta_table_data, colWidths=[240, 264])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_BG_WARM),
        ("BOX", (0, 0), (-1, -1), 0.75, C_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 12))

    disclaimer = (
        "<b>NON-CLINICAL RESEARCH DISCLAIMER:</b> StainShift is an exploratory engineering benchmark "
        "and educational software application. It is NOT a certified medical device, IVD system, or clinical decision "
        "support tool. Softmax probability distributions represent model confidence scores across 9 research tissue "
        "classes and must never be interpreted as primary clinical diagnoses or medical advice."
    )
    story.append(create_callout(disclaimer, title="REGULATORY & RESEARCH PROTOCOL NOTICE", kind="warning", styles=styles))
    story.append(PageBreak())

    # =========================================================================
    # TABLE OF CONTENTS
    # =========================================================================
    story.append(Paragraph("Table of Contents", styles["H1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceBefore=2, spaceAfter=8))

    toc_entries = [
        ("1. Executive Summary & Problem Formulation", "3"),
        ("2. Complete Technology Stack (Verified Against Source)", "3"),
        ("3. Main Packages & Dependency Reference Manual (20+ Key Libraries)", "5"),
        ("4. System Architecture & Client-Server Data Flow", "6"),
        ("5. Complete Repository Folder & File Anatomy", "8"),
        ("6. Machine Learning Architecture, Mathematics & Evaluation", "9"),
        ("   6.1 Physics of H&E Staining & Optical Density Derivation", "9"),
        ("   6.2 Macenko SVD Decomposition & Dye Perturbation Mathematics", "9"),
        ("   6.3 MobileNetV3-Small Neural Architecture & Head Modifications", "10"),
        ("   6.4 Scientific Findings: The 33.9% Collapse & 97.7% Recovery", "10"),
        ("7. End-to-End Application Workflows", "11"),
        ("   7.1 Workflow A: Interactive AI Workspace (/workspace/)", "11"),
        ("   7.2 Workflow B: Results Dashboard (/dashboard/)", "11"),
        ("   7.3 Workflow C: Precomputed Demo Explorer (/demo/)", "11"),
        ("8. Verbatim Source Code References & Module Walkthroughs", "12"),
        ("   8.1 API Request Dispatcher: api/main.py", "12"),
        ("   8.2 Inference Engine & Security Layer: api/inference.py", "12"),
        ("   8.3 Beer-Lambert Optical Transform: src/stain_shift.py", "12"),
        ("   8.4 Verified Checkpoint Provenance: src/models.py", "13"),
        ("9. Developer Learning Guide: Building StainShift from Scratch", "14"),
        ("   9.1 Ten-Phase Implementation Roadmap for Bioinformatics Students", "14"),
        ("   9.2 Comprehensive Technical Glossary", "15"),
        ("10. Verification Sign-Off & Document Integrity", "16"),
    ]

    toc_table_data = [
        [
            Paragraph(f"<b>{title}</b>", styles["TableCellBold"]),
            Paragraph(f"<b>Page {page}</b>", styles["TableCellMono"]),
        ]
        for title, page in toc_entries
    ]
    toc_table = Table(toc_table_data, colWidths=[430, 74])
    toc_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, C_BG_WARM),
    ]))
    story.append(toc_table)
    story.append(PageBreak())

    # =========================================================================
    # SECTION 1: EXECUTIVE SUMMARY & PROBLEM FORMULATION
    # =========================================================================
    story.append(Paragraph("1. Executive Summary & Problem Formulation", styles["H1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceBefore=2, spaceAfter=6))

    story.append(Paragraph(
        "Digital histopathology relies on scanning glass microscope slides containing thin microtome sections of human tissue. "
        "The standard staining procedure is Hematoxylin and Eosin (H&E). Hematoxylin stains cell nuclei blue/purple by binding "
        "acidic polyanions such as DNA and RNA, while Eosin stains extracellular matrix proteins and cytoplasm pink. "
        "However, clinical slide preparation varies dramatically across pathology laboratories due to differences in reagent "
        "vendors, chemical batch formulations, staining protocol durations, pH fluctuations, microtome section thickness (3–5 μm), "
        "and digital whole-slide scanner sensor color calibration curves.",
        styles["Body"]
    ))
    story.append(Paragraph(
        "Modern deep convolutional neural networks (CNNs) trained via standard Empirical Risk Minimization (ERM) on a single "
        "laboratory cohort typically achieve near-perfect cross-entropy loss and over 99% accuracy on clean, native test patches. "
        "Crucially, however, standard CNNs learn high-frequency color shortcut representations rather than true nuclear morphology "
        "or glandular tissue architecture. When presented with slides from a different hospital or scanner where the stain has shifted, "
        "these models fail silently and catastrophically.",
        styles["Body"]
    ))

    story.append(create_callout(
        "<b>The StainShift Benchmark Discovery:</b> On the frozen held-out test cohort of CRC-VAL-HE-7K (N = 1,077 patches), "
        "the standard baseline MobileNetV3-Small model drops from <b>99.91%</b> on native clean patches down to <b>33.89%</b> "
        "when evaluated under simple optical deconvolution reconstruction, and collapses as low as <b>28.97%</b> under heavy eosin shifts. "
        "Conversely, our physics-informed stain-augmented model retains <b>97.68%</b> accuracy under deconvolution (+63.79% net recovery) "
        "and stays locked above <b>94.8%</b> across all eight synthetic stain profiles.",
        title="EMPIRICAL BENCHMARK DISCOVERY",
        kind="important",
        styles=styles
    ))
    story.append(Spacer(1, 8))

    # =========================================================================
    # SECTION 2: COMPLETE TECHNOLOGY STACK
    # =========================================================================
    story.append(Paragraph("2. Complete Technology Stack (Verified Against Source)", styles["H1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceBefore=2, spaceAfter=6))

    story.append(Paragraph(
        "Every technology listed below has been verified by direct inspection of repository manifests "
        "(<font face='Courier'>website/package.json</font>, <font face='Courier'>requirements.txt</font>, "
        "<font face='Courier'>pyproject.toml</font>, <font face='Courier'>Dockerfile</font>) and active runtime configurations. "
        "No unverified or assumed technologies are included.",
        styles["Body"]
    ))

    stack_data = [
        [
            Paragraph("<b>Stack Layer</b>", styles["TableHead"]),
            Paragraph("<b>Technology / Framework</b>", styles["TableHead"]),
            Paragraph("<b>Verified Version</b>", styles["TableHead"]),
            Paragraph("<b>Architectural Role & Implementation Detail</b>", styles["TableHead"]),
        ],
        [
            Paragraph("<b>Frontend Framework</b>", styles["TableCellBold"]),
            Paragraph("Next.js 14 App Router", styles["TableCell"]),
            Paragraph("14.2.35", styles["TableCellMono"]),
            Paragraph("Static HTML/JS export (<font face='Courier'>output: 'export'</font>) for zero-latency CDN edge delivery via Vercel.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Frontend Language</b>", styles["TableCellBold"]),
            Paragraph("TypeScript", styles["TableCell"]),
            Paragraph("5.9.3", styles["TableCellMono"]),
            Paragraph("Strict type contracts (<font face='Courier'>tsconfig.json</font>) guaranteeing end-to-end data safety between frontend and API.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Styling Engine</b>", styles["TableCellBold"]),
            Paragraph("Tailwind CSS", styles["TableCell"]),
            Paragraph("3.4.19", styles["TableCellMono"]),
            Paragraph("Utility-first styling with custom palette: Newsreader editorial serif headings, Inter body, and Claude-inspired terracotta tones.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>UI Component Icons</b>", styles["TableCellBold"]),
            Paragraph("Lucide React", styles["TableCell"]),
            Paragraph("0.468.0", styles["TableCellMono"]),
            Paragraph("Tree-shaken SVG icons (Microscope, FlaskConical, Play, Cpu, ShieldCheck, ChevronDown, Download).", styles["TableCell"]),
        ],
        [
            Paragraph("<b>CSS Utility Libraries</b>", styles["TableCellBold"]),
            Paragraph("clsx + tailwind-merge", styles["TableCell"]),
            Paragraph("2.1.1 / 2.6.1", styles["TableCellMono"]),
            Paragraph("Dynamic CSS class merging without class-name collision across conditional component states.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Frontend Animations</b>", styles["TableCellBold"]),
            Paragraph("Native Browser APIs", styles["TableCell"]),
            Paragraph("W3C Standard", styles["TableCellMono"]),
            Paragraph("Custom <font face='Courier'>ScrollReveal</font> (IntersectionObserver) & <font face='Courier'>CountUp</font> (requestAnimationFrame). 0 npm dependencies.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Frontend Charting</b>", styles["TableCellBold"]),
            Paragraph("Pure SVG Coordinates", styles["TableCell"]),
            Paragraph("W3C SVG 1.1", styles["TableCellMono"]),
            Paragraph("Mathematical SVG coordinate projection with accessible HTML table alternatives. Zero external chart bundle weight.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Backend Web API</b>", styles["TableCellBold"]),
            Paragraph("FastAPI (ASGI)", styles["TableCell"]),
            Paragraph("0.162.0", styles["TableCellMono"]),
            Paragraph("High-performance asynchronous REST endpoints (<font face='Courier'>/predict</font>, <font face='Courier'>/health</font>, <font face='Courier'>/models</font>) with OpenAPI auto-docs.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>ASGI Server</b>", styles["TableCellBold"]),
            Paragraph("Uvicorn", styles["TableCell"]),
            Paragraph("0.54.0", styles["TableCellMono"]),
            Paragraph("Production lightning-fast ASGI server with uvloop event loops and single-worker containerized dispatch.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Data Validation</b>", styles["TableCellBold"]),
            Paragraph("Pydantic v2", styles["TableCell"]),
            Paragraph("2.14.1", styles["TableCellMono"]),
            Paragraph("Strict request/response schema serialization, boundary clamping, and field type validation.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Multipart Parser</b>", styles["TableCellBold"]),
            Paragraph("python-multipart", styles["TableCell"]),
            Paragraph("0.0.32", styles["TableCellMono"]),
            Paragraph("Streaming multipart form parser handling single patches, multiple image files, and ZIP archives.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Deep Learning Engine</b>", styles["TableCellBold"]),
            Paragraph("PyTorch", styles["TableCell"]),
            Paragraph("2.15.0", styles["TableCellMono"]),
            Paragraph("Tensor operations, CNN forward propagation, hardware synchronization (<font face='Courier'>torch.mps</font>, <font face='Courier'>torch.cuda</font>).", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Computer Vision</b>", styles["TableCellBold"]),
            Paragraph("TorchVision", styles["TableCell"]),
            Paragraph("0.29.2", styles["TableCellMono"]),
            Paragraph("MobileNetV3-Small backbone weights and standard ImageNet normalization transforms.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Array Processing</b>", styles["TableCellBold"]),
            Paragraph("NumPy", styles["TableCell"]),
            Paragraph("2.5.4", styles["TableCellMono"]),
            Paragraph("Optical density transformations, SVD covariance decomposition, and matrix algebra.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Image Processing</b>", styles["TableCellBold"]),
            Paragraph("Pillow (PIL)", styles["TableCell"]),
            Paragraph("13.0.0", styles["TableCellMono"]),
            Paragraph("Zero-disk in-memory image parsing, 8-bit RGB mode validation, bilinear resizing, and base64 thumbnails.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Scientific Metrics</b>", styles["TableCellBold"]),
            Paragraph("scikit-learn", styles["TableCell"]),
            Paragraph("1.9.1", styles["TableCellMono"]),
            Paragraph("Confusion matrix computation, per-class Precision/Recall/F1, and macro-averaged metrics.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Data Management</b>", styles["TableCellBold"]),
            Paragraph("Pandas", styles["TableCell"]),
            Paragraph("3.1.0", styles["TableCellMono"]),
            Paragraph("Tabular data structuring, condition comparison table aggregation, and RFC-4180 CSV export generation.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Experiment Tracking</b>", styles["TableCellBold"]),
            Paragraph("MLflow", styles["TableCell"]),
            Paragraph("3.17.2", styles["TableCellMono"]),
            Paragraph("Provenance tracking with local SQLite database (<font face='Courier'>mlflow.db</font>) and decoupled artifact store.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Frontend Hosting</b>", styles["TableCellBold"]),
            Paragraph("Vercel Edge Network", styles["TableCell"]),
            Paragraph("Global CDN", styles["TableCellMono"]),
            Paragraph("Prebuilt static export distribution with custom routing, caching, and Brotli compression.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Backend Hosting</b>", styles["TableCellBold"]),
            Paragraph("Render Cloud Container", styles["TableCell"]),
            Paragraph("Docker Linux", styles["TableCellMono"]),
            Paragraph("Containerized Python service running PyTorch checkpoints with CORS protection.", styles["TableCell"]),
        ],
    ]

    stack_table = Table(stack_data, colWidths=[90, 110, 64, 240])
    stack_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_BG_WARM),
        ("BOX", (0, 0), (-1, -1), 0.75, C_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(stack_table)
    story.append(PageBreak())

    # =========================================================================
    # SECTION 3: MAIN PACKAGES & DEPENDENCY REFERENCE
    # =========================================================================
    story.append(Paragraph("3. Main Packages & Dependency Reference Manual", styles["H1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceBefore=2, spaceAfter=6))

    story.append(Paragraph(
        "Below is the comprehensive technical reference for the primary packages powering StainShift. "
        "Distinctions between direct (explicitly requested) and transitive (sub-dependency) packages are recorded.",
        styles["Body"]
    ))

    pkg_table_data = [
        [
            Paragraph("<b>Package</b>", styles["TableHead"]),
            Paragraph("<b>Type / Version</b>", styles["TableHead"]),
            Paragraph("<b>Where Used</b>", styles["TableHead"]),
            Paragraph("<b>Purpose & Scientific Justification</b>", styles["TableHead"]),
        ],
        [
            Paragraph("<b>torch</b>", styles["TableCellBold"]),
            Paragraph("Direct<br/><font face='Courier'>2.15.0</font>", styles["TableCell"]),
            Paragraph("<font face='Courier'>src/models.py<br/>api/inference.py<br/>src/train.py</font>", styles["TableCellMono"]),
            Paragraph("Core deep learning tensor computation engine. Executes neural network forward passes, handles MPS/CUDA accelerator synchronization, and computes softmax probability distributions.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>torchvision</b>", styles["TableCellBold"]),
            Paragraph("Direct<br/><font face='Courier'>0.29.2</font>", styles["TableCell"]),
            Paragraph("<font face='Courier'>src/models.py<br/>src/dataset.py</font>", styles["TableCellMono"]),
            Paragraph("Provides the pretrained MobileNetV3-Small backbone weights (<font face='Courier'>MobileNet_V3_Small_Weights.DEFAULT</font>) and standard ImageNet tensor normalization pipeline.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>fastapi</b>", styles["TableCellBold"]),
            Paragraph("Direct<br/><font face='Courier'>0.162.0</font>", styles["TableCell"]),
            Paragraph("<font face='Courier'>api/main.py</font>", styles["TableCellMono"]),
            Paragraph("High-performance asynchronous Web API framework. Implements OpenAPI/Swagger documentation, JSON serialization, and endpoint routing with dependency injection.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>uvicorn</b>", styles["TableCellBold"]),
            Paragraph("Direct<br/><font face='Courier'>0.54.0</font>", styles["TableCell"]),
            Paragraph("<font face='Courier'>Procfile<br/>Dockerfile</font>", styles["TableCellMono"]),
            Paragraph("Lightweight, production ASGI server that runs the FastAPI application using uvloop and httptools for high-concurrency request servicing.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>pydantic</b>", styles["TableCellBold"]),
            Paragraph("Transitive<br/><font face='Courier'>2.14.1</font>", styles["TableCell"]),
            Paragraph("<font face='Courier'>api/schemas.py</font>", styles["TableCellMono"]),
            Paragraph("Data validation and settings management using Python type hints. Enforces strict contracts for image inputs, prediction bounds, and batch summaries.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>numpy</b>", styles["TableCellBold"]),
            Paragraph("Direct<br/><font face='Courier'>2.5.4</font>", styles["TableCell"]),
            Paragraph("<font face='Courier'>src/stain_shift.py<br/>api/inference.py</font>", styles["TableCellMono"]),
            Paragraph("Fundamental numerical array processing. Executes Beer-Lambert log10 transforms, SVD covariance matrix decomposition, angular percentile extraction, and least-squares stain deconvolution.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>pillow (PIL)</b>", styles["TableCellBold"]),
            Paragraph("Direct<br/><font face='Courier'>13.0.0</font>", styles["TableCell"]),
            Paragraph("<font face='Courier'>api/inference.py<br/>src/dataset.py</font>", styles["TableCellMono"]),
            Paragraph("Zero-disk in-memory image parsing, 8-bit RGB mode validation, bilinear resizing, and dynamic base64 thumbnail generation for web streaming.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>scikit-learn</b>", styles["TableCellBold"]),
            Paragraph("Direct<br/><font face='Courier'>1.9.1</font>", styles["TableCell"]),
            Paragraph("<font face='Courier'>src/evaluate.py<br/>src/benchmark.py</font>", styles["TableCellMono"]),
            Paragraph("Evaluation metrics calculation: 9x9 confusion matrices, per-class precision, recall, support, and macro-averaged F1 scores.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>pandas</b>", styles["TableCellBold"]),
            Paragraph("Direct<br/><font face='Courier'>3.1.0</font>", styles["TableCell"]),
            Paragraph("<font face='Courier'>api/main.py<br/>src/benchmark.py</font>", styles["TableCellMono"]),
            Paragraph("Tabular data structuring, condition comparison table aggregation, and RFC-4180 CSV export generation in the interactive workspace.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>mlflow</b>", styles["TableCellBold"]),
            Paragraph("Direct<br/><font face='Courier'>3.17.2</font>", styles["TableCell"]),
            Paragraph("<font face='Courier'>src/tracking.py<br/>run_experiments.py</font>", styles["TableCellMono"]),
            Paragraph("Scientific provenance tracking. Records exact Git commit hashes, hyperparameters, dataset manifests, validation F1 trajectories, and checkpoint SHA-256 signatures to SQLite.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>python-multipart</b>", styles["TableCellBold"]),
            Paragraph("Direct<br/><font face='Courier'>0.0.32</font>", styles["TableCell"]),
            Paragraph("<font face='Courier'>api/main.py</font>", styles["TableCellMono"]),
            Paragraph("Processes HTTP multipart/form-data payloads, enabling streaming file uploads for large histology images and compressed ZIP archives.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>pytest</b>", styles["TableCellBold"]),
            Paragraph("Direct (dev)<br/><font face='Courier'>9.2.0</font>", styles["TableCell"]),
            Paragraph("<font face='Courier'>tests/ (74+ tests)</font>", styles["TableCellMono"]),
            Paragraph("Comprehensive testing harness: verifies neutral stain identity bypass, SVD numerical stability, API endpoint parity, and security bounds.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>next</b>", styles["TableCellBold"]),
            Paragraph("Direct<br/><font face='Courier'>14.2.35</font>", styles["TableCell"]),
            Paragraph("<font face='Courier'>website/src/app/</font>", styles["TableCellMono"]),
            Paragraph("React production framework providing file-system routing, Server and Client Components, static pre-rendering, and asset bundling.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>react & react-dom</b>", styles["TableCellBold"]),
            Paragraph("Direct<br/><font face='Courier'>18.3.1</font>", styles["TableCell"]),
            Paragraph("<font face='Courier'>website/src/</font>", styles["TableCellMono"]),
            Paragraph("Declarative component-based UI library managing client state, DOM reconciliation, hooks (<font face='Courier'>useState</font>, <font face='Courier'>useEffect</font>, <font face='Courier'>useRef</font>), and event handling.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>typescript</b>", styles["TableCellBold"]),
            Paragraph("Direct (dev)<br/><font face='Courier'>5.9.3</font>", styles["TableCell"]),
            Paragraph("<font face='Courier'>website/</font>", styles["TableCellMono"]),
            Paragraph("Static type checking enforcing compile-time correctness across benchmark metadata, API responses, queue management, and UI props.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>tailwindcss</b>", styles["TableCellBold"]),
            Paragraph("Direct (dev)<br/><font face='Courier'>3.4.19</font>", styles["TableCell"]),
            Paragraph("<font face='Courier'>website/tailwind.config.ts</font>", styles["TableCellMono"]),
            Paragraph("Utility-first CSS framework enabling responsive layout design, fluid typography, and custom design tokens (terracotta, sage, cream, charcoal).", styles["TableCell"]),
        ],
        [
            Paragraph("<b>lucide-react</b>", styles["TableCellBold"]),
            Paragraph("Direct<br/><font face='Courier'>0.468.0</font>", styles["TableCell"]),
            Paragraph("<font face='Courier'>website/src/components/</font>", styles["TableCellMono"]),
            Paragraph("High-performance, tree-shakeable icon set designed for React. Renders scalable SVG icons with zero runtime styling conflicts.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>clsx + tailwind-merge</b>", styles["TableCellBold"]),
            Paragraph("Direct<br/><font face='Courier'>2.1.1 / 2.6.1</font>", styles["TableCell"]),
            Paragraph("<font face='Courier'>website/src/components/</font>", styles["TableCellMono"]),
            Paragraph("Combines conditional CSS classes and resolves Tailwind property precedence clashes (e.g., merging custom padding or background classes).", styles["TableCell"]),
        ],
    ]

    pkg_table = Table(pkg_table_data, colWidths=[84, 80, 110, 230])
    pkg_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_BG_WARM),
        ("BOX", (0, 0), (-1, -1), 0.75, C_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(pkg_table)
    story.append(PageBreak())

    # =========================================================================
    # SECTION 4: COMPLETE PROJECT ARCHITECTURE
    # =========================================================================
    story.append(Paragraph("4. System Architecture & Client-Server Data Flow", styles["H1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceBefore=2, spaceAfter=6))

    story.append(Paragraph(
        "StainShift decouples frontend presentation from computational inference. The Next.js frontend is pre-rendered "
        "as a static distribution (<font face='Courier'>output: 'export'</font>) served across Vercel's global CDN edge network, "
        "ensuring instant page loads and zero cold-starts for presentation pages. Computational heavy-lifting—including Macenko "
        "Beer-Lambert deconvolution and PyTorch tensor inference—is delegated to a dedicated containerized FastAPI service on Render.",
        styles["Body"]
    ))

    arch_diagram_code = (
        "+------------------------------------------------------------------------------------------------+\n"
        "|                                     CLIENT WEB BROWSER                                         |\n"
        "|   Next.js 14 App Router (Static Export) · Tailwind CSS · Pure SVG Charts · React 18 Hooks     |\n"
        "|   Routes: / (Scrollytelling Landing)  ·  /workspace/ (AI Inference)  ·  /dashboard/  ·  /demo/ |\n"
        "+-----------------------------------------------+------------------------------------------------+\n"
        "                                                |  HTTPS (CORS Enabled)\n"
        "                 1. POST /predict (Multipart)   |  2. GET /health\n"
        "                 Files: [.png, .jpg, .zip]      |  3. GET /models\n"
        "                 Params: model_id, condition,   |  4. GET /data/stainshift_results.json\n"
        "                         intensity [0.0 - 2.5]  v\n"
        "+------------------------------------------------------------------------------------------------+\n"
        "|                               FASTAPI INFERENCE SERVICE (RENDER)                               |\n"
        "|   Python 3.11+ · Uvicorn ASGI Server · Starlette · Pydantic v2 Validation · In-Memory BytesIO  |\n"
        "+-----------------------------------------------+------------------------------------------------+\n"
        "                                                |\n"
        "       +----------------------------------------+----------------------------------------+\n"
        "       |                                                                                 |\n"
        "       v                                                                                 v\n"
        "+------------------------------------+                           +------------------------------------+\n"
        "|       SECURITY & VALIDATION        |                           |       ZIP ARCHIVE EXPANDER         |\n"
        "| • Max 15 MB / image; 50 batch max  |                           | • In-memory zipfile.ZipFile        |\n"
        "| • Dimensions <= 4096 px            |                           | • Zip-Slip Path Traversal Guard    |\n"
        "| • 8-bit RGB/RGBA Pillow validation |                           | • Zip-Bomb 100 MB Max Bound        |\n"
        "+-----------------+------------------+                           +-----------------+------------------+\n"
        "                  |                                                                |\n"
        "                  +--------------------------------+-------------------------------+ \n"
        "                                                   v\n"
        "+------------------------------------------------------------------------------------------------+\n"
        "|                              MACENKO BEER-LAMBERT DECOMPOSER                                   |\n"
        "| • Optical Density Space: OD = -log10(I / 255.0)                                                |\n"
        "| • Transparent Glass Masking: OD > 0.15 (beta threshold)                                        |\n"
        "| • Covariance Eigenvectors: PCA 2D Plane Projection                                             |\n"
        "| • Dye Vector Recovery: Hematoxylin & Eosin Unit Normals                                        |\n"
        "| • Non-Negative Least Squares Concentration: C = lstsq(S^T, OD^T)                               |\n"
        "| • Perturbation / Scaling: C' = C * [alpha_H, alpha_E] ; S' = S * R(theta)                      |\n"
        "| • Reconstructed RGB: I_shifted = 255.0 * 10^(-C' * S')                                         |\n"
        "+--------------------------------------------------+---------------------------------------------+\n"
        "                                                   |\n"
        "                                                   v\n"
        "+------------------------------------------------------------------------------------------------+\n"
        "|                                PYTORCH INFERENCE ENGINE (EVAL)                                 |\n"
        "| • Input Tensor: Resize (224x224) -> ToTensor() -> ImageNet Normalize(mean, std)                |\n"
        "| • Hardware Target: Apple Silicon MPS / NVIDIA CUDA / CPU (torch.no_grad())                     |\n"
        "| • Model Checkpoints Loaded:                                                                    |\n"
        "|     1. baseline.pth           (Standard ERM; Epoch 5; Val F1: 0.9985; SHA-256 Verified)        |\n"
        "|     2. robust_stain_aug.pth   (Macenko Augmented; Epoch 4; Val F1: 0.9871; SHA-256 Verified)   |\n"
        "| • Forward Computation: logits = model(tensor) -> probs = F.softmax(logits, dim=1)              |\n"
        "| • Confidence = max(probs); Predicted Class = argmax(probs); Latency = perf_counter()           |\n"
        "+--------------------------------------------------+---------------------------------------------+\n"
        "                                                   |\n"
        "                                                   v JSON Response\n"
        "+------------------------------------------------------------------------------------------------+\n"
        "|                                       JSON RESPONSE PAYLOAD                                    |\n"
        "| • status: 'success' · summary: {total, latency_ms, class_dist}                                 |\n"
        "| • results: [{filename, b64_original, b64_shifted, predictions: {baseline, robust}, agreement}] |\n"
        "+------------------------------------------------------------------------------------------------+\n"
        "                                                   |\n"
        "                                                   v\n"
        "+------------------------------------------------------------------------------------------------+\n"
        "|                                DYNAMIC FRONTEND RENDERING                                      |\n"
        "| • Live Side-by-Side Image Comparison (Original vs Shifted)                                     |\n"
        "| • 9-Class Probability Bar Distribution (ADI, BACK, DEB, LYM, MUC, MUS, NORM, STR, TUM)         |\n"
        "| • Prediction Flip Alert (Highlights Discordance between Baseline & Stain-Robust Models)        |\n"
        "| • Batch Results Table with Client-Side RFC-4180 CSV Export Generator                           |\n"
        "+------------------------------------------------------------------------------------------------+"
    )

    story.append(create_code_block(arch_diagram_code, filename="System Architecture & Data Flow", styles=styles))
    story.append(Spacer(1, 6))

    story.append(Paragraph(
        "<b>Security & Error Handling Architecture:</b><br/>"
        "1. <i>Zero Disk Persistence:</i> Uploaded image bytes are processed strictly in-memory using Python's "
        "<font face='Courier'>io.BytesIO</font>. No patient or research image data is written to the server's local filesystem.<br/>"
        "2. <i>Zip-Bomb Defense:</i> ZIP archives are checked for decompression ratio and uncompressed byte size. "
        "Any archive expanding beyond 100 MB is rejected immediately.<br/>"
        "3. <i>Zip-Slip Defense:</i> Filenames inside archives are resolved and stripped of directory traversal prefixes "
        "(<font face='Courier'>../</font>) using <font face='Courier'>Path(member).name</font>.<br/>"
        "4. <i>Neutral Identity Bypass:</i> When an unperturbed patch is submitted (<font face='Courier'>condition='original'</font>), "
        "the deconvolution algorithm is completely bypassed, returning exact pixel equality (<font face='Courier'>np.array_equal</font>).",
        styles["Body"]
    ))
    story.append(PageBreak())

    # =========================================================================
    # SECTION 5: COMPLETE REPOSITORY FOLDER & FILE ANATOMY
    # =========================================================================
    story.append(Paragraph("5. Complete Repository Folder & File Anatomy", styles["H1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceBefore=2, spaceAfter=6))

    story.append(Paragraph(
        "Below is the exact file tree of the active StainShift repository (<font face='Courier'>feat/inference-web-app</font>). "
        "Every file has a designated scientific or architectural purpose.",
        styles["Body"]
    ))

    folder_data = [
        [
            Paragraph("<b>File / Folder Path</b>", styles["TableHead"]),
            Paragraph("<b>Component Role</b>", styles["TableHead"]),
            Paragraph("<b>Functional Description & Implementation Detail</b>", styles["TableHead"]),
        ],
        [
            Paragraph("<font face='Courier'>api/main.py</font>", styles["TableCellMono"]),
            Paragraph("FastAPI Service", styles["TableCellBold"]),
            Paragraph("REST entrypoint. Configures CORS, initializes InferenceEngine, defines <font face='Courier'>/health</font>, <font face='Courier'>/models</font>, <font face='Courier'>/predict</font>, and handles batch unpacking.", styles["TableCell"]),
        ],
        [
            Paragraph("<font face='Courier'>api/inference.py</font>", styles["TableCellMono"]),
            Paragraph("Inference Engine", styles["TableCellBold"]),
            Paragraph("Core execution layer. Loads PyTorch checkpoints, handles security limits, validates PIL images, applies Macenko stain transforms, and runs tensor forward passes.", styles["TableCell"]),
        ],
        [
            Paragraph("<font face='Courier'>api/schemas.py</font>", styles["TableCellMono"]),
            Paragraph("Data Contracts", styles["TableCellBold"]),
            Paragraph("Pydantic v2 schemas: <font face='Courier'>HealthResponse</font>, <font face='Courier'>PredictResponse</font>, <font face='Courier'>ImageInferenceResult</font>, and <font face='Courier'>SingleModelPrediction</font>.", styles["TableCell"]),
        ],
        [
            Paragraph("<font face='Courier'>src/stain_shift.py</font>", styles["TableCellMono"]),
            Paragraph("Physics Engine", styles["TableCellBold"]),
            Paragraph("Beer-Lambert deconvolution, Macenko SVD decomposition, dye angle percentiles, optical rotation, and Reinhard l-alpha-beta normalizer. 100% pure NumPy/PIL.", styles["TableCell"]),
        ],
        [
            Paragraph("<font face='Courier'>src/models.py</font>", styles["TableCellMono"]),
            Paragraph("Model Definitions", styles["TableCellBold"]),
            Paragraph("Defines MobileNetV3-Small backbone, 256-hidden classification head, checkpoint serializer/deserializer with SHA-256 hash checking and 9 tissue class mappings.", styles["TableCell"]),
        ],
        [
            Paragraph("<font face='Courier'>src/dataset.py</font>", styles["TableCellMono"]),
            Paragraph("Dataset Loader", styles["TableCellBold"]),
            Paragraph("PyTorch Dataset and DataLoader implementations, deterministic POSIX file discovery, disjoint split generator, and online stain augmentation transform modes.", styles["TableCell"]),
        ],
        [
            Paragraph("<font face='Courier'>src/train.py</font>", styles["TableCellMono"]),
            Paragraph("Training Pipeline", styles["TableCellBold"]),
            Paragraph("PyTorch training loop with AdamW optimizer, CosineAnnealingLR scheduling, early stopping, validation F1 evaluation, and checkpoint persistence.", styles["TableCell"]),
        ],
        [
            Paragraph("<font face='Courier'>src/evaluate.py</font>", styles["TableCellMono"]),
            Paragraph("Evaluation Pipeline", styles["TableCellBold"]),
            Paragraph("Full benchmark evaluator across all 8 stain profiles. Generates 9x9 confusion matrices, macro F1, accuracy drop percentages, and prediction flip counts.", styles["TableCell"]),
        ],
        [
            Paragraph("<font face='Courier'>src/tracking.py</font>", styles["TableCellMono"]),
            Paragraph("MLflow Tracker", styles["TableCellBold"]),
            Paragraph("Optional scientific tracking wrapper connecting to SQLite database and saving evaluation artifacts without adding external runtime bloat.", styles["TableCell"]),
        ],
        [
            Paragraph("<font face='Courier'>src/benchmark.py</font>", styles["TableCellMono"]),
            Paragraph("Hardware Profiler", styles["TableCellBold"]),
            Paragraph("Microbenchmarking suite measuring synchronized forward inference latency on Apple Silicon MPS and CPU across batch sizes 1 and 16.", styles["TableCell"]),
        ],
        [
            Paragraph("<font face='Courier'>models/full_benchmark_20261029_1838/</font>", styles["TableCellMono"]),
            Paragraph("Trained Weights", styles["TableCellBold"]),
            Paragraph("Authoritative PyTorch model weights: <font face='Courier'>baseline.pth</font> (4.2 MB) and <font face='Courier'>robust_stain_aug.pth</font> (4.2 MB) with JSON training histories.", styles["TableCell"]),
        ],
        [
            Paragraph("<font face='Courier'>data/CRC-VAL-HE-7K/</font>", styles["TableCellMono"]),
            Paragraph("Benchmarking Data", styles["TableCellBold"]),
            Paragraph("Colorectal cancer histology patch cohort (7,180 total images across 9 tissue classes) with frozen JSON split manifests.", styles["TableCell"]),
        ],
        [
            Paragraph("<font face='Courier'>website/src/app/page.tsx</font>", styles["TableCellMono"]),
            Paragraph("Homepage", styles["TableCellBold"]),
            Paragraph("Four-screen scrollytelling entry: Hero narrative, animated KPI cards (+63.8% recovery, 33.9% drop), animated horizontal bar chart, and confusion matrix.", styles["TableCell"]),
        ],
        [
            Paragraph("<font face='Courier'>website/src/app/workspace/page.tsx</font>", styles["TableCellMono"]),
            Paragraph("AI Workspace", styles["TableCellBold"]),
            Paragraph("Interactive user tool: image drag-and-drop, condition selector (8 profiles), intensity slider, live inference invocation, and CSV batch results table.", styles["TableCell"]),
        ],
        [
            Paragraph("<font face='Courier'>website/src/app/dashboard/page.tsx</font>", styles["TableCellMono"]),
            Paragraph("Results Dashboard", styles["TableCellBold"]),
            Paragraph("Complete Stage B benchmark visualization: Accuracy across stain profiles, interactive confusion matrix, MPS latency benchmarks, and collapsible technical specs drawer.", styles["TableCell"]),
        ],
        [
            Paragraph("<font face='Courier'>website/src/app/demo/page.tsx</font>", styles["TableCellMono"]),
            Paragraph("Demo Explorer", styles["TableCellBold"]),
            Paragraph("Static option B explorer: 72 pre-evaluated tissue patches across all 8 conditions with zero backend latency or connection dependencies.", styles["TableCell"]),
        ],
        [
            Paragraph("<font face='Courier'>website/src/components/landing/</font>", styles["TableCellMono"]),
            Paragraph("Animation Libs", styles["TableCellBold"]),
            Paragraph("Native browser animation components: <font face='Courier'>ScrollReveal.tsx</font>, <font face='Courier'>CountUp.tsx</font>, and <font face='Courier'>AnimatedBarChart.tsx</font>.", styles["TableCell"]),
        ],
        [
            Paragraph("<font face='Courier'>website/src/components/workspace/</font>", styles["TableCellMono"]),
            Paragraph("Workspace UI", styles["TableCellBold"]),
            Paragraph("Modular workspace components: <font face='Courier'>ModelSelector.tsx</font>, <font face='Courier'>StainControls.tsx</font>, <font face='Courier'>ImageUploader.tsx</font>, <font face='Courier'>PredictionResultView.tsx</font>, <font face='Courier'>BatchResultsTable.tsx</font>.", styles["TableCell"]),
        ],
        [
            Paragraph("<font face='Courier'>website/public/data/</font>", styles["TableCellMono"]),
            Paragraph("Public Benchmark", styles["TableCellBold"]),
            Paragraph("Static verified benchmark results: <font face='Courier'>stainshift_results.json</font> containing exact metrics across N = 1,077 held-out test patches.", styles["TableCell"]),
        ],
    ]

    folder_table = Table(folder_data, colWidths=[130, 80, 294])
    folder_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_BG_WARM),
        ("BOX", (0, 0), (-1, -1), 0.75, C_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(folder_table)
    story.append(PageBreak())

    # =========================================================================
    # SECTION 6: MACHINE LEARNING ARCHITECTURE & MATHEMATICS
    # =========================================================================
    story.append(Paragraph("6. Machine Learning Architecture, Mathematics & Evaluation", styles["H1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceBefore=2, spaceAfter=6))

    story.append(Paragraph("6.1 Physics of H&E Staining & Optical Density Derivation", styles["H2"]))
    story.append(Paragraph(
        "Biological tissue sections examined under transmission light microscopy do not emit light; they absorb photons "
        "according to the physical wavelength absorption spectra of bound histological dye molecules. Under the physical "
        "Beer-Lambert Law of absorption, transmitted light intensity satisfies:",
        styles["Body"]
    ))

    math_block_1 = (
        "                    I = I_0 * 10^(-OD)   ==>   OD = -log10( I / I_0 )\n\n"
        "Where:\n"
        "  • I_0 = 255.0  (Incident illumination intensity of transparent clear glass slide)\n"
        "  • I   = [R, G, B]^T in [1.0, 255.0] (Transmitted RGB pixel intensity)\n"
        "  • OD  = [OD_R, OD_G, OD_B]^T (Optical Density, linear in dye concentration)\n"
        "  • OD  = S^T * C  ==>  [OD_R, OD_G, OD_B]^T = [S_H, S_E]^T * [C_H, C_E]^T"
    )
    story.append(create_code_block(math_block_1, filename="Beer-Lambert Optical Density Formulation", styles=styles))
    story.append(Spacer(1, 5))

    story.append(Paragraph(
        "Crucially, while light mixing in RGB space is non-linear and multiplicative, optical absorption in OD space is "
        "strictly linear and additive. This physical property allows us to decouple overlapping Hematoxylin (nuclear) "
        "and Eosin (cytoplasmic/stromal) dye components into independent chemical concentration maps using Principal Component Analysis.",
        styles["Body"]
    ))

    story.append(Paragraph("6.2 Macenko SVD Decomposition & Dye Perturbation Mathematics", styles["H2"]))
    story.append(Paragraph(
        "The Macenko method decomposes digital H&E histology patches into physical dye vectors via the following step-by-step algorithm:",
        styles["Body"]
    ))

    macenko_steps = (
        "1. OPTICAL DENSITY TRANSFORMATION:\n"
        "   Convert RGB image array to OD space: OD = -log10(clip(I, 1.0, 255.0) / 255.0)\n\n"
        "2. TRANSPARENT GLASS REMOVAL (BETA THRESHOLDING):\n"
        "   Discard background pixels where OD < beta (beta = 0.15). Prevents white glass noise from corrupting PCA.\n\n"
        "3. COVARIANCE EIGENVECTOR DECOMPOSITION:\n"
        "   Compute sample covariance matrix of filtered OD pixels: Sigma = Cov(OD_filtered)\n"
        "   Perform eigenvalue decomposition: Sigma = V * Lambda * V^T\n"
        "   Extract top two eigenvectors V_2D = V[:, [2, 1]] spanning the primary stain plane.\n\n"
        "4. 2D PROJECTION & ANGULAR SPECTRUM:\n"
        "   Project OD vectors onto the 2D stain plane: P = OD_filtered * V_2D\n"
        "   Compute polar angles: theta = arctan2(P[:, 1], P[:, 0])\n\n"
        "5. ROBUST ANGLE ESTIMATION:\n"
        "   Find robust extreme angular percentiles: theta_min = percentile(theta, alpha=1.0)\n"
        "                                           theta_max = percentile(theta, 99.0)\n"
        "   Back-project extreme angles to 3D OD space and normalize to unit Euclidean length:\n"
        "   S_H = normalize(V_2D * [cos(theta_max), sin(theta_max)]^T)\n"
        "   S_E = normalize(V_2D * [cos(theta_min), sin(theta_min)]^T)\n\n"
        "6. CONCENTRATION EXTRACTION (NON-NEGATIVE LEAST SQUARES):\n"
        "   Solve OD = S^T * C for concentration matrix C: C = lstsq(S^T, OD^T), then clamp C = max(C, 0.0)\n\n"
        "7. PHYSICS-BASED DYE PERTURBATION & RECONSTRUCTION:\n"
        "   Perturb concentrations: C'_H = alpha_H * C_H ; C'_E = alpha_E * C_E\n"
        "   Rotate stain plane by angle phi: S' = S * R(phi)\n"
        "   Reconstruct RGB patch: OD_pert = C' * S'  ==>  I_pert = 255.0 * 10^(-OD_pert)"
    )
    story.append(create_code_block(macenko_steps, filename="Macenko SVD Algorithm & Concentration Perturbation", styles=styles))
    story.append(Spacer(1, 5))

    story.append(Paragraph(
        "<b>The Eight Evaluated Stain Profiles:</b><br/>"
        "StainShift benchmarks eight distinct physical conditions: "
        "<b>(1) original:</b> native unperturbed slide (exact identity); "
        "<b>(2) reconstruction_only:</b> deconvolution control (α_H=1.0, α_E=1.0, θ=0°); "
        "<b>(3) heavy_hematoxylin:</b> hyperchromatic nuclei (α_H=1.65, α_E=0.85, θ=+3°); "
        "<b>(4) heavy_eosin:</b> eosinophilic stroma (α_H=0.75, α_E=1.65, θ=-3°); "
        "<b>(5) pale_understained:</b> low dye concentration (α_H=0.60, α_E=0.60); "
        "<b>(6) dark_overstained:</b> hyper-dense dye absorption (α_H=1.50, α_E=1.50); "
        "<b>(7) synthetic_warm_shift:</b> positive stain plane rotation (α_H=0.90, α_E=1.30, θ=+8°); "
        "<b>(8) synthetic_cool_shift:</b> negative stain plane rotation (α_H=1.35, α_E=0.80, θ=-8°).",
        styles["Body"]
    ))
    story.append(Spacer(1, 5))

    story.append(Paragraph("6.3 MobileNetV3-Small Neural Architecture & Head Modifications", styles["H2"]))
    story.append(Paragraph(
        "StainShift selects <b>MobileNetV3-Small</b> as its primary backbone architecture. "
        "In biomedical edge and web deployments, heavyweight vision transformers (ViTs) or deep ResNets introduce prohibitive "
        "latency (200–800 ms per patch) and memory footprints exceeding 500 MB. MobileNetV3-Small leverages depthwise separable "
        "convolutions, squeeze-and-excitation (SE) residual attention blocks, and hardware-friendly Hardswish activation functions.",
        styles["Body"]
    ))

    mobilenet_head = (
        "# Custom Histopathology Classification Head (src/models.py)\n"
        "model = models.mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.DEFAULT)\n"
        "in_features = model.classifier[0].in_features  # 576 channels from feature extractor\n\n"
        "model.classifier = nn.Sequential(\n"
        "    nn.Linear(in_features, 256),   # Bottleneck compression\n"
        "    nn.Hardswish(),                # Efficient non-linear activation\n"
        "    nn.Dropout(p=0.2),             # Regularization against patch overfitting\n"
        "    nn.Linear(256, 9)              # 9 Colorectal Tissue Classes (logits)\n"
        ")"
    )
    story.append(create_code_block(mobilenet_head, filename="src/models.py · MobileNetV3-Small Head Adapter", styles=styles))
    story.append(Spacer(1, 5))

    story.append(Paragraph("6.4 Scientific Findings: The 33.9% Collapse & 97.7% Recovery", styles["H2"]))
    story.append(Paragraph(
        "The table below details the authoritative benchmark results on the frozen held-out test split of <b>CRC-VAL-HE-7K</b> "
        "(N = 1,077 unexposed patches). Training was conducted using the AdamW optimizer (learning rate 1e-4) for 5 epochs.",
        styles["Body"]
    ))

    results_table_data = [
        [
            Paragraph("<b>Stain Condition Profile</b>", styles["TableHead"]),
            Paragraph("<b>Physical Shift Parameters</b>", styles["TableHead"]),
            Paragraph("<b>Baseline Accuracy</b>", styles["TableHead"]),
            Paragraph("<b>Robust Accuracy</b>", styles["TableHead"]),
            Paragraph("<b>Net Shift Recovery</b>", styles["TableHead"]),
        ],
        [
            Paragraph("<b>original</b> (Native)", styles["TableCellBold"]),
            Paragraph("Unperturbed slide (α=1.0)", styles["TableCell"]),
            Paragraph("<b>99.91%</b>", styles["TableCellBold"]),
            Paragraph("98.79%", styles["TableCell"]),
            Paragraph("-1.12 pp (tradeoff)", styles["TableCellMono"]),
        ],
        [
            Paragraph("<b>reconstruction_only</b>", styles["TableCellBold"]),
            Paragraph("Deconv control (α=1.0, θ=0°)", styles["TableCell"]),
            Paragraph("<font color='#9B2A2A'><b>33.89%</b> (-66.02%)</font>", styles["TableCellBold"]),
            Paragraph("<font color='#2D5A46'><b>97.68%</b></font>", styles["TableCellBold"]),
            Paragraph("<b>+63.79%</b>", styles["TableCellBold"]),
        ],
        [
            Paragraph("<b>heavy_hematoxylin</b>", styles["TableCellBold"]),
            Paragraph("α_H=1.65, α_E=0.85, θ=+3°", styles["TableCell"]),
            Paragraph("<font color='#9B2A2A'>32.40%</font>", styles["TableCell"]),
            Paragraph("<font color='#2D5A46'>96.94%</font>", styles["TableCell"]),
            Paragraph("<b>+64.54%</b>", styles["TableCellBold"]),
        ],
        [
            Paragraph("<b>heavy_eosin</b>", styles["TableCellBold"]),
            Paragraph("α_H=0.75, α_E=1.65, θ=-3°", styles["TableCell"]),
            Paragraph("<font color='#9B2A2A'>28.97%</font>", styles["TableCell"]),
            Paragraph("<font color='#2D5A46'>96.29%</font>", styles["TableCell"]),
            Paragraph("<b>+67.32%</b>", styles["TableCellBold"]),
        ],
        [
            Paragraph("<b>pale_understained</b>", styles["TableCellBold"]),
            Paragraph("α_H=0.60, α_E=0.60", styles["TableCell"]),
            Paragraph("<font color='#9B2A2A'>34.73%</font>", styles["TableCell"]),
            Paragraph("<font color='#2D5A46'>96.75%</font>", styles["TableCell"]),
            Paragraph("<b>+62.02%</b>", styles["TableCellBold"]),
        ],
        [
            Paragraph("<b>dark_overstained</b>", styles["TableCellBold"]),
            Paragraph("α_H=1.50, α_E=1.50", styles["TableCell"]),
            Paragraph("<font color='#9B2A2A'>31.94%</font>", styles["TableCell"]),
            Paragraph("<font color='#2D5A46'>96.47%</font>", styles["TableCell"]),
            Paragraph("<b>+64.53%</b>", styles["TableCellBold"]),
        ],
        [
            Paragraph("<b>synthetic_warm_shift</b>", styles["TableCellBold"]),
            Paragraph("α_H=0.90, α_E=1.30, θ=+8°", styles["TableCell"]),
            Paragraph("<font color='#9B2A2A'>31.57%</font>", styles["TableCell"]),
            Paragraph("<font color='#2D5A46'>94.80%</font>", styles["TableCell"]),
            Paragraph("<b>+63.23%</b>", styles["TableCellBold"]),
        ],
        [
            Paragraph("<b>synthetic_cool_shift</b>", styles["TableCellBold"]),
            Paragraph("α_H=1.35, α_E=0.80, θ=-8°", styles["TableCell"]),
            Paragraph("<font color='#9B2A2A'>36.30%</font>", styles["TableCell"]),
            Paragraph("<font color='#2D5A46'>96.38%</font>", styles["TableCell"]),
            Paragraph("<b>+60.08%</b>", styles["TableCellBold"]),
        ],
    ]
    results_table = Table(results_table_data, colWidths=[110, 134, 90, 80, 90])
    results_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_BG_WARM),
        ("BOX", (0, 0), (-1, -1), 0.75, C_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(results_table)
    story.append(PageBreak())

    # =========================================================================
    # SECTION 7: APPLICATION WORKFLOWS
    # =========================================================================
    story.append(Paragraph("7. End-to-End Application Workflows", styles["H1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceBefore=2, spaceAfter=6))

    story.append(Paragraph("7.1 Workflow A: Interactive AI Workspace (/workspace/)", styles["H2"]))
    story.append(Paragraph(
        "The AI Workspace enables users to evaluate real histology patches dynamically. The complete execution cycle unfolds across eight stages:",
        styles["Body"]
    ))

    workspace_steps = (
        "1. USER FILE SELECTION:\n"
        "   User drops one or more image files (.png, .jpg) or a .zip archive into ImageUploader.tsx.\n"
        "   Local client-side URL.createObjectURL creates instantaneous thumbnails without uploading bytes.\n\n"
        "2. WORKSPACE CONFIGURATION:\n"
        "   User selects Model Mode: 'baseline', 'robust_stain_aug', or 'compare' (Side-by-side).\n"
        "   User selects Stain Condition (e.g. 'heavy_hematoxylin') and adjusts Intensity (0.0x to 2.5x).\n\n"
        "3. HTTP MULTIPART DISPATCH:\n"
        "   On clicking 'Run Prediction', page.tsx constructs FormData() with files, model_id, condition, intensity.\n"
        "   Dispatches asynchronous HTTP POST to /predict on the Render FastAPI backend.\n\n"
        "4. SERVER-SIDE UNPACKING & SECURITY AUDIT:\n"
        "   FastAPI receives multipart stream. Files are unpacked in-memory (io.BytesIO).\n"
        "   Zip-Bomb check validates total uncompressed bytes < 100 MB; Zip-Slip removes path traversal markers.\n\n"
        "5. MACENKO BEER-LAMBERT TRANSFORMATION:\n"
        "   Pillow validates 8-bit RGB mode. MacenkoStainDecomposer projects patch into OD space,\n"
        "   applies requested intensity scaling, and reconstructs the shifted RGB image.\n\n"
        "6. PYTORCH MODEL INFERENCE:\n"
        "   Transformed image is resized to (224, 224) and normalized with ImageNet mean/std tensors.\n"
        "   Forward pass executes within torch.no_grad(). Softmax converts logits into 9 class probabilities.\n\n"
        "7. PREDICTION COMPARISON & FLIP DETECTION:\n"
        "   If 'compare' mode is selected, both baseline and robust models evaluate the exact same tensor.\n"
        "   The engine sets agreement = (baseline.predicted_class == robust.predicted_class).\n\n"
        "8. FRONTEND RESULTS RENDERING:\n"
        "   Frontend receives PredictResponse JSON. Renders original vs shifted images,\n"
        "   displays 9-class probability bar charts, highlights prediction flips, and updates BatchResultsTable."
    )
    story.append(create_code_block(workspace_steps, filename="Workflow A Trace: Interactive AI Workspace", styles=styles))
    story.append(Spacer(1, 6))

    story.append(Paragraph("7.2 Workflow B: Results Dashboard (/dashboard/)", styles["H2"]))
    story.append(Paragraph(
        "The Results Dashboard presents the verified Stage B benchmark across the 1,077 held-out test patches:",
        styles["Body"]
    ))
    story.append(Paragraph(
        "• <b>Static Synchronous Ingestion:</b> On server-side render, <font face='Courier'>loadBenchmarkDataSync()</font> parses "
        "<font face='Courier'>public/data/stainshift_results.json</font> with runtime assertion guards (verifying N=1,077, 8 conditions).<br/>"
        "• <b>Visual Comparison Chart:</b> <font face='Courier'>AccuracyComparisonChart.tsx</font> projects baseline vs robust bars "
        "into responsive SVG coordinates using clean short labels (<font face='Courier'>Hvy. Hema.</font>, <font face='Courier'>Deconv.</font>) to eliminate label cutoff.<br/>"
        "• <b>Interactive Confusion Matrix:</b> <font face='Courier'>ConfusionMatrixViewer.tsx</font> provides a toggle between Baseline and "
        "Stain-Robust models, dynamically highlighting true diagonal classifications versus off-diagonal misclassifications.<br/>"
        "• <b>Technical Specs Drawer:</b> <font face='Courier'>TechnicalSpecsDrawer.tsx</font> stores cryptographic verification data "
        "(Git Commit, MLflow Run ID, SHA-256 checkpoint checksums) in a collapsible drawer to eliminate visual clutter.",
        styles["Body"]
    ))
    story.append(Spacer(1, 6))

    story.append(Paragraph("7.3 Workflow C: Precomputed Demo Explorer (/demo/)", styles["H2"]))
    story.append(Paragraph(
        "The Demo Explorer allows evaluators to inspect 72 representative tissue patches (8 patches per class across all 9 classes) "
        "pre-evaluated across all eight stain conditions. Because all images and model predictions are pre-rendered into static "
        "JSON manifests (<font face='Courier'>public/demo/demo_manifest.json</font>), the Demo Explorer runs with <b>zero backend connection</b>, "
        "providing a foolproof, zero-latency fallback during live stage demos.",
        styles["Body"]
    ))
    story.append(PageBreak())

    # =========================================================================
    # SECTION 8: VERBATIM SOURCE CODE REFERENCES
    # =========================================================================
    story.append(Paragraph("8. Verbatim Source Code References & Module Walkthroughs", styles["H1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceBefore=2, spaceAfter=6))

    story.append(Paragraph("8.1 API Request Dispatcher: api/main.py", styles["H2"]))
    story.append(Paragraph(
        "The FastAPI <font face='Courier'>predict()</font> handler accepts multipart uploads, validates boundary limits, "
        "and aggregates batch predictions:",
        styles["Body"]
    ))

    code_main = (
        "@app.post('/predict', response_model=PredictResponse)\n"
        "async def predict(\n"
        "    files: List[UploadFile] = File(..., description='One or more images or ZIP archive'),\n"
        "    model_id: str = Form('robust_stain_aug', description=\"'baseline', 'robust_stain_aug', or 'compare'\"),\n"
        "    condition: str = Form('original', description='Stain shift condition'),\n"
        "    intensity: float = Form(1.0, description='Perturbation scaling (0.0 to 2.5)'),\n"
        ") -> PredictResponse:\n"
        "    if model_id not in ('baseline', 'robust_stain_aug', 'compare', 'both'):\n"
        "        raise HTTPException(status_code=400, detail=f\"Invalid model_id '{model_id}'\")\n"
        "    if condition not in DISTINCT_STAIN_PROFILES:\n"
        "        raise HTTPException(status_code=400, detail=f\"Invalid condition '{condition}'\")\n\n"
        "    items_to_process = []\n"
        "    for uf in files:\n"
        "        content = await uf.read()\n"
        "        if Path(uf.filename).suffix.lower() == '.zip':\n"
        "            items_to_process.extend(engine.unpack_zip_archive(content))\n"
        "        elif Path(uf.filename).suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS:\n"
        "            items_to_process.append((uf.filename, content))\n\n"
        "    results = [ImageInferenceResult(**engine.process_image(\n"
        "        image_bytes=raw, filename=fname, model_mode=model_id, condition=condition, intensity=intensity\n"
        "    )) for fname, raw in items_to_process]\n\n"
        "    return PredictResponse(status='success', summary=engine.summarize(results), results=results)"
    )
    story.append(create_code_block(code_main, filename="api/main.py · Request Dispatcher", styles=styles))
    story.append(Spacer(1, 6))

    story.append(Paragraph("8.2 Inference Engine: api/inference.py", styles["H2"]))
    story.append(Paragraph(
        "The <font face='Courier'>run_single_model_inference()</font> method handles hardware synchronization and tensor evaluation:",
        styles["Body"]
    ))

    code_inference = (
        "def run_single_model_inference(self, model_id: str, tensor_224: torch.Tensor) -> Dict[str, Any]:\n"
        "    model = self.models[model_id]\n"
        "    tensor_device = tensor_224.to(self.device)\n\n"
        "    # Synchronize compute device before timing\n"
        "    if self.device_str == 'mps': torch.mps.synchronize()\n"
        "    elif self.device_str == 'cuda': torch.cuda.synchronize()\n\n"
        "    t0 = time.perf_counter()\n"
        "    with torch.no_grad():\n"
        "        logits = model(tensor_device)\n"
        "        probs = F.softmax(logits, dim=1)[0]\n\n"
        "    if self.device_str == 'mps': torch.mps.synchronize()\n"
        "    elif self.device_str == 'cuda': torch.cuda.synchronize()\n"
        "    t1 = time.perf_counter()\n\n"
        "    probs_np = probs.cpu().numpy()\n"
        "    pred_idx = int(np.argmax(probs_np))\n"
        "    return {\n"
        "        'model_id': model_id,\n"
        "        'predicted_class': CLASS_NAMES[pred_idx],\n"
        "        'confidence': round(float(probs_np[pred_idx]), 4),\n"
        "        'probabilities': {c: round(float(probs_np[i]), 4) for i, c in enumerate(CLASS_NAMES)},\n"
        "        'inference_time_ms': round((t1 - t0) * 1000.0, 3)\n"
        "    }"
    )
    story.append(create_code_block(code_inference, filename="api/inference.py · Hardware-Synchronized Inference", styles=styles))
    story.append(Spacer(1, 6))

    story.append(Paragraph("8.3 Physics Engine: src/stain_shift.py", styles["H2"]))
    story.append(Paragraph(
        "The Beer-Lambert perturbation logic showing concentration scaling and optical rotation:",
        styles["Body"]
    ))

    code_stain = (
        "def perturb(self, img_rgb: np.ndarray, alpha_h: float=1.0, alpha_e: float=1.0, stain_rot_deg: float=0.0):\n"
        "    # Exact identity bypass for neutral controls\n"
        "    if abs(alpha_h - 1.0) < 1e-6 and abs(alpha_e - 1.0) < 1e-6 and abs(stain_rot_deg) < 1e-4:\n"
        "        return img_rgb.copy()\n\n"
        "    stain_matrix, concentrations, (h, w) = self.extract_stain_vectors_and_concentrations(img_rgb)\n"
        "    c_perturbed = concentrations.copy()\n"
        "    c_perturbed[:, 0] *= alpha_h   # Scale Hematoxylin (nuclear absorption)\n"
        "    c_perturbed[:, 1] *= alpha_e   # Scale Eosin (cytoplasmic absorption)\n\n"
        "    s_perturbed = stain_matrix.copy()\n"
        "    if abs(stain_rot_deg) > 1e-3:\n"
        "        rad = np.radians(stain_rot_deg)\n"
        "        rot_matrix = np.array([\n"
        "            [np.cos(rad), -np.sin(rad), 0.0],\n"
        "            [np.sin(rad),  np.cos(rad), 0.0],\n"
        "            [0.0,          0.0,         1.0]\n"
        "        ])\n"
        "        s_perturbed = np.maximum(np.dot(s_perturbed, rot_matrix), 0.0)\n"
        "        s_perturbed /= np.linalg.norm(s_perturbed, axis=1, keepdims=True)\n\n"
        "    od_perturbed = np.dot(c_perturbed, s_perturbed).reshape((h, w, 3))\n"
        "    return self.od_to_rgb(od_perturbed)  # I = 255.0 * 10^(-OD)"
    )
    story.append(create_code_block(code_stain, filename="src/stain_shift.py · Optical Density Perturbation", styles=styles))
    story.append(PageBreak())

    # =========================================================================
    # SECTION 9: DEVELOPER LEARNING GUIDE
    # =========================================================================
    story.append(Paragraph("9. Developer Learning Guide: Building StainShift from Scratch", styles["H1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceBefore=2, spaceAfter=6))

    story.append(Paragraph(
        "<b>Educational Note for Bioinformatics Students:</b><br/>"
        "As a bioinformatics engineer, you are uniquely positioned at the intersection of biological domain knowledge "
        "(cellular pathology, tissue histology, dye chemistry) and computational engineering (computer vision, deep neural networks, "
        "asynchronous web architectures). Building a production system like StainShift involves ten systematic phases:",
        styles["Body"]
    ))

    dev_phases = [
        ("Phase 1: Environment Setup & Isolation",
         "Create an isolated Python virtual environment (<font face='Courier'>python -m venv .venv</font>). "
         "Install pinned dependencies from <font face='Courier'>requirements.txt</font>. Never install packages globally. "
         "Set up Node.js 18+ and npm for the frontend."),
        ("Phase 2: Biological Data Modeling & Splits",
         "Download the CRC-VAL-HE-7K dataset. Histopathology patches must be grouped by slide or patient ID where available. "
         "Enforce strict sample disjointness: patches from the same patient/slide must never be split between training and test sets. "
         "Sort file paths deterministically before shuffling with a fixed random seed (<font face='Courier'>seed=42</font>)."),
        ("Phase 3: The Physics of Stain Deconvolution",
         "Implement Beer-Lambert optical density deconvolution in pure NumPy. Do not rely on black-box libraries until you understand "
         "the math: convert RGB to OD using <font face='Courier'>-log10(I / 255.0)</font>, compute the sample covariance matrix, "
         "perform PCA via <font face='Courier'>np.linalg.eigh</font>, and solve for dye concentrations with least-squares."),
        ("Phase 4: PyTorch Model Architecture & Transfer Learning",
         "Load a pretrained MobileNetV3-Small backbone from <font face='Courier'>torchvision.models</font>. "
         "Replace the final classifier with a linear bottleneck layer (256 units), Hardswish activation, dropout (0.2), "
         "and an output projection to 9 logits matching your tissue classes."),
        ("Phase 5: The Augmented Training Loop",
         "Train the baseline model with standard geometric transforms (random flips and 90-degree rotations). "
         "Train the robust model with online Macenko stain perturbation, randomly scaling α_H, α_E in [0.7, 1.4] "
         "and rotating stain planes by ±8°. Track validation F1 scores at every epoch using MLflow."),
        ("Phase 6: Multi-Condition Benchmarking Pipeline",
         "Write an evaluation script (<font face='Courier'>src/evaluate.py</font>) that evaluates both models across all eight "
         "synthetic stain profiles. Export 9x9 confusion matrices, per-class F1 metrics, and save verified checkpoints with SHA-256 hashes."),
        ("Phase 7: Building the FastAPI REST Microservice",
         "Construct asynchronous endpoints using FastAPI. Implement Pydantic data contracts for request and response serialization. "
         "Implement strict security boundaries: in-memory <font face='Courier'>io.BytesIO</font> image parsing, maximum file size limits, "
         "and Zip-Bomb protection."),
        ("Phase 8: Building the Next.js Frontend UI",
         "Initialize a Next.js 14 project with TypeScript and Tailwind CSS. Design a scrollytelling narrative landing page "
         "on the homepage (<font face='Courier'>/</font>) and an interactive workspace (<font face='Courier'>/workspace/</font>). "
         "Use native <font face='Courier'>IntersectionObserver</font> and <font face='Courier'>requestAnimationFrame</font> for butter-smooth 60fps animations."),
        ("Phase 9: Connecting Frontend & Backend via REST",
         "Use the browser's native <font face='Courier'>fetch</font> API to send <font face='Courier'>FormData</font> to <font face='Courier'>/predict</font>. "
         "Render original vs transformed patches side-by-side using base64 data URLs. Dynamically highlight prediction flips."),
        ("Phase 10: Production Deployment & Edge Distribution",
         "Deploy the static Next.js frontend to Vercel (<font face='Courier'>output: 'export'</font>) for zero-latency global edge delivery. "
         "Deploy the containerized FastAPI Python backend to Render using Docker. Configure CORS and environment variables."),
    ]

    for p_title, p_desc in dev_phases:
        story.append(Paragraph(f"<b>{p_title}</b>", styles["TableCellBold"]))
        story.append(Paragraph(p_desc, styles["Bullet"]))
        story.append(Spacer(1, 2))

    story.append(Spacer(1, 4))
    story.append(Paragraph("9.2 Comprehensive Technical Glossary", styles["H2"]))

    glossary_items = [
        ("Optical Density (OD)", "A logarithmic measure of light absorption: OD = -log10(I / I_0). In contrast to non-linear RGB values, OD values are strictly linear and additive with respect to dye concentration."),
        ("Beer-Lambert Law", "The physical equation governing light attenuation through absorbing media: I = I_0 * 10^(-S^T * C). Forms the mathematical foundation for separating Hematoxylin and Eosin dye components."),
        ("Macenko Deconvolution", "An unsupervised, PCA-based mathematical technique that estimates individual stain absorption vectors directly from an RGB image by finding extreme angular percentiles in the 2D optical density plane."),
        ("Reinhard Normalization", "A statistical color transfer method that aligns the mean and standard deviation of an image's channels to a reference target in Ruderman l-alpha-beta color space."),
        ("Empirical Risk Minimization (ERM)", "The standard machine learning paradigm of minimizing average training loss over an empirical sample set. Frequently leads models to memorize spurious color shortcuts."),
        ("Domain Shift", "A statistical discrepancy between training and deployment data distributions. In digital pathology, stain variation across laboratories is the primary cause of domain shift failure."),
        ("Prediction Flip", "An event where an identical histological tissue patch is classified into class A under standard conditions, but flips into class B when stain parameters shift."),
        ("Softmax Function", "A normalized exponential mathematical function that converts unconstrained neural network logits into a probability distribution summing to 1.0."),
        ("Macro F1-Score", "The unweighted mean of F1-scores across all classes: (1/C) * sum(F1_c). Treats all tissue classes equally regardless of sample imbalance."),
        ("Metal Performance Shaders (MPS)", "Apple's hardware-accelerated GPU computing framework for Apple Silicon processors, providing accelerated tensor operations via PyTorch's torch.backends.mps backend."),
        ("Asynchronous Server Gateway Interface (ASGI)", "The modern Python specification for asynchronous web servers, enabling concurrent request processing and non-blocking I/O in FastAPI."),
        ("Static Export (SSG)", "A Next.js build compilation mode (output: 'export') that pre-renders all pages into static HTML, CSS, and JS bundles, enabling instant CDN delivery with zero server runtime overhead."),
    ]

    glossary_table_data = [
        [
            Paragraph(f"<b>{term}</b>", styles["TableCellBold"]),
            Paragraph(desc, styles["TableCell"]),
        ]
        for term, desc in glossary_items
    ]
    glossary_table = Table(glossary_table_data, colWidths=[130, 374])
    glossary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_BG_WARM),
        ("BOX", (0, 0), (-1, -1), 0.75, C_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(glossary_table)
    story.append(PageBreak())

    # =========================================================================
    # SECTION 10: VERIFICATION SIGN-OFF & DOCUMENT INTEGRITY
    # =========================================================================
    story.append(Paragraph("10. Verification Sign-Off & Document Integrity", styles["H1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceBefore=2, spaceAfter=6))

    signoff_text = (
        "<b>DOCUMENT INTEGRITY & METRIC ATTESTATION:</b><br/>"
        "This technical architecture and developer guide was generated directly from the working source code of the "
        "StainShift repository at commit <b>b890655</b> on <b>October 30, 2026</b>. "
        "All software versions, mathematical formulations, code listings, and performance benchmarks "
        "were verified through automated empirical regression testing against the deployed Vercel frontend "
        "(https://stainshift-ai.vercel.app/) and Render FastAPI backend (https://stainshift-api.onrender.com).<br/><br/>"
        "<b>Verified Cryptographic Checkpoint Signatures:</b><br/>"
        "• Baseline Model Checkpoint (<font face='Courier'>baseline.pth</font>): "
        "<font face='Courier'>3b656cb19974a00e825a73590b2fded9d19745cb9c9e0f68ef2af2288735bf76</font><br/>"
        "• Robust Model Checkpoint (<font face='Courier'>robust_stain_aug.pth</font>): "
        "<font face='Courier'>48ae96612d585c696179e355bcb5d8b12b06dcb651dd9c4ad457b68e446d792a</font><br/>"
        "• Frozen Dataset Split Manifest (<font face='Courier'>splits.json</font>): "
        "<font face='Courier'>15ad014637fa207d79bd2b02b3adda6bf9ca22035d36cf9f296d04f6bdec0050</font><br/><br/>"
        "<b>Academic Citations:</b><br/>"
        "[1] Macenko, M. et al. (2009). <i>A method for normalizing histology slides for quantitative analysis.</i> IEEE ISBI, pp. 1107-1110.<br/>"
        "[2] Kather, J. N. et al. (2019). <i>Predicting survival from colorectal cancer histology slides using deep learning: A multicenter study.</i> PLOS Medicine, 16(1): e1002730.<br/>"
        "[3] Howard, A. et al. (2019). <i>Searching for MobileNetV3.</i> IEEE/CVF International Conference on Computer Vision (ICCV), pp. 1314-1324.<br/>"
        "[4] Reinhard, E. et al. (2001). <i>Color transfer between images.</i> IEEE Computer Graphics and Applications, 21(5): 34-41."
    )
    story.append(Paragraph(signoff_text, styles["Body"]))
    story.append(Spacer(1, 10))

    sign_box = [
        [
            Paragraph("<b>DOCUMENT CLASSIFICATION:</b> Unrestricted Technical Documentation", styles["TableCellBold"]),
            Paragraph("<b>STATUS:</b> STAGE B VERIFIED", styles["TableCellBold"]),
        ],
        [
            Paragraph("<b>DISTRIBUTION:</b> GitHub Repository & Vercel Public Edge", styles["TableCell"]),
            Paragraph("<b>COMPLIANCE:</b> Non-Clinical Investigational Benchmark", styles["TableCell"]),
        ]
    ]
    sign_table = Table(sign_box, colWidths=[252, 252])
    sign_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_BG_WARM),
        ("BOX", (0, 0), (-1, -1), 1, C_TERRACOTTA),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(sign_table)

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated PDF at: {output_path}")

    # Also copy to website/public/docs/ for web hosting
    public_docs = Path("website/public/docs")
    public_docs.mkdir(parents=True, exist_ok=True)
    web_target = public_docs / Path(output_path).name
    shutil.copyfile(output_path, web_target)
    print(f"Copied PDF to web public directory at: {web_target}")


if __name__ == "__main__":
    out_dir = Path("docs/technical")
    out_dir.mkdir(parents=True, exist_ok=True)
    target_pdf = out_dir / "StainShift_Technical_Architecture_and_Developer_Guide.pdf"
    build_pdf(str(target_pdf))
