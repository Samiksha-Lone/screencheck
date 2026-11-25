"""Statistical methods for paired synthetic-screening experiments."""

import math

import numpy as np
from scipy import stats


BOOTSTRAP_REPLICATES = 10000
BOOTSTRAP_SEED = 42


def holm_adjust(p_values: list[float | None]) -> list[float | None]:
    """Return Holm-adjusted p-values while preserving input order."""
    adjusted = [None] * len(p_values)
    valid = [
        (index, float(value))
        for index, value in enumerate(p_values)
        if value is not None and math.isfinite(float(value))
    ]
    valid.sort(key=lambda item: item[1])
    total = len(valid)
    running_max = 0.0
    for rank, (index, value) in enumerate(valid):
        candidate = min(1.0, (total - rank) * value)
        running_max = max(running_max, candidate)
        adjusted[index] = running_max
    return adjusted


def _bootstrap_pair_statistics(
    differences: np.ndarray,
    seed: int,
    replicates: int,
    strata: list[str] | None = None,
) -> dict:
    generator = np.random.default_rng(seed)
    if strata is None:
        indices = generator.integers(
            0,
            len(differences),
            size=(replicates, len(differences)),
        )
    else:
        if len(strata) != len(differences):
            raise ValueError("Bootstrap strata must match the paired observations")
        indices = np.empty((replicates, len(differences)), dtype=int)
        strata_array = np.asarray(strata)
        for stratum in sorted(set(strata)):
            positions = np.flatnonzero(strata_array == stratum)
            sampled = generator.choice(
                positions,
                size=(replicates, len(positions)),
                replace=True,
            )
            indices[:, positions] = sampled
    samples = differences[indices]
    means = np.mean(samples, axis=1)
    medians = np.median(samples, axis=1)
    return {
        "mean_ci_95": [
            float(np.quantile(means, 0.025)),
            float(np.quantile(means, 0.975)),
        ],
        "median_ci_95": [
            float(np.quantile(medians, 0.025)),
            float(np.quantile(medians, 0.975)),
        ],
        "replicates": replicates,
        "seed": seed,
    }


def paired_summary(
    control_scores: list[float],
    treatment_scores: list[float],
    *,
    expected_n: int,
    seed: int = BOOTSTRAP_SEED,
    replicates: int = BOOTSTRAP_REPLICATES,
    bootstrap_strata: list[str] | None = None,
) -> dict:
    """Summarize paired score changes, tests, effects, and bootstrap intervals."""
    if len(control_scores) != len(treatment_scores):
        raise ValueError("Paired score lists must have equal lengths")
    if len(control_scores) > expected_n:
        raise ValueError("Observed pair count exceeds the expected sample size")

    control = np.asarray(control_scores, dtype=float)
    treatment = np.asarray(treatment_scores, dtype=float)
    if not np.all(np.isfinite(control)) or not np.all(np.isfinite(treatment)):
        raise ValueError("Paired scores must be finite")
    differences = treatment - control
    count = len(differences)
    summary = {
        "n_expected": expected_n,
        "n_included": count,
        "n_missing": expected_n - count,
        "control_mean": None,
        "treatment_mean": None,
        "mean_difference": None,
        "median_difference": None,
        "difference_sd": None,
        "control_sd": None,
        "spread_units": None,
        "cohen_dz": None,
        "rank_biserial": None,
        "higher_n": 0,
        "lower_n": 0,
        "tie_n": 0,
        "higher_percent": None,
        "absolute_change_over_5_percent": None,
        "wilcoxon_p": None,
        "sign_test_p": None,
        "mean_ci_95": None,
        "median_ci_95": None,
        "bootstrap_replicates": replicates,
        "bootstrap_seed": seed,
    }
    if count == 0:
        return summary

    positive = differences > 0
    negative = differences < 0
    nonzero = positive | negative
    higher_n = int(np.sum(positive))
    lower_n = int(np.sum(negative))
    tie_n = count - higher_n - lower_n
    difference_sd = (
        float(np.std(differences, ddof=1)) if count > 1 else 0.0
    )
    control_sd = float(np.std(control, ddof=1)) if count > 1 else 0.0

    if not np.any(nonzero):
        wilcoxon_p = 1.0
        sign_test_p = 1.0
        rank_biserial = 0.0
    else:
        wilcoxon_p = float(
            stats.wilcoxon(
                differences,
                zero_method="wilcox",
                alternative="two-sided",
                method="auto",
            ).pvalue
        )
        sign_test_p = float(
            stats.binomtest(
                higher_n,
                n=higher_n + lower_n,
                p=0.5,
                alternative="two-sided",
            ).pvalue
        )
        ranks = stats.rankdata(np.abs(differences[nonzero]), method="average")
        signed_ranks = np.sign(differences[nonzero]) * ranks
        rank_biserial = float(np.sum(signed_ranks) / np.sum(ranks))

    mean_difference = float(np.mean(differences))
    summary.update(
        {
            "control_mean": float(np.mean(control)),
            "treatment_mean": float(np.mean(treatment)),
            "mean_difference": mean_difference,
            "median_difference": float(np.median(differences)),
            "difference_sd": difference_sd,
            "control_sd": control_sd,
            "spread_units": (
                mean_difference / control_sd if control_sd > 0 else None
            ),
            "cohen_dz": (
                mean_difference / difference_sd if difference_sd > 0 else None
            ),
            "rank_biserial": rank_biserial,
            "higher_n": higher_n,
            "lower_n": lower_n,
            "tie_n": tie_n,
            "higher_percent": 100.0 * higher_n / count,
            "absolute_change_over_5_percent": (
                100.0 * np.count_nonzero(np.abs(differences) > 5.0) / count
            ),
            "wilcoxon_p": wilcoxon_p,
            "sign_test_p": sign_test_p,
        }
    )
    intervals = _bootstrap_pair_statistics(
        differences,
        seed,
        replicates,
        strata=bootstrap_strata,
    )
    summary["mean_ci_95"] = intervals["mean_ci_95"]
    summary["median_ci_95"] = intervals["median_ci_95"]
    return summary


def bootstrap_mean_interval(
    values: list[float],
    *,
    seed: int = BOOTSTRAP_SEED,
    replicates: int = BOOTSTRAP_REPLICATES,
) -> list[float] | None:
    """Calculate a percentile confidence interval by resampling observations."""
    if not values:
        return None
    array = np.asarray(values, dtype=float)
    if not np.all(np.isfinite(array)):
        raise ValueError("Bootstrap values must be finite")
    generator = np.random.default_rng(seed)
    indices = generator.integers(0, len(array), size=(replicates, len(array)))
    means = np.mean(array[indices], axis=1)
    return [
        float(np.quantile(means, 0.025)),
        float(np.quantile(means, 0.975)),
    ]


def spearman_summary(
    x_values: list[float],
    y_values: list[float],
    *,
    seed: int = BOOTSTRAP_SEED,
    replicates: int = BOOTSTRAP_REPLICATES,
    bootstrap_strata: list[str] | None = None,
) -> dict:
    """Report Spearman correlation with candidate-paired bootstrap uncertainty."""
    if len(x_values) != len(y_values):
        raise ValueError("Correlation inputs must have equal lengths")
    x = np.asarray(x_values, dtype=float)
    y = np.asarray(y_values, dtype=float)
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise ValueError("Correlation inputs must be finite")
    count = len(x)
    output = {
        "n": count,
        "rho": None,
        "p_value": None,
        "rho_ci_95": None,
        "bootstrap_replicates": replicates,
        "bootstrap_seed": seed,
    }
    if count < 2:
        return output
    result = stats.spearmanr(x, y)
    rho = float(result.statistic)
    p_value = float(result.pvalue)
    output.update({"rho": rho, "p_value": p_value})
    if not math.isfinite(rho):
        output["rho"] = None
        output["p_value"] = None
        return output

    generator = np.random.default_rng(seed)
    correlations = []
    batch_size = 1000
    strata_array = None
    if bootstrap_strata is not None:
        if len(bootstrap_strata) != count:
            raise ValueError("Correlation bootstrap strata length mismatch")
        strata_array = np.asarray(bootstrap_strata)
    for start in range(0, replicates, batch_size):
        current_size = min(batch_size, replicates - start)
        if strata_array is None:
            indices = generator.integers(
                0,
                count,
                size=(current_size, count),
            )
        else:
            indices = np.empty((current_size, count), dtype=int)
            for stratum in sorted(set(bootstrap_strata)):
                positions = np.flatnonzero(strata_array == stratum)
                sampled = generator.choice(
                    positions,
                    size=(current_size, len(positions)),
                    replace=True,
                )
                indices[:, positions] = sampled
        for row in indices:
            if np.ptp(x[row]) == 0 or np.ptp(y[row]) == 0:
                continue
            correlation = float(stats.spearmanr(x[row], y[row]).statistic)
            if math.isfinite(correlation):
                correlations.append(correlation)
    if correlations:
        output["rho_ci_95"] = [
            float(np.quantile(correlations, 0.025)),
            float(np.quantile(correlations, 0.975)),
        ]
    output["bootstrap_valid_replicates"] = len(correlations)
    return output


def intraclass_correlation_2_1(scores_by_candidate: list[list[float]]) -> float | None:
    """Calculate two-way random-effects, absolute-agreement ICC(2,1)."""
    matrix = np.asarray(scores_by_candidate, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] < 2 or matrix.shape[1] < 2:
        return None
    if not np.all(np.isfinite(matrix)):
        raise ValueError("ICC scores must be finite")
    subject_count, run_count = matrix.shape
    grand_mean = float(np.mean(matrix))
    subject_means = np.mean(matrix, axis=1)
    run_means = np.mean(matrix, axis=0)
    subject_ms = (
        run_count
        * float(np.sum((subject_means - grand_mean) ** 2))
        / (subject_count - 1)
    )
    run_ms = (
        subject_count
        * float(np.sum((run_means - grand_mean) ** 2))
        / (run_count - 1)
    )
    residuals = (
        matrix
        - subject_means[:, None]
        - run_means[None, :]
        + grand_mean
    )
    error_ms = float(np.sum(residuals**2)) / (
        (subject_count - 1) * (run_count - 1)
    )
    denominator = (
        subject_ms
        + (run_count - 1) * error_ms
        + run_count * (run_ms - error_ms) / subject_count
    )
    if denominator == 0:
        return None
    return float((subject_ms - error_ms) / denominator)


def fractional_top_fraction(
    scores: list[float],
    fraction: float = 0.20,
) -> list[float]:
    """Select the top fraction, sharing boundary ties fractionally."""
    if not 0.0 < fraction <= 1.0:
        raise ValueError("Shortlist fraction must be in (0, 1]")
    if not scores:
        return []
    values = np.asarray(scores, dtype=float)
    if not np.all(np.isfinite(values)):
        raise ValueError("Shortlist scores must be finite")
    remaining = fraction * len(values)
    inclusion = np.zeros(len(values), dtype=float)
    for score in sorted(set(float(value) for value in values), reverse=True):
        matching = np.flatnonzero(values == score)
        if remaining <= 0:
            break
        probability = min(1.0, remaining / len(matching))
        inclusion[matching] = probability
        remaining -= probability * len(matching)
    return inclusion.tolist()
