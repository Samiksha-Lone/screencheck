import json
import math

import pytest

from src.stats.experiment_analysis import (
    build_paired_comparisons,
    build_score_index,
    build_shortlist_analysis,
    build_stability_analysis,
    build_true_fit_validation,
)
from src.stats.reporting import write_analysis_outputs
from src.stats.statistical_analysis import (
    fractional_top_fraction,
    holm_adjust,
    intraclass_correlation_2_1,
    paired_summary,
    spearman_summary,
)
from src.validation.analysis_inputs import (
    EXPECTED_EXPERIMENTS,
    AnalysisInputError,
    _validate_phase6,
    read_jsonl,
)


def test_paired_statistics_report_missing_pairs_effects_and_reproducible_ci():
    first = paired_summary(
        [10, 12, 10, 9],
        [12, 12, 9, 10],
        expected_n=5,
        seed=17,
        replicates=1000,
    )
    second = paired_summary(
        [10, 12, 10, 9],
        [12, 12, 9, 10],
        expected_n=5,
        seed=17,
        replicates=1000,
    )
    assert first["n_included"] == 4
    assert first["n_missing"] == 1
    assert first["mean_difference"] == pytest.approx(0.5)
    assert first["median_difference"] == pytest.approx(0.5)
    assert first["higher_n"] == 2
    assert first["lower_n"] == 1
    assert first["tie_n"] == 1
    assert first["mean_ci_95"] == second["mean_ci_95"]
    assert first["median_ci_95"] == second["median_ci_95"]
    assert first["wilcoxon_p"] is not None
    assert first["sign_test_p"] is not None


def test_pooled_bootstrap_preserves_role_sample_counts():
    result = paired_summary(
        [0, 0, 0, 0],
        [0, 0, 100, 100],
        expected_n=4,
        seed=17,
        replicates=1000,
        bootstrap_strata=["backend", "backend", "analyst", "analyst"],
    )
    assert result["mean_difference"] == 50
    assert result["mean_ci_95"] == [50, 50]


def test_all_tied_paired_scores_are_reported_without_invalid_test_values():
    result = paired_summary(
        [5, 5, 5],
        [5, 5, 5],
        expected_n=3,
        replicates=100,
    )
    assert result["mean_difference"] == 0
    assert result["tie_n"] == 3
    assert result["wilcoxon_p"] == 1
    assert result["sign_test_p"] == 1
    assert result["rank_biserial"] == 0
    assert result["mean_ci_95"] == [0, 0]


def test_holm_adjustment_preserves_order_and_handles_missing_p_values():
    adjusted = holm_adjust([0.01, 0.04, 0.03, None])
    assert adjusted[:3] == pytest.approx([0.03, 0.06, 0.06])
    assert adjusted[3] is None


def test_fractional_shortlist_tie_policy_uses_exact_top_fraction():
    inclusion = fractional_top_fraction([10, 10, 8, 4], fraction=0.25)
    assert inclusion == [0.5, 0.5, 0.0, 0.0]
    assert sum(inclusion) == pytest.approx(1.0)


def test_icc_uses_candidate_by_run_repeated_measure_matrix():
    assert intraclass_correlation_2_1(
        [[10, 10, 10, 10, 10], [20, 20, 20, 20, 20], [30, 30, 30, 30, 30]]
    ) == pytest.approx(1.0)
    assert intraclass_correlation_2_1([[5, 5], [5, 5]]) is None


def test_spearman_correlation_has_candidate_bootstrap_interval():
    result = spearman_summary(
        [1, 2, 3, 4, 5],
        [10, 20, 30, 40, 50],
        seed=7,
        replicates=200,
    )
    assert result["rho"] == pytest.approx(1.0)
    assert result["p_value"] == pytest.approx(0.0)
    assert result["rho_ci_95"] == pytest.approx([1.0, 1.0])


def test_score_index_uses_corrected_s2_and_only_approved_e5():
    original = [
        {
            "result_id": "s1-e1",
            "experiment_id": "E1",
            "screener_id": "S1",
            "status": "completed",
            "job_id": "backend",
            "base_candidate_id": "backend-001",
            "variant_id": "base",
            "run_number": 1,
            "score": 60,
        },
        {
            "result_id": "s2-e1",
            "experiment_id": "E1",
            "screener_id": "S2",
            "status": "completed",
            "job_id": "backend",
            "base_candidate_id": "backend-001",
            "variant_id": "base",
            "run_number": 1,
            "score": 1,
        },
        {
            "result_id": "old-e5",
            "experiment_id": "E5",
            "screener_id": "S2",
            "status": "completed",
            "job_id": "backend",
            "base_candidate_id": "backend-001",
            "variant_id": "twin",
            "run_number": 1,
            "score": 99,
        },
    ]
    genuine_e5 = [
        {
            "result_id": "new-e5",
            "experiment_id": "E5_LAYOUT_AWARE_V1",
            "screener_id": "S2",
            "status": "completed",
            "job_id": "backend",
            "candidate_id": "backend-001",
            "layout": "two-column",
            "file_format": "pdf",
            "variant_id": "two-column",
            "run_number": 1,
            "raw_similarity": 0.5,
            "score": 0.5,
        }
    ]
    datasets = {
        "original_records": original,
        "normalized_s2_by_id": {
            "s2-e1": {"corrected_score": 72.5},
            "old-e5": {"corrected_score": 100.0},
        },
        "e5_layout_records": genuine_e5,
        "candidates": [],
    }
    index = build_score_index(datasets)
    assert index[("E1", "S1", "backend", "backend-001", "base", 1, None)] == 60
    assert index[("E1", "S2", "backend", "backend-001", "base", 1, None)] == 72.5
    assert (
        "E5",
        "S2",
        "backend",
        "backend-001",
        "two-column",
        1,
        "pdf",
    ) in index
    assert index[
        ("E5", "S2", "backend", "backend-001", "two-column", 1, "pdf")
    ] == 75
    assert index[
        ("E5", "S2", "backend", "backend-001", "two-column", 1, "pdf")
    ] != 99


def test_paired_comparison_matches_by_candidate_and_reports_missing_variant():
    candidates = [
        {"candidate_id": "backend-001", "job_id": "backend", "true_fit": 50}
    ]
    original = [
        {
            "result_id": "base",
            "experiment_id": "E1",
            "screener_id": "S1",
            "status": "completed",
            "job_id": "backend",
            "base_candidate_id": "backend-001",
            "variant_id": "base",
            "run_number": 1,
            "score": 40,
        },
        {
            "result_id": "group-a",
            "experiment_id": "E1",
            "screener_id": "S1",
            "status": "completed",
            "job_id": "backend",
            "base_candidate_id": "backend-001",
            "variant_id": "group_a",
            "run_number": 1,
            "score": 45,
        },
    ]
    index = build_score_index(
        {
            "original_records": original,
            "normalized_s2_by_id": {},
            "e5_layout_records": [],
            "candidates": candidates,
        }
    )
    comparisons = build_paired_comparisons(
        {"candidates": candidates},
        index,
    )
    observed = next(
        row
        for row in comparisons
        if row["experiment_id"] == "E1"
        and row["screener_id"] == "S1"
        and row["comparison"] == "base_to_name_group_a"
        and row["role"] == "all_roles"
    )
    missing = next(
        row
        for row in comparisons
        if row["experiment_id"] == "E1"
        and row["screener_id"] == "S1"
        and row["comparison"] == "base_to_name_group_b"
        and row["role"] == "all_roles"
    )
    assert observed["n_included"] == 1
    assert observed["n_missing"] == 0
    assert observed["mean_difference"] == 5
    assert missing["n_included"] == 0
    assert missing["n_missing"] == 1


def test_true_fit_results_are_separated_by_job_role():
    candidates = []
    index = {}
    for role in ("backend", "full_stack", "data_analyst"):
        for ordinal, true_fit in enumerate((40, 80), start=1):
            candidate_id = f"{role}-{ordinal}"
            candidates.append(
                {
                    "candidate_id": candidate_id,
                    "job_id": role,
                    "true_fit": true_fit,
                }
            )
            for screener, score in (("S1", true_fit), ("S2", true_fit * 0.8)):
                index[
                    ("E1", screener, role, candidate_id, "base", 1, None)
                ] = score
    rows = build_true_fit_validation(
        {"candidates": candidates},
        index,
        replicates=100,
    )
    backend_s1 = next(
        row
        for row in rows
        if row["screener_id"] == "S1" and row["role"] == "backend"
    )
    pooled_s2 = next(
        row
        for row in rows
        if row["screener_id"] == "S2" and row["role"] == "all_roles"
    )
    assert len(rows) == 8
    assert backend_s1["n"] == 2
    assert backend_s1["rho"] == pytest.approx(1)
    assert pooled_s2["n"] == 6
    assert pooled_s2["pooled_role_caveat"]


def test_e10_repeated_runs_preserve_candidate_level_units():
    candidates = [
        {"candidate_id": f"{role}-{ordinal}", "job_id": role}
        for role in ("backend", "full_stack", "data_analyst")
        for ordinal in range(2)
    ]
    index = {}
    for screener in ("S1", "S2"):
        for candidate in candidates:
            for run_number in range(1, 6):
                index[
                    (
                        "E10",
                        screener,
                        candidate["job_id"],
                        candidate["candidate_id"],
                        "identical_repeat",
                        run_number,
                        None,
                    )
                ] = 20 + int(candidate["candidate_id"][-1])
            index[
                (
                    "E10",
                    screener,
                    candidate["job_id"],
                    candidate["candidate_id"],
                    "section_reordering",
                    1,
                    None,
                )
            ] = 23 + int(candidate["candidate_id"][-1])
            index[
                (
                    "E10",
                    screener,
                    candidate["job_id"],
                    candidate["candidate_id"],
                    "synonym_rewording",
                    1,
                    None,
                )
            ] = 23 + int(candidate["candidate_id"][-1])
    results = build_stability_analysis(
        {"candidates": candidates},
        index,
        replicates=100,
    )
    row = next(
        item
        for item in results["repeated_runs"]
        if item["screener_id"] == "S1" and item["role"] == "backend"
    )
    assert row["n_included"] == 2
    assert row["runs_per_candidate"] == 5
    assert row["icc_2_1_absolute_agreement"] == pytest.approx(1)
    assert row["mean_within_candidate_sd"] == pytest.approx(0)
    assert len(results["rank_stability"]) == 12
    assert all(
        row["holm_family"] == "all_e10_rank_stability_spearman_tests"
        and (
            row["p_adjusted_holm"] is not None
            or row["p_value"] is None
            or not math.isfinite(row["p_value"])
        )
        for row in results["rank_stability"]
    )


def test_shortlist_bootstrap_uses_candidate_clusters_and_tie_sharing():
    candidate = {"candidate_id": "backend-001", "job_id": "backend"}
    index = {}
    for screener in ("S1", "S2"):
        for experiment, variants in (
            ("E1", ("base", "group_a", "group_b")),
            ("E3_COLLEGE", ("base", "twin")),
            ("E3_PROJECT", ("base", "twin")),
            ("E5", ("one-column", "two-column", "table")),
            ("E7", ("base", "twin")),
            ("E9", ("base", "twin")),
            ("E10", ("repeat_mean", "section_reordering", "synonym_rewording")),
        ):
            for variant in variants:
                file_formats = ("pdf", "docx") if experiment == "E5" else (None,)
                for file_format in file_formats:
                    run_number = 0 if variant == "repeat_mean" else 1
                    index[
                        (
                            experiment,
                            screener,
                            "backend",
                            candidate["candidate_id"],
                            variant,
                            run_number,
                            file_format,
                        )
                    ] = 50.0
    result = build_shortlist_analysis(
        {"candidates": [candidate]},
        index,
        replicates=25,
    )
    e1_groups = [
        row
        for row in result["groups"]
        if row["experiment_id"] == "E1"
        and row["screener_id"] == "S1"
        and row["role"] == "backend"
    ]
    assert len(e1_groups) == 3
    assert all(row["shortlist_rate"] == pytest.approx(0.2) for row in e1_groups)
    assert all(row["impact_ratio_to_highest_group"] == pytest.approx(1) for row in e1_groups)


def test_reports_are_aggregate_only_and_include_experiment_outputs(tmp_path):
    pair = {
        "experiment_id": "E1",
        "comparison": "base_to_name_group_a",
        "screener_id": "S1",
        "role": "all_roles",
        "file_format": None,
        "n_included": 3,
        "n_expected": 3,
        "mean_difference": 1.0,
        "mean_ci_95": [0.1, 1.9],
        "median_difference": 1.0,
        "spread_units": 0.2,
        "rank_biserial": 0.5,
        "wilcoxon_p": 0.05,
        "p_adjusted_holm": 0.1,
        "sign_test_p": 0.1,
        "practical_score_effect": False,
    }
    group = {
        "experiment_id": "E1",
        "screener_id": "S1",
        "role": "backend",
        "file_format": None,
        "condition": "base",
        "n_expected": 3,
        "n_included": 3,
        "shortlist_rate": 0.2,
        "impact_ratio_to_highest_group": 1.0,
        "impact_ratio_ci_95": [1.0, 1.0],
    }
    true_fit = {
        "screener_id": "S1",
        "role": "backend",
        "n": 3,
        "rho": 0.5,
        "rho_ci_95": [0.1, 0.8],
        "p_adjusted_holm": 0.2,
    }
    stability = {
        "screener_id": "S1",
        "role": "backend",
        "n_included": 3,
        "mean_within_candidate_sd": 0.0,
        "mean_within_candidate_sd_ci_95": [0.0, 0.0],
        "icc_2_1_absolute_agreement": 1.0,
        "pairwise_run_spearman_mean": 1.0,
        "pairwise_run_top20_overlap_mean": 1.0,
    }
    result = {
        "data_audit": {
            "phase6": {
                "record_count": 18000,
                "sha256": "phase6-hash",
                "status_counts": {"S3|skipped": 6000},
            },
            "genuine_e5_layout": {
                "record_count": 3600,
                "extraction_hashes_checked": 1800,
            },
        },
        "paired_comparisons": [pair],
        "shortlist": {"groups": [group], "candidate_changes": []},
        "true_fit_validation": [true_fit],
        "stability": {
            "repeated_runs": [stability],
            "rank_stability": [],
        },
    }
    write_analysis_outputs(result, tmp_path)
    assert (tmp_path / "analysis_results.json").is_file()
    assert (tmp_path / "summary.md").is_file()
    assert (tmp_path / "experiments" / "e1_analysis.md").is_file()
    assert (tmp_path / "figures" / "paired_score_changes.svg").is_file()
    serialized = (tmp_path / "analysis_results.json").read_text(encoding="utf-8")
    assert "candidate_id" not in serialized
    assert "Aarav Shah" not in serialized
    json.loads(serialized)


def test_phase6_integrity_validation_checks_count_ids_status_and_hash(monkeypatch):
    records = []
    for screener, status in (
        ("S1", "completed"),
        ("S2", "completed"),
        ("S3", "skipped"),
    ):
        for ordinal in range(6000):
            records.append(
                {
                    "result_id": f"{screener}-{ordinal}",
                    "experiment_id": EXPECTED_EXPERIMENTS[
                        ordinal % len(EXPECTED_EXPERIMENTS)
                    ],
                    "screener_id": screener,
                    "status": status,
                }
            )
    monkeypatch.setattr(
        "src.validation.analysis_inputs.EXPECTED_PHASE6_SHA256",
        "verified-hash",
    )
    audit = _validate_phase6(records, "verified-hash")
    assert audit["record_count"] == 18000
    assert audit["unique_result_ids"] == 18000
    assert audit["status_counts"]["S3|skipped"] == 6000

    with pytest.raises(AnalysisInputError, match="hash"):
        _validate_phase6(records, "different-hash")
    records[-1]["result_id"] = records[0]["result_id"]
    with pytest.raises(AnalysisInputError, match="duplicated"):
        _validate_phase6(records, "verified-hash")


def test_jsonl_reader_rejects_malformed_records(tmp_path):
    malformed = tmp_path / "malformed.jsonl"
    malformed.write_text('{"valid": true}\n{broken}\n', encoding="utf-8")
    with pytest.raises(AnalysisInputError, match="line 2"):
        read_jsonl(malformed)
