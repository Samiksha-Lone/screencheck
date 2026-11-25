"""experiment runner for the ScreenCheck resume screeners."""

import argparse
import copy
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.factory.resume_renderer import resume_text
from src.screeners.screeners import EmbeddingScreener, KeywordScreener, LLMJudge


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
TWINS_DIR = DATA_DIR / "private" / "twins"
OUTPUT_DIR = DATA_DIR / "private" / "experiments"

EXPERIMENTS = ("E1", "E3_COLLEGE", "E3_PROJECT", "E5", "E7", "E9", "E10")
SCREENERS = ("S1", "S2", "S3")

JOB_FILES = {
    "backend": "backend_software_engineer.json",
    "full_stack": "full_stack_developer.json",
    "data_analyst": "data_analyst.json",
}


def load_jobs() -> dict:
    jobs = {}
    for job_id, filename in JOB_FILES.items():
        with (DATA_DIR / filename).open("r", encoding="utf-8") as file:
            jobs[job_id] = json.load(file)
    return jobs


def load_pairs(experiment_id: str, pilot: bool = False) -> list[dict]:
    folder = experiment_id.lower()
    paths = sorted((TWINS_DIR / folder).glob("**/*.json"))
    pairs = []
    for path in paths:
        with path.open("r", encoding="utf-8") as file:
            pairs.append(json.load(file))
    pairs.sort(key=lambda pair: pair["pair_id"])

    if pilot:
        base_ids = []
        selected = []
        for pair in pairs:
            base_id = pair["base_candidate_id"]
            if base_id not in base_ids:
                base_ids.append(base_id)
                selected.append(pair)
                if len(base_ids) == 10:
                    break
    else:
        selected = pairs
    return selected


def variant_resume_text(candidate: dict, variant_id: str = "") -> str:
    """Convert one candidate variant into the same text representation."""
    text = resume_text(candidate)
    if candidate.get("keyword_stuffing", {}).get("visible"):
        terms = ", ".join(candidate["keyword_stuffing"]["terms"])
        text += "\nVisible Keyword List\n" + terms

    section_order = candidate.get("section_order")
    if section_order:
        sections = {
            "summary": candidate["job_title"],
            "skills": "Skills\n" + ", ".join(candidate["skills"]),
            "experience": "Experience\n"
            + "\n".join(
                item["summary"]
                for item in candidate.get("experience", [])
            ),
            "projects": "Projects\n"
            + "\n".join(
                f"{item['name']}: {item['description']} {item['details']}"
                for item in candidate.get("projects", [])
            ),
        }
        text = "\n".join(sections[key] for key in section_order)
    return text


def deterministic_result_id(
    experiment_id: str,
    pair_id: str,
    screener_id: str,
    variant_id: str,
    run_number: int,
) -> str:
    value = (
        f"{experiment_id}|{pair_id}|{screener_id}|"
        f"{variant_id}|{run_number}"
    )
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def result_record(
    *,
    experiment_id: str,
    pair_id: str,
    base_candidate_id: str,
    job_id: str,
    screener_id: str,
    variant_id: str,
    variant_type: str,
    run_number: int,
    score,
    status: str,
    explanation: str = "",
    matched_skills=None,
    missing_skills=None,
    model=None,
    error=None,
    similarity=None,
) -> dict:
    return {
        "result_id": deterministic_result_id(
            experiment_id,
            pair_id,
            screener_id,
            variant_id,
            run_number,
        ),
        "experiment_id": experiment_id,
        "pair_id": pair_id,
        "base_candidate_id": base_candidate_id,
        "job_id": job_id,
        "screener_id": screener_id,
        "variant_id": variant_id,
        "variant_type": variant_type,
        "run_number": run_number,
        "score": score,
        "status": status,
        "matched_skills": matched_skills or [],
        "missing_skills": missing_skills or [],
        "explanation": explanation,
        "model": model,
        "similarity": similarity,
        "error": error,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def load_completed(output_dir: Path) -> dict:
    result_path = output_dir / "experiment_results.jsonl"
    completed = {}
    if result_path.exists():
        with result_path.open("r", encoding="utf-8") as file:
            for line in file:
                if line.strip():
                    record = json.loads(line)
                    completed[record["result_id"]] = record
    return completed


def append_result(output_dir: Path, record: dict) -> None:
    result_path = output_dir / "experiment_results.jsonl"
    existing_ids = set()
    if result_path.exists():
        with result_path.open("r", encoding="utf-8") as file:
            for line in file:
                if line.strip():
                    existing_ids.add(json.loads(line)["result_id"])
    if record["result_id"] in existing_ids:
        return
    with result_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, sort_keys=True) + "\n")


def pair_variants(experiment_id: str, pair: dict) -> list[dict]:
    """Return baseline and variant resume inputs for one experiment pair."""
    if experiment_id == "E1":
        return [
            {
                "variant_id": "base",
                "variant_type": "baseline",
                "candidate": pair["base"],
            },
            {
                "variant_id": "group_a",
                "variant_type": "synthetic_group_a",
                "candidate": pair["comparison_variant"],
            },
            {
                "variant_id": "group_b",
                "variant_type": "synthetic_group_b",
                "candidate": pair["twin"],
            },
        ]

    if experiment_id == "E10":
        variant_type = pair["variant_type"]
        return [
            {
                "variant_id": pair["variant_type"],
                "variant_type": variant_type,
                "candidate": pair["twin"],
            }
        ]

    return [
        {
            "variant_id": "base",
            "variant_type": "baseline",
            "candidate": pair["base"],
        },
        {
            "variant_id": "twin",
            "variant_type": pair["variant_type"],
            "candidate": pair["twin"],
        },
    ]


class ExperimentRunner:
    def __init__(self, output_dir: str | Path = OUTPUT_DIR):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.jobs = load_jobs()
        self.completed = load_completed(self.output_dir)
        self.keyword = KeywordScreener()
        self.embedding = EmbeddingScreener(
            cache_dir=self.output_dir / "embedding_cache"
        )
        self.llm = LLMJudge(
            cache_path=self.output_dir / "llm_cache.json"
        )

    def configured_screeners(self, requested: list[str]) -> list[str]:
        if "S3" not in requested:
            return requested
        if self.llm.model or self.llm.api_key:
            return requested
        return requested

    def run_s1(
        self,
        experiment_id: str,
        pair: dict,
        variant: dict,
        run_number: int,
    ) -> dict:
        job = self.jobs[pair["base"]["job_id"]]
        text = variant_resume_text(variant["candidate"])
        result = self.keyword.score(text, job)
        return result_record(
            experiment_id=experiment_id,
            pair_id=pair["pair_id"],
            base_candidate_id=pair["base_candidate_id"],
            job_id=pair["base"]["job_id"],
            screener_id="S1",
            variant_id=variant["variant_id"],
            variant_type=variant["variant_type"],
            run_number=run_number,
            score=result["score"],
            status="completed",
            explanation=result["explanation"],
            matched_skills=result["matched_skills"],
            missing_skills=result["missing_skills"],
            model="screencheck-keyword-v1",
        )

    def run_s2(
        self,
        experiment_id: str,
        pair: dict,
        variant: dict,
        run_number: int,
    ) -> dict:
        job = self.jobs[pair["base"]["job_id"]]
        text = variant_resume_text(variant["candidate"])
        similarity = self.embedding.similarity(
            text, job["original_job_description"]
        )
        return result_record(
            experiment_id=experiment_id,
            pair_id=pair["pair_id"],
            base_candidate_id=pair["base_candidate_id"],
            job_id=pair["base"]["job_id"],
            screener_id="S2",
            variant_id=variant["variant_id"],
            variant_type=variant["variant_type"],
            run_number=run_number,
            score=None,
            status="pending_scaling",
            similarity=similarity,
            model=self.embedding.model_name,
        )

    def run_s3(
        self,
        experiment_id: str,
        pair: dict,
        variant: dict,
        run_number: int,
    ) -> dict:
        job = self.jobs[pair["base"]["job_id"]]
        text = variant_resume_text(variant["candidate"])
        try:
            result = self.llm.score(text, job)
            return result_record(
                experiment_id=experiment_id,
                pair_id=pair["pair_id"],
                base_candidate_id=pair["base_candidate_id"],
                job_id=pair["base"]["job_id"],
                screener_id="S3",
                variant_id=variant["variant_id"],
                variant_type=variant["variant_type"],
                run_number=run_number,
                score=result["score"],
                status="completed",
                explanation=result["reason"],
                model=result["model"],
            )
        except Exception as error:
            status = "skipped" if "No LLM configured" in str(error) else "error"
            return result_record(
                experiment_id=experiment_id,
                pair_id=pair["pair_id"],
                base_candidate_id=pair["base_candidate_id"],
                job_id=pair["base"]["job_id"],
                screener_id="S3",
                variant_id=variant["variant_id"],
                variant_type=variant["variant_type"],
                run_number=run_number,
                score=None,
                status=status,
                model=self.llm.model or "not-configured",
                error=str(error),
                explanation="LLM evaluation was not produced.",
            )

    def scale_embedding_scores(self) -> None:
        """Apply role-specific min-max scaling to all pending S2 records."""
        result_path = self.output_dir / "experiment_results.jsonl"
        if not result_path.exists():
            return

        records = []
        with result_path.open("r", encoding="utf-8") as file:
            for line in file:
                if line.strip():
                    records.append(json.loads(line))

        groups = {}
        for record in records:
            if record["screener_id"] == "S2" and record["status"] == "pending_scaling":
                groups.setdefault(record["job_id"], []).append(record)

        for role_records in groups.values():
            similarities = [record["similarity"] for record in role_records]
            scores = EmbeddingScreener.scale_scores(similarities)
            for record, score in zip(role_records, scores):
                record["score"] = score
                record["status"] = "completed"
                record["explanation"] = (
                    "Min-max scaled across this job/role experiment pool."
                )

        with result_path.open("w", encoding="utf-8") as file:
            for record in records:
                file.write(json.dumps(record, sort_keys=True) + "\n")

    def prepare_embedding_similarities(
        self,
        experiments: list[str],
        pilot: bool = False,
    ) -> None:
        """Batch precompute unique resume/job cosine similarities."""
        import numpy as np

        texts = set()
        for experiment_id in experiments:
            for pair in load_pairs(experiment_id, pilot=pilot):
                for variant in pair_variants(experiment_id, pair):
                    run_numbers = (
                        range(1, 6)
                        if experiment_id == "E10"
                        and variant["variant_type"] == "identical_control"
                        else (1,)
                    )
                    for run_number in run_numbers:
                        variant_id = (
                            "identical_repeat"
                            if experiment_id == "E10"
                            and variant["variant_type"] == "identical_control"
                            else variant["variant_id"]
                        )
                        result_id = deterministic_result_id(
                            experiment_id,
                            pair["pair_id"],
                            "S2",
                            variant_id,
                            run_number,
                        )
                        if result_id not in self.completed:
                            texts.add(variant_resume_text(variant["candidate"]))

        texts = sorted(texts)
        if not texts:
            return
        model = self.embedding._load_model()
        resume_embeddings = model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            batch_size=32,
            show_progress_bar=True,
        )

        for job_id, job in self.jobs.items():
            job_embedding = model.encode(
                [job["original_job_description"]],
                convert_to_numpy=True,
                normalize_embeddings=True,
            )[0]
            for text, resume_embedding in zip(texts, resume_embeddings):
                similarity = round(
                    max(
                        -1.0,
                        min(1.0, float(np.dot(resume_embedding, job_embedding))),
                    ),
                    6,
                )
                self.embedding._similarity_cache[
                    (text, job["original_job_description"])
                ] = similarity

    def run(
        self,
        experiments: list[str],
        screeners: list[str],
        pilot: bool = False,
        resume: bool = True,
    ) -> dict:
        summary = {
            "status_counts": {},
            "screeners": {},
            "experiments": {},
            "pilot": pilot,
        }

        if "S2" in screeners:
            self.prepare_embedding_similarities(experiments, pilot=pilot)

        for experiment_id in experiments:
            pairs = load_pairs(experiment_id, pilot=pilot)
            summary["experiments"][experiment_id] = {
                "pair_count": len(pairs),
                "completed": 0,
                "error": 0,
                "skipped": 0,
            }

            for pair in pairs:
                variants = pair_variants(experiment_id, pair)

                if experiment_id == "E10":
                    variants_to_run = []
                    for variant in variants:
                        if variant["variant_type"] == "identical_control":
                            for run_number in range(1, 6):
                                variants_to_run.append(
                                    {
                                        **variant,
                                        "run_number": run_number,
                                        "variant_id": "identical_repeat",
                                    }
                                )
                        else:
                            variants_to_run.append(
                                {**variant, "run_number": 1}
                            )
                else:
                    variants_to_run = [
                        {**variant, "run_number": 1}
                        for variant in variants
                    ]

                for variant in variants_to_run:
                    for screener_id in screeners:
                        if screener_id == "S1":
                            record = self.run_s1(
                                experiment_id,
                                pair,
                                variant,
                                variant["run_number"],
                            )
                        elif screener_id == "S2":
                            record = self.run_s2(
                                experiment_id,
                                pair,
                                variant,
                                variant["run_number"],
                            )
                        else:
                            record = self.run_s3(
                                experiment_id,
                                pair,
                                variant,
                                variant["run_number"],
                            )

                        if (
                            resume
                            and record["result_id"] in self.completed
                        ):
                            continue

                        append_result(self.output_dir, record)
                        if record["status"] == "completed":
                            summary["experiments"][experiment_id]["completed"] += 1
                        elif record["status"] == "error":
                            summary["experiments"][experiment_id]["error"] += 1
                        elif record["status"] in ("skipped", "pending_scaling"):
                            summary["experiments"][experiment_id]["skipped"] += 1

        self.scale_embedding_scores()

        all_records = []
        result_path = self.output_dir / "experiment_results.jsonl"
        if result_path.exists():
            with result_path.open("r", encoding="utf-8") as file:
                all_records = [
                    json.loads(line)
                    for line in file
                    if line.strip()
                ]

        status_counts = {}
        screener_counts = {}
        for record in all_records:
            status_counts[record["status"]] = status_counts.get(record["status"], 0) + 1
            screener_id = record["screener_id"]
            screener_counts.setdefault(screener_id, {})
            status = record["status"]
            screener_counts[screener_id][status] = (
                screener_counts[screener_id].get(status, 0) + 1
            )

        summary["status_counts"] = status_counts
        summary["screeners"] = screener_counts
        experiment_counts = {}
        for experiment_id in EXPERIMENTS:
            experiment_records = [
                record
                for record in all_records
                if record["experiment_id"] == experiment_id
            ]
            pair_count = len(
                {
                    record["pair_id"]
                    for record in experiment_records
                }
            )
            experiment_counts[experiment_id] = {
                "pair_count": pair_count,
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
        summary["experiments"] = experiment_counts
        summary["normalization"] = {
            "S2": "Cosine similarity min-max scaled independently within each job_id."
        }

        manifest_path = self.output_dir / "experiment_manifest.json"
        with manifest_path.open("w", encoding="utf-8") as file:
            json.dump(summary, file, indent=2)
        return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ScreenCheck Phase 6 experiments")
    parser.add_argument(
        "--experiments",
        nargs="+",
        choices=list(EXPERIMENTS),
        default=list(EXPERIMENTS),
    )
    parser.add_argument(
        "--screeners",
        nargs="+",
        choices=list(SCREENERS),
        default=list(SCREENERS),
    )
    parser.add_argument(
        "--pilot",
        action="store_true",
        help="Run only the first 10 base comparisons",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run the complete experiment set",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=True,
        help="Skip completed deterministic result IDs",
    )
    parser.add_argument(
        "--no-resume",
        action="store_false",
        dest="resume",
        help="Do not skip completed result IDs",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    runner = ExperimentRunner()
    summary = runner.run(
        experiments=args.experiments,
        screeners=args.screeners,
        pilot=args.pilot,
        resume=args.resume,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
