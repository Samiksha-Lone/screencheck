# Statistical methods and limitations

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
