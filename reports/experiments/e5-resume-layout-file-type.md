# E5 — Resume layout and file type

## Research question, objective, and hypothesis

**Question.** Does the score change when identical synthetic candidate
content is presented in one-column, two-column, or table-based layout, and
does the pattern differ between PDF and DOCX inputs?

**Objective.** Evaluate both in-house screeners on text extracted from
existing rendered resumes, separately within each file format.

**Hypothesis.** With candidate content held constant, changing layout or
file format should have little or no score effect.

## Background and rationale

Resume screeners may respond to document structure or extraction rather than
qualifications. The initial E5 records were not a valid basis for layout
conclusions: S1 bypassed layout extraction, and S2 similarities for a
two-column condition were copied from table-layout records. Those
superseded records are preserved for provenance but excluded. This report
uses only the corrected, layout-aware dataset of actual extracted text.

## Design and methods

| Element | Specification |
|---|---|
| Conditions | One-column, two-column, table layout, each rendered as PDF and DOCX |
| Control | One-column within the same format |
| Manipulated variable | Layout; format is stratified (PDF or DOCX) |
| Controlled variables | Base candidate, role, job description and source resume content |
| Dataset | 300 synthetic candidates; 100 per role; six rendered document conditions per candidate |
| Coverage | 1,800 documents extracted; 3,600 completed screener records; 300 paired candidates per layout contrast and format |
| Screeners | S1 and S2; S3 was skipped/unconfigured |

The approved records are in `e5_layout_aware_v1.jsonl`; each record includes
source-document path, layout, format, extracted-text hash and extraction
status. Validation checked all 1,800 extracted documents and verified 3,600
completed results. S1 scored the extracted text. S2 used
`all-MiniLM-L6-v2`; for E5 comparisons, raw cosine similarity was mapped to
points using `50 * (cosine + 1)`, a fixed transformation. No direct
PDF-versus-DOCX paired contrast is reported: the layout comparisons are
estimated separately inside each format.

## Evaluation and statistical methods

Six paired contrasts were evaluated for each screener: one-column versus
two-column, one-column versus table, and two-column versus table, separately
for PDF and DOCX. Each contrast has 300 matched observations. The analysis
reports mean and median differences with 95% percentile bootstrap intervals
(10,000 candidate-level resamples), spread-unit and paired effect sizes,
matched rank-biserial correlation, Wilcoxon and sign tests with Holm
correction, and the proportions higher or changing by more than five points.
Top-20 shortlist rates are calculated separately by role and format, with
fractional boundary ties and candidate-cluster bootstrap intervals.

## Results

| Format | Contrast | Screener | n | Mean Δ (95% bootstrap CI) | Median Δ | Spread units | Rank-biserial | Higher | Absolute change > 5 | Wilcoxon p (Holm) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PDF | One → two columns | S1 | 300 | 0.000 [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 0.0% | 0.0% | 1.000 (1.000) |
| PDF | One → two columns | S2 | 300 | 0.000 [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 0.0% | 0.0% | 1.000 (1.000) |
| PDF | One → table | S1 | 300 | 0.000 [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 0.0% | 0.0% | 1.000 (1.000) |
| PDF | One → table | S2 | 300 | 0.573 [0.521, 0.625] | 0.543 | 0.207 | 0.908 | 89.0% | 0.0% | <0.001 (<0.001) |
| PDF | Two → table | S1 | 300 | 0.000 [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 0.0% | 0.0% | 1.000 (1.000) |
| PDF | Two → table | S2 | 300 | 0.573 [0.522, 0.625] | 0.543 | 0.207 | 0.908 | 89.0% | 0.0% | <0.001 (<0.001) |
| DOCX | One → two columns | S1 | 300 | 0.000 [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 0.0% | 0.0% | 1.000 (1.000) |
| DOCX | One → two columns | S2 | 300 | 0.000 [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 0.0% | 0.0% | 1.000 (1.000) |
| DOCX | One → table | S1 | 300 | 0.000 [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 0.0% | 0.0% | 1.000 (1.000) |
| DOCX | One → table | S2 | 300 | 0.430 [0.377, 0.484] | 0.472 | 0.155 | 0.667 | 77.0% | 0.0% | <0.001 (<0.001) |
| DOCX | Two → table | S1 | 300 | 0.000 [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 0.0% | 0.0% | 1.000 (1.000) |
| DOCX | Two → table | S2 | 300 | 0.430 [0.379, 0.484] | 0.472 | 0.155 | 0.667 | 77.0% | 0.0% | <0.001 (<0.001) |

| S2 role / format | One-column rate (impact ratio) | Two-column rate | Table rate (impact ratio; 95% CI) |
|---|---:|---:|---:|
| Backend PDF | 15.0% (0.500) | 15.0% (0.500) | 30.0% (1.000; [1.000, 1.000]) |
| Full-stack PDF | 17.0% (0.654) | 17.0% (0.654) | 26.0% (1.000; [0.927, 1.000]) |
| Data analyst PDF | 18.0% (0.750) | 18.0% (0.750) | 24.0% (1.000; [0.927, 1.000]) |
| Backend DOCX | 16.0% (0.571) | 16.0% (0.571) | 28.0% (1.000; [1.000, 1.000]) |
| Full-stack DOCX | 23.0% (1.000) | 23.0% (1.000) | 14.0% (0.609; [0.500, 1.000]) |
| Data analyst DOCX | 16.5% (0.611) | 16.5% (0.611) | 27.0% (1.000; [1.000, 1.000]) |

S1's shortlist rate was 20.0% for every role, layout and format. The
full-stack DOCX S2 table condition moved in the opposite direction from the
other table comparisons; this result is retained rather than averaged away.
The paired score shifts are all below the three-point score threshold, even
where Wilcoxon tests are small.

![Pooled paired score changes, including layout contrasts, with 95% bootstrap intervals](../analysis/figures/paired_score_changes.svg)

## Interpretation

S1 produced identical scores across all layout and format conditions. S2
scores were unchanged between one- and two-column files, but table-layout
contrasts showed small positive mean score differences in both formats.
Although these differences were statistically detectable, they were under
one point on the fixed 0–100 comparison scale and none exceeded five points.
S2 shortlist rates changed more substantially in some roles, with one
unexpected reversal for full-stack DOCX. These are screening outcomes from
the synthetic benchmark and do not establish unfairness or legal
non-compliance.

## Limitations, confounders, deviations, and null findings

- Only three layouts and two file types were rendered. Format is reported as
  a stratum; a direct PDF-versus-DOCX effect was not tested.
- Document extraction can alter text ordering or representation. The
  analysis intentionally evaluates the extracted text the screeners
  actually received, with hashes and source documents verified.
- The earlier invalid layout records are excluded. The normalized S2 file
  contains 1,200 rows tagged E5, including 600 original Phase 6 rows and 600
  supplemental superseded repair rows; neither set is used to draw layout
  conclusions.
- The approved `e5_layout_aware_v1.jsonl` has 3,600 records from 1,800
  extracted documents and is the sole E5 score source.
- S1 null effects, one/two-column equivalence for S2, small score changes,
  and the full-stack DOCX reversal are all reported.
- S3 was skipped/unconfigured and is excluded.

## Conclusion

S1 was invariant to the tested layouts and formats. S2 was invariant to
one-versus-two columns but showed small score changes for table layouts and
larger, role-dependent shortlist shifts. The conclusions apply only to the
corrected extracted-text dataset, not the superseded legacy results.

## Reproducibility

- Design and corrected E5 execution: [`e5_layout_aware.py`](../../src/experiments/e5_layout_aware.py),
  [`resume_renderer.py`](../../src/factory/resume_renderer.py), and
  [data provenance](../../docs/data_provenance.md).
- Approved private source: `data/private/analysis/e5_layout_aware_v1.jsonl`,
  SHA-256 `6f2a1afb338976abb8f118c582174d70e6d9c40ad5efa4dd33587a3ddbd95a3a`;
  manifest: `data/private/analysis/e5_layout_aware_v1_manifest.json`.
- Phase 6 baseline source:
  `data/private/experiments/experiment_results.jsonl`,
  SHA-256 `2433a2925afbf55bc1108a31da1bd53a28d1da982980a1150171626c4d18e4c4`.
- Machine-readable estimates:
  [`analysis_results.json`](../analysis/analysis_results.json),
  [`paired_comparisons.csv`](../analysis/paired_comparisons.csv),
  [`shortlist_group_rates.csv`](../analysis/shortlist_group_rates.csv), and
  [`shortlist_inclusion_changes.csv`](../analysis/shortlist_inclusion_changes.csv).
- Verified aggregate-analysis command (not rerun for this report):
  `python -m src.stats.run_analysis`.
