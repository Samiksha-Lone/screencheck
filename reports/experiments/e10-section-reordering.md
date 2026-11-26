# E10 — Section reordering

## Research question, objective, and hypothesis

**Question.** Does moving the resume summary from the first to the last
section change scores or candidate rankings when section content is
otherwise unchanged?

**Objective.** Test sensitivity to a harmless change in section order for
the keyword and embedding screeners.

**Hypothesis.** Section reordering will have little or no effect on score or
shortlist outcomes.

## Background and rationale

Screeners can depend on order-sensitive text representations even when
qualifications remain unchanged. The E10 variant changes only a defined
section-order sequence and is distinct from the repeated-run and
synonym-rewriting reports.

## Design and methods

| Element | Specification |
|---|---|
| Control | `summary → skills → experience → projects` |
| Treatment | `skills → experience → projects → summary` |
| Manipulated variable | Section order |
| Controlled variables | Candidate content, role, job description, section text and screener settings |
| Dataset | 300 candidates; 100 per role |
| Paired comparisons | 300 treatment-to-control candidate pairs; no missing pairs |
| Screeners | S1 and S2; S3 was skipped/unconfigured |

The runner constructs the ordered text consistently from the candidate's
fields. S1 applies weighted term matching; S2 compares the resulting
sequence against the job description using `all-MiniLM-L6-v2`. The control
score is the candidate's mean over five identical-input runs.

## Evaluation and statistical methods

Paired treatment-minus-control score differences are reported with
10,000-resample percentile bootstrap 95% intervals. The analysis also
reports median differences, spread units, paired *dz*, matched rank-biserial
correlation, higher and absolute-change-over-five proportions, Wilcoxon and
sign tests, and Holm-adjusted Wilcoxon values. Rank stability is measured
with Spearman correlation and candidate-bootstrap 95% intervals; top-20
overlap is reported by role. Top-20 shortlist rates use candidate-cluster
bootstrap intervals and fractional ties.

## Results

| Screener | n | Mean Δ (95% bootstrap CI) | Median Δ | Spread units | Rank-biserial | Higher | Absolute change > 5 | Wilcoxon p (Holm) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| S1 | 300 | 0.000 [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 0.0% | 0.0% | 1.000 (1.000) |
| S2 | 300 | -11.500 [-12.835, -10.171] | -13.570 | -0.517 | -0.747 | 19.0% | 80.7% | <0.001 (<0.001) |

| Screener | Role | Rank Spearman ρ (95% bootstrap CI) | Top-20 overlap | Rank-test p (Holm) |
|---|---|---:|---:|---:|
| S1 | Backend | 1.000 [1.000, 1.000] | 1.000 | <0.001 (<0.001)* |
| S1 | Full-stack | 1.000 [1.000, 1.000] | 1.000 | <0.001 (<0.001)* |
| S1 | Data analyst | 1.000 [1.000, 1.000] | 1.000 | <0.001 (<0.001)* |
| S2 | Backend | 0.898 [0.848, 0.930] | 0.650 | <0.001 (<0.001) |
| S2 | Full-stack | 0.883 [0.821, 0.921] | 0.650 | <0.001 (<0.001) |
| S2 | Data analyst | 0.821 [0.740, 0.874] | 0.500 | <0.001 (<0.001) |

*For S1, scores and ranks are exactly tied before and after the edit; the
raw and Holm-adjusted asymptotic rank-test p-values are not substantively
informative for this exact-invariance case.

S2's role-level paired mean changes were -20.413 points for backend
(95% CI [-22.286, -18.421]), -11.667 for full-stack
([-13.691, -9.593]), and -2.421 for data analyst ([-5.284, 0.426]).
S2 top-20 impact ratios were 0.000 for backend, 0.129 for full-stack, and
1.000 for data analyst. S1 had 20% shortlist rates in all roles and
conditions.

![Pooled paired score changes, including section reordering, with 95% bootstrap intervals](../analysis/figures/paired_score_changes.svg)

## Interpretation

S1 was invariant to the section-order change. S2 scores fell substantially
in backend and full-stack and modestly, with an interval spanning zero, in
data analyst. Rank correlations remained positive but top-20 overlap fell
to 50–65% for S2 in the three roles. Reordering therefore changed more than
just a small score detail for this embedding model. These results remain
specific to this serialization, model and synthetic benchmark.

## Limitations, confounders, deviations, and null findings

- Only one alternative sequence was tested; other orderings may differ.
- This tests the exact text assembly and embedding model used by the
  repository, not a document parser or commercial screening product.
- S1's exact null result and the less pronounced data-analyst S2 effect are
  reported alongside the large S2 changes in the other roles.
- Impact ratios are screening heuristics for this synthetic pool, not proof
  of unfairness or legal non-compliance.
- S3 was unconfigured and excluded.

## Conclusion

S1 was insensitive to section reordering, while S2 showed substantial,
role-dependent score and rank changes. A harmless content-order edit can
matter to this tested embedding-based screener.

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
- Shared analysis command:
  `python -m src.stats.run_analysis` (documented, not rerun for this report).
