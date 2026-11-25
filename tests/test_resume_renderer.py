import json
from pathlib import Path

import pytest

from src.factory.resume_renderer import (
    calculate_word_recall,
    extract_docx_text,
    extract_pdf_text,
    extract_text,
    load_candidates,
    render_pdf,
    render_docx,
    resume_text,
)


@pytest.fixture
def candidate():
    return load_candidates()[0]


def test_rendered_pdf_and_docx_extract(candidate, tmp_path):
    pdf_path = render_pdf(candidate, tmp_path / "resume.pdf", "one-column")
    docx_path = render_docx(candidate, tmp_path / "resume.docx", "two-column")

    assert pdf_path.exists()
    assert docx_path.exists()
    assert candidate["name"] in extract_pdf_text(pdf_path)
    assert candidate["name"] in extract_docx_text(docx_path)


@pytest.mark.parametrize("layout", ["one-column", "two-column", "table"])
def test_layout_formats_have_same_expected_content(candidate, tmp_path, layout):
    pdf_path = render_pdf(candidate, tmp_path / f"{layout}.pdf", layout)
    docx_path = render_docx(candidate, tmp_path / f"{layout}.docx", layout)

    expected = resume_text(candidate).lower()
    pdf_text = extract_text(pdf_path).lower()
    docx_text = extract_text(docx_path).lower()

    assert candidate["name"].lower() in pdf_text
    assert candidate["name"].lower() in docx_text
    assert calculate_word_recall(pdf_text, candidate) >= 98
    assert calculate_word_recall(docx_text, candidate) >= 98


def test_word_recall_does_not_double_count(candidate):
    repeated = resume_text(candidate) + " " + resume_text(candidate)
    assert calculate_word_recall(repeated, candidate) == 100.0


def test_missing_words_lower_recall(candidate):
    recall = calculate_word_recall("Aarav Shah", candidate)
    assert 0 < recall < 100


def test_loads_all_300_candidates():
    candidates = load_candidates()
    assert len(candidates) == 300
    assert len({candidate["candidate_id"] for candidate in candidates}) == 300
