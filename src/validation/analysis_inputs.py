"""Load and validate the immutable inputs used by the analysis engine."""

import hashlib
import json
import math
from collections import Counter
from pathlib import Path

from src.factory.resume_renderer import extract_text, load_candidates


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
PRIVATE_DIR = DATA_DIR / "private"
PHASE6_RESULTS = PRIVATE_DIR / "experiments" / "experiment_results.jsonl"
S2_NORMALIZED_RESULTS = (
    PRIVATE_DIR / "analysis" / "s2_role_reference_normalized_v1.jsonl"
)
E5_LAYOUT_RESULTS = PRIVATE_DIR / "analysis" / "e5_layout_aware_v1.jsonl"
EXPECTED_PHASE6_SHA256 = (
    "2433a2925afbf55bc1108a31da1bd53a28d1da982980a1150171626c4d18e4c4"
)
EXPECTED_EXPERIMENTS = (
    "E1",
    "E3_COLLEGE",
    "E3_PROJECT",
    "E5",
    "E7",
    "E9",
    "E10",
)
LAYOUTS = ("one-column", "two-column", "table")
FORMATS = ("pdf", "docx")
SCREENERS = ("S1", "S2")


class AnalysisInputError(ValueError):
    """Raised when a source dataset fails a required integrity check."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise AnalysisInputError(
                    f"Malformed JSON in {path} at line {line_number}"
                ) from error
    return records


def _validate_phase6(records: list[dict], digest: str) -> dict:
    if len(records) != 18000:
        raise AnalysisInputError(
            f"Expected 18,000 Phase 6 records; found {len(records)}"
        )
    result_ids = [record.get("result_id") for record in records]
    if None in result_ids or len(set(result_ids)) != len(result_ids):
        raise AnalysisInputError("Phase 6 result IDs are missing or duplicated")
    if digest != EXPECTED_PHASE6_SHA256:
        raise AnalysisInputError(
            "Phase 6 results hash differs from the audited original"
        )

    counts = Counter(
        (record.get("screener_id"), record.get("status"))
        for record in records
    )
    expected = {
        ("S1", "completed"): 6000,
        ("S2", "completed"): 6000,
        ("S3", "skipped"): 6000,
    }
    if dict(counts) != expected:
        raise AnalysisInputError(
            f"Unexpected Phase 6 screener statuses: {dict(counts)}"
        )

    experiment_ids = {record.get("experiment_id") for record in records}
    if experiment_ids != set(EXPECTED_EXPERIMENTS):
        raise AnalysisInputError(
            f"Unexpected Phase 6 experiments: {sorted(experiment_ids)}"
        )
    return {
        "record_count": len(records),
        "unique_result_ids": len(set(result_ids)),
        "status_counts": {
            f"{screener}|{status}": count
            for (screener, status), count in sorted(counts.items())
        },
        "sha256": digest,
    }


def _validate_s2_normalized(
    records: list[dict],
    original_records: list[dict],
) -> tuple[dict[str, dict], dict]:
    result_ids = [record.get("result_id") for record in records]
    if len(records) != 6600:
        raise AnalysisInputError(
            f"Expected 6,600 role-normalized S2 rows; found {len(records)}"
        )
    if None in result_ids or len(set(result_ids)) != len(result_ids):
        raise AnalysisInputError("Role-normalized S2 result IDs are duplicated")

    normalized_by_id = {record["result_id"]: record for record in records}
    original_s2 = [
        record
        for record in original_records
        if record["screener_id"] == "S2"
        and record["status"] == "completed"
    ]
    missing_ids = [
        record["result_id"]
        for record in original_s2
        if record["result_id"] not in normalized_by_id
    ]
    if missing_ids:
        raise AnalysisInputError(
            f"Role-normalized data omits {len(missing_ids)} original S2 rows"
        )

    references = {}
    for record in records:
        role = record["role"]
        reference = (
            float(record["reference_min"]),
            float(record["reference_max"]),
        )
        references.setdefault(role, set()).add(reference)
        raw = float(record["raw_similarity"])
        score = float(record["corrected_score"])
        if not math.isfinite(raw) or not -1.0 <= raw <= 1.0:
            raise AnalysisInputError("Invalid raw similarity in S2 data")
        minimum, maximum = reference
        if maximum == minimum:
            expected_score = 50.0
        else:
            expected_score = round(
                100 * (raw - minimum) / (maximum - minimum),
                2,
            )
        expected_score = max(0.0, min(100.0, expected_score))
        if score != expected_score:
            raise AnalysisInputError(
                f"Inconsistent role-normalized score for {role}"
            )
    if any(len(values) != 1 for values in references.values()):
        raise AnalysisInputError("S2 normalization references vary by role")

    base_references = {}
    for record in records:
        if record["experiment_id"] == "E1" and record["variant"] == "base":
            base_references.setdefault(record["role"], {})[
                record["candidate_id"]
            ] = float(record["raw_similarity"])
    if set(base_references) != {"backend", "full_stack", "data_analyst"}:
        raise AnalysisInputError("Missing S2 base references for a job role")
    for role, values in base_references.items():
        if len(values) != 100:
            raise AnalysisInputError(
                f"Expected 100 base candidates for S2 reference {role}"
            )
        reference_min, reference_max = next(iter(references[role]))
        if min(values.values()) != reference_min:
            raise AnalysisInputError(f"S2 reference minimum mismatch for {role}")
        if max(values.values()) != reference_max:
            raise AnalysisInputError(f"S2 reference maximum mismatch for {role}")

    legacy_e5_rows = [
        record for record in records if record["experiment_id"] == "E5"
    ]
    return normalized_by_id, {
        "record_count": len(records),
        "unique_result_ids": len(set(result_ids)),
        "original_s2_rows_covered": len(original_s2),
        "role_references": {
            role: {
                "candidate_count": len(values),
                "minimum": next(iter(references[role]))[0],
                "maximum": next(iter(references[role]))[1],
            }
            for role, values in sorted(base_references.items())
        },
        "legacy_e5_rows_excluded_from_e5_analysis": len(legacy_e5_rows),
        "legacy_e5_status": "superseded; never used for layout conclusions",
        "sha256": sha256_file(S2_NORMALIZED_RESULTS),
    }


def _validate_e5_layout(
    records: list[dict],
    candidates: list[dict],
) -> dict:
    candidate_by_id = {
        candidate["candidate_id"]: candidate for candidate in candidates
    }
    expected_keys = {
        (candidate_id, layout, file_format, screener)
        for candidate_id in candidate_by_id
        for layout in LAYOUTS
        for file_format in FORMATS
        for screener in SCREENERS
    }
    actual_keys = set()
    result_ids = []
    text_hashes = {}
    for record in records:
        key = (
            record.get("candidate_id"),
            record.get("layout"),
            record.get("file_format"),
            record.get("screener_id"),
        )
        if key in actual_keys:
            raise AnalysisInputError(f"Duplicate genuine E5 condition: {key}")
        actual_keys.add(key)
        result_ids.append(record.get("result_id"))
        if record.get("status") != "completed":
            raise AnalysisInputError("Genuine E5 data contains incomplete results")
        if record.get("extraction_status") != "completed":
            raise AnalysisInputError("Genuine E5 extraction is not complete")
        if record.get("screening_status") != "completed":
            raise AnalysisInputError("Genuine E5 screening is not complete")
        candidate = candidate_by_id.get(record["candidate_id"])
        if not candidate or candidate["job_id"] != record["job_id"]:
            raise AnalysisInputError("Genuine E5 role/candidate linkage is invalid")

        source_path = PROJECT_ROOT / record["source_document_path"]
        if not source_path.is_file():
            raise AnalysisInputError(
                f"Genuine E5 source document is missing: {source_path}"
            )
        extracted = extract_text(source_path)
        extracted_hash = hashlib.sha256(
            extracted.encode("utf-8")
        ).hexdigest()
        if extracted_hash != record.get("extracted_text_sha256"):
            raise AnalysisInputError(
                "Genuine E5 extracted-text hash does not match its document"
            )
        text_hash_key = (
            record["candidate_id"],
            record["layout"],
            record["file_format"],
        )
        previous_hash = text_hashes.setdefault(
            text_hash_key,
            record["extracted_text_sha256"],
        )
        if previous_hash != record["extracted_text_sha256"]:
            raise AnalysisInputError(
                "S1 and S2 records do not share the extracted document text"
            )
        if record["screener_id"] == "S1":
            if record.get("score") is None:
                raise AnalysisInputError("Genuine E5 S1 score is missing")
            if not isinstance(record.get("matched_skills"), list) or not isinstance(
                record.get("missing_skills"), list
            ):
                raise AnalysisInputError("Genuine E5 S1 skill fields are invalid")
        else:
            similarity = record.get("raw_similarity")
            if similarity is None or not math.isfinite(float(similarity)):
                raise AnalysisInputError("Genuine E5 S2 similarity is missing")
            if not -1.0 <= float(similarity) <= 1.0:
                raise AnalysisInputError("Genuine E5 S2 similarity is out of range")
            if float(record["score"]) != float(similarity):
                raise AnalysisInputError(
                    "Genuine E5 score is not the recorded raw similarity"
                )

    if len(records) != 3600 or actual_keys != expected_keys:
        raise AnalysisInputError(
            "Genuine E5 layout/format/screener coverage is incomplete"
        )
    if len(set(result_ids)) != len(result_ids):
        raise AnalysisInputError("Genuine E5 result IDs are duplicated")

    return {
        "record_count": len(records),
        "unique_result_ids": len(set(result_ids)),
        "candidate_count": len(candidates),
        "role_candidate_counts": dict(
            Counter(candidate["job_id"] for candidate in candidates)
        ),
        "layout_count": len(LAYOUTS),
        "format_count": len(FORMATS),
        "extraction_hashes_checked": len(text_hashes),
        "sha256": sha256_file(E5_LAYOUT_RESULTS),
    }


def load_analysis_datasets() -> dict:
    """Load authoritative files and verify their provenance and completeness."""
    original_records = read_jsonl(PHASE6_RESULTS)
    phase6_hash = sha256_file(PHASE6_RESULTS)
    phase6_audit = _validate_phase6(original_records, phase6_hash)

    candidates = load_candidates()
    if len(candidates) != 300:
        raise AnalysisInputError(
            f"Expected 300 base candidates; found {len(candidates)}"
        )
    candidate_ids = [candidate["candidate_id"] for candidate in candidates]
    if len(set(candidate_ids)) != len(candidate_ids):
        raise AnalysisInputError("Base candidate IDs are duplicated")
    role_counts = Counter(candidate["job_id"] for candidate in candidates)
    if role_counts != Counter(
        {"backend": 100, "full_stack": 100, "data_analyst": 100}
    ):
        raise AnalysisInputError("Base candidate role counts are not 100 each")
    if any(
        not isinstance(candidate.get("true_fit"), (int, float))
        or not math.isfinite(float(candidate["true_fit"]))
        for candidate in candidates
    ):
        raise AnalysisInputError("Base candidate True Fit values are invalid")

    normalized_s2_records = read_jsonl(S2_NORMALIZED_RESULTS)
    normalized_s2_by_id, s2_audit = _validate_s2_normalized(
        normalized_s2_records,
        original_records,
    )
    e5_records = read_jsonl(E5_LAYOUT_RESULTS)
    e5_audit = _validate_e5_layout(e5_records, candidates)

    candidate_hashes = {}
    for path in sorted((DATA_DIR / "generated").glob("*_candidates.json")):
        candidate_hashes[path.name] = sha256_file(path)

    return {
        "original_records": original_records,
        "normalized_s2_by_id": normalized_s2_by_id,
        "e5_layout_records": e5_records,
        "candidates": candidates,
        "audit": {
            "phase6": phase6_audit,
            "role_normalized_s2": s2_audit,
            "genuine_e5_layout": e5_audit,
            "candidate_role_counts": dict(sorted(role_counts.items())),
            "candidate_data_sha256": candidate_hashes,
        },
    }
