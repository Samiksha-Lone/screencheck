"""Write aggregate research tables, reports, and lightweight SVG figures."""

import csv
import html
import json
import math
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT_DIR = PROJECT_ROOT / "reports" / "analysis"

EXPERIMENT_TITLES = {
    "E1": "Name-coded groups",
    "E3_COLLEGE": "College prestige",
    "E3_PROJECT": "Project evidence",
    "E5": "Resume layout",
    "E7": "Keyword stuffing",
    "E9": "Genuine resume improvements",
    "E10": "Screening stability",
}


def _clean(value):
    if isinstance(value, dict):
        return {key: _clean(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _format(value, digits: int = 3) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: json.dumps(value, sort_keys=True)
                    if isinstance(value, (dict, list, tuple))
                    else value
                    for key, value in row.items()
                }
            )


def _paired_label(row: dict) -> str:
    label = (
        f"{row['experiment_id']} {row['comparison']} "
        f"{row['screener_id']}"
    )
    if row.get("file_format"):
        label += f" {row['file_format'].upper()}"
    return label


def _svg_text(x: float, y: float, text: str, *, size: int = 12, anchor: str = "start") -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" '
        f'text-anchor="{anchor}" fill="#24313a">'
        f"{html.escape(str(text))}</text>"
    )


def _paired_figure(rows: list[dict], path: Path) -> None:
    data = [
        row
        for row in rows
        if row["role"] == "all_roles"
        and row["mean_difference"] is not None
    ]
    data.sort(
        key=lambda row: (
            row["experiment_id"],
            row.get("file_format") or "",
            row["comparison"],
            row["screener_id"],
        )
    )
    width = 1120
    left = 360
    right = 95
    top = 72
    row_height = 25
    bottom = 54
    height = top + row_height * max(1, len(data)) + bottom
    lows = [
        row["mean_ci_95"][0]
        for row in data
        if row.get("mean_ci_95")
    ]
    highs = [
        row["mean_ci_95"][1]
        for row in data
        if row.get("mean_ci_95")
    ]
    minimum = min([-1.0] + lows)
    maximum = max([1.0] + highs)
    span = maximum - minimum or 1.0
    minimum -= 0.06 * span
    maximum += 0.06 * span
    plot_width = width - left - right

    def x_position(value: float) -> float:
        return left + (value - minimum) / (maximum - minimum) * plot_width

    pieces = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        _svg_text(left, 26, "Paired score change with 95% candidate-bootstrap CI", size=18),
        _svg_text(left, 48, "Positive values indicate a higher treatment-condition score.", size=12),
    ]
    zero_x = x_position(0.0)
    pieces.append(
        f'<line x1="{zero_x:.1f}" y1="{top-8}" x2="{zero_x:.1f}" '
        f'y2="{height-bottom}" stroke="#687780" stroke-dasharray="4 4"/>'
    )
    for index, row in enumerate(data):
        y = top + index * row_height
        label = _paired_label(row)
        pieces.append(_svg_text(left - 10, y + 4, label, size=11, anchor="end"))
        interval = row.get("mean_ci_95")
        if interval:
            low_x, high_x = x_position(interval[0]), x_position(interval[1])
            pieces.append(
                f'<line x1="{low_x:.1f}" y1="{y}" x2="{high_x:.1f}" '
                f'y2="{y}" stroke="#276678" stroke-width="2"/>'
            )
        mean_x = x_position(row["mean_difference"])
        pieces.append(
            f'<circle cx="{mean_x:.1f}" cy="{y}" r="3.5" fill="#d1495b"/>'
        )
    tick_count = 6
    for tick in range(tick_count + 1):
        value = minimum + (maximum - minimum) * tick / tick_count
        x = x_position(value)
        pieces.append(
            f'<line x1="{x:.1f}" y1="{height-bottom}" x2="{x:.1f}" '
            f'y2="{height-bottom+5}" stroke="#24313a"/>'
        )
        pieces.append(
            _svg_text(x, height - 23, f"{value:.1f}", size=10, anchor="middle")
        )
    pieces.append(
        _svg_text(left + plot_width / 2, height - 5, "Score-point change (treatment − control)", size=11, anchor="middle")
    )
    pieces.append("</svg>")
    path.write_text("\n".join(pieces), encoding="utf-8")


def _correlation_figure(rows: list[dict], path: Path) -> None:
    data = [row for row in rows if row["role"] != "all_roles" and row["rho"] is not None]
    data.sort(key=lambda row: (row["role"], row["screener_id"]))
    width = 900
    height = 80 + 38 * max(1, len(data)) + 48
    left, right, top = 210, 70, 62
    plot_width = width - left - right
    pieces = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        _svg_text(left, 28, "Screener association with synthetic True Fit", size=17),
        _svg_text(left, 48, "Role-stratified Spearman ρ with candidate-bootstrap 95% CI", size=11),
    ]
    for tick in (-1.0, -0.5, 0.0, 0.5, 1.0):
        x = left + (tick + 1.0) / 2.0 * plot_width
        pieces.append(
            f'<line x1="{x:.1f}" y1="{top-8}" x2="{x:.1f}" y2="{height-48}" '
            f'stroke="#e2e7e9"/>'
        )
        pieces.append(_svg_text(x, height - 23, f"{tick:.1f}", size=10, anchor="middle"))
    for index, row in enumerate(data):
        y = top + index * 38
        label = f"{row['role']} · {row['screener_id']}"
        pieces.append(_svg_text(left - 10, y + 4, label, size=11, anchor="end"))
        interval = row.get("rho_ci_95")
        if interval:
            low = left + (interval[0] + 1) / 2 * plot_width
            high = left + (interval[1] + 1) / 2 * plot_width
            pieces.append(
                f'<line x1="{low:.1f}" y1="{y}" x2="{high:.1f}" '
                f'y2="{y}" stroke="#276678" stroke-width="2"/>'
            )
        rho_x = left + (row["rho"] + 1) / 2 * plot_width
        pieces.append(f'<circle cx="{rho_x:.1f}" cy="{y}" r="4" fill="#d1495b"/>')
    pieces.append("</svg>")
    path.write_text("\n".join(pieces), encoding="utf-8")


def _stability_figure(rows: list[dict], path: Path) -> None:
    data = [row for row in rows if row["mean_within_candidate_sd"] is not None]
    data.sort(key=lambda row: (row["role"], row["screener_id"]))
    width = 900
    height = 80 + 38 * max(1, len(data)) + 48
    left, right, top = 260, 70, 62
    plot_width = width - left - right
    maximum = max(
        [0.01]
        + [row["mean_within_candidate_sd"] for row in data]
        + [
            row["mean_within_candidate_sd_ci_95"][1]
            for row in data
            if row["mean_within_candidate_sd_ci_95"]
        ]
    )
    pieces = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        _svg_text(left, 28, "E10 repeated-run score variability", size=17),
        _svg_text(left, 48, "Mean within-candidate SD across five identical runs", size=11),
    ]
    for index, row in enumerate(data):
        y = top + index * 38
        pieces.append(
            _svg_text(left - 10, y + 4, f"{row['role']} · {row['screener_id']}", size=11, anchor="end")
        )
        interval = row.get("mean_within_candidate_sd_ci_95")
        if interval:
            low = left + interval[0] / maximum * plot_width
            high = left + interval[1] / maximum * plot_width
            pieces.append(
                f'<line x1="{low:.1f}" y1="{y}" x2="{high:.1f}" '
                f'y2="{y}" stroke="#276678" stroke-width="2"/>'
            )
        point = left + row["mean_within_candidate_sd"] / maximum * plot_width
        pieces.append(f'<circle cx="{point:.1f}" cy="{y}" r="4" fill="#d1495b"/>')
    pieces.append("</svg>")
    path.write_text("\n".join(pieces), encoding="utf-8")


def _methodology_markdown() -> str:
    return """# Statistical methods and limitations

## Data sources and exclusions

The analysis is regenerated from the immutable Phase 6 JSONL, the role-reference
normalized S2 dataset, the approved extracted-text E5 layout dataset, and the
synthetic base candidate files. E5 conclusions use only the versioned
layout-aware dataset. The earlier E5 legacy records are excluded because their
S1 inputs bypassed layout extraction and their S2 similarities were copied
from table-layout records. All S3 rows are recorded as skipped and are not
analyzed.

The S2 values outside E5 use the frozen role-specific min/max references built
from 100 original base candidates per role. E5 S2 retains raw cosine similarity;
for score-point contrasts only, it is mapped by `50 * (cosine + 1)` to a fixed
0–100 scale. This is a fixed transformation, not a sample- or role-based
rescaling.

## Matched score comparisons

Each contrast is paired by base candidate ID, role, experiment condition, and
where applicable file format. Reported differences are treatment minus control.
The primary paired test is the two-sided Wilcoxon signed-rank test; the exact
two-sided sign test is also reported as a distribution-light sensitivity
analysis. Ties are retained in descriptive summaries and omitted only from
the sign-test denominator. Mean and median differences receive percentile
confidence intervals from 10,000 candidate-level paired bootstrap samples.

Effect sizes include mean change divided by the control-score standard
deviation, paired Cohen's dz, and matched rank-biserial correlation. Holm
adjustment is applied to the family of all estimable pooled and role-stratified
Wilcoxon tests. True Fit correlation tests use a separate Holm family.
E10 rank-stability Spearman tests use their own Holm-adjusted family.

## Shortlists

Shortlists use the pre-specified top 20% within each job role. For E5, PDF and
DOCX are separate pools. Each experiment's compared conditions are pooled
within role (and format for E5), as specified in the research plan for matched
conditions. If an exact-score tie crosses the cutoff, tied observations share
the remaining shortlist slots fractionally. Rates, impact ratios, and matched
candidate inclusion changes receive candidate-cluster bootstrap intervals.
The impact ratio is a screening heuristic; it is not a legal finding.

## True Fit and stability

S1 and S2 are correlated with synthetic True Fit using Spearman's rho, with
candidate-paired bootstrap intervals. Role-specific results are primary;
pooled associations may reflect between-role score differences. True Fit is a
constructed research proxy, not real-world hiring truth.

E10 identical-input stability uses five runs per candidate. Score variability
is summarized within candidate and reliability is estimated with two-way
random-effects, absolute-agreement ICC(2,1). Run-rank correlations and top-20%
overlap are descriptive. Reordered and synonym-reworded inputs are compared
with each candidate's mean identical-run score; candidate identity is the
resampling unit.

## Practical thresholds and interpretation

The research plan's thresholds are retained: an absolute score change of at
least 3 points or an impact ratio at or below 0.80 is flagged for follow-up.
These are investigation thresholds, not tests of fairness or legal compliance.
E1 uses synthetic name-coded groups; results do not establish effects for real
identities. E7 score gains do not imply improved candidate quality.

## Reproducibility

Bootstrap resampling uses NumPy's generator with a fixed base seed of 42 and
comparison-specific deterministic seeds. Dataset hashes, sample sizes,
exclusions, score scales, and analysis parameters are recorded in the
machine-readable output and data provenance note.
"""


def _comparison_table(rows: list[dict]) -> str:
    lines = [
        "| Comparison | Screener | Format | n / expected | Mean Δ (95% CI) | Median Δ | "
        "Spread units | Rank-biserial | Wilcoxon p (Holm) | Sign p |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        if row["role"] != "all_roles":
            continue
        interval = row.get("mean_ci_95")
        ci = (
            f"[{_format(interval[0])}, {_format(interval[1])}]"
            if interval
            else "—"
        )
        lines.append(
            "| "
            + " | ".join(
                (
                    row["comparison"],
                    row["screener_id"],
                    row.get("file_format") or "—",
                    f"{row['n_included']} / {row['n_expected']}",
                    f"{_format(row['mean_difference'])} {ci}",
                    _format(row["median_difference"]),
                    _format(row["spread_units"]),
                    _format(row["rank_biserial"]),
                    f"{_format(row['wilcoxon_p'], 4)} "
                    f"({_format(row['p_adjusted_holm'], 4)})",
                    _format(row["sign_test_p"], 4),
                )
            )
            + " |"
        )
    return "\n".join(lines)


def _experiment_report(experiment: str, result: dict) -> str:
    title = EXPERIMENT_TITLES[experiment]
    comparisons = [
        row
        for row in result["paired_comparisons"]
        if row["experiment_id"] == experiment
    ]
    shortlist = [
        row
        for row in result["shortlist"]["groups"]
        if row["experiment_id"] == experiment
    ]
    lines = [
        f"# {experiment} — {title}",
        "",
        "All tables contain aggregate results only. Candidate IDs and names are not published.",
        "",
        "## Matched score comparisons",
        "",
        _comparison_table(comparisons),
        "",
        "Role-stratified estimates and all missing-pair counts are available in `analysis_results.json`.",
        "",
        "## Top-20% shortlist rates and impact ratios",
        "",
        "| Screener | Role | Format | Condition | n | Rate | Impact ratio | 95% CI |",
        "|---|---|---|---|---:|---:|---:|---:|",
    ]
    for row in shortlist:
        interval = row["impact_ratio_ci_95"]
        interval_text = (
            f"[{_format(interval[0])}, {_format(interval[1])}]"
            if interval
            else "—"
        )
        lines.append(
            f"| {row['screener_id']} | {row['role']} | "
            f"{row['file_format'] or '—'} | {row['condition']} | "
            f"{row['n_included']}/{row['n_expected']} | "
            f"{_format(row['shortlist_rate'] * 100, 1)}% | "
            f"{_format(row['impact_ratio_to_highest_group'])} | "
            f"{interval_text} |"
        )
    if experiment == "E1":
        lines.extend(
            [
                "",
                "Name-coded groups are synthetic test labels; these results do not establish effects for real identities.",
            ]
        )
    if experiment == "E7":
        lines.extend(
            [
                "",
                "A score increase from keyword stuffing is not evidence of improved candidate quality.",
            ]
        )
    if experiment == "E5":
        lines.extend(
            [
                "",
                "Only the extracted-text layout-aware dataset was used. PDF and DOCX are reported separately; legacy E5 rows are excluded.",
            ]
        )
    if experiment == "E10":
        lines.extend(
            [
                "",
                "## Repeated-run variability",
                "",
                "| Screener | Role | n | Mean within-candidate SD | ICC(2,1) | Pairwise run ρ | Top-20 overlap |",
                "|---|---|---:|---:|---:|---:|---:|",
            ]
        )
        for row in result["stability"]["repeated_runs"]:
            lines.append(
                f"| {row['screener_id']} | {row['role']} | "
                f"{row['n_included']} | "
                f"{_format(row['mean_within_candidate_sd'])} | "
                f"{_format(row['icc_2_1_absolute_agreement'])} | "
                f"{_format(row['pairwise_run_spearman_mean'])} | "
                f"{_format(row['pairwise_run_top20_overlap_mean'])} |"
            )
        lines.extend(
            [
                "",
                "## Rank stability after input changes",
                "",
                "| Screener | Role | Comparison | n | Spearman ρ (95% CI) | Top-20 overlap | Holm p |",
                "|---|---|---|---:|---:|---:|---:|",
            ]
        )
        for row in result["stability"]["rank_stability"]:
            interval = row["rho_ci_95"]
            ci = (
                f"[{_format(interval[0])}, {_format(interval[1])}]"
                if interval
                else "—"
            )
            lines.append(
                f"| {row['screener_id']} | {row['role']} | "
                f"{row['comparison']} | {row['n']} | "
                f"{_format(row['rho'])} {ci} | "
                f"{_format(row['top20_overlap'])} | "
                f"{_format(row['p_adjusted_holm'], 4)} |"
            )
    return "\n".join(lines) + "\n"


def _summary_markdown(result: dict) -> str:
    pooled = [
        row
        for row in result["paired_comparisons"]
        if row["role"] == "all_roles"
    ]
    meaningful = [
        row
        for row in pooled
        if row["practical_score_effect"] is True
        or (
            row["mean_difference"] is not None
            and abs(row["mean_difference"]) >= 3.0
        )
    ]
    shortlist_flags = [
        row
        for row in result["shortlist"]["groups"]
        if row.get("impact_ratio_to_highest_group") is not None
        and row["impact_ratio_to_highest_group"] <= 0.80
    ]
    lines = [
        "# ScreenCheck statistical analysis",
        "",
        "This report summarizes controlled experiments on synthetic resumes and in-house screening systems. It does not evaluate commercial hiring products.",
        "",
        "## Data integrity and coverage",
        "",
        f"- Phase 6: {result['data_audit']['phase6']['record_count']:,} records; "
        f"SHA-256 `{result['data_audit']['phase6']['sha256']}`.",
        f"- S1 and S2: 6,000 completed observations each. S3: "
        f"{result['data_audit']['phase6']['status_counts']['S3|skipped']:,} explicitly skipped; no S3 scores were inferred.",
        f"- Approved E5: {result['data_audit']['genuine_e5_layout']['record_count']:,} complete layout-aware records from "
        f"{result['data_audit']['genuine_e5_layout']['extraction_hashes_checked']:,} verified document extractions.",
        "- The earlier E5 legacy records are superseded and excluded from all layout analyses.",
        "",
        "## Pooled matched score comparisons",
        "",
        _comparison_table(pooled),
        "",
        "## Practical score changes",
        "",
    ]
    if meaningful:
        for row in meaningful:
            interval = row.get("mean_ci_95")
            ci = (
                f"[{_format(interval[0])}, {_format(interval[1])}]"
                if interval
                else "CI unavailable"
            )
            lines.append(
                f"- {row['experiment_id']} {row['comparison']} {row['screener_id']}"
                + (f" ({row['file_format'].upper()})" if row["file_format"] else "")
                + f": mean change {_format(row['mean_difference'])} points "
                f"({ci}; n={row['n_included']})."
            )
    else:
        lines.append("- No pooled paired score contrast crossed the 3-point practical threshold.")
    lines.extend(["", "## Shortlist impact flags", ""])
    if shortlist_flags:
        for row in shortlist_flags:
            lines.append(
                f"- {row['experiment_id']} {row['screener_id']} "
                f"{row['role']} "
                + (f"{row['file_format'].upper()} " if row["file_format"] else "")
                + f"{row['condition']}: impact ratio "
                f"{_format(row['impact_ratio_to_highest_group'])} "
                f"(95% CI "
                f"{_format(row['impact_ratio_ci_95'][0])} to "
                f"{_format(row['impact_ratio_ci_95'][1])}; "
                f"n={row['n_included']})."
            )
    else:
        lines.append("- No observed group impact ratio was at or below 0.80.")
    lines.extend(
        [
            "",
            "## True Fit validation",
            "",
            "| Screener | Role | n | Spearman ρ | 95% CI | Holm p |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in result["true_fit_validation"]:
        interval = row["rho_ci_95"]
        ci = (
            f"[{_format(interval[0])}, {_format(interval[1])}]"
            if interval
            else "—"
        )
        lines.append(
            f"| {row['screener_id']} | {row['role']} | {row['n']} | "
            f"{_format(row['rho'])} | {ci} | "
            f"{_format(row['p_adjusted_holm'], 4)} |"
        )
    lines.extend(
        [
            "",
            "True Fit is a synthetic research proxy, not real-world hiring truth. Pooled correlations may reflect role differences.",
            "",
            "## E10 stability",
            "",
            "| Screener | Role | n | Mean within-candidate SD | ICC(2,1) | Pairwise run ρ | Top-20 overlap |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in result["stability"]["repeated_runs"]:
        lines.append(
            f"| {row['screener_id']} | {row['role']} | {row['n_included']} | "
            f"{_format(row['mean_within_candidate_sd'])} | "
            f"{_format(row['icc_2_1_absolute_agreement'])} | "
            f"{_format(row['pairwise_run_spearman_mean'])} | "
            f"{_format(row['pairwise_run_top20_overlap_mean'])} |"
        )
    lines.extend(
        [
            "",
            "### Rank stability after input changes",
            "",
            "| Screener | Role | Comparison | n | Spearman ρ (95% CI) | Top-20 overlap | Holm p |",
            "|---|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in result["stability"]["rank_stability"]:
        interval = row["rho_ci_95"]
        ci = (
            f"[{_format(interval[0])}, {_format(interval[1])}]"
            if interval
            else "—"
        )
        lines.append(
            f"| {row['screener_id']} | {row['role']} | "
            f"{row['comparison']} | {row['n']} | "
            f"{_format(row['rho'])} {ci} | "
            f"{_format(row['top20_overlap'])} | "
            f"{_format(row['p_adjusted_holm'], 4)} |"
        )
    lines.extend(
        [
            "",
            "## Figures and detailed results",
            "",
            "- [Paired score changes](figures/paired_score_changes.svg)",
            "- [True Fit correlations](figures/true_fit_correlations.svg)",
            "- [E10 repeat variability](figures/e10_repeat_variability.svg)",
            "- Detailed machine-readable estimates: `analysis_results.json`.",
            "- Methods, tie policy, thresholds, and limitations: [methodology](methodology.md).",
        ]
    )
    return "\n".join(lines) + "\n"


def write_analysis_outputs(
    result: dict,
    output_dir: str | Path = DEFAULT_REPORT_DIR,
) -> dict:
    """Write aggregate-only analysis data, experiment reports, and figures."""
    output_dir = Path(output_dir)
    experiment_dir = output_dir / "experiments"
    figure_dir = output_dir / "figures"
    experiment_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    cleaned = _clean(result)
    (output_dir / "analysis_results.json").write_text(
        json.dumps(cleaned, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    _write_csv(
        output_dir / "paired_comparisons.csv",
        cleaned["paired_comparisons"],
    )
    _write_csv(
        output_dir / "shortlist_group_rates.csv",
        cleaned["shortlist"]["groups"],
    )
    _write_csv(
        output_dir / "shortlist_inclusion_changes.csv",
        cleaned["shortlist"]["candidate_changes"],
    )
    _write_csv(
        output_dir / "true_fit_correlations.csv",
        cleaned["true_fit_validation"],
    )
    _write_csv(
        output_dir / "stability_repeated_runs.csv",
        cleaned["stability"]["repeated_runs"],
    )
    _write_csv(
        output_dir / "stability_rank_comparisons.csv",
        cleaned["stability"]["rank_stability"],
    )
    (output_dir / "methodology.md").write_text(
        _methodology_markdown(),
        encoding="utf-8",
    )
    (output_dir / "summary.md").write_text(
        _summary_markdown(cleaned),
        encoding="utf-8",
    )

    experiment_files = {}
    for experiment in EXPERIMENT_TITLES:
        filename = f"{experiment.lower()}_analysis.md"
        (experiment_dir / filename).write_text(
            _experiment_report(experiment, cleaned),
            encoding="utf-8",
        )
        experiment_files[experiment] = f"experiments/{filename}"

    _paired_figure(
        cleaned["paired_comparisons"],
        figure_dir / "paired_score_changes.svg",
    )
    _correlation_figure(
        cleaned["true_fit_validation"],
        figure_dir / "true_fit_correlations.svg",
    )
    _stability_figure(
        cleaned["stability"]["repeated_runs"],
        figure_dir / "e10_repeat_variability.svg",
    )
    return {
        "output_dir": str(output_dir),
        "experiment_reports": experiment_files,
        "aggregate_only": True,
    }
