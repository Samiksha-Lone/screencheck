import copy
import json

import pytest

from src.experiments.experiment_runner import (
    ExperimentRunner,
    deterministic_result_id,
    load_pairs,
    pair_variants,
    result_record,
    variant_resume_text,
)
from src.screeners.screeners import EmbeddingScreener


def test_loads_pairs_and_pilot_limit():
    pairs = load_pairs("E1")
    pilot = load_pairs("E1", pilot=True)
    assert len(pairs) == 300
    assert len(pilot) == 10
    assert len({pair["base_candidate_id"] for pair in pilot}) == 10


def test_e1_matched_variants_and_field_isolation():
    pair = load_pairs("E1")[0]
    variants = pair_variants("E1", pair)
    assert [variant["variant_id"] for variant in variants] == [
        "base",
        "group_a",
        "group_b",
    ]
    assert pair["matched_names"]["length_matched"] is True

    base = copy.deepcopy(pair["base"])
    group_a = copy.deepcopy(pair["comparison_variant"])
    group_b = copy.deepcopy(pair["twin"])
    for candidate in (group_a, group_b):
        candidate.pop("candidate_id")
        candidate.pop("name")
    base.pop("candidate_id")
    base.pop("name")
    assert group_a == base
    assert group_b == base


def test_e3_comparisons_remain_separate():
    college = load_pairs("E3_COLLEGE")[0]
    project = load_pairs("E3_PROJECT")[0]
    assert college["base"].get("education") != college["twin"].get("education")
    assert college["base"].get("projects") == college["twin"].get("projects")
    assert project["base"].get("education") == project["twin"].get("education")
    assert project["base"].get("projects") != project["twin"].get("projects")


def test_e10_variants_are_separate():
    pair_types = {}
    for pair in load_pairs("E10"):
        pair_types.setdefault(pair["variant_type"], 0)
        pair_types[pair["variant_type"]] += 1
    assert pair_types["identical_control"] == 300
    assert pair_types["section_reordering"] == 300
    assert pair_types["synonym_rewording"] == 300


def test_result_schema_and_deterministic_id():
    record = result_record(
        experiment_id="E1",
        pair_id="base:E1:test",
        base_candidate_id="base",
        job_id="backend",
        screener_id="S1",
        variant_id="base",
        variant_type="baseline",
        run_number=1,
        score=50.0,
        status="completed",
        matched_skills=["Python"],
    )
    assert set(
        ("experiment_id", "base_candidate_id", "job_id", "screener_id",
         "variant_id", "run_number", "score", "status")
    ).issubset(record)
    assert record["result_id"] == deterministic_result_id(
        "E1", "base:E1:test", "S1", "base", 1
    )
    assert deterministic_result_id(
        "E5", "backend-candidate-001:E5:two-column", "S1", "base", 1
    ) != deterministic_result_id(
        "E5", "backend-candidate-001:E5:table", "S1", "base", 1
    )


def test_resume_behavior_keyword_and_layout():
    pair = load_pairs("E7")[0]
    text = variant_resume_text(pair["base"])
    stuffed = variant_resume_text(pair["twin"])
    assert "Visible Keyword List" not in text
    assert "Visible Keyword List" in stuffed

    layout_pair = load_pairs("E5")[0]
    assert variant_resume_text(layout_pair["base"]) == variant_resume_text(
        layout_pair["twin"]
    )


def test_honest_improvement_is_isolated():
    pair = load_pairs("E9")[0]
    assert pair["base"]["skills"] == pair["twin"]["skills"]
    assert len(pair["twin"]["projects"]) == len(pair["base"]["projects"]) + 1


def test_s2_identical_score_edge_case():
    assert EmbeddingScreener.scale_scores([0.5, 0.5]) == [50.0, 50.0]


def test_phase5_e5_layouts_and_missing_two_column_scope():
    pairs = load_pairs("E5")
    assert len(pairs) == 600
    layouts = sorted({pair["twin"]["layout"] for pair in pairs})
    assert layouts == ["table", "two-column"]
    two_column = [
        pair for pair in pairs if pair["twin"]["layout"] == "two-column"
    ]
    assert len(two_column) == 300
    assert len({pair["base_candidate_id"] for pair in two_column}) == 300
    assert all(
        pair["base"]["layout"] == "one-column"
        and pair["twin"]["layout"] == "two-column"
        for pair in two_column
    )


def test_pilot_runner_s1(tmp_path):
    runner = ExperimentRunner(tmp_path)
    jobs = runner.jobs
    assert runner.keyword is not None
    summary = runner.run(
        experiments=["E7"],
        screeners=["S1"],
        pilot=True,
        resume=True,
    )
    assert summary["experiments"]["E7"]["pair_count"] == 10
