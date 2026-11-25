"""Build matched comparisons and aggregate analyses for ScreenCheck data."""

import hashlib
import math
from collections import defaultdict

import numpy as np
from scipy import stats

from src.stats.statistical_analysis import (
    BOOTSTRAP_REPLICATES,
    BOOTSTRAP_SEED,
    bootstrap_mean_interval,
    fractional_top_fraction,
    holm_adjust,
    intraclass_correlation_2_1,
    paired_summary,
    spearman_summary,
)


SCREENERS = ("S1", "S2")
ROLE_NAMES = ("backend", "full_stack", "data_analyst")
SHORTLIST_FRACTION = 0.20
PRACTICAL_SCORE_THRESHOLD = 3.0
SHORTLIST_IMPACT_THRESHOLD = 0.80


def _stable_seed(label: str) -> int:
    digest = hashlib.sha256(
        f"{BOOTSTRAP_SEED}|{label}".encode("utf-8")
    ).hexdigest()
    return int(digest[:8], 16)


def _insert_score(
    index: dict,
    key: tuple,
    value: float,
    record_id: str,
) -> None:
    if key in index:
        raise ValueError(f"Duplicate observation key: {key}")
    if not math.isfinite(float(value)):
        raise ValueError(f"Non-finite score in result {record_id}")
    index[key] = float(value)


def build_score_index(datasets: dict) -> dict:
    """Create one validated score lookup; never use legacy E5 repair rows."""
    index = {}
    normalized_s2 = datasets["normalized_s2_by_id"]

    for record in datasets["original_records"]:
        experiment = record["experiment_id"]
        screener = record["screener_id"]
        if experiment == "E5" or screener not in SCREENERS:
            continue
        if record["status"] != "completed":
            continue
        if screener == "S1":
            score = record["score"]
        else:
            normalized = normalized_s2.get(record["result_id"])
            if normalized is None:
                raise ValueError(
                    f"Missing role-normalized S2 score for {record['result_id']}"
                )
            score = normalized["corrected_score"]

        key = (
            experiment,
            screener,
            record["job_id"],
            record["base_candidate_id"],
            record["variant_id"],
            record["run_number"],
            None,
        )
        _insert_score(index, key, score, record["result_id"])

    for record in datasets["e5_layout_records"]:
        screener = record["screener_id"]
        if screener == "S2":
            raw_similarity = float(record["raw_similarity"])
            score = 50.0 * (raw_similarity + 1.0)
        else:
            score = record["score"]
        key = (
            "E5",
            screener,
            record["job_id"],
            record["candidate_id"],
            record["layout"],
            record["run_number"],
            record["file_format"],
        )
        _insert_score(index, key, score, record["result_id"])

    for screener in SCREENERS:
        for role in ROLE_NAMES:
            for candidate in datasets["candidates"]:
                if candidate["job_id"] != role:
                    continue
                runs = [
                    index.get(
                        (
                            "E10",
                            screener,
                            role,
                            candidate["candidate_id"],
                            "identical_repeat",
                            run_number,
                            None,
                        )
                    )
                    for run_number in range(1, 6)
                ]
                if all(value is not None for value in runs):
                    key = (
                        "E10",
                        screener,
                        role,
                        candidate["candidate_id"],
                        "repeat_mean",
                        0,
                        None,
                    )
                    index[key] = float(np.mean(runs))

    return index


def _contrast_definitions() -> list[dict]:
    definitions = []
    for control, treatment, label in (
        ("base", "group_a", "base_to_name_group_a"),
        ("base", "group_b", "base_to_name_group_b"),
        ("group_a", "group_b", "name_group_a_to_group_b"),
    ):
        definitions.append(
            {
                "experiment_id": "E1",
                "control": control,
                "treatment": treatment,
                "comparison": label,
                "file_format": None,
            }
        )
    for experiment in ("E3_COLLEGE", "E3_PROJECT", "E7", "E9"):
        definitions.append(
            {
                "experiment_id": experiment,
                "control": "base",
                "treatment": "twin",
                "comparison": "base_to_twin",
                "file_format": None,
            }
        )
    for file_format in ("pdf", "docx"):
        for control, treatment, label in (
            ("one-column", "two-column", "one_column_to_two_column"),
            ("one-column", "table", "one_column_to_table"),
            ("two-column", "table", "two_column_to_table"),
        ):
            definitions.append(
                {
                    "experiment_id": "E5",
                    "control": control,
                    "treatment": treatment,
                    "comparison": label,
                    "file_format": file_format,
                }
            )
    for treatment in ("section_reordering", "synonym_rewording"):
        definitions.append(
            {
                "experiment_id": "E10",
                "control": "repeat_mean",
                "treatment": treatment,
                "comparison": f"repeat_mean_to_{treatment}",
                "file_format": None,
            }
        )
    return definitions


def build_paired_comparisons(
    datasets: dict,
    score_index: dict,
    *,
    replicates: int = BOOTSTRAP_REPLICATES,
) -> list[dict]:
    role_by_candidate = {
        candidate["candidate_id"]: candidate["job_id"]
        for candidate in datasets["candidates"]
    }
    all_candidate_ids = sorted(role_by_candidate)
    comparisons = []

    for definition in _contrast_definitions():
        experiment = definition["experiment_id"]
        for screener in SCREENERS:
            for role_scope in (None, *ROLE_NAMES):
                candidate_ids = [
                    candidate_id
                    for candidate_id in all_candidate_ids
                    if role_scope is None
                    or role_by_candidate[candidate_id] == role_scope
                ]
                control_by_id = {}
                treatment_by_id = {}
                for candidate_id in candidate_ids:
                    role = role_by_candidate[candidate_id]
                    control_key = (
                        experiment,
                        screener,
                        role,
                        candidate_id,
                        definition["control"],
                        0 if definition["control"] == "repeat_mean" else 1,
                        definition["file_format"],
                    )
                    treatment_key = (
                        experiment,
                        screener,
                        role,
                        candidate_id,
                        definition["treatment"],
                        0 if definition["treatment"] == "repeat_mean" else 1,
                        definition["file_format"],
                    )
                    if control_key in score_index:
                        control_by_id[candidate_id] = score_index[control_key]
                    if treatment_key in score_index:
                        treatment_by_id[candidate_id] = score_index[treatment_key]

                matched_ids = sorted(
                    set(control_by_id).intersection(treatment_by_id)
                )
                expected_n = len(candidate_ids)
                seed_label = "|".join(
                    (
                        experiment,
                        screener,
                        definition["comparison"],
                        role_scope or "all_roles",
                        definition["file_format"] or "all_formats",
                    )
                )
                summary = paired_summary(
                    [control_by_id[candidate_id] for candidate_id in matched_ids],
                    [
                        treatment_by_id[candidate_id]
                        for candidate_id in matched_ids
                    ],
                    expected_n=expected_n,
                    seed=_stable_seed(seed_label),
                    replicates=replicates,
                    bootstrap_strata=[
                        role_by_candidate[candidate_id]
                        for candidate_id in matched_ids
                    ],
                )
                summary.update(
                    {
                        "experiment_id": experiment,
                        "screener_id": screener,
                        "comparison": definition["comparison"],
                        "control_condition": definition["control"],
                        "treatment_condition": definition["treatment"],
                        "role": role_scope or "all_roles",
                        "file_format": definition["file_format"],
                        "difference_direction": "treatment_minus_control",
                        "score_scale": (
                            "0_to_100_fixed_cosine_map"
                            if experiment == "E5" and screener == "S2"
                            else "0_to_100"
                        ),
                        "score_scale_note": (
                            "E5 S2 uses 50 * (raw cosine + 1); a fixed "
                            "monotonic map, not pool normalization."
                            if experiment == "E5" and screener == "S2"
                            else None
                        ),
                        "practical_score_threshold": PRACTICAL_SCORE_THRESHOLD,
                        "practical_score_effect": (
                            abs(summary["mean_difference"])
                            >= PRACTICAL_SCORE_THRESHOLD
                            if summary["mean_difference"] is not None
                            else None
                        ),
                        "p_adjusted_holm": None,
                        "holm_family": "all_paired_wilcoxon_contrasts",
                    }
                )
                comparisons.append(summary)

    adjusted = holm_adjust([row["wilcoxon_p"] for row in comparisons])
    for row, p_adjusted in zip(comparisons, adjusted):
        row["p_adjusted_holm"] = p_adjusted
    return comparisons


def _shortlist_pool(
    conditions: dict[str, list[float]],
    fraction: float,
) -> tuple[dict[str, list[float]], dict[str, float]]:
    names = list(conditions)
    scores = [score for name in names for score in conditions[name]]
    probabilities = fractional_top_fraction(scores, fraction)
    included = {}
    offset = 0
    for name in names:
        count = len(conditions[name])
        included[name] = probabilities[offset : offset + count]
        offset += count
    rates = {
        name: float(np.mean(values)) if values else 0.0
        for name, values in included.items()
    }
    return included, rates


def _bootstrap_shortlist_rates(
    conditions: dict[str, list[float]],
    fraction: float,
    seed: int,
    replicates: int,
) -> tuple[dict[str, list[float]], dict[str, list[float]]]:
    names = list(conditions)
    candidate_count = len(next(iter(conditions.values())))
    generator = np.random.default_rng(seed)
    rate_draws = {name: [] for name in names}
    impact_draws = {name: [] for name in names}

    for _ in range(replicates):
        indices = generator.integers(0, candidate_count, size=candidate_count)
        sampled = {
            name: np.asarray(values, dtype=float)[indices].tolist()
            for name, values in conditions.items()
        }
        _, rates = _shortlist_pool(sampled, fraction)
        highest = max(rates.values())
        for name in names:
            rate_draws[name].append(rates[name])
            impact_draws[name].append(
                rates[name] / highest if highest > 0 else 1.0
            )
    return rate_draws, impact_draws


def _percentile_interval(values: list[float]) -> list[float] | None:
    if not values:
        return None
    return [
        float(np.quantile(values, 0.025)),
        float(np.quantile(values, 0.975)),
    ]


def build_shortlist_analysis(
    datasets: dict,
    score_index: dict,
    *,
    replicates: int = BOOTSTRAP_REPLICATES,
) -> dict:
    role_by_candidate = {
        candidate["candidate_id"]: candidate["job_id"]
        for candidate in datasets["candidates"]
    }
    scenarios = [
        ("E1", ("base", "group_a", "group_b"), (None,)),
        ("E3_COLLEGE", ("base", "twin"), (None,)),
        ("E3_PROJECT", ("base", "twin"), (None,)),
        ("E5", ("one-column", "two-column", "table"), ("pdf", "docx")),
        ("E7", ("base", "twin"), (None,)),
        ("E9", ("base", "twin"), (None,)),
        (
            "E10",
            ("repeat_mean", "section_reordering", "synonym_rewording"),
            (None,),
        ),
    ]
    group_rows = []
    contrast_rows = []

    for experiment, variants, formats in scenarios:
        for screener in SCREENERS:
            for file_format in formats:
                for role in ROLE_NAMES:
                    candidate_ids = sorted(
                        candidate_id
                        for candidate_id, candidate_role in role_by_candidate.items()
                        if candidate_role == role
                    )
                    complete_ids = [
                        candidate_id
                        for candidate_id in candidate_ids
                        if all(
                            (
                                experiment,
                                screener,
                                role,
                                candidate_id,
                                variant,
                                0 if variant == "repeat_mean" else 1,
                                file_format,
                            )
                            in score_index
                            for variant in variants
                        )
                    ]
                    conditions = {
                        variant: [
                            score_index[
                                (
                                    experiment,
                                    screener,
                                    role,
                                    candidate_id,
                                    variant,
                                    0 if variant == "repeat_mean" else 1,
                                    file_format,
                                )
                            ]
                            for candidate_id in complete_ids
                        ]
                        for variant in variants
                    }
                    if not complete_ids:
                        for variant in variants:
                            group_rows.append(
                                {
                                    "experiment_id": experiment,
                                    "screener_id": screener,
                                    "role": role,
                                    "file_format": file_format,
                                    "condition": variant,
                                    "n_expected": len(candidate_ids),
                                    "n_included": 0,
                                    "n_missing": len(candidate_ids),
                                    "shortlist_fraction": SHORTLIST_FRACTION,
                                    "shortlist_expected_count": None,
                                    "shortlist_rate": None,
                                    "shortlist_rate_ci_95": None,
                                    "impact_ratio_to_highest_group": None,
                                    "impact_ratio_ci_95": None,
                                    "impact_threshold": SHORTLIST_IMPACT_THRESHOLD,
                                    "below_impact_threshold": None,
                                    "tie_policy": (
                                        "fractional inclusion among exact-score "
                                        "ties crossing the top-20% boundary"
                                    ),
                                    "bootstrap_replicates": replicates,
                                    "bootstrap_seed": _stable_seed(
                                        f"shortlist|{experiment}|{screener}|{role}|"
                                        f"{file_format or 'all_formats'}"
                                    ),
                                }
                            )
                        continue
                    seed_label = (
                        f"shortlist|{experiment}|{screener}|{role}|"
                        f"{file_format or 'all_formats'}"
                    )
                    seed = _stable_seed(seed_label)
                    included, rates = _shortlist_pool(
                        conditions,
                        SHORTLIST_FRACTION,
                    )
                    rate_draws, impact_draws = _bootstrap_shortlist_rates(
                        conditions,
                        SHORTLIST_FRACTION,
                        seed,
                        replicates,
                    )
                    highest_rate = max(rates.values()) if rates else 0.0

                    for variant in variants:
                        rate = rates[variant]
                        impact = (
                            rate / highest_rate if highest_rate > 0 else 1.0
                        )
                        group_rows.append(
                            {
                                "experiment_id": experiment,
                                "screener_id": screener,
                                "role": role,
                                "file_format": file_format,
                                "condition": variant,
                                "n_expected": len(candidate_ids),
                                "n_included": len(complete_ids),
                                "n_missing": len(candidate_ids) - len(complete_ids),
                                "shortlist_fraction": SHORTLIST_FRACTION,
                                "shortlist_expected_count": (
                                    rate * len(complete_ids)
                                ),
                                "shortlist_rate": rate,
                                "shortlist_rate_ci_95": _percentile_interval(
                                    rate_draws[variant]
                                ),
                                "impact_ratio_to_highest_group": impact,
                                "impact_ratio_ci_95": _percentile_interval(
                                    impact_draws[variant]
                                ),
                                "impact_threshold": SHORTLIST_IMPACT_THRESHOLD,
                                "below_impact_threshold": (
                                    impact <= SHORTLIST_IMPACT_THRESHOLD
                                ),
                                "tie_policy": (
                                    "fractional inclusion among exact-score "
                                    "ties crossing the top-20% boundary"
                                ),
                                "bootstrap_replicates": replicates,
                                "bootstrap_seed": seed,
                            }
                        )

                    control = variants[0]
                    for treatment in variants[1:]:
                        deltas = np.asarray(included[treatment]) - np.asarray(
                            included[control]
                        )
                        delta_ci = bootstrap_mean_interval(
                            deltas.tolist(),
                            seed=_stable_seed(
                                seed_label + "|" + control + "|" + treatment
                            ),
                            replicates=replicates,
                        )
                        contrast_rows.append(
                            {
                                "experiment_id": experiment,
                                "screener_id": screener,
                                "role": role,
                                "file_format": file_format,
                                "control_condition": control,
                                "treatment_condition": treatment,
                                "n_expected": len(candidate_ids),
                                "n_included": len(complete_ids),
                                "n_missing": len(candidate_ids) - len(complete_ids),
                                "mean_inclusion_probability_change": (
                                    float(np.mean(deltas)) if len(deltas) else None
                                ),
                                "mean_change_ci_95": delta_ci,
                                "candidate_inclusion_changed_n": int(
                                    np.count_nonzero(np.abs(deltas) > 0)
                                ),
                                "candidate_inclusion_increased_n": int(
                                    np.count_nonzero(deltas > 0)
                                ),
                                "candidate_inclusion_decreased_n": int(
                                    np.count_nonzero(deltas < 0)
                                ),
                                "control_impact_ratio": (
                                    rates[control] / highest_rate
                                    if highest_rate > 0
                                    else 1.0
                                ),
                                "treatment_impact_ratio": (
                                    rates[treatment] / highest_rate
                                    if highest_rate > 0
                                    else 1.0
                                ),
                                "bootstrap_replicates": replicates,
                            }
                        )
    return {"groups": group_rows, "candidate_changes": contrast_rows}


def build_true_fit_validation(
    datasets: dict,
    score_index: dict,
    *,
    replicates: int = BOOTSTRAP_REPLICATES,
) -> list[dict]:
    candidate_by_id = {
        candidate["candidate_id"]: candidate for candidate in datasets["candidates"]
    }
    rows = []
    for screener in SCREENERS:
        for role_scope in ("all_roles", *ROLE_NAMES):
            candidate_ids = sorted(
                candidate_id
                for candidate_id, candidate in candidate_by_id.items()
                if role_scope == "all_roles" or candidate["job_id"] == role_scope
            )
            matched_ids = [
                candidate_id
                for candidate_id in candidate_ids
                if (
                    "E1",
                    screener,
                    candidate_by_id[candidate_id]["job_id"],
                    candidate_id,
                    "base",
                    1,
                    None,
                )
                in score_index
            ]
            scores = [
                score_index[
                    (
                        "E1",
                        screener,
                        candidate_by_id[candidate_id]["job_id"],
                        candidate_id,
                        "base",
                        1,
                        None,
                    )
                ]
                for candidate_id in matched_ids
            ]
            true_fit = [
                float(candidate_by_id[candidate_id]["true_fit"])
                for candidate_id in matched_ids
            ]
            seed = _stable_seed(
                f"true_fit|{screener}|{role_scope}"
            )
            correlation = spearman_summary(
                scores,
                true_fit,
                seed=seed,
                replicates=replicates,
                bootstrap_strata=[
                    candidate_by_id[candidate_id]["job_id"]
                    for candidate_id in matched_ids
                ],
            )
            correlation.update(
                {
                    "screener_id": screener,
                    "role": role_scope,
                    "n_expected": len(candidate_ids),
                    "n_missing": len(candidate_ids) - len(matched_ids),
                    "score_source": (
                        "S1 E1 baseline score"
                        if screener == "S1"
                        else "role-reference-normalized S2 E1 baseline score"
                    ),
                    "ground_truth": "synthetic True Fit proxy",
                    "pooled_role_caveat": (
                        "The pooled association may reflect between-role "
                        "differences; role-stratified estimates are primary."
                        if role_scope == "all_roles"
                        else None
                    ),
                    "p_adjusted_holm": None,
                }
            )
            rows.append(correlation)

    adjusted = holm_adjust([row["p_value"] for row in rows])
    for row, p_adjusted in zip(rows, adjusted):
        row["p_adjusted_holm"] = p_adjusted
    return rows


def _top_fraction_overlap(first: list[float], second: list[float]) -> float:
    first_inclusion = np.asarray(
        fractional_top_fraction(first, SHORTLIST_FRACTION),
        dtype=float,
    )
    second_inclusion = np.asarray(
        fractional_top_fraction(second, SHORTLIST_FRACTION),
        dtype=float,
    )
    expected_top_count = SHORTLIST_FRACTION * len(first)
    if expected_top_count == 0:
        return 1.0
    return float(np.sum(np.minimum(first_inclusion, second_inclusion)) / expected_top_count)


def build_stability_analysis(
    datasets: dict,
    score_index: dict,
    *,
    replicates: int = BOOTSTRAP_REPLICATES,
) -> dict:
    candidates_by_role = {
        role: sorted(
            candidate["candidate_id"]
            for candidate in datasets["candidates"]
            if candidate["job_id"] == role
        )
        for role in ROLE_NAMES
    }
    repeat_rows = []
    rank_rows = []
    for screener in SCREENERS:
        for role, candidate_ids in candidates_by_role.items():
            complete = [
                candidate_id
                for candidate_id in candidate_ids
                if all(
                    (
                        "E10",
                        screener,
                        role,
                        candidate_id,
                        "identical_repeat",
                        run_number,
                        None,
                    )
                    in score_index
                    for run_number in range(1, 6)
                )
            ]
            matrix = np.asarray(
                [
                    [
                        score_index[
                            (
                                "E10",
                                screener,
                                role,
                                candidate_id,
                                "identical_repeat",
                                run_number,
                                None,
                            )
                        ]
                        for run_number in range(1, 6)
                    ]
                    for candidate_id in complete
                ],
                dtype=float,
            )
            within_sd = (
                np.std(matrix, axis=1, ddof=1).tolist()
                if matrix.size
                else []
            )
            ranges = (
                (np.max(matrix, axis=1) - np.min(matrix, axis=1)).tolist()
                if matrix.size
                else []
            )
            seed = _stable_seed(f"e10_repeat|{screener}|{role}")
            pair_correlations = []
            pair_overlaps = []
            if matrix.size:
                for first in range(5):
                    for second in range(first + 1, 5):
                        correlation = stats.spearmanr(
                            matrix[:, first],
                            matrix[:, second],
                        ).statistic
                        if math.isfinite(float(correlation)):
                            pair_correlations.append(float(correlation))
                        pair_overlaps.append(
                            _top_fraction_overlap(
                                matrix[:, first].tolist(),
                                matrix[:, second].tolist(),
                            )
                        )
            repeat_rows.append(
                {
                    "screener_id": screener,
                    "role": role,
                    "n_expected": len(candidate_ids),
                    "n_included": len(complete),
                    "n_missing": len(candidate_ids) - len(complete),
                    "runs_per_candidate": 5,
                    "mean_within_candidate_sd": (
                        float(np.mean(within_sd)) if within_sd else None
                    ),
                    "mean_within_candidate_sd_ci_95": bootstrap_mean_interval(
                        within_sd,
                        seed=seed,
                        replicates=replicates,
                    ),
                    "median_within_candidate_sd": (
                        float(np.median(within_sd)) if within_sd else None
                    ),
                    "mean_candidate_range": (
                        float(np.mean(ranges)) if ranges else None
                    ),
                    "exactly_stable_candidate_percent": (
                        100.0
                        * sum(value == 0 for value in ranges)
                        / len(ranges)
                        if ranges
                        else None
                    ),
                    "icc_2_1_absolute_agreement": (
                        intraclass_correlation_2_1(matrix.tolist())
                        if matrix.size
                        else None
                    ),
                    "pairwise_run_correlations_n": len(pair_correlations),
                    "pairwise_run_spearman_mean": (
                        float(np.mean(pair_correlations))
                        if pair_correlations
                        else None
                    ),
                    "pairwise_run_spearman_min": (
                        min(pair_correlations) if pair_correlations else None
                    ),
                    "pairwise_run_top20_overlap_mean": (
                        float(np.mean(pair_overlaps))
                        if pair_overlaps
                        else None
                    ),
                    "bootstrap_replicates": BOOTSTRAP_REPLICATES,
                    "bootstrap_seed": seed,
                }
            )

            if not complete:
                continue
            baseline = np.mean(matrix, axis=1).tolist()
            for variant in ("section_reordering", "synonym_rewording"):
                variant_scores = [
                    score_index.get(
                        (
                            "E10",
                            screener,
                            role,
                            candidate_id,
                            variant,
                            1,
                            None,
                        )
                    )
                    for candidate_id in complete
                ]
                valid = [
                    index
                    for index, value in enumerate(variant_scores)
                    if value is not None
                ]
                if not valid:
                    continue
                base_values = [baseline[index] for index in valid]
                current_values = [variant_scores[index] for index in valid]
                correlation = spearman_summary(
                    base_values,
                    current_values,
                    seed=_stable_seed(
                        f"e10_rank|{screener}|{role}|{variant}"
                    ),
                    replicates=replicates,
                )
                correlation.update(
                    {
                        "screener_id": screener,
                        "role": role,
                        "comparison": f"repeat_mean_to_{variant}",
                        "n_expected": len(candidate_ids),
                        "n_missing": len(candidate_ids) - len(valid),
                        "top20_overlap": _top_fraction_overlap(
                            base_values,
                            current_values,
                        ),
                    }
                )
                rank_rows.append(correlation)

    adjusted = holm_adjust([row["p_value"] for row in rank_rows])
    for row, p_adjusted in zip(rank_rows, adjusted):
        row["p_adjusted_holm"] = p_adjusted
        row["holm_family"] = "all_e10_rank_stability_spearman_tests"
    return {"repeated_runs": repeat_rows, "rank_stability": rank_rows}


def run_analysis(
    datasets: dict,
    *,
    replicates: int = BOOTSTRAP_REPLICATES,
) -> dict:
    """Run all pre-specified comparisons on the validated datasets."""
    score_index = build_score_index(datasets)
    paired = build_paired_comparisons(
        datasets,
        score_index,
        replicates=replicates,
    )
    shortlist = build_shortlist_analysis(
        datasets,
        score_index,
        replicates=replicates,
    )
    true_fit = build_true_fit_validation(
        datasets,
        score_index,
        replicates=replicates,
    )
    stability = build_stability_analysis(
        datasets,
        score_index,
        replicates=replicates,
    )

    status_counts = defaultdict(int)
    for record in datasets["original_records"]:
        status_counts[
            f"{record['experiment_id']}|{record['screener_id']}|{record['status']}"
        ] += 1
    return {
        "analysis_version": "1.0",
        "bootstrap_replicates": replicates,
        "bootstrap_seed_base": BOOTSTRAP_SEED,
        "shortlist_fraction": SHORTLIST_FRACTION,
        "practical_score_threshold": PRACTICAL_SCORE_THRESHOLD,
        "shortlist_impact_threshold": SHORTLIST_IMPACT_THRESHOLD,
        "paired_comparisons": paired,
        "shortlist": shortlist,
        "true_fit_validation": true_fit,
        "stability": stability,
        "screening_status_counts": dict(sorted(status_counts.items())),
        "data_audit": datasets["audit"],
    }
