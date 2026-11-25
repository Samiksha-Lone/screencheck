"""Historical preparation of analysis datasets from Phase 6 results.

The generated two-column E5 records are superseded and must not be used for
layout-effect conclusions. The genuine extracted-text dataset is separate.
"""

import copy
import glob
import hashlib
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

from src.experiments.experiment_runner import (
    deterministic_result_id,
    variant_resume_text,
)
from src.factory.resume_renderer import resume_text
from src.screeners.screeners import EmbeddingScreener, KeywordScreener


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
ORIGINAL_RESULTS = DATA_DIR / "private" / "experiments" / "experiment_results.jsonl"
ANALYSIS_DIR = DATA_DIR / "private" / "analysis"
LOG_PATH = (
    DATA_DIR
    / "private"
    / "analysis"
    / "analysis_dataset_preparation_log.json"
)
TWINS_DIR = DATA_DIR / "private" / "twins"
SUPERSEDED_E5_PATH = (
    ANALYSIS_DIR / "e5_two_column_legacy_records_superseded.jsonl"
)
ROLE_NORMALIZED_S2_PATH = (
    ANALYSIS_DIR / "s2_role_reference_normalized_v1.jsonl"
)


def original_hash() -> str:
    return hashlib.sha256(ORIGINAL_RESULTS.read_bytes()).hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))
    return records


def load_jobs() -> dict:
    jobs = {}
    for job_id, filename in (
        ("backend", "backend_software_engineer.json"),
        ("full_stack", "full_stack_developer.json"),
        ("data_analyst", "data_analyst.json"),
    ):
        with (DATA_DIR / filename).open("r", encoding="utf-8") as file:
            jobs[job_id] = json.load(file)
    return jobs


def load_base_candidates() -> dict[tuple[str, str], dict]:
    candidates = {}
    for path in sorted((DATA_DIR / "generated").glob("*_candidates.json")):
        with path.open("r", encoding="utf-8") as file:
            dataset = json.load(file)
        for candidate in dataset["candidates"]:
            candidates[(candidate["job_id"], candidate["candidate_id"])] = candidate
    return candidates


def load_phase5_e5() -> tuple[list[dict], list[dict]]:
    paths = sorted((TWINS_DIR / "e5").glob("**/*.json"))
    pairs = []
    for path in paths:
        with path.open("r", encoding="utf-8") as file:
            pairs.append(json.load(file))
    two_column = [
        pair for pair in pairs if pair["twin"].get("layout") == "two-column"
    ]
    table = [pair for pair in pairs if pair["twin"].get("layout") == "table"]
    return two_column, table


def derive_raw_base_similarities(original_records: list[dict]) -> dict[tuple[str, str], list[float]]:
    """Collect raw S2 similarities from base-candidate variants only."""
    values = {}
    for record in original_records:
        if (
            record["screener_id"] != "S2"
            or record["status"] != "completed"
            or record.get("similarity") is None
        ):
            continue

        is_original_base = record["variant_id"] in ("base",)
        is_e10_base_run = (
            record["experiment_id"] == "E10"
            and record["variant_id"] == "identical_repeat"
            and record["run_number"] == 1
        )
        if not (is_original_base or is_e10_base_run):
            continue

        key = (record["job_id"], record["base_candidate_id"])
        values.setdefault(key, []).append(record["similarity"])
    return values


def build_superseded_e5_records(
    original_records: list[dict],
    role_reference: dict,
) -> tuple[list[dict], dict]:
    """Recreate historical E5 rows; these are not valid layout measurements."""
    two_column, table = load_phase5_e5()
    jobs = load_jobs()
    keyword = KeywordScreener()
    embedding = EmbeddingScreener()

    original_ids = {record["result_id"] for record in original_records}
    existing_e5 = [
        record
        for record in original_records
        if record["experiment_id"] == "E5"
    ]
    table_raw = {}
    table_s1 = {}
    for record in existing_e5:
        if "table" not in record["pair_id"]:
            continue
        key = (record["base_candidate_id"], record["variant_id"])
        if record["screener_id"] == "S2" and record.get("similarity") is not None:
            table_raw[key] = record["similarity"]
        if record["screener_id"] == "S1" and record["status"] == "completed":
            table_s1[key] = record

    legacy_records = []
    legacy_ids = set()
    role_counts = {}

    for pair in two_column:
        job_id = pair["base"]["job_id"]
        role_counts[job_id] = role_counts.get(job_id, 0) + 1

        for variant_id, candidate in (
            ("base", pair["base"]),
            ("twin", pair["twin"]),
        ):
            variant_text = variant_resume_text(candidate)
            job = jobs[job_id]

            s1_result = keyword.score(variant_text, job)
            s1_id = deterministic_result_id(
                "E5",
                pair["pair_id"],
                "S1",
                variant_id,
                1,
            )
            s1_record = {
                "result_id": s1_id,
                "experiment_id": "E5",
                "pair_id": pair["pair_id"],
                "base_candidate_id": pair["base_candidate_id"],
                "job_id": job_id,
                "screener_id": "S1",
                "variant_id": variant_id,
                "variant_type": "baseline" if variant_id == "base" else "two-column",
                "run_number": 1,
                "score": s1_result["score"],
                "status": "completed",
                "matched_skills": s1_result["matched_skills"],
                "missing_skills": s1_result["missing_skills"],
                "explanation": s1_result["explanation"],
                "model": "screencheck-keyword-v1",
                "similarity": None,
                "error": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "repair": "phase7.1-e5-two-column",
            }

            s2_id = deterministic_result_id(
                "E5",
                pair["pair_id"],
                "S2",
                variant_id,
                1,
            )
            table_key = (pair["base_candidate_id"], variant_id)
            if table_key not in table_raw:
                raise RuntimeError(
                    f"Missing existing table raw S2 similarity for {table_key}"
                )
            similarity = table_raw[table_key]
            minimum = role_reference[job_id]["min"]
            maximum = role_reference[job_id]["max"]
            if maximum == minimum:
                corrected_score = 50.0
            else:
                corrected_score = round(
                    100 * (similarity - minimum) / (maximum - minimum),
                    2,
                )
            s2_record = {
                "result_id": s2_id,
                "experiment_id": "E5",
                "pair_id": pair["pair_id"],
                "base_candidate_id": pair["base_candidate_id"],
                "job_id": job_id,
                "screener_id": "S2",
                "variant_id": variant_id,
                "variant_type": "baseline" if variant_id == "base" else "two-column",
                "run_number": 1,
                "score": corrected_score,
                "status": "completed",
                "matched_skills": [],
                "missing_skills": [],
                "explanation": "Raw cosine similarity retained for Phase 7.1 corrected normalization.",
                "model": embedding.model_name,
                "similarity": similarity,
                "corrected_score": corrected_score,
                "reference_min": minimum,
                "reference_max": maximum,
                "error": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "repair": "phase7.1-e5-two-column",
            }

            for record in (s1_record, s2_record):
                if (
                    record["result_id"] in original_ids
                    or record["result_id"] in legacy_ids
                ):
                    raise RuntimeError("Duplicate legacy E5 result ID")
                legacy_ids.add(record["result_id"])
                legacy_records.append(record)

    summary = {
        "two_column_pairs": len(two_column),
        "table_pairs": len(table),
        "role_counts": dict(sorted(role_counts.items())),
        "legacy_record_count": len(legacy_records),
        "s1_record_count": sum(
            r["screener_id"] == "S1" for r in legacy_records
        ),
        "s2_record_count": sum(
            r["screener_id"] == "S2" for r in legacy_records
        ),
    }
    return legacy_records, summary


def build_role_reference_normalized_s2(
    original_records: list[dict],
    extra_records: list[dict] | None = None,
) -> tuple[list[dict], dict]:
    base_values = derive_raw_base_similarities(original_records)
    role_reference = {}

    for role in sorted({job_id for job_id, _ in base_values}):
        keys = [(job_id, candidate_id) for job_id, candidate_id in base_values if job_id == role]
        if len(keys) != 100:
            raise RuntimeError(
                f"Expected 100 unique base candidates for {role}, found {len(keys)}"
            )
        similarities = []
        for key in keys:
            observations = set(round(value, 6) for value in base_values[key])
            # Each true base content has many repeat representations.
            # One-micro-unit differences are floating/output rounding only.
            exact_consensus = round(statistics.median(observations), 6)
            if any(abs(value - exact_consensus) > 0.000002 for value in observations):
                raise RuntimeError(
                    f"Duplicate raw S2 observations materially disagree for {key}: {observations}"
                )
            similarities.append(exact_consensus)

        minimum = min(similarities)
        maximum = max(similarities)
        role_reference[role] = {"min": minimum, "max": maximum, "count": len(similarities)}

    normalized_records = []
    analysis_records = list(original_records) + list(extra_records or [])
    for record in analysis_records:
        if (
            record["screener_id"] != "S2"
            or record["status"] != "completed"
            or record.get("similarity") is None
        ):
            continue
        role = record["job_id"]
        candidate_id = record.get("base_candidate_id") or record.get("candidate_id")
        minimum = role_reference[role]["min"]
        maximum = role_reference[role]["max"]
        if maximum == minimum:
            normalized = 50.0
        else:
            normalized = round(
                100 * (record["similarity"] - minimum) / (maximum - minimum),
                2,
            )
        normalized = max(0.0, min(100.0, normalized))
        normalized_records.append(
            {
                "candidate_id": candidate_id,
                "role": role,
                "experiment_id": record["experiment_id"],
                "variant": record["variant_id"],
                "variant_type": record["variant_type"],
                "pair_id": record["pair_id"],
                "run_number": record["run_number"],
                "raw_similarity": record["similarity"],
                "corrected_score": normalized,
                "reference_min": minimum,
                "reference_max": maximum,
                "model": record["model"],
                "result_id": record["result_id"],
            }
        )

    return normalized_records, role_reference


def main() -> dict:
    if SUPERSEDED_E5_PATH.exists() or ROLE_NORMALIZED_S2_PATH.exists():
        raise FileExistsError(
            "Refusing to overwrite preserved analysis datasets"
        )
    pre_hash = original_hash()
    original_records = load_jsonl(ORIGINAL_RESULTS)
    if len(original_records) != 18000:
        raise RuntimeError(
            f"Original Phase 6 result count changed: {len(original_records)}"
        )
    if len({record["result_id"] for record in original_records}) != 18000:
        raise RuntimeError("Original Phase 6 result IDs are duplicated")

    normalized_s2, role_reference = build_role_reference_normalized_s2(
        original_records
    )
    superseded_e5_records, e5_summary = build_superseded_e5_records(
        original_records,
        role_reference,
    )
    legacy_s2_records = [
        record
        for record in superseded_e5_records
        if record["screener_id"] == "S2"
    ]

    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    with SUPERSEDED_E5_PATH.open("w", encoding="utf-8") as file:
        for record in superseded_e5_records:
            file.write(json.dumps(record, sort_keys=True) + "\n")

    legacy_normalized_s2 = []
    for record in legacy_s2_records:
        minimum = record["reference_min"]
        maximum = record["reference_max"]
        raw = record["similarity"]
        corrected_score = record["corrected_score"]
        legacy_normalized_s2.append(
            {
                "candidate_id": record["base_candidate_id"],
                "role": record["job_id"],
                "experiment_id": record["experiment_id"],
                "variant": record["variant_id"],
                "variant_type": record["variant_type"],
                "pair_id": record["pair_id"],
                "run_number": record["run_number"],
                "raw_similarity": raw,
                "corrected_score": corrected_score,
                "reference_min": minimum,
                "reference_max": maximum,
                "model": record["model"],
                "result_id": record["result_id"],
            }
        )

    with ROLE_NORMALIZED_S2_PATH.open("w", encoding="utf-8") as file:
        for record in normalized_s2:
            file.write(json.dumps(record, sort_keys=True) + "\n")
        for record in legacy_normalized_s2:
            file.write(json.dumps(record, sort_keys=True) + "\n")

    post_hash = original_hash()
    if post_hash != pre_hash:
        raise RuntimeError("Original Phase 6 results file changed during repair")

    log = {}
    if LOG_PATH.exists():
        with LOG_PATH.open("r", encoding="utf-8") as file:
            log = json.load(file)
    log.update(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "original_results_sha256_before": pre_hash,
            "original_results_sha256_after": post_hash,
            "original_results_count": len(original_records),
            "hash_unchanged": pre_hash == post_hash,
            "defects": [
                "Phase 6 omitted E5 two-column comparisons.",
                "Old E5 result IDs omitted pair ID and could collide across layouts.",
                "Saved S2 0-100 scores include incomplete batch scaling.",
            ],
            "superseded_e5_generation": e5_summary,
            "id_generation": (
                "SHA-256 of experiment_id|pair_id|screener_id|variant_id|run_number"
            ),
            "s2_repair": {
                "method": (
                    "100 unique original base candidates per role; raw similarity "
                    "min/max role reference; 100*(raw-min)/(max-min)"
                ),
                "reference": role_reference,
                "normalized_record_count": len(normalized_s2),
                "derived_dataset": str(ROLE_NORMALIZED_S2_PATH),
                "superseded_e5_dataset": str(SUPERSEDED_E5_PATH),
            },
            "e5_layout_status": (
                "Superseded: legacy S1 inputs bypassed layout extraction and "
                "legacy S2 similarities were reused from table-layout records."
            ),
            "original_file_preserved": pre_hash == post_hash,
        }
    )
    with LOG_PATH.open("w", encoding="utf-8") as file:
        json.dump(log, file, indent=2)

    return {
        "original_hash": pre_hash,
        "superseded_e5_generation": e5_summary,
        "normalized_s2_count": len(normalized_s2)
        + len(legacy_normalized_s2),
        "role_reference": role_reference,
    }


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
