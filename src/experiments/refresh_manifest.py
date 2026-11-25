"""Refresh the Phase 6 manifest from the existing JSONL result file."""

import collections
import json
from pathlib import Path


OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "private" / "experiments"


def main() -> None:
    records = []
    with (OUTPUT_DIR / "experiment_results.jsonl").open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))

    statuses = collections.Counter(record["status"] for record in records)
    screener_statuses = collections.Counter(
        (record["screener_id"], record["status"]) for record in records
    )
    experiments = {}
    experiment_ids = (
        "E1",
        "E3_COLLEGE",
        "E3_PROJECT",
        "E5",
        "E7",
        "E9",
        "E10",
    )
    for experiment_id in experiment_ids:
        experiment_records = [
            record
            for record in records
            if record["experiment_id"] == experiment_id
        ]
        experiments[experiment_id] = {
            "pair_count": len(
                {record["pair_id"] for record in experiment_records}
            ),
            "completed": sum(
                record["status"] == "completed"
                for record in experiment_records
            ),
            "error": sum(
                record["status"] == "error"
                for record in experiment_records
            ),
            "skipped": sum(
                record["status"] == "skipped"
                for record in experiment_records
            ),
        }

    screeners = {}
    for screener_id in ("S1", "S2", "S3"):
        screeners[screener_id] = {
            status: screener_statuses[(screener_id, status)]
            for status in ("completed", "skipped", "pending_scaling", "error")
            if screener_statuses[(screener_id, status)]
        }

    manifest = {
        "pilot": False,
        "status_counts": dict(statuses),
        "screeners": screeners,
        "experiments": experiments,
        "normalization": {
            "S2": (
                "Cosine similarity min-max scaled independently "
                "within each job_id."
            )
        },
    }
    with (OUTPUT_DIR / "experiment_manifest.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(manifest, file, indent=2)


if __name__ == "__main__":
    main()
