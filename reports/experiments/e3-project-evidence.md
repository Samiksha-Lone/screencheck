# E3 — Project evidence

## Research question, objective, and hypothesis

**Question.** Does adding one relevant, evidence-bearing synthetic project
change screening scores and shortlist outcomes relative to an otherwise
identical resume with a lesser-known synthetic college?

**Objective.** Measure the response to a concrete, role-aligned project as an
evidence contrast, distinct from the college-label contrast in the separate
E3 college report.

**Hypothesis.** A relevant project with specific synthetic outcomes will
increase scores and top-20 shortlist inclusion.

## Background and rationale

This experiment contrasts substantive evidence with the E3 college-name
manipulation. Each project is fictional and tailored to one of the tested
roles. The values in project descriptions are simulated, not observed
performance by real people or organizations.

## Design and methods

| Element | Specification |
|---|---|
| Control | Candidate with the lesser-known synthetic college and original projects |
| Treatment | Same candidate plus one role-matched synthetic project and project-evidence score of 10 |
| Manipulated variables | Project text, project details, and `project_evidence` field |
| Controlled variables | College label, base candidate, role, job description, skills and experience, except for the project addition |
| Dataset | 300 synthetic candidates; 100 each in backend, full-stack and data-analyst roles |
| Paired comparisons | 300 control-treatment pairs; 100 per role; no missing pairs |
| Screeners | S1 keyword matcher and S2 embedding matcher; S3 was skipped/unconfigured |

Role-specific additions are specified in `ROLE_PROJECTS` in
[`twin_builder.py`](../../src/experiments/twin_builder.py): a reliability API
for backend, a planning portal for full-stack, and a synthetic sales-insights
analysis for data analyst. The same candidate supplies both paired
observations. S2 uses role-specific normalized scores.

## Evaluation and statistical methods

The primary measure is the paired treatment-minus-control score. Means and
medians use 95% percentile bootstrap intervals (10,000 candidate-level
resamples). The machine-readable outputs include spread units, paired
Cohen's *dz*, matched rank-biserial correlation, proportions higher and
above five points, Wilcoxon signed-rank and sign tests, and Holm-adjusted
Wilcoxon results. Shortlist rates and impact ratios are measured within role
at the top 20%, with fractional ties and candidate-cluster bootstrap
intervals.

## Results

| Screener | n | Mean Δ (95% bootstrap CI) | Median Δ | Spread units | Rank-biserial | Higher | Absolute change > 5 | Wilcoxon p (Holm) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| S1 | 300 | 1.208 [0.833, 1.583] | 0.000 | 0.053 | 1.000 | 9.7% | 9.7% | <0.001 (<0.001) |
| S2 | 300 | 17.093 [16.117, 18.106] | 15.620 | 0.768 | 0.998 | 97.7% | 94.0% | <0.001 (<0.001) |

| Screener / role | Control shortlist rate (impact ratio) | Project shortlist rate (impact ratio; 95% CI) |
|---|---:|---:|
| S1 — backend | 20.0% (1.000) | 20.0% (1.000; [1.000, 1.000]) |
| S1 — full-stack | 17.5% (0.778) | 22.5% (1.000; [1.000, 1.000]) |
| S1 — data analyst | 20.0% (1.000) | 20.0% (1.000; [1.000, 1.000]) |
| S2 — backend | 6.0% (0.176) | 34.0% (1.000; [1.000, 1.000]) |
| S2 — full-stack | 13.0% (0.481) | 27.0% (1.000; [1.000, 1.000]) |
| S2 — data analyst | 5.0% (0.143) | 35.0% (1.000; [1.000, 1.000]) |

The score shifts for S1 and S2 are below and above, respectively, the
pre-specified three-point investigation threshold. The S1 median difference
is zero despite a positive mean: most scores tie and a minority of candidates
gain points. All S2 role-specific shortlist rates rose in this benchmark.

![Pooled paired score changes, including the project-evidence contrast, with 95% bootstrap intervals](../analysis/figures/paired_score_changes.svg)

## Interpretation

Adding the synthetic project had a large positive association with S2 scores
and increased its shortlist rate in each role. S1 changed by only 1.208
points on average and showed a zero median; its full-stack shortlist outcome
changed modestly while the other two roles remained at 20%. The screeners
responded differently to the added text, consistent with their distinct
keyword and embedding designs. This is a controlled result for synthetic
inputs, not evidence about real applicants, genuine project quality, or
commercial systems.

Compared with the separate E3 college-label contrast, which changed neither
screener's scores, the project contrast produced mean increases of 1.208
points for S1 and 17.093 points for S2. The tested project response was
therefore larger than the tested college-label response for both screeners.

## Limitations, deviations, and null findings

- Project contents and quantified outcomes are generated and role-specific;
  no project was independently assessed as real-world evidence.
- The S1 zero median and unchanged backend/data-analyst shortlist rates are
  retained as null or small findings despite its significant paired test.
- S2's large shift may reflect the specific embedding model and crafted
  project wording.
- Shortlist impact ratios summarize rankings within this synthetic
  benchmark; they do not establish unfairness or legal violations.
- S3 was unconfigured and excluded.

## Conclusion

The project addition produced a large score and shortlist response from S2
and a much smaller average score response from S1. This supports the narrow
claim that the two tested screeners react differently to this particular
synthetic evidence addition.

## Reproducibility

- Pair and project definitions: [PLAN.md](../../PLAN.md) and
  [`twin_builder.py`](../../src/experiments/twin_builder.py)
  (`ROLE_PROJECTS`, `build_e3_project_pairs`).
- Candidate data: `data/generated/*_candidates.json`; seed 42;
  `data/private/twins/twin_manifest.json` records 300 valid pairs and zero
  validation failures.
- Original results:
  `data/private/experiments/experiment_results.jsonl`,
  SHA-256 `2433a2925afbf55bc1108a31da1bd53a28d1da982980a1150171626c4d18e4c4`.
- Machine-readable estimates:
  [`analysis_results.json`](../analysis/analysis_results.json),
  [`paired_comparisons.csv`](../analysis/paired_comparisons.csv),
  [`shortlist_group_rates.csv`](../analysis/shortlist_group_rates.csv), and
  [`shortlist_inclusion_changes.csv`](../analysis/shortlist_inclusion_changes.csv).
- Analysis command documented by the repository:
  `python -m src.stats.run_analysis` (not rerun for this report).
