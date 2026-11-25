import copy
import json

import pytest

from src.experiments.twin_builder import (
    build_e1_pairs,
    build_e3_college_pairs,
    build_e3_project_pairs,
    build_e5_pairs,
    build_e7_pairs,
    build_e9_pairs,
    build_e10_pairs,
    build_experiment,
    diff_fields,
    generate_e1_twins,
    generate_all_twins,
    load_candidates,
    NAME_GROUP_A,
    NAME_GROUP_B,
    validate_pair,
    validate_twin,
)


@pytest.fixture(scope="module")
def candidates():
    return load_candidates()


def test_all_experiments_process_300_candidates(candidates):
    expected = {
        "E1": 300,
        "E3_COLLEGE": 300,
        "E3_PROJECT": 300,
        "E5": 600,
        "E7": 300,
        "E9": 300,
        "E10": 900,
    }
    for experiment_id, count in expected.items():
        pairs = build_experiment(experiment_id, candidates, 42)
        assert len(pairs) == count
        assert all(validate_pair(pair)["valid"] for pair in pairs)


def test_e1_names_change_only(candidates):
    pairs = build_e1_pairs(candidates[:3], 42)
    assert len(pairs) == 3
    for pair in pairs:
        assert pair["variant_type"] == "matched_comparison"
        base = copy.deepcopy(pair["base"])
        twin = copy.deepcopy(pair["twin"])
        base.pop("name")
        twin.pop("name")
        base.pop("candidate_id")
        twin.pop("candidate_id")
        assert base == twin

        comparison = copy.deepcopy(pair["comparison_variant"])
        comparison_base = copy.deepcopy(pair["base"])
        comparison.pop("name")
        comparison.pop("candidate_id")
        comparison_base.pop("name")
        comparison_base.pop("candidate_id")
        assert comparison == comparison_base
        assert pair["matched_names"]["length_matched"] is True
        assert len(pair["matched_names"]["synthetic_group_a"]) == len(
            pair["matched_names"]["synthetic_group_b"]
        )


def test_e1_name_pools_have_twenty_names_and_matching_lengths(candidates):
    assert len(NAME_GROUP_A) == len(set(NAME_GROUP_A)) == 20
    assert len(NAME_GROUP_B) == len(set(NAME_GROUP_B)) == 20
    pairs = build_e1_pairs(candidates, 42)

    exact_matches = sum(
        len(pair["matched_names"]["synthetic_group_a"])
        == len(pair["matched_names"]["synthetic_group_b"])
        for pair in pairs
    )
    assert exact_matches == 300
    assert all(validate_pair(pair)["valid"] for pair in pairs)


def test_e3_comparisons_are_separate(candidates):
    college = build_e3_college_pairs(candidates[:1], 42)[0]
    project = build_e3_project_pairs(candidates[:1], 42)[0]

    assert college["experiment_id"] == "E3_COLLEGE"
    assert college["base"]["education"] != college["twin"]["education"]
    assert college["base"].get("projects") == college["twin"].get("projects")

    assert project["experiment_id"] == "E3_PROJECT"
    assert project["base"]["education"] == project["twin"]["education"]
    assert project["base"]["projects"] != project["twin"]["projects"]
    assert project["twin"]["project_evidence"] == 10


def test_e5_layout_preserves_content(candidates):
    pairs = build_e5_pairs(candidates[:2], 42)
    assert len(pairs) == 4
    for pair in pairs:
        base = copy.deepcopy(pair["base"])
        twin = copy.deepcopy(pair["twin"])
        base.pop("layout")
        twin.pop("layout")
        base.pop("candidate_id")
        twin.pop("candidate_id")
        assert base == twin


def test_e7_keyword_stuffing_does_not_change_evidence(candidates):
    pairs = build_e7_pairs(candidates[:3], 42)
    for pair in pairs:
        for field in ("skills", "experience", "projects", "project_evidence"):
            assert pair["base"][field] == pair["twin"][field]
        assert pair["twin"]["keyword_stuffing"]["supporting_evidence_added"] is False


def test_e9_honest_improvement_adds_project(candidates):
    pair = build_e9_pairs(candidates[:1], 42)[0]
    assert len(pair["twin"]["projects"]) == len(pair["base"]["projects"]) + 1
    assert pair["twin"]["project_evidence"] == 10
    assert pair["base"]["skills"] == pair["twin"]["skills"]
    assert "Improved" in pair["twin"]["experience"][0]["summary"]


def test_e10_variants(candidates):
    pairs = build_e10_pairs(candidates[:2], 42)
    assert len(pairs) == 6

    identical = [pair for pair in pairs if pair["variant_type"] == "identical_control"]
    reordered = [pair for pair in pairs if pair["variant_type"] == "section_reordering"]
    synonym = [pair for pair in pairs if pair["variant_type"] == "synonym_rewording"]

    assert len(identical) == 2
    assert len(reordered) == 2
    assert len(synonym) == 2
    for pair in reordered:
        base = copy.deepcopy(pair["base"])
        twin = copy.deepcopy(pair["twin"])
        base.pop("section_order")
        twin.pop("section_order")
        base.pop("candidate_id")
        twin.pop("candidate_id")
        assert base == twin


def test_original_candidates_are_not_mutated(candidates):
    original = copy.deepcopy(candidates)
    build_e9_pairs(candidates, 42)
    build_e7_pairs(candidates, 42)
    build_e1_pairs(candidates, 42)
    assert candidates == original


def test_fixed_seed_reproducibility(candidates):
    first = build_e1_pairs(candidates[:10], 42)
    second = build_e1_pairs(candidates[:10], 42)
    assert first == second


def test_ids_are_unique(candidates):
    pairs = build_experiment("E10", candidates, 42)
    ids = [pair["twin_candidate_id"] for pair in pairs]
    assert len(ids) == len(set(ids))

    e1_pairs = build_e1_pairs(candidates, 42)
    e1_ids = [
        twin_id
        for pair in e1_pairs
        for twin_id in (
            pair["group_a_candidate_id"],
            pair["group_b_candidate_id"],
        )
    ]
    assert len(e1_ids) == len(set(e1_ids))


def test_field_level_diff_detects_unexpected_change(candidates):
    base = copy.deepcopy(candidates[0])
    twin = copy.deepcopy(base)
    twin["candidate_id"] = "unexpected-twin"
    twin["skills"].append("Unsupported Skill")
    result = validate_twin(
        base,
        twin,
        ["candidate_id"],
        "TEST",
        "test-pair",
    )
    assert result["valid"] is False
    assert "skills" in result["errors"][0]
    assert "skills" in diff_fields(base, twin)


def test_invalid_pair_is_rejected(candidates):
    pair = build_e1_pairs(candidates[:1], 42)[0]
    pair["twin"]["experience"][0]["summary"] = "Unexpected alteration"
    result = validate_pair(pair)
    assert result["valid"] is False
    assert any("experience" in error for error in result["errors"])
