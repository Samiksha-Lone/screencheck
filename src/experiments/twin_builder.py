"""Create controlled synthetic resume twins for ScreenCheck experiments."""

import copy
import json
import random
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
GENERATED_DIR = DATA_DIR / "generated"
OUTPUT_DIR = DATA_DIR / "private" / "twins"

EXPERIMENT_IDS = ("E1", "E3_COLLEGE", "E3_PROJECT", "E5", "E7", "E9", "E10")

NAME_GROUP_A = [
    "Aditi Mehta", "Anita Rao", "Devika Shah", "Isha Kapoor",
    "Kavya Iyer", "Meera Patel", "Nisha Singh", "Priya Verma",
    "Rhea Malhotra", "Ritu Bhat", "Sana Joshi", "Shreya Nair",
    "Simran Gill", "Tara Menon", "Anvi Desai", "Diya Sethi",
    "Ira Khanna", "Kiara Bose", "Maya Kulkarni", "Leena Arora",
]

NAME_GROUP_B = [
    "Amit Shah", "Ravi Bhat", "Manav Roy", "Dhir Sethi",
    "Kunal Bose", "Aditya Roy", "Karan Iyer", "Tarun Nair",
    "Sahil Bhat", "Shiv Kapoor", "Anay Kapoor", "Kabir Mehta",
    "Arjun Sethi", "Rohan Singh", "Ritesh Gill", "Rahul Verma",
    "Ishan Sethi", "Nikhil Bose", "Amit Malhotra", "Neel Kulkarni",
]

ROLE_PROJECTS = {
    "backend": {
        "name": "Reliability API Project",
        "description": "A synthetic REST API with automated tests and documented deployment.",
        "details": "Reduced simulated response time by 20 percent and added 25 automated service checks.",
    },
    "full_stack": {
        "name": "Full-Stack Planning Portal",
        "description": "A synthetic responsive portal with a tested React interface and API.",
        "details": "Implemented 12 tested workflows and reduced simulated form completion time by 15 percent.",
    },
    "data_analyst": {
        "name": "Synthetic Sales Insights Project",
        "description": "A fictional analysis with cleaned data, a dashboard and an assumptions note.",
        "details": "Analyzed 5,000 synthetic records and identified a 18 percent improvement opportunity.",
    },
}

JOB_TERMS = {
    "backend": ["REST APIs", "Python", "PostgreSQL", "Git", "Docker", "Kubernetes"],
    "full_stack": ["JavaScript", "React", "Node.js", "Express.js", "PostgreSQL", "Git"],
    "data_analyst": ["SQL", "Excel", "Tableau", "Power BI", "Python", "Data Analysis"],
}


def load_candidates(data_dir: str | Path = GENERATED_DIR) -> list[dict]:
    """Load all 300 generated candidates without mutating source data."""
    candidates = []
    for path in sorted(Path(data_dir).glob("*_candidates.json")):
        with path.open("r", encoding="utf-8") as file:
            dataset = json.load(file)
        candidates.extend(copy.deepcopy(dataset["candidates"]))
    return candidates


def diff_fields(base: dict, twin: dict, prefix: str = "") -> list[str]:
    """Return recursively identified field paths whose values differ."""
    differences = []
    keys = set(base.keys()) | set(twin.keys())
    for key in sorted(keys):
        path = f"{prefix}.{key}" if prefix else key
        if key not in base or key not in twin:
            differences.append(path)
        elif isinstance(base[key], dict) and isinstance(twin[key], dict):
            differences.extend(diff_fields(base[key], twin[key], path))
        elif isinstance(base[key], list) and isinstance(twin[key], list):
            if base[key] != twin[key]:
                differences.append(path)
        elif base[key] != twin[key]:
            differences.append(path)
    return differences


def validate_twin(
    base: dict,
    twin: dict,
    allowed_changed_fields: Iterable[str],
    experiment_id: str,
    pair_id: str,
) -> dict:
    """Strictly validate a resume twin and return a readable result."""
    allowed = set(allowed_changed_fields)
    actual = set(diff_fields(base, twin))
    def field_allowed(field: str) -> bool:
        return any(
            field == allowed_field or field.startswith(allowed_field + ".")
            for allowed_field in allowed
        )

    unexpected = sorted(field for field in actual if not field_allowed(field))
    missing_allowed = sorted(
        allowed_field
        for allowed_field in allowed
        if not any(
            field == allowed_field or field.startswith(allowed_field + ".")
            for field in actual
        )
    )

    errors = []
    if not pair_id:
        errors.append("Missing pair ID")
    if not base.get("candidate_id"):
        errors.append("Base resume has no candidate_id")
    if not twin.get("candidate_id"):
        errors.append("Twin resume has no candidate_id")
    if twin.get("candidate_id") == base.get("candidate_id"):
        errors.append("Twin candidate_id must be unique")
    if unexpected:
        errors.append(
            f"{pair_id}: unexpected field changes in {experiment_id}: "
            + ", ".join(unexpected)
        )

    return {
        "valid": not errors,
        "pair_id": pair_id,
        "experiment_id": experiment_id,
        "actual_changed_fields": sorted(actual),
        "allowed_changed_fields": sorted(
            field for field in actual if field_allowed(field)
        ),
        "missing_allowed_changes": missing_allowed,
        "errors": errors,
    }


def validate_pair(pair: dict) -> dict:
    """Validate a pair record using its stored experiment rules."""
    result = validate_twin(
        pair["base"],
        pair["twin"],
        pair["allowed_changed_fields"],
        pair["experiment_id"],
        pair["pair_id"],
    )
    if pair["experiment_id"] == "E1":
        comparison_variant = pair.get("comparison_variant")
        if comparison_variant is not None:
            comparison_result = validate_twin(
                pair["base"],
                comparison_variant,
                pair["allowed_changed_fields"],
                pair["experiment_id"],
                pair["pair_id"] + ":group_a",
            )
            result["valid"] = result["valid"] and comparison_result["valid"]
            result["errors"].extend(comparison_result["errors"])

        names = pair.get("matched_names")
        if names is not None:
            if names["character_length"] != len(names["synthetic_group_a"]):
                result["errors"].append(
                    f"{pair['pair_id']}: recorded name length mismatch"
                )
            if len(names["synthetic_group_a"]) != len(names["synthetic_group_b"]):
                result["errors"].append(
                    f"{pair['pair_id']}: Group A and Group B names have different lengths"
                )
                names["length_matched"] = False
            result["valid"] = not result["errors"]
    return result


def _twin_id(base_id: str, experiment_id: str, variant: str) -> str:
    safe_variant = variant.lower().replace(" ", "_").replace("/", "_")
    return f"{base_id}__{experiment_id.lower()}__{safe_variant}"


def _make_pair(
    base: dict,
    twin: dict,
    experiment_id: str,
    variant_type: str,
    seed: int,
    allowed_changed_fields: Iterable[str],
    pair_suffix: str,
) -> dict:
    base_copy = copy.deepcopy(base)
    twin_copy = copy.deepcopy(twin)
    twin_copy["candidate_id"] = _twin_id(
        base_copy["candidate_id"], experiment_id, pair_suffix
    )
    pair_id = f"{base_copy['candidate_id']}:{experiment_id}:{pair_suffix}"
    pair = {
        "pair_id": pair_id,
        "base_candidate_id": base_copy["candidate_id"],
        "twin_candidate_id": twin_copy["candidate_id"],
        "experiment_id": experiment_id,
        "variant_type": variant_type,
        "seed": seed,
        "allowed_changed_fields": sorted(set(allowed_changed_fields)),
        "base": base_copy,
        "twin": twin_copy,
    }
    pair["validation"] = validate_pair(pair)
    return pair


def build_e1_pairs(candidates: Iterable[dict], seed: int = 42) -> list[dict]:
    """Create synthetic name-variant pairs using two neutral groups."""
    rng = random.Random(seed)
    pairs = []

    def names_by_length(names: Iterable[str]) -> dict[int, list[str]]:
        buckets = {}
        for name in names:
            buckets.setdefault(len(name), []).append(name)
        return buckets

    group_a_by_length = names_by_length(NAME_GROUP_A)
    group_b_by_length = names_by_length(NAME_GROUP_B)

    if set(group_a_by_length) != set(group_b_by_length):
        raise ValueError("E1 name pools do not cover the same character lengths")

    for base in candidates:
        shared_lengths = [
            length
            for length in group_a_by_length
            if group_a_by_length[length] and group_b_by_length[length]
        ]
        name_length = rng.choice(shared_lengths)
        group_a_name = rng.choice(group_a_by_length[name_length])
        group_b_name = rng.choice(group_b_by_length[name_length])

        group_a_twin = copy.deepcopy(base)
        group_b_twin = copy.deepcopy(base)
        group_a_twin["name"] = group_a_name
        group_b_twin["name"] = group_b_name

        pair = _make_pair(
            base,
            group_b_twin,
            "E1",
            "matched_comparison",
            seed,
            ["name", "candidate_id"],
            "matched_comparison",
        )
        pair["group_a_candidate_id"] = _twin_id(
            base["candidate_id"], "E1", "matched_comparison_a"
        )
        pair["group_b_candidate_id"] = pair["twin_candidate_id"]
        pair["comparison_variant"] = copy.deepcopy(group_a_twin)
        pair["comparison_variant"]["candidate_id"] = pair["group_a_candidate_id"]
        pair["matched_names"] = {
            "synthetic_group_a": group_a_name,
            "synthetic_group_b": group_b_name,
            "character_length": len(group_a_name),
            "length_matched": len(group_a_name) == len(group_b_name),
        }
        pair["twin_variant"] = copy.deepcopy(group_b_twin)
        pair["validation"] = validate_pair(pair)
        pairs.append(pair)
    return pairs


def build_e3_college_pairs(candidates: Iterable[dict], seed: int = 42) -> list[dict]:
    pairs = []
    for base in candidates:
        lesser = copy.deepcopy(base)
        well_known = copy.deepcopy(base)
        lesser["education"] = {
            "college": "Synthetic Regional Technical College",
            "tier": "lesser_known",
        }
        well_known["education"] = {
            "college": "Synthetic National Technical University",
            "tier": "well_known",
        }
        pairs.append(
            _make_pair(
                lesser,
                well_known,
                "E3_COLLEGE",
                "college_prestige",
                seed,
                ["education", "candidate_id"],
                "well_known",
            )
        )
    return pairs


def build_e3_project_pairs(candidates: Iterable[dict], seed: int = 42) -> list[dict]:
    pairs = []
    for base in candidates:
        base_variant = copy.deepcopy(base)
        base_variant["education"] = {
            "college": "Synthetic Regional Technical College",
            "tier": "lesser_known",
        }
        project_variant = copy.deepcopy(base_variant)
        project_variant["projects"] = copy.deepcopy(base_variant["projects"])
        project_variant["projects"].append(
            copy.deepcopy(ROLE_PROJECTS[base["job_id"]])
        )
        project_variant["project_evidence"] = 10
        pairs.append(
            _make_pair(
                base_variant,
                project_variant,
                "E3_PROJECT",
                "real_project_evidence",
                seed,
                ["projects", "project_evidence", "candidate_id"],
                "with_project",
            )
        )
    return pairs


def build_e5_pairs(candidates: Iterable[dict], seed: int = 42) -> list[dict]:
    pairs = []
    for base in candidates:
        one_column = copy.deepcopy(base)
        one_column["layout"] = "one-column"
        for layout in ("two-column", "table"):
            twin = copy.deepcopy(one_column)
            twin["layout"] = layout
            pairs.append(
                _make_pair(
                    one_column,
                    twin,
                    "E5",
                    "resume_layout",
                    seed,
                    ["layout", "candidate_id"],
                    layout,
                )
            )
    return pairs


def build_e7_pairs(candidates: Iterable[dict], seed: int = 42) -> list[dict]:
    pairs = []
    for base in candidates:
        twin = copy.deepcopy(base)
        twin["keyword_stuffing"] = {
            "visible": True,
            "terms": JOB_TERMS[base["job_id"]],
            "supporting_evidence_added": False,
        }
        pairs.append(
            _make_pair(
                base,
                twin,
                "E7",
                "keyword_stuffing",
                seed,
                ["keyword_stuffing", "candidate_id"],
                "visible_keywords",
            )
        )
    return pairs


def build_e9_pairs(candidates: Iterable[dict], seed: int = 42) -> list[dict]:
    pairs = []
    for base in candidates:
        twin = copy.deepcopy(base)
        twin["projects"] = copy.deepcopy(base["projects"])
        twin["projects"].append(copy.deepcopy(ROLE_PROJECTS[base["job_id"]]))
        twin["project_evidence"] = 10
        twin["experience"] = copy.deepcopy(base["experience"])
        for item in twin["experience"]:
            item["summary"] = (
                item["summary"].replace("Fictional experience using", "Built and measured work using")
                + " Improved a synthetic outcome by 15 percent."
            )
        pairs.append(
            _make_pair(
                base,
                twin,
                "E9",
                "honest_improvement",
                seed,
                ["projects", "project_evidence", "experience", "candidate_id"],
                "genuine_project",
            )
        )
    return pairs


def build_e10_pairs(candidates: Iterable[dict], seed: int = 42) -> list[dict]:
    pairs = []
    for base in candidates:
        identical = copy.deepcopy(base)
        pairs.append(
            _make_pair(
                base,
                identical,
                "E10",
                "identical_control",
                seed,
                ["candidate_id"],
                "identical",
            )
        )

        reordered_base = copy.deepcopy(base)
        reordered_base["section_order"] = ["summary", "skills", "experience", "projects"]
        reordered = copy.deepcopy(reordered_base)
        reordered["section_order"] = ["skills", "experience", "projects", "summary"]
        pairs.append(
            _make_pair(
                reordered_base,
                reordered,
                "E10",
                "section_reordering",
                seed,
                ["section_order", "candidate_id"],
                "reordered",
            )
        )

        synonym = copy.deepcopy(base)
        for item in synonym["experience"]:
            item["summary"] = item["summary"].replace(
                "Fictional experience using", "Synthetic hands-on work with"
            )
        for item in synonym["projects"]:
            item["details"] = item["details"].replace(
                "Documented implementation, tests, deployment details, and measured outcomes.",
                "Recorded implementation, test coverage, deployment information, and outcome measurements.",
            )
        pairs.append(
            _make_pair(
                base,
                synonym,
                "E10",
                "synonym_rewording",
                seed,
                ["experience", "projects", "candidate_id"],
                "synonym",
            )
        )
    return pairs


def build_experiment(
    experiment_id: str,
    candidates: Iterable[dict],
    seed: int = 42,
) -> list[dict]:
    candidates = list(candidates)
    builders = {
        "E1": build_e1_pairs,
        "E3_COLLEGE": build_e3_college_pairs,
        "E3_PROJECT": build_e3_project_pairs,
        "E5": build_e5_pairs,
        "E7": build_e7_pairs,
        "E9": build_e9_pairs,
        "E10": build_e10_pairs,
    }
    if experiment_id not in builders:
        raise ValueError("unknown experiment: " + experiment_id)
    return builders[experiment_id](candidates, seed)


def validate_pairs(pairs: Iterable[dict]) -> dict:
    pairs = list(pairs)
    results = [validate_pair(pair) for pair in pairs]
    failures = [result for result in results if not result["valid"]]
    return {
        "pair_count": len(pairs),
        "valid_pair_count": len(pairs) - len(failures),
        "failure_count": len(failures),
        "failures": failures,
    }


def generate_all_twins(
    seed: int = 42,
    output_dir: str | Path = OUTPUT_DIR,
) -> dict:
    """Generate, validate and save all twin datasets without API keys."""
    candidates = load_candidates()
    original_snapshot = copy.deepcopy(candidates)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    all_pairs = {}
    validation = {}
    for experiment_id in EXPERIMENT_IDS:
        pairs = build_experiment(experiment_id, candidates, seed)
        all_pairs[experiment_id] = pairs
        validation[experiment_id] = validate_pairs(pairs)

        experiment_dir = output_dir / experiment_id.lower()
        experiment_dir.mkdir(parents=True, exist_ok=True)
        for pair in pairs:
            job_id = pair["base"]["job_id"]
            job_dir = experiment_dir / job_id
            job_dir.mkdir(parents=True, exist_ok=True)
            pair_path = job_dir / f"{pair['pair_id'].replace(':', '__')}.json"
            with pair_path.open("w", encoding="utf-8") as file:
                json.dump(pair, file, indent=2)

    twin_ids = [
        pair["twin_candidate_id"]
        for pairs in all_pairs.values()
        for pair in pairs
    ]
    unique_twin_ids = len(set(twin_ids)) == len(twin_ids)
    total_pairs = sum(len(pairs) for pairs in all_pairs.values())
    total_failures = sum(
        result["failure_count"] for result in validation.values()
    )

    manifest = {
        "seed": seed,
        "base_candidate_count": len(candidates),
        "experiment_ids": list(EXPERIMENT_IDS),
        "pair_counts": {
            experiment_id: len(pairs)
            for experiment_id, pairs in all_pairs.items()
        },
        "total_pair_count": total_pairs,
        "unique_twin_ids": unique_twin_ids,
        "validation_failures": total_failures,
        "validation": validation,
    }
    manifest_path = output_dir / "twin_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=2)

    manifest["original_candidates_unchanged"] = (
        candidates == original_snapshot
    )
    return manifest


def generate_e1_twins(
    seed: int = 42,
    output_dir: str | Path = OUTPUT_DIR,
) -> dict:
    """Regenerate only E1 and update only E1-related manifest counts."""
    candidates = load_candidates()
    original_snapshot = copy.deepcopy(candidates)
    output_dir = Path(output_dir)
    experiment_dir = output_dir / "e1"

    if experiment_dir.exists():
        for pair_path in experiment_dir.rglob("*.json"):
            pair_path.unlink()

    pairs = build_e1_pairs(candidates, seed)
    experiment_dir.mkdir(parents=True, exist_ok=True)
    for pair in pairs:
        job_dir = experiment_dir / pair["base"]["job_id"]
        job_dir.mkdir(parents=True, exist_ok=True)
        pair_path = job_dir / f"{pair['pair_id'].replace(':', '__')}.json"
        with pair_path.open("w", encoding="utf-8") as file:
            json.dump(pair, file, indent=2)

    validation = validate_pairs(pairs)
    manifest_path = output_dir / "twin_manifest.json"
    if manifest_path.exists():
        with manifest_path.open("r", encoding="utf-8") as file:
            manifest = json.load(file)
    else:
        manifest = {
            "seed": seed,
            "base_candidate_count": len(candidates),
            "experiment_ids": list(EXPERIMENT_IDS),
            "pair_counts": {},
            "validation": {},
        }

    manifest["seed"] = seed
    manifest["base_candidate_count"] = len(candidates)
    manifest["pair_counts"]["E1"] = len(pairs)
    manifest["validation"]["E1"] = validation
    manifest["total_pair_count"] = sum(manifest["pair_counts"].values())
    manifest["validation_failures"] = sum(
        result["failure_count"]
        for result in manifest["validation"].values()
    )

    twin_ids = [
        twin_id
        for pair in pairs
        for twin_id in (
            pair["group_a_candidate_id"],
            pair["group_b_candidate_id"],
        )
    ]
    manifest["unique_twin_ids"] = len(twin_ids) == len(set(twin_ids))
    manifest["original_candidates_unchanged"] = candidates == original_snapshot

    output_dir.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=2)
    return manifest


if __name__ == "__main__":
    print(json.dumps(generate_e1_twins(), indent=2))
