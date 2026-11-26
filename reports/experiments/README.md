# Individual experiment research reports

These reports document each conducted experiment and separately reported
variant. They provide the design, paired estimates, screening outcomes,
interpretation, limitations, and reproducibility details behind the
[comprehensive aggregate report](../analysis/summary.md). The [research
plan](../../PLAN.md) and [statistical methods](../analysis/methodology.md)
provide the shared pre-specified thresholds and analysis procedures.

| Experiment | Individual report |
|---|---|
| E1 — Name-coded groups | [Name-coded groups](e1-name-coded-groups.md) |
| E3 — College prestige | [College prestige](e3-college-prestige.md) |
| E3 — Project evidence | [Project evidence](e3-project-evidence.md) |
| E5 — Resume layout and file type | [Resume layout and file type](e5-resume-layout-file-type.md) |
| E7 — Keyword stuffing | [Keyword stuffing](e7-keyword-stuffing.md) |
| E9 — Honest improvements | [Honest improvements](e9-honest-improvements.md) |
| E10 — Repeated-run stability | [Repeated-run stability](e10-repeated-run-stability.md) |
| E10 — Section reordering | [Section reordering](e10-section-reordering.md) |
| E10 — Synonym rewriting | [Synonym rewriting](e10-synonym-rewriting.md) |

## Shared analysis conventions

The experiments use 300 synthetic base candidates: 100 each for backend,
full-stack, and data-analyst roles. S1 is the deterministic, weighted keyword
matcher; S2 is the `sentence-transformers/all-MiniLM-L6-v2` embedding matcher.
S3 was unconfigured: all 6,000 Phase 6 S3 records are marked skipped and no
S3 result is included in any conclusion.

Unless stated otherwise, score differences are treatment minus control, with
300/300 paired observations. Mean and median intervals are candidate-level
percentile bootstrap intervals with 10,000 resamples and deterministic seeds.
Paired Wilcoxon signed-rank tests and sign tests are reported; Holm adjustment
covers the pre-specified family of estimable paired tests. Effect sizes include
the mean change in control-score standard-deviation units and matched
rank-biserial correlation. Shortlist results use the top 20% within role,
fractional inclusion at a tied cutoff, and candidate-cluster bootstrap
intervals. These are screening outcomes in this synthetic benchmark, not
evidence of real-world unfairness or legal violations.

The reports summarize the existing machine-readable outputs; they do not
regenerate data or rerun the analysis. Private candidate-level inputs remain
under `data/private/` and are excluded from Git.
