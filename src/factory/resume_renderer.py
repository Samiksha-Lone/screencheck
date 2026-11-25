"""Render and extract synthetic candidate resumes in PDF and DOCX formats."""

import json
import re
import statistics
from html import escape
from pathlib import Path
from typing import Iterable

import fitz
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_OUTPUT_DIR = DATA_DIR / "private" / "rendered"
LAYOUTS = ("one-column", "two-column", "table")
FORMATS = ("pdf", "docx")


def load_candidates(data_dir: str | Path = DATA_DIR / "generated") -> list[dict]:
    """Load every generated candidate from the three datasets."""
    candidates = []
    for path in sorted(Path(data_dir).glob("*_candidates.json")):
        with path.open("r", encoding="utf-8") as file:
            dataset = json.load(file)
        candidates.extend(dataset["candidates"])
    return candidates


def candidate_content(candidate: dict) -> dict:
    """Build the shared resume content used by every layout and format."""
    experience = candidate["experience"]
    projects = candidate["projects"]
    return {
        "name": candidate["name"],
        "job_title": candidate["job_title"],
        "skills": list(candidate["skills"]),
        "experience": experience,
        "projects": projects,
    }


def resume_text(candidate: dict) -> str:
    """Create a plain-text representation of the resume content."""
    content = candidate_content(candidate)
    lines = [
        content["name"],
        content["job_title"],
        "Skills",
        ", ".join(content["skills"]),
    ]
    for item in content["experience"]:
        lines.extend(
            [
                "Experience",
                item["title"],
                item["organization"],
                f"{item['years']} years",
                item["summary"],
            ]
        )
    for item in content["projects"]:
        lines.extend(
            [
                "Projects",
                item["name"],
                item["description"],
                item["details"],
            ]
        )
    return "\n".join(lines)


def normalized_words(text: str) -> set[str]:
    """Normalize text and return unique words for recall calculations."""
    normalized = re.sub(r"[^\w]+", " ", text.lower(), flags=re.UNICODE)
    return {word for word in normalized.split() if word}


def calculate_word_recall(extracted_text: str, candidate: dict) -> float:
    """Calculate unique-word recall against the candidate's resume content."""
    expected = normalized_words(resume_text(candidate))
    extracted = normalized_words(extracted_text)
    if not expected:
        return 100.0
    return round(100.0 * len(expected.intersection(extracted)) / len(expected), 2)


def _pdf_styles():
    styles = getSampleStyleSheet()
    styles["Title"].fontName = "Helvetica-Bold"
    styles["Title"].fontSize = 20
    styles["Title"].alignment = TA_CENTER
    styles["Title"].leading = 24
    styles["Heading2"].fontName = "Helvetica-Bold"
    styles["Heading2"].fontSize = 11
    styles["Heading2"].textColor = colors.HexColor("#2F3E46")
    styles["Heading2"].leading = 14
    styles["BodyText"].fontName = "Helvetica"
    styles["BodyText"].fontSize = 9
    styles["BodyText"].leading = 12
    return styles


def _pdf_sections(candidate: dict, styles) -> tuple[list, list, list]:
    content = candidate_content(candidate)
    header = [
        Paragraph(content["name"], styles["Title"]),
        Paragraph(content["job_title"], styles["Heading2"]),
        Spacer(1, 8),
    ]
    left = [Paragraph("Skills", styles["Heading2"])]
    left.append(Paragraph(", ".join(content["skills"]), styles["BodyText"]))

    right = [Paragraph("Experience", styles["Heading2"])]
    for item in content["experience"]:
        right.append(
            Paragraph(
                f"<b>{item['title']}</b><br/>{item['organization']}<br/>"
                f"{item['years']} years<br/>"
                f"{item['summary']}",
                styles["BodyText"],
            )
        )

    right.append(Paragraph("Projects", styles["Heading2"]))
    for item in content["projects"]:
        right.append(
            Paragraph(
                f"<b>{item['name']}</b><br/>{item['description']}<br/>{item['details']}",
                styles["BodyText"],
            )
        )
    return header, left, right


def render_pdf(candidate: dict, output_path: str | Path, layout: str) -> Path:
    """Render a candidate resume as PDF using a selected layout."""
    if layout not in LAYOUTS:
        raise ValueError("unknown PDF layout: " + layout)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    styles = _pdf_styles()
    header, left, right = _pdf_sections(candidate, styles)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
        title="",
        author="",
        subject="",
        creator="",
    )
    story = header

    if layout == "one-column":
        story.extend(left)
        story.extend(right)
    elif layout == "two-column":
        table = Table([[left, right]], colWidths=[2.15 * inch, 4.25 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("LINEBEFORE", (1, 0), (1, 0), 0.5, colors.HexColor("#CBD5D8")),
                ]
            )
        )
        story.append(table)
    else:
        table = Table(
            [
                [
                    Paragraph("Skills", styles["Heading2"]),
                    Paragraph(
                        escape(", ".join(candidate_content(candidate)["skills"])),
                        styles["BodyText"],
                    ),
                ],
                [
                    Paragraph("Experience", styles["Heading2"]),
                    Paragraph(
                        escape(_pdf_experience_plain_text(candidate)).replace(
                            "\n", "<br/>"
                        ),
                        styles["BodyText"],
                    ),
                ],
                [
                    Paragraph("Projects", styles["Heading2"]),
                    Paragraph(
                        escape(_pdf_project_plain_text(candidate)).replace(
                            "\n", "<br/>"
                        ),
                        styles["BodyText"],
                    ),
                ],
            ],
            colWidths=[1.25 * inch, 5.15 * inch],
        )
        table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("LEADING", (0, 0), (-1, -1), 12),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5D8")),
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF3F4")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        story.append(table)

    doc.build(story)
    pdf = fitz.open(output_path)
    pdf.set_metadata({})
    pdf.save(str(output_path) + ".tmp", garbage=4)
    pdf.close()
    Path(str(output_path) + ".tmp").replace(output_path)
    return output_path


def _pdf_experience_text(candidate: dict) -> str:
    return "<br/>".join(
        f"<b>{item['title']}</b> — {item['organization']} — {item['years']} years — "
        f"{item['summary']}"
        for item in candidate["experience"]
    )


def _pdf_project_text(candidate: dict) -> str:
    return "<br/>".join(
        f"<b>{item['name']}</b> — {item['description']} — {item['details']}"
        for item in candidate["projects"]
    )


def _pdf_experience_plain_text(candidate: dict) -> str:
    return "\n".join(
        f"{item['title']} - {item['organization']} - {item['years']} years - "
        f"{item['summary']}"
        for item in candidate["experience"]
    )


def _pdf_project_plain_text(candidate: dict) -> str:
    return "\n".join(
        f"{item['name']} - {item['description']} - {item['details']}"
        for item in candidate["projects"]
    )


def _docx_add_header(document: Document, candidate: dict) -> None:
    content = candidate_content(candidate)
    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title.add_run(content["name"])
    title_run.bold = True
    title_run.font.size = Pt(18)
    job = document.add_paragraph()
    job.alignment = WD_ALIGN_PARAGRAPH.CENTER
    job_run = job.add_run(content["job_title"])
    job_run.bold = True
    job_run.font.size = Pt(11)
    document.add_paragraph()


def _docx_add_skills(document: Document, candidate: dict) -> None:
    heading = document.add_paragraph()
    heading.add_run("Skills").bold = True
    document.add_paragraph(", ".join(candidate_content(candidate)["skills"]))


def _docx_add_experience(document: Document, candidate: dict) -> None:
    heading = document.add_paragraph()
    heading.add_run("Experience").bold = True
    for item in candidate["experience"]:
        paragraph = document.add_paragraph()
        paragraph.add_run(item["title"]).bold = True
        paragraph.add_run(
            f"\n{item['organization']}\n{item['years']} years\n{item['summary']}"
        )


def _docx_add_projects(document: Document, candidate: dict) -> None:
    heading = document.add_paragraph()
    heading.add_run("Projects").bold = True
    for item in candidate["projects"]:
        paragraph = document.add_paragraph()
        paragraph.add_run(item["name"]).bold = True
        paragraph.add_run(
            f"\n{item['description']}\n{item['details']}"
        )


def render_docx(candidate: dict, output_path: str | Path, layout: str) -> Path:
    """Render a candidate resume as DOCX using a selected layout."""
    if layout not in LAYOUTS:
        raise ValueError("unknown DOCX layout: " + layout)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    document = Document()
    document.core_properties.title = ""
    document.core_properties.author = ""
    document.core_properties.subject = ""
    document.core_properties.comments = ""
    _docx_add_header(document, candidate)

    if layout == "one-column":
        _docx_add_skills(document, candidate)
        _docx_add_experience(document, candidate)
        _docx_add_projects(document, candidate)
    elif layout == "two-column":
        table = document.add_table(rows=1, cols=2)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        left = table.cell(0, 0)
        right = table.cell(0, 1)
        left.paragraphs[0].add_run("Skills").bold = True
        left.add_paragraph(", ".join(candidate_content(candidate)["skills"]))
        right.paragraphs[0].add_run("Experience").bold = True
        for item in candidate["experience"]:
            right.add_paragraph(
                f"{item['title']}\n{item['organization']}\n"
                f"{item['years']} years\n{item['summary']}"
            )
        projects_heading = right.add_paragraph()
        projects_heading.add_run("Projects").bold = True
        for item in candidate["projects"]:
            right.add_paragraph(
                f"{item['name']}\n{item['description']}\n{item['details']}"
            )
    else:
        table = document.add_table(rows=1, cols=2)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.style = "Table Grid"
        table.rows[0].cells[0].text = "Skills"
        table.rows[0].cells[1].text = ", ".join(candidate_content(candidate)["skills"])
        for label, text in (
            ("Experience", _docx_experience_text(candidate)),
            ("Projects", _docx_project_text(candidate)),
        ):
            row = table.add_row()
            row.cells[0].text = label
            row.cells[1].text = text

    document.save(output_path)
    return output_path


def _docx_experience_text(candidate: dict) -> str:
    return "\n".join(
        f"{item['title']} — {item['organization']} — {item['years']} years — "
        f"{item['summary']}"
        for item in candidate["experience"]
    )


def _docx_project_text(candidate: dict) -> str:
    return "\n".join(
        f"{item['name']} — {item['description']} — {item['details']}"
        for item in candidate["projects"]
    )


def extract_pdf_text(path: str | Path) -> str:
    pdf = fitz.open(str(path))
    text = "\n".join(page.get_text("text") for page in pdf)
    pdf.close()
    return text


def extract_docx_text(path: str | Path) -> str:
    document = Document(str(path))
    lines = [paragraph.text for paragraph in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                lines.append(cell.text)
    return "\n".join(lines)


def render_resume(candidate: dict, output_path: str | Path, layout: str, format: str) -> Path:
    """Render one resume in a supported layout and format."""
    if format == "pdf":
        return render_pdf(candidate, output_path, layout)
    if format == "docx":
        return render_docx(candidate, output_path, layout)
    raise ValueError("unknown document format: " + format)


def extract_text(path: str | Path) -> str:
    suffix = Path(path).suffix.lower()
    if suffix == ".pdf":
        return extract_pdf_text(path)
    if suffix == ".docx":
        return extract_docx_text(path)
    raise ValueError("unknown document type: " + suffix)


def render_all_resumes(
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    data_dir: str | Path = DATA_DIR / "generated",
) -> dict:
    """Render all candidates and create a recall and failure manifest."""
    candidates = load_candidates(data_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    failures = []
    metrics = {
        f"{layout}-{format}": []
        for layout in LAYOUTS
        for format in FORMATS
    }
    documents_generated = 0

    for candidate in candidates:
        job_dir = output_dir / candidate["job_id"]
        for layout in LAYOUTS:
            layout_dir = job_dir / layout
            for format in FORMATS:
                suffix = ".pdf" if format == "pdf" else ".docx"
                output_path = layout_dir / (
                    candidate["candidate_id"] + suffix
                )
                try:
                    render_resume(candidate, output_path, layout, format)
                    extracted = extract_text(output_path)
                    recall = calculate_word_recall(extracted, candidate)
                    metrics[f"{layout}-{format}"].append(recall)
                    documents_generated += 1
                except Exception as error:
                    failures.append(
                        {
                            "candidate_id": candidate["candidate_id"],
                            "layout": layout,
                            "format": format,
                            "error": str(error),
                        }
                    )

    metric_summary = {}
    for key, recalls in metrics.items():
        metric_summary[key] = {
            "document_count": len(recalls),
            "average_recall_percent": (
                round(statistics.mean(recalls), 2) if recalls else 0.0
            ),
            "minimum_recall_percent": min(recalls) if recalls else 0.0,
            "maximum_recall_percent": max(recalls) if recalls else 0.0,
        }

    manifest = {
        "candidate_count": len(candidates),
        "layout_count": len(LAYOUTS),
        "format_count": len(FORMATS),
        "expected_document_count": len(candidates) * len(LAYOUTS) * len(FORMATS),
        "documents_generated": documents_generated,
        "failure_count": len(failures),
        "failures": failures,
        "metrics": metric_summary,
    }

    manifest_path = PROJECT_ROOT / "reports" / "rendering_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=2)
        file.write("\n")

    return manifest


if __name__ == "__main__":
    result = render_all_resumes()
    print(
        json.dumps(
            {
                "candidate_count": result["candidate_count"],
                "documents_generated": result["documents_generated"],
                "failure_count": result["failure_count"],
                "one_column_pdf": result["metrics"]["one-column-pdf"],
            },
            indent=2,
        )
    )
