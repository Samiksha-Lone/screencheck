# E9 — Honest improvements

## Research question, objective, and hypothesis

**Question.** Does a package of relevant, evidence-oriented resume
improvements increase screening scores and shortlist inclusion?

**Objective.** Compare a synthetic base resume with a variant that adds a
role-specific project and makes its experience descriptions more specific.

**Hypothesis.** Adding relevant evidence and clearer, quantified outcomes
will increase scores and shortlist inclusion.

## Background and rationale

E9 contrasts evidence-bearing content changes with E7's unsupported keyword
list. It evaluates a combined improvement package, not the isolated causal
contribution of each edit. Project facts and outcomes are synthetic.

## Design and methods

| Element | Specification |
|---|---|
| Control | Original synthetic candidate resume |
| Treatment | One role-specific project, project-evidence score of 10, and revised experience summaries with simulated 15% outcomes |
| Manipulated variables | Project text/details, `project_evidence`, and all experience summaries |
| Controlled variables | Candidate identity/role, job description, underlying candidate record and screener implementation |
| Dataset | 300 candidates; 100 each in backend, full-stack and data-analyst roles |
| Paired comparisons | 300 treatment-control pairs; no missing pairs |
| Screeners | S1 keyword matcher and S2 embedding matcher; S3 was skipped/unconfigured |

Project templates are role-specific and shared with the E3 project evidence
experiment. Experience descriptions are rewritten from “Fictional experience
using” to “Built and measured work using” and append a simulated 15% outcome.
S1 uses weighted skill matches; S2 uses `all-MiniLM-L6-v2` on the
role-normalized scale.

## Evaluation and statistical methods

Paired score changes, 95% percentile bootstrap intervals (10,000
candidate-level resamples), spread-unit and paired effects, rank-biserial
correlations, proportions higher and above five points, Wilcoxon
signed-rank and sign tests with Holm correction are read from the existing
analysis outputs. Top-20 shortlist rates use role-specific pools, fractional
ties and candidate-cluster bootstrap intervals.

## Results

| Screener | n | Mean Δ (95% bootstrap CI) | Median Δ | Spread units | Rank-biserial | Higher | Absolute change > 5 | Wilcoxon p (Holm) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| S1 | 300 | 1.208 [0.833, 1.583] | 0.000 | 0.053 | 1.000 | 9.7% | 9.7% | <0.001 (<0.001) |
| S2 | 300 | 12.275 [11.025, 13.559] | 10.770 | 0.551 | 0.905 | 87.3% | 75.0% | <0.001 (<0.001) |

| Screener / role | Base shortlist rate (impact ratio; 95% CI) | Improved rate (impact ratio; 95% CI) |
|---|---:|---:|
| S1 — backend | 20.0% (1.000; [1.000, 1.000]) | 20.0% (1.000; [1.000, 1.000]) |
| S1 — full-stack | 17.5% (0.778; [0.630, 0.920]) | 22.5% (1.000; [1.000, 1.000]) |
| S1 — data analyst | 20.0% (1.000; [1.000, 1.000]) | 20.0% (1.000; [1.000, 1.000]) |
| S2 — backend | 11.0% (0.379; [0.250, 0.739]) | 29.0% (1.000; [1.000, 1.000]) |
| S2 — full-stack | 14.0% (0.538; [0.333, 0.818]) | 26.0% (1.000; [1.000, 1.000]) |
| S2 — data analyst | 9.0% (0.290; [0.176, 0.481]) | 31.0% (1.000; [1.000, 1.000]) |

The S1 mean is below the three-point threshold, with a zero median and a
small proportion of changed candidates. S2's mean is above the threshold and
its bootstrap interval is positive. Both screeners had significant paired
tests, reflecting that a small consistent S1 shift can test as nonzero even
when the average practical effect is small.

![Pooled paired score changes, including E9, with 95% bootstrap intervals](../analysis/figures/paired_score_changes.svg)

## Interpretation

S2 responded strongly to the combined project-and-specificity package, with
higher scores for most candidates and higher shortlist rates in all three
roles. S1 showed a smaller average shift and no shortlist-rate change for
backend or data analyst. The data support a response to this composite
synthetic content change; they do not isolate the effect of the project,
quantification, or wording individually, nor prove improvement in actual
candidate quality.

## Limitations, confounders, deviations, and null findings

- Multiple treatment elements changed together. The design does not isolate
  project addition from revised wording or simulated metrics.
- All projects, work histories and quantified outcomes are fictional.
- S1's zero median and unchanged rates in two roles are null/small findings
  and are reported alongside its significant paired test.
- S2's large changes may be specific to the embedding model and phrasing.
- Shortlist impact is benchmark-specific; no inference about unfairness or
  legal violations follows.
- S3 was unconfigured and excluded.

## Conclusion

The combined honest-improvement variant raised S2 scores and shortlist rates
substantially in this synthetic benchmark. S1's average score shift was
small despite statistical detectability. Follow-up experiments would need to
separate individual edits before attributing effects to any one component.

## Reproducibility

- Treatment construction: [PLAN.md](../../PLAN.md) and
  [`twin_builder.py`](../../src/experiments/twin_builder.py)
  (`ROLE_PROJECTS`, `build_e9_pairs`).
- Candidate data: `data/generated/*_candidates.json`; seed 42;
  `data/private/twins/twin_manifest.json` records 300 valid pairs and zero
  validation failures.
- Original results:
  `data/private/experiments/experiment_results.jsonl`,
  SHA-256 `2433a2925afbf55bc1108a31da1bd53a28d1da982980a1150171626c4d18e4c4`.
- Results: [`analysis_results.json`](../analysis/analysis_results.json),
  [`paired_comparisons.csv`](../analysis/paired_comparisons.csv),
  [`shortlist_group_rates.csv`](../analysis/shortlist_group_rates.csv), and
  [`shortlist_inclusion_changes.csv`](../analysis/shortlist_inclusion_changes.csv).
- Existing analysis command: `python -m src.stats.run_analysis`
  (documented, not rerun for this report).
