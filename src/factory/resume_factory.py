"""Generate deterministic synthetic candidate data for ScreenCheck."""

import json
import random
from datetime import date
from pathlib import Path
from typing import Iterable

from src.factory.true_fit import calculate_true_fit


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

JOB_FILES = {
    "backend": ("backend_software_engineer.json", "backend_candidates.json"),
    "full_stack": ("full_stack_developer.json", "full_stack_candidates.json"),
    "data_analyst": ("data_analyst.json", "data_analyst_candidates.json"),
}

FIRST_NAMES = [
    "Aarav",
    "Anika",
    "Dev",
    "Isha",
    "Kabir",
    "Mira",
    "Nikhil",
    "Priya",
    "Rohan",
    "Sara",
]

LAST_NAMES = [
    "Mehta",
    "Shah",
    "Patel",
    "Rao",
    "Kapoor",
    "Iyer",
    "Singh",
    "Verma",
]


def load_job_definition(job_key: str) -> dict:
    """Load one of the three job definitions."""
    if job_key not in JOB_FILES:
        raise ValueError("unknown job key: " + str(job_key))

    job_file, _ = JOB_FILES[job_key]
    with (DATA_DIR / job_file).open("r", encoding="utf-8") as file:
        return json.load(file)


def _choose_skills(rng: random.Random, skills: list[str], count: int) -> list[str]:
    """Choose a count of skills without duplicates."""
    chosen = list(skills)
    rng.shuffle(chosen)
    return chosen[:count]


def _project_for_job(job_key: str, evidence: int, rng: random.Random) -> dict:
    """Create a fictional project consistent with the selected job."""
    projects = {
        "backend": [
            "Inventory API",
            "Task Queue Service",
            "Library Checkout API",
            "Order Tracking Service",
        ],
        "full_stack": [
            "Community Board",
            "Project Dashboard",
            "Book Exchange Portal",
            "Volunteer Scheduling App",
        ],
        "data_analyst": [
            "Retail Sales Analysis",
            "Student Enrollment Dashboard",
            "Customer Support Trends",
            "Public Transit Usage Report",
        ],
    }

    name = rng.choice(projects[job_key])
    if evidence == 10:
        detail = "Documented implementation, tests, deployment details, and measured outcomes."
    elif evidence == 5:
        detail = "Clear implementation and a short written summary of the approach."
    else:
        detail = "Listed only as an introductory learning project without supporting details."

    return {
        "name": name,
        "description": "A fictional synthetic project used for research testing.",
        "details": detail,
    }


def _candidate_name(rng: random.Random) -> str:
    return rng.choice(FIRST_NAMES) + " " + rng.choice(LAST_NAMES)


def generate_candidates(
    job_key: str | dict,
    count: int = 100,
    seed: int = 42,
    generation_date: str | None = None,
) -> dict:
    """Generate candidates for one job using a local random generator."""
    rng = random.Random(seed)
    if isinstance(job_key, dict):
        job = job_key
        job_id = str(job.get("job_id") or job["job_title"].lower().replace(" ", "_"))
        resolved_job_key = next(
            (
                key
                for key, (job_file, _) in JOB_FILES.items()
                if json.loads((DATA_DIR / job_file).read_text(encoding="utf-8"))["job_title"]
                == job["job_title"]
            ),
            "backend",
        )
    else:
        job = load_job_definition(job_key)
        job_id = job_key
        resolved_job_key = job_key

    must_have = list(job["must_have_skills"])
    nice_have = list(job["nice_to_have_skills"])
    generated_date = generation_date or date(2026, 11, 25).isoformat()

    candidates = []
    for index in range(1, count + 1):
        tier_position = (index - 1) % count
        if tier_position < count * 0.34:
            tier = "strong"
        elif tier_position < count * 0.67:
            tier = "medium"
        else:
            tier = "weak"

        if tier == "strong":
            must_count = rng.randint(max(1, len(must_have) - 1), len(must_have))
            nice_count = rng.randint(2, len(nice_have))
            project_evidence = rng.choice([5, 10])
        elif tier == "medium":
            must_count = rng.randint(max(2, len(must_have) // 2), len(must_have) - 1)
            must_count = min(must_count, len(must_have))
            nice_count = rng.randint(1, max(1, len(nice_have) // 2))
            project_evidence = rng.choice([0, 5])
        else:
            must_count = rng.randint(2, max(2, len(must_have) // 2))
            must_count = min(must_count, len(must_have))
            nice_count = rng.randint(0, 1) if nice_have else 0
            project_evidence = rng.choice([0, 5])

        selected_must = _choose_skills(rng, must_have, must_count)
        selected_nice = _choose_skills(rng, nice_have, nice_count)
        skills = selected_must + selected_nice
        skills = list(dict.fromkeys(normalize_skill_list(skills)))

        true_fit = calculate_true_fit(
            skills,
            must_have,
            nice_have,
            project_evidence,
        )

        # Avoid perfect or implausibly high scores while preserving valid evidence.
        if true_fit > 95:
            project_evidence = 5 if 5 in (5, project_evidence) else 0
            true_fit = calculate_true_fit(
                skills,
                must_have,
                nice_have,
                project_evidence,
            )

        years = rng.randint(1, 8)
        candidate_name = _candidate_name(rng)

        candidates.append(
            {
                "candidate_id": f"{job_id}-candidate-{index:03d}",
                "name": candidate_name,
                "job_id": job_id,
                "job_title": job["job_title"],
                "tier": tier,
                "skills": skills,
                "experience": [
                    {
                        "title": _experience_title(resolved_job_key),
                        "organization": "Fictional " + rng.choice(
                            ["Digital Studio", "Learning Lab", "Technology Group"]
                        ),
                        "years": years,
                        "summary": "Fictional experience using " + ", ".join(skills[:3]) + ".",
                    }
                ],
                "projects": [_project_for_job(resolved_job_key, project_evidence, rng)],
                "project_evidence": project_evidence,
                "true_fit": true_fit,
            }
        )

    return {
        "metadata": {
            "job_id": job_id,
            "job_title": job["job_title"],
            "seed": seed,
            "generation_date": generated_date,
            "candidate_count": count,
            "synthetic": True,
        },
        "candidates": candidates,
    }


def normalize_skill_list(skills: Iterable[str]) -> list[str]:
    """Normalize a skill list while preserving list order."""
    from src.factory.skill_normalizer import normalize_skill

    normalized = []
    for skill in skills:
        clean_skill = normalize_skill(skill)
        if clean_skill and clean_skill not in normalized:
            normalized.append(clean_skill)
    return normalized


def _experience_title(job_key: str) -> str:
    titles = {
        "backend": "Fictional Backend Developer",
        "full_stack": "Fictional Full-Stack Developer",
        "data_analyst": "Fictional Data Analyst",
    }
    return titles[job_key]


def save_generated_datasets(
    seed: int = 42,
    data_dir: str | Path | None = None,
    generation_date: str | None = None,
) -> list[Path]:
    """Generate and save all three candidate datasets."""
    output_dir = Path(data_dir) if data_dir is not None else DATA_DIR / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)

    saved_files = []
    for job_key, (_, output_file) in JOB_FILES.items():
        dataset = generate_candidates(
            job_key,
            count=100,
            seed=seed,
            generation_date=generation_date,
        )
        output_path = output_dir / output_file
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(dataset, file, indent=2, ensure_ascii=False)
            file.write("\n")
        saved_files.append(output_path)
    return saved_files


if __name__ == "__main__":
    for saved_file in save_generated_datasets():
        print(saved_file)
