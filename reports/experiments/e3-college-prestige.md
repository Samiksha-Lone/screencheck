# E3 — College prestige

## Research question, objective, and hypothesis

**Question.** Does replacing a lesser-known synthetic college label with a
well-known synthetic college label change an otherwise identical resume's
score or shortlist inclusion?

**Objective.** Isolate the college-name field while comparing the two
in-house screeners on the same fictional candidate and role.

**Hypothesis.** A college-name substitution, without any change in
qualifications, will not change the score or shortlist outcome.

## Background and rationale

Education labels can be treated as proxies for candidate quality by screening
systems. This controlled synthetic contrast tests whether the current
screeners respond to one such label. The college names are intentionally
fictional and do not stand in for actual institutions or their graduates.

## Design and methods

| Element | Specification |
|---|---|
| Control | `Synthetic Regional Technical College` (lesser-known label) |
| Treatment | `Synthetic National Technical University` (well-known label) |
| Manipulated variable | College name and its synthetic tier label in the education field |
| Controlled variables | Candidate, skills, project/experience evidence, role, job description and screener settings |
| Dataset | 300 synthetic candidates; 100 each in backend, full-stack and data-analyst roles |
| Paired comparisons | 300 control-treatment pairs; no missing pairs |
| Screeners | S1 keyword matcher and S2 embedding matcher; S3 was skipped/unconfigured |

Each pair is constructed from one candidate and validated so only education
and the unique candidate identifier differ. S1 uses weighted skill matches.
S2 uses `all-MiniLM-L6-v2` and role-specific normalization from original base
candidates. Candidate-level paired analysis compares the treatment score with
the lesser-known-college control.

## Evaluation and statistical methods

Mean and median paired score differences receive 95% percentile bootstrap
intervals from 10,000 candidate-level resamples. The existing analysis also
reports spread-unit and paired effect sizes, matched rank-biserial
correlation, Wilcoxon signed-rank and sign tests, with Holm correction across
the family of paired tests. Role-specific shortlist rates use the top 20% and
candidate-cluster bootstrap intervals with fractional boundary ties.

## Results

| Screener | n | Mean Δ (95% bootstrap CI) | Median Δ | Spread units | Rank-biserial | Higher | Absolute change > 5 | Wilcoxon p (Holm) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| S1 | 300 | 0.000 [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 0.0% | 0.0% | 1.000 (1.000) |
| S2 | 300 | 0.000 [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 0.0% | 0.0% | 1.000 (1.000) |

For both screeners, all roles had a 20.0% top-20 shortlist rate in both
conditions; each treatment-to-highest-group impact ratio was 1.000 with
95% CI [1.000, 1.000]. There were no missing pairs and no observed score
changes.

## Interpretation

The two screeners returned identical scores for the two synthetic college
labels in this dataset. This is a null finding for the tested labels, not
evidence that education fields never affect other screeners or other
institutions' names.

## Limitations, confounders, deviations, and null findings

- The synthetic labels may not capture actual college-name semantics or
  prestige signals.
- Candidates, labels, roles, and screeners are limited to this in-house
  benchmark.
- The exact zero effects and unchanged shortlist rates are the central null
  result; no positive effect was observed.
- S3 was unconfigured and is excluded from all conclusions.

## Conclusion

Changing between the two fictional college labels did not change scores or
top-20 shortlist rates for S1 or S2. No inference about actual colleges,
graduates, or hiring systems follows from this result.

## Reproducibility

- Design and pair construction: [PLAN.md](../../PLAN.md) and
  [`twin_builder.py`](../../src/experiments/twin_builder.py)
  (`build_e3_college_pairs`).
- Source candidates: `data/generated/*_candidates.json`; seed 42;
  `data/private/twins/twin_manifest.json` records 300 valid pairs and zero
  validation failures.
- Original result file and SHA-256:
  `data/private/experiments/experiment_results.jsonl`,
  `2433a2925afbf55bc1108a31da1bd53a28d1da982980a1150171626c4d18e4c4`.
- Estimates and role-level results:
  [`analysis_results.json`](../analysis/analysis_results.json),
  [`paired_comparisons.csv`](../analysis/paired_comparisons.csv), and
  [`shortlist_group_rates.csv`](../analysis/shortlist_group_rates.csv).
- Shared analysis command, documented in [README.md](../../README.md):
  `python -m src.stats.run_analysis` (not rerun for this report).
