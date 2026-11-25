"""Run E5 against text extracted from existing rendered resume layouts."""

import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from src.experiments.experiment_runner import load_jobs
from src.factory.resume_renderer import (
    DEFAULT_OUTPUT_DIR,
    extract_text,
    load_candidates,
)
from src.screeners.screeners import EmbeddingScreener, KeywordScreener


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
EXPERIMENT_ID = "E5_LAYOUT_AWARE_V1"
LAYOUTS = ("one-column", "two-column", "table")
FORMATS = ("pdf", "docx")
RESULTS_PATH = DATA_DIR / "private" / "analysis" / "e5_layout_aware_v1.jsonl"
MANIFEST_PATH = (
    DATA_DIR / "private" / "analysis" / "e5_layout_aware_v1_manifest.json"
)
PHASE6_RESULTS_PATH = (
    DATA_DIR / "private" / "experiments" / "experiment_results.jsonl"
)
EXTRACTION_METHOD = "src.factory.resume_renderer.extract_text"


def _sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _result_id(
    candidate_id: str,
    job_id: str,
    layout: str,
    file_format: str,
    screener_id: str,
) -> str:
    identity = "|".join(
        (
            EXPERIMENT_ID,
            candidate_id,
            job_id,
            file_format,
            layout,
            screener_id,
            "1",
        )
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def _source_path(
    candidate: dict,
    layout: str,
    file_format: str,
    rendered_dir: Path,
) -> Path:
    return (
        rendered_dir
        / candidate["job_id"]
        / layout
        / f'{candidate["candidate_id"]}.{file_format}'
    )


def _extract_documents(
    candidates: list[dict],
    rendered_dir: Path,
    extractor=None,
) -> list[dict]:
    text_extractor = extractor or extract_text
    documents = []

    for candidate in sorted(candidates, key=lambda item: item["candidate_id"]):
        for layout in LAYOUTS:
            for file_format in FORMATS:
                source_path = _source_path(
                    candidate,
                    layout,
                    file_format,
                    rendered_dir,
                )
                document = {
                    "candidate_id": candidate["candidate_id"],
                    "job_id": candidate["job_id"],
                    "layout": layout,
                    "file_format": file_format,
                    "pair_id": (
                        f"{EXPERIMENT_ID}:{candidate['job_id']}:"
                        f"{candidate['candidate_id']}:{file_format}"
                    ),
                    "source_document_path": (
                        source_path.relative_to(PROJECT_ROOT).as_posix()
                        if source_path.is_relative_to(PROJECT_ROOT)
                        else source_path.resolve().as_posix()
                    ),
                    "source_document_id": (
                        f"{candidate['candidate_id']}:{layout}:{file_format}"
                    ),
                    "extracted_text_source": EXTRACTION_METHOD,
                    "extracted_text": None,
                    "extracted_text_sha256": None,
                    "extraction_status": "error",
                    "extraction_error": None,
                }
                try:
                    if not source_path.is_file():
                        raise FileNotFoundError(
                            f"Rendered document not found: {source_path}"
                        )
                    extracted = text_extractor(source_path)
                    if not isinstance(extracted, str) or not extracted.strip():
                        raise ValueError("Document extraction returned no text")
                    document["extracted_text"] = extracted
                    document["extracted_text_sha256"] = hashlib.sha256(
                        extracted.encode("utf-8")
                    ).hexdigest()
                    document["extraction_status"] = "completed"
                except Exception as error:
                    document["extraction_error"] = {
                        "type": type(error).__name__,
                        "message": str(error),
                    }
                documents.append(document)

    return documents


def _base_result(document: dict, screener_id: str) -> dict:
    return {
        "result_id": _result_id(
            document["candidate_id"],
            document["job_id"],
            document["layout"],
            document["file_format"],
            screener_id,
        ),
        "experiment_id": EXPERIMENT_ID,
        "pair_id": document["pair_id"],
        "base_candidate_id": document["candidate_id"],
        "candidate_id": document["candidate_id"],
        "job_id": document["job_id"],
        "layout": document["layout"],
        "variant_id": document["layout"],
        "variant_type": "resume_layout",
        "file_format": document["file_format"],
        "source_document_path": document["source_document_path"],
        "source_document_id": document["source_document_id"],
        "extracted_text_source": document["extracted_text_source"],
        "extracted_text_sha256": document["extracted_text_sha256"],
        "extraction_status": document["extraction_status"],
        "screener_id": screener_id,
        "run_number": 1,
        "score": None,
        "similarity": None,
        "raw_similarity": None,
        "score_scale": None,
        "matched_skills": [],
        "missing_skills": [],
        "explanation": "",
        "model": None,
        "screening_status": "not_run",
        "status": "error" if document["extraction_status"] != "completed" else "pending",
        "error": (
            {
                "stage": "extraction",
                **document["extraction_error"],
            }
            if document["extraction_error"]
            else None
        ),
    }


def _screen_keyword(document: dict, job: dict, keyword: KeywordScreener) -> dict:
    record = _base_result(document, "S1")
    record["model"] = "screencheck-keyword-v1"
    if document["extraction_status"] != "completed":
        return record

    try:
        result = keyword.score(document["extracted_text"], job)
        record.update(
            {
                "score": result["score"],
                "matched_skills": result["matched_skills"],
                "missing_skills": result["missing_skills"],
                "explanation": result["explanation"],
                "screening_status": "completed",
                "status": "completed",
                "error": None,
            }
        )
    except Exception as error:
        record.update(
            {
                "screening_status": "error",
                "status": "error",
                "error": {
                    "stage": "screening",
                    "type": type(error).__name__,
                    "message": str(error),
                },
            }
        )
    return record


def _screen_embeddings(
    documents: list[dict],
    jobs: dict,
    embedding: EmbeddingScreener,
) -> dict[str, dict]:
    """Encode every extracted document, then calculate each cosine score."""
    completed_documents = [
        document
        for document in documents
        if document["extraction_status"] == "completed"
    ]
    job_ids = sorted({document["job_id"] for document in completed_documents})
    model_name = embedding.model_name
    results = {}

    for document in documents:
        if document["extraction_status"] != "completed":
            record = _base_result(document, "S2")
            record["model"] = model_name
            results[document["source_document_id"]] = record

    if not completed_documents:
        return results

    try:
        model = embedding._load_model()
        texts = [document["extracted_text"] for document in completed_documents]
        job_texts = [jobs[job_id]["original_job_description"] for job_id in job_ids]
        vectors = model.encode(
            texts + job_texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        if len(vectors) != len(texts) + len(job_texts):
            raise ValueError("Embedding model returned an unexpected vector count")
    except Exception as error:
        for document in completed_documents:
            record = _base_result(document, "S2")
            record.update(
                {
                    "model": model_name,
                    "screening_status": "error",
                    "status": "error",
                    "error": {
                        "stage": "screening",
                        "type": type(error).__name__,
                        "message": str(error),
                    },
                }
            )
            results[document["source_document_id"]] = record
        return results

    job_vector_indices = {
        job_id: len(completed_documents) + index
        for index, job_id in enumerate(job_ids)
    }
    for index, document in enumerate(completed_documents):
        record = _base_result(document, "S2")
        try:
            similarity = float(
                np.dot(vectors[index], vectors[job_vector_indices[document["job_id"]]])
            )
            if not math.isfinite(similarity):
                raise ValueError("Embedding model returned a non-finite similarity")
            similarity = round(max(-1.0, min(1.0, similarity)), 6)
            record.update(
                {
                    "score": similarity,
                    "similarity": similarity,
                    "raw_similarity": similarity,
                    "score_scale": "raw_cosine_similarity_-1_to_1",
                    "model": model_name,
                    "screening_status": "completed",
                    "status": "completed",
                    "error": None,
                }
            )
        except Exception as error:
            record.update(
                {
                    "model": model_name,
                    "screening_status": "error",
                    "status": "error",
                    "error": {
                        "stage": "screening",
                        "type": type(error).__name__,
                        "message": str(error),
                    },
                }
            )
        results[document["source_document_id"]] = record

    return results


def build_records(
    candidates: list[dict],
    jobs: dict,
    rendered_dir: str | Path = DEFAULT_OUTPUT_DIR,
    keyword: KeywordScreener | None = None,
    embedding: EmbeddingScreener | None = None,
    extractor=None,
) -> list[dict]:
    """Extract and screen all candidate/layout/format combinations."""
    candidate_ids = [candidate["candidate_id"] for candidate in candidates]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("Candidate IDs must be unique")

    documents = _extract_documents(
        candidates,
        Path(rendered_dir),
        extractor=extractor,
    )
    keyword_screener = keyword or KeywordScreener()
    embedding_screener = embedding or EmbeddingScreener()
    s1_records = [
        _screen_keyword(document, jobs[document["job_id"]], keyword_screener)
        for document in documents
    ]
    s2_records = _screen_embeddings(documents, jobs, embedding_screener)

    records = []
    for document, s1_record in zip(documents, s1_records):
        records.extend(
            (
                s1_record,
                s2_records[document["source_document_id"]],
            )
        )

    result_ids = [record["result_id"] for record in records]
    if len(result_ids) != len(set(result_ids)):
        raise ValueError("Generated duplicate result IDs")
    expected_records = len(candidates) * len(LAYOUTS) * len(FORMATS) * 2
    if len(records) != expected_records:
        raise ValueError(
            f"Expected {expected_records} result records, generated {len(records)}"
        )
    return records


def build_manifest(
    records: list[dict],
    candidates: list[dict],
    generated_at: str,
    phase6_sha256: str | None,
    model_name: str,
) -> dict:
    by_condition = Counter(
        (
            record["layout"],
            record["file_format"],
            record["screener_id"],
            record["status"],
        )
        for record in records
    )
    by_role = Counter(
        (record["job_id"], record["layout"], record["file_format"], record["screener_id"], record["status"])
        for record in records
    )
    return {
        "experiment_id": EXPERIMENT_ID,
        "generated_at": generated_at,
        "candidate_count": len(candidates),
        "expected_documents": len(candidates) * len(LAYOUTS) * len(FORMATS),
        "documents_extracted": sum(
            record["screener_id"] == "S1"
            and record["extraction_status"] == "completed"
            for record in records
        ),
        "results_record_count": len(records),
        "unique_result_ids": len({record["result_id"] for record in records}),
        "layouts": list(LAYOUTS),
        "file_formats": list(FORMATS),
        "screeners": ["S1", "S2"],
        "extraction_method": EXTRACTION_METHOD,
        "s2_model": model_name,
        "s2_score_scale": "raw cosine similarity in [-1, 1]; no pool normalization",
        "phase6_results_sha256": phase6_sha256,
        "by_condition": {
            "|".join(key): value for key, value in sorted(by_condition.items())
        },
        "by_role": {
            "|".join(key): value for key, value in sorted(by_role.items())
        },
        "errors": [
            {
                "result_id": record["result_id"],
                "candidate_id": record["candidate_id"],
                "job_id": record["job_id"],
                "layout": record["layout"],
                "file_format": record["file_format"],
                "screener_id": record["screener_id"],
                "error": record["error"],
            }
            for record in records
            if record["status"] == "error"
        ],
    }


def run(
    results_path: str | Path = RESULTS_PATH,
    manifest_path: str | Path = MANIFEST_PATH,
    rendered_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict:
    results_path = Path(results_path)
    manifest_path = Path(manifest_path)
    if results_path.exists() or manifest_path.exists():
        raise FileExistsError(
            "Refusing to overwrite an existing versioned E5 output"
        )

    candidates = load_candidates()
    jobs = load_jobs()
    phase6_hash_before = _sha256_file(PHASE6_RESULTS_PATH)
    keyword = KeywordScreener()
    embedding = EmbeddingScreener()
    records = build_records(
        candidates,
        jobs,
        rendered_dir=rendered_dir,
        keyword=keyword,
        embedding=embedding,
    )
    generated_at = datetime.now(timezone.utc).isoformat()
    manifest = build_manifest(
        records,
        candidates,
        generated_at,
        phase6_hash_before,
        embedding.model_name,
    )

    results_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    phase6_hash_after = _sha256_file(PHASE6_RESULTS_PATH)
    if phase6_hash_after != phase6_hash_before:
        raise RuntimeError("The original Phase 6 results hash changed during the run")
    manifest["phase6_results_sha256_after"] = phase6_hash_after
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run layout-aware E5 against existing rendered resumes."
    )
    parser.add_argument("--results", type=Path, default=RESULTS_PATH)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--rendered-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    manifest = run(args.results, args.manifest, args.rendered_dir)
    print(
        json.dumps(
            {
                "results_path": str(args.results),
                "manifest_path": str(args.manifest),
                "result_record_count": manifest["results_record_count"],
                "documents_extracted": manifest["documents_extracted"],
                "error_count": len(manifest["errors"]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
