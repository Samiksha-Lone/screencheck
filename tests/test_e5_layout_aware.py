import hashlib
import json

import numpy as np
import pytest

from src.experiments.e5_layout_aware import (
    EXPERIMENT_ID,
    FORMATS,
    LAYOUTS,
    build_manifest,
    build_records,
    run,
)


class RecordingKeyword:
    def __init__(self):
        self.inputs = []

    def score(self, resume_text, job):
        self.inputs.append(resume_text)
        return {
            "score": float("one-column" in resume_text) * 100,
            "matched_skills": ["Python"] if "one-column" in resume_text else [],
            "missing_skills": [] if "one-column" in resume_text else ["Python"],
            "explanation": "test keyword screener",
        }


class FakeEmbeddingModel:
    def __init__(self):
        self.inputs = []

    def encode(self, texts, **kwargs):
        self.inputs.extend(texts)
        assert kwargs["convert_to_numpy"] is True
        assert kwargs["normalize_embeddings"] is True
        vectors = []
        for text in texts:
            if text == "backend job description":
                vectors.append([1.0, 0.0])
            elif "one-column" in text:
                vectors.append([1.0, 0.0])
            elif "two-column" in text:
                vectors.append([0.0, 1.0])
            elif "table" in text:
                vectors.append([-1.0, 0.0])
            else:
                raise AssertionError(f"Unexpected model input: {text}")
        return np.asarray(vectors, dtype=float)


class FakeEmbeddingScreener:
    model_name = "test-local-model"

    def __init__(self, fail=False):
        self.model = FakeEmbeddingModel()
        self.fail = fail

    def _load_model(self):
        if self.fail:
            raise RuntimeError("test model failure")
        return self.model


def _candidate():
    return {
        "candidate_id": "backend-candidate-001",
        "job_id": "backend",
    }


def _create_rendered_files(rendered_dir, candidate):
    for layout in LAYOUTS:
        for file_format in FORMATS:
            path = (
                rendered_dir
                / candidate["job_id"]
                / layout
                / f'{candidate["candidate_id"]}.{file_format}'
            )
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                f'extracted:{layout}:{file_format}:{candidate["candidate_id"]}',
                encoding="utf-8",
            )


def _extract_file(path):
    return path.read_text(encoding="utf-8")


def _run_with_fakes(tmp_path, *, embedding=None):
    candidate = _candidate()
    rendered_dir = tmp_path / "rendered"
    _create_rendered_files(rendered_dir, candidate)
    keyword = RecordingKeyword()
    embedding_screener = embedding or FakeEmbeddingScreener()
    records = build_records(
        [candidate],
        {"backend": {"original_job_description": "backend job description"}},
        rendered_dir=rendered_dir,
        keyword=keyword,
        embedding=embedding_screener,
        extractor=_extract_file,
    )
    return records, keyword, embedding_screener


def test_extracts_each_layout_and_screens_the_extracted_text(tmp_path):
    records, keyword, embedding = _run_with_fakes(tmp_path)
    assert len(records) == 12
    expected_texts = {
        f"extracted:{layout}:{file_format}:backend-candidate-001"
        for layout in LAYOUTS
        for file_format in FORMATS
    }
    assert set(keyword.inputs) == expected_texts
    assert set(embedding.model.inputs[:-1]) == expected_texts
    assert embedding.model.inputs[-1] == "backend job description"

    for record in records:
        assert record["experiment_id"] == EXPERIMENT_ID
        assert record["extraction_status"] == "completed"
        assert record["extracted_text_source"].endswith("extract_text")
        assert record["source_document_path"].endswith(
            f'{record["layout"]}/backend-candidate-001.{record["file_format"]}'
        )
        assert record["extracted_text_sha256"] == hashlib.sha256(
            f'extracted:{record["layout"]}:{record["file_format"]}:'
            "backend-candidate-001".encode("utf-8")
        ).hexdigest()


def test_result_ids_and_layout_pairs_are_unique_and_deterministic(tmp_path):
    records, _, _ = _run_with_fakes(tmp_path / "first")
    repeated, _, _ = _run_with_fakes(tmp_path / "second")
    assert [row["result_id"] for row in records] == [
        row["result_id"] for row in repeated
    ]
    assert len({row["result_id"] for row in records}) == 12

    for file_format in FORMATS:
        layout_records = [
            row
            for row in records
            if row["file_format"] == file_format and row["screener_id"] == "S2"
        ]
        assert {row["layout"] for row in layout_records} == set(LAYOUTS)
        assert len({row["pair_id"] for row in layout_records}) == 1
    assert len({row["pair_id"] for row in records}) == len(FORMATS)


def test_s2_computes_a_similarity_from_each_layout_input(tmp_path):
    records, _, embedding = _run_with_fakes(tmp_path)
    s2 = [row for row in records if row["screener_id"] == "S2"]
    by_condition = {
        (row["layout"], row["file_format"]): row["raw_similarity"]
        for row in s2
    }
    for file_format in FORMATS:
        assert by_condition[("one-column", file_format)] == 1.0
        assert by_condition[("two-column", file_format)] == 0.0
        assert by_condition[("table", file_format)] == -1.0
    assert all(row["score"] == row["raw_similarity"] for row in s2)
    assert all(row["score_scale"] == "raw_cosine_similarity_-1_to_1" for row in s2)
    assert len(embedding.model.inputs) == 7


def test_missing_artifact_is_recorded_for_both_screeners(tmp_path):
    candidate = _candidate()
    rendered_dir = tmp_path / "rendered"
    _create_rendered_files(rendered_dir, candidate)
    missing = (
        rendered_dir
        / "backend"
        / "table"
        / "backend-candidate-001.docx"
    )
    missing.unlink()

    records = build_records(
        [candidate],
        {"backend": {"original_job_description": "backend job description"}},
        rendered_dir=rendered_dir,
        keyword=RecordingKeyword(),
        embedding=FakeEmbeddingScreener(),
        extractor=_extract_file,
    )
    failed = [
        row
        for row in records
        if row["layout"] == "table"
        and row["file_format"] == "docx"
    ]
    assert {row["screener_id"] for row in failed} == {"S1", "S2"}
    assert all(row["status"] == "error" for row in failed)
    assert all(row["extraction_status"] == "error" for row in failed)
    assert all(row["screening_status"] == "not_run" for row in failed)
    assert all(row["error"]["type"] == "FileNotFoundError" for row in failed)
    assert len(records) == 12


def test_extraction_exception_is_not_silently_dropped(tmp_path):
    candidate = _candidate()
    rendered_dir = tmp_path / "rendered"
    _create_rendered_files(rendered_dir, candidate)

    def failing_extractor(path):
        if path.name.endswith(".pdf") and path.parent.name == "two-column":
            raise ValueError("unreadable test document")
        return _extract_file(path)

    records = build_records(
        [candidate],
        {"backend": {"original_job_description": "backend job description"}},
        rendered_dir=rendered_dir,
        keyword=RecordingKeyword(),
        embedding=FakeEmbeddingScreener(),
        extractor=failing_extractor,
    )
    failed = [
        row
        for row in records
        if row["layout"] == "two-column" and row["file_format"] == "pdf"
    ]
    assert len(failed) == 2
    assert all(row["status"] == "error" for row in failed)
    assert all(row["error"]["message"] == "unreadable test document" for row in failed)


def test_embedding_failure_is_recorded_without_blocking_s1(tmp_path):
    records, _, _ = _run_with_fakes(tmp_path, embedding=FakeEmbeddingScreener(fail=True))
    s1 = [row for row in records if row["screener_id"] == "S1"]
    s2 = [row for row in records if row["screener_id"] == "S2"]
    assert all(row["status"] == "completed" for row in s1)
    assert all(row["status"] == "error" for row in s2)
    assert all(row["error"]["stage"] == "screening" for row in s2)


def test_manifest_counts_extracted_documents_and_errors(tmp_path):
    records, _, embedding = _run_with_fakes(tmp_path)
    manifest = build_manifest(
        records,
        [_candidate()],
        "2026-01-01T00:00:00+00:00",
        "phase6-hash",
        embedding.model_name,
    )
    assert manifest["candidate_count"] == 1
    assert manifest["expected_documents"] == 6
    assert manifest["documents_extracted"] == 6
    assert manifest["results_record_count"] == 12
    assert manifest["unique_result_ids"] == 12
    assert manifest["errors"] == []


def test_runner_refuses_to_overwrite_versioned_outputs(tmp_path):
    results = tmp_path / "results.jsonl"
    manifest = tmp_path / "manifest.json"
    results.write_text("existing", encoding="utf-8")
    with pytest.raises(FileExistsError):
        run(results, manifest)
    assert results.read_text(encoding="utf-8") == "existing"
