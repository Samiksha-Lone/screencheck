import json

from src.factory.resume_factory import (
    JOB_FILES,
    generate_candidates,
    save_generated_datasets,
)
from src.factory.true_fit import calculate_true_fit


def test_generates_100_candidates_for_each_job():
    for job_key in JOB_FILES:
        dataset = generate_candidates(job_key, seed=42)
        assert len(dataset["candidates"]) == 100
        assert dataset["metadata"]["candidate_count"] == 100


def test_candidate_ids_are_unique():
    all_ids = []
    for job_key in JOB_FILES:
        dataset = generate_candidates(job_key, seed=42)
        all_ids.extend(
            candidate["candidate_id"] for candidate in dataset["candidates"]
        )

    assert len(all_ids) == len(set(all_ids))


def test_same_seed_is_reproducible():
    first = generate_candidates("backend", seed=123)
    second = generate_candidates("backend", seed=123)
    assert first == second


def test_different_seeds_produce_different_results():
    first = generate_candidates("full_stack", seed=42)
    second = generate_candidates("full_stack", seed=43)
    assert first["candidates"] != second["candidates"]


def test_skills_have_no_duplicates():
    for job_key in JOB_FILES:
        dataset = generate_candidates(job_key, seed=42)
        for candidate in dataset["candidates"]:
            assert len(candidate["skills"]) == len(set(candidate["skills"]))


def test_true_fit_scores_are_valid_and_match_existing_function():
    for job_key in JOB_FILES:
        dataset = generate_candidates(job_key, seed=42)
        job_path = "data/" + JOB_FILES[job_key][0]
        with open(job_path, "r", encoding="utf-8") as file:
            job = json.load(file)

        for candidate in dataset["candidates"]:
            score = candidate["true_fit"]
            assert 0 <= score <= 100
            assert candidate["project_evidence"] in (0, 5, 10)

            expected = calculate_true_fit(
                candidate["skills"],
                job["must_have_skills"],
                job["nice_to_have_skills"],
                candidate["project_evidence"],
            )
            assert score == expected


def test_scores_are_in_requested_distribution_range():
    all_scores = []
    for job_key in JOB_FILES:
        dataset = generate_candidates(job_key, seed=42)
        all_scores.extend(
            candidate["true_fit"] for candidate in dataset["candidates"]
        )

    assert min(all_scores) >= 20
    assert max(all_scores) <= 95
    assert len(set(all_scores)) > 10


def test_save_and_read_generated_datasets(tmp_path):
    saved_files = save_generated_datasets(seed=42, data_dir=tmp_path)
    assert len(saved_files) == 3

    total = 0
    for saved_file in saved_files:
        with saved_file.open("r", encoding="utf-8") as file:
            dataset = json.load(file)
        assert len(dataset["candidates"]) == 100
        assert dataset["metadata"]["seed"] == 42
        total += len(dataset["candidates"])

    assert total == 300
