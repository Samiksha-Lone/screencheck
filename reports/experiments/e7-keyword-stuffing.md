# E7 — Keyword stuffing

## Research question, objective, and hypothesis

**Question.** Does adding a visible list of job-description keywords, without
adding evidence of those skills, increase screening scores or shortlist
inclusion?

**Objective.** Measure the response to keyword repetition in two simple
in-house screeners.

**Hypothesis.** Keyword stuffing should produce little or no score gain
because it does not add demonstrated experience or project evidence.

## Background and rationale

Keyword-matching systems may reward terms independently of their supporting
context. This experiment tests that failure mode using synthetic resumes. It
does not assess whether any listed term accurately represents a real
candidate's skills.

## Design and methods

| Element | Specification |
|---|---|
| Control | Original synthetic base resume |
| Treatment | Same resume plus a visible list of six role-specific job terms |
| Manipulated variable | Additional keyword list only; `supporting_evidence_added` is false |
| Controlled variables | Candidate qualifications and evidence, role, job description and screener settings |
| Dataset | 300 candidates; 100 each in backend, full-stack and data-analyst roles |
| Paired comparisons | 300 treatment-control pairs; no missing pairs |
| Screeners | S1 keyword matcher and S2 embedding matcher; S3 was skipped/unconfigured |

The term lists are defined by role in
[`twin_builder.py`](../../src/experiments/twin_builder.py) (`JOB_TERMS`).
S1 scores explicit skill matches with must-have skills weighted twice as
highly as nice-to-have skills. S2 embeds the resume and job description with
`all-MiniLM-L6-v2` and uses the role-normalized 0–100 scale.

## Evaluation and statistical methods

The primary comparison is paired score change (treatment minus control).
Mean and median 95% percentile bootstrap intervals use 10,000 paired
candidate resamples. Effect sizes include change in control-score spread
units and matched rank-biserial correlation; paired Cohen's *dz*, proportion
higher, and proportion with absolute changes above five points are retained
in machine-readable estimates. Wilcoxon signed-rank and sign tests are
reported with Holm adjustment for paired tests. Shortlist rates compare
top-20 outcomes by role, using fractional ties and candidate-cluster
bootstrap intervals.

## Results

| Screener | n | Mean Δ (95% bootstrap CI) | Median Δ | Spread units | Rank-biserial | Higher | Absolute change > 5 | Wilcoxon p (Holm) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| S1 | 300 | 27.274 [25.334, 29.256] | 25.000 | 1.188 | 1.000 | 87.0% | 87.0% | <0.001 (<0.001) |
| S2 | 300 | 13.641 [12.514, 14.771] | 10.605 | 0.613 | 0.997 | 97.0% | 80.3% | <0.001 (<0.001) |

| Screener / role | Base shortlist rate (impact ratio; 95% CI) | Stuffed rate (impact ratio; 95% CI) |
|---|---:|---:|
| S1 — backend | 5.0% (0.141; [0.041, 0.290]) | 35.0% (1.000; [1.000, 1.000]) |
| S1 — full-stack | 12.7% (0.463; [0.325, 0.622]) | 27.3% (1.000; [1.000, 1.000]) |
| S1 — data analyst | 5.9% (0.172; [0.077, 0.332]) | 34.1% (1.000; [1.000, 1.000]) |
| S2 — backend | 8.0% (0.250; [0.143, 0.481]) | 32.0% (1.000; [1.000, 1.000]) |
| S2 — full-stack | 14.0% (0.538; [0.290, 0.818]) | 26.0% (1.000; [1.000, 1.000]) |
| S2 — data analyst | 10.0% (0.333; [0.212, 0.538]) | 30.0% (1.000; [1.000, 1.000]) |

Both pooled average changes exceed the three-point investigation threshold.
Every role's stuffed-condition shortlist rate exceeded its corresponding
base rate in these combined synthetic pools.

![Pooled paired score changes, including E7, with 95% bootstrap intervals](../analysis/figures/paired_score_changes.svg)

## Interpretation

Both screeners rewarded the visible keyword list despite no supporting
evidence being added. S1's larger mean increase is consistent with its
explicit keyword-matching design; S2 also changed substantially, showing
sensitivity to this particular appended content. These measured shortlist
shifts are screening impacts in the synthetic benchmark. They do not prove
that a real screener would behave similarly, that the fictional candidates
have or lack skills, or that any legal standard was violated.

## Limitations, confounders, deviations, and null findings

- The treatment adds six role-specific terms in a visible list; different
  wording, placement, or system designs may behave differently.
- No evidence was added, but the terms may alter the full text representation
  for S2 beyond a simple count of repetitions.
- Both screeners produced large gains; no pooled null result was observed.
- The impact ratios compare screening outcomes in this synthetic setup and
  are not fairness or legality determinations.
- S3 was unconfigured and is excluded.

## Conclusion

Visible keyword stuffing increased the scores and top-20 shortlist rates of
both in-house screeners in this experiment, without new supporting evidence.
This result demonstrates behavior of these test systems only.

## Reproducibility

- Treatment construction: [PLAN.md](../../PLAN.md) and
  [`twin_builder.py`](../../src/experiments/twin_builder.py)
  (`JOB_TERMS`, `build_e7_pairs`).
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
