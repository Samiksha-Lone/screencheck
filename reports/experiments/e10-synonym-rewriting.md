# E10 — Synonym rewriting

## Research question, objective, and hypothesis

**Question.** Does replacing selected phrases with close synonyms change
scores or candidate rankings when the underlying qualifications and evidence
are intended to remain the same?

**Objective.** Measure sensitivity to small, meaning-preserving
experience/project rewording in the two in-house screeners.

**Hypothesis.** Small synonym substitutions should cause little or no score
or shortlist change.

## Background and rationale

Different wording can affect literal matching and embedding similarity even
when the author intends no change in evidence. E10's synonym treatment
replaces fixed phrases in synthetic experience and project content; it is
distinct from section reordering and repeated-run stability.

## Design and methods

| Element | Specification |
|---|---|
| Control | Original synthetic resume text |
| Treatment | Experience phrase changed to “Synthetic hands-on work with”; selected project details paraphrased |
| Manipulated variable | Selected wording in experience and project descriptions |
| Controlled variables | Candidate, role, job description, skills, project/experience facts and screener settings |
| Dataset | 300 candidates; 100 per role |
| Paired comparisons | 300 treatment-control candidate pairs; no missing pairs |
| Screeners | S1 and S2; S3 was skipped/unconfigured |

The substitutions are defined in `build_e10_pairs` in
[`twin_builder.py`](../../src/experiments/twin_builder.py). S1 uses weighted
keyword matches; S2 uses `all-MiniLM-L6-v2` with role-normalized scores.
Control scores are the candidate's means over five identical-input runs.

## Evaluation and statistical methods

Paired score changes receive 95% percentile bootstrap intervals from 10,000
candidate-level resamples. The output also reports median and spread-unit
changes, paired *dz*, matched rank-biserial effect, proportion higher,
proportion changing by more than five points, Wilcoxon signed-rank and sign
tests with Holm correction. Per-role rank stability uses Spearman
correlations and candidate-bootstrap intervals, plus top-20 overlap.
Shortlist rates and impact ratios use fractional ties and candidate-cluster
bootstrap intervals.

## Results

| Screener | n | Mean Δ (95% bootstrap CI) | Median Δ | Spread units | Rank-biserial | Higher | Absolute change > 5 | Wilcoxon p (Holm) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| S1 | 300 | 0.000 [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 0.0% | 0.0% | 1.000 (1.000) |
| S2 | 300 | 1.208 [0.701, 1.708] | 2.165 | 0.054 | 0.355 | 67.3% | 35.7% | <0.001 (<0.001) |

| Screener | Role | Rank Spearman ρ (95% bootstrap CI) | Top-20 overlap | Rank-test p (Holm) |
|---|---|---:|---:|---:|
| S1 | Backend | 1.000 [1.000, 1.000] | 1.000 | <0.001 (<0.001)* |
| S1 | Full-stack | 1.000 [1.000, 1.000] | 1.000 | <0.001 (<0.001)* |
| S1 | Data analyst | 1.000 [1.000, 1.000] | 1.000 | <0.001 (<0.001)* |
| S2 | Backend | 0.982 [0.965, 0.989] | 0.850 | <0.001 (<0.001) |
| S2 | Full-stack | 0.985 [0.970, 0.990] | 0.750 | <0.001 (<0.001) |
| S2 | Data analyst | 0.944 [0.900, 0.966] | 0.650 | <0.001 (<0.001) |

*For S1, the exact score and rank invariance means the raw and Holm-adjusted
rank-test p-values are not substantively informative.

S2's role-level paired mean changes were +4.316 for backend
(95% CI [3.627, 5.011]), +2.770 for full-stack ([2.190, 3.364]), and
-3.462 for data analyst ([-4.716, -2.272]). Its shortlist impact ratios
were 1.000, 1.000, and 0.542, respectively; the data-analyst treatment
shortlist rate was 13.0% versus 23.0% for the repeat-mean control.

![Pooled paired score changes, including synonym rewriting, with 95% bootstrap intervals](../analysis/figures/paired_score_changes.svg)

## Interpretation

S1 produced no score or rank changes. S2's pooled mean was a modest +1.208
points, but this masks opposite role-level directions: positive in backend
and full-stack, negative for data analyst. S2 rankings stayed relatively
highly correlated, yet top-20 overlap was 65–85%, with reduced inclusion in
the data-analyst treatment pool. Thus, a modest pooled average does not mean
all candidates or roles were insensitive. These outcomes describe this
specific synthetic wording and embedding model.

## Limitations, confounders, deviations, and null findings

- The substitutions are intended as close synonyms but semantic equivalence
  cannot be assumed for every model or context.
- Only selected experience and project phrases were rewritten.
- Pooled S2 mean is small and S1 is an exact null; role-specific S2 effects
  include both directions and are retained.
- Shortlist impact reflects the synthetic pool and is not evidence of
  real-world unfairness or legal violations.
- S3 was unconfigured and excluded.

## Conclusion

Synonym rewriting did not affect S1, while S2 showed a small pooled shift
that concealed opposite role-level movements and changed shortlist overlap.
The experiment indicates sensitivity to this wording in this benchmark, not
a general effect of synonym use.

## Reproducibility

- Variant construction and scoring: [`twin_builder.py`](../../src/experiments/twin_builder.py)
  (`build_e10_pairs`) and
  [`experiment_runner.py`](../../src/experiments/experiment_runner.py)
  (`variant_resume_text`).
- Source results:
  `data/private/experiments/experiment_results.jsonl`,
  SHA-256 `2433a2925afbf55bc1108a31da1bd53a28d1da982980a1150171626c4d18e4c4`.
- Estimates:
  [`analysis_results.json`](../analysis/analysis_results.json),
  [`paired_comparisons.csv`](../analysis/paired_comparisons.csv),
  [`stability_rank_comparisons.csv`](../analysis/stability_rank_comparisons.csv),
  and [`shortlist_group_rates.csv`](../analysis/shortlist_group_rates.csv).
- Existing aggregate command: `python -m src.stats.run_analysis`
  (documented, not rerun for this report).
