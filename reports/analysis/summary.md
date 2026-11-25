# ScreenCheck statistical analysis

This report summarizes controlled experiments on synthetic resumes and in-house screening systems. It does not evaluate commercial hiring products.

## Data integrity and coverage

- Phase 6: 18,000 records; SHA-256 `2433a2925afbf55bc1108a31da1bd53a28d1da982980a1150171626c4d18e4c4`.
- S1 and S2: 6,000 completed observations each. S3: 6,000 explicitly skipped; no S3 scores were inferred.
- Approved E5: 3,600 complete layout-aware records from 1,800 verified document extractions.
- The earlier E5 legacy records are superseded and excluded from all layout analyses.

## Pooled matched score comparisons

| Comparison | Screener | Format | n / expected | Mean Δ (95% CI) | Median Δ | Spread units | Rank-biserial | Wilcoxon p (Holm) | Sign p |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| base_to_name_group_a | S1 | — | 300 / 300 | 0.000 [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 1.0000 (1.0000) | 1.0000 |
| base_to_name_group_a | S2 | — | 300 / 300 | -3.237 [-4.670, -1.815] | -3.480 | -0.145 | -0.299 | 0.0000 (0.0006) | 0.0002 |
| base_to_name_group_b | S1 | — | 300 / 300 | 0.000 [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 1.0000 (1.0000) | 1.0000 |
| base_to_name_group_b | S2 | — | 300 / 300 | -4.639 [-6.254, -3.042] | -3.515 | -0.208 | -0.325 | 0.0000 (0.0001) | 0.0021 |
| name_group_a_to_group_b | S1 | — | 300 / 300 | 0.000 [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 1.0000 (1.0000) | 1.0000 |
| name_group_a_to_group_b | S2 | — | 300 / 300 | -1.403 [-3.133, 0.263] | -1.665 | -0.064 | -0.095 | 0.1544 (1.0000) | 0.0150 |
| base_to_twin | S1 | — | 300 / 300 | 0.000 [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 1.0000 (1.0000) | 1.0000 |
| base_to_twin | S2 | — | 300 / 300 | 0.000 [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 1.0000 (1.0000) | 1.0000 |
| base_to_twin | S1 | — | 300 / 300 | 1.208 [0.833, 1.583] | 0.000 | 0.053 | 1.000 | 0.0000 (0.0000) | 0.0000 |
| base_to_twin | S2 | — | 300 / 300 | 17.093 [16.117, 18.106] | 15.620 | 0.768 | 0.998 | 0.0000 (0.0000) | 0.0000 |
| base_to_twin | S1 | — | 300 / 300 | 27.274 [25.334, 29.256] | 25.000 | 1.188 | 1.000 | 0.0000 (0.0000) | 0.0000 |
| base_to_twin | S2 | — | 300 / 300 | 13.641 [12.514, 14.771] | 10.605 | 0.613 | 0.997 | 0.0000 (0.0000) | 0.0000 |
| base_to_twin | S1 | — | 300 / 300 | 1.208 [0.833, 1.583] | 0.000 | 0.053 | 1.000 | 0.0000 (0.0000) | 0.0000 |
| base_to_twin | S2 | — | 300 / 300 | 12.275 [11.025, 13.559] | 10.770 | 0.551 | 0.905 | 0.0000 (0.0000) | 0.0000 |
| one_column_to_two_column | S1 | pdf | 300 / 300 | 0.000 [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 1.0000 (1.0000) | 1.0000 |
| one_column_to_two_column | S2 | pdf | 300 / 300 | 0.000 [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 1.0000 (1.0000) | 1.0000 |
| one_column_to_table | S1 | pdf | 300 / 300 | 0.000 [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 1.0000 (1.0000) | 1.0000 |
| one_column_to_table | S2 | pdf | 300 / 300 | 0.573 [0.521, 0.625] | 0.543 | 0.207 | 0.908 | 0.0000 (0.0000) | 0.0000 |
| two_column_to_table | S1 | pdf | 300 / 300 | 0.000 [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 1.0000 (1.0000) | 1.0000 |
| two_column_to_table | S2 | pdf | 300 / 300 | 0.573 [0.522, 0.625] | 0.543 | 0.207 | 0.908 | 0.0000 (0.0000) | 0.0000 |
| one_column_to_two_column | S1 | docx | 300 / 300 | 0.000 [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 1.0000 (1.0000) | 1.0000 |
| one_column_to_two_column | S2 | docx | 300 / 300 | 0.000 [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 1.0000 (1.0000) | 1.0000 |
| one_column_to_table | S1 | docx | 300 / 300 | 0.000 [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 1.0000 (1.0000) | 1.0000 |
| one_column_to_table | S2 | docx | 300 / 300 | 0.430 [0.377, 0.484] | 0.472 | 0.155 | 0.667 | 0.0000 (0.0000) | 0.0000 |
| two_column_to_table | S1 | docx | 300 / 300 | 0.000 [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 1.0000 (1.0000) | 1.0000 |
| two_column_to_table | S2 | docx | 300 / 300 | 0.430 [0.379, 0.484] | 0.472 | 0.155 | 0.667 | 0.0000 (0.0000) | 0.0000 |
| repeat_mean_to_section_reordering | S1 | — | 300 / 300 | 0.000 [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 1.0000 (1.0000) | 1.0000 |
| repeat_mean_to_section_reordering | S2 | — | 300 / 300 | -11.500 [-12.835, -10.171] | -13.570 | -0.517 | -0.747 | 0.0000 (0.0000) | 0.0000 |
| repeat_mean_to_synonym_rewording | S1 | — | 300 / 300 | 0.000 [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 1.0000 (1.0000) | 1.0000 |
| repeat_mean_to_synonym_rewording | S2 | — | 300 / 300 | 1.208 [0.701, 1.708] | 2.165 | 0.054 | 0.355 | 0.0000 (0.0000) | 0.0000 |

## Practical score changes

- E1 base_to_name_group_a S2: mean change -3.237 points ([-4.670, -1.815]; n=300).
- E1 base_to_name_group_b S2: mean change -4.639 points ([-6.254, -3.042]; n=300).
- E3_PROJECT base_to_twin S2: mean change 17.093 points ([16.117, 18.106]; n=300).
- E7 base_to_twin S1: mean change 27.274 points ([25.334, 29.256]; n=300).
- E7 base_to_twin S2: mean change 13.641 points ([12.514, 14.771]; n=300).
- E9 base_to_twin S2: mean change 12.275 points ([11.025, 13.559]; n=300).
- E10 repeat_mean_to_section_reordering S2: mean change -11.500 points ([-12.835, -10.171]; n=300).

## Shortlist impact flags

- E1 S2 backend group_a: impact ratio 0.692 (95% CI 0.467 to 1.000; n=100).
- E1 S2 backend group_b: impact ratio 0.615 (95% CI 0.406 to 0.913; n=100).
- E1 S2 full_stack group_a: impact ratio 0.654 (95% CI 0.464 to 1.000; n=100).
- E1 S2 full_stack group_b: impact ratio 0.654 (95% CI 0.467 to 1.000; n=100).
- E3_PROJECT S1 full_stack base: impact ratio 0.778 (95% CI 0.631 to 0.924; n=100).
- E3_PROJECT S2 backend base: impact ratio 0.176 (95% CI 0.053 to 0.333; n=100).
- E3_PROJECT S2 full_stack base: impact ratio 0.481 (95% CI 0.250 to 0.667; n=100).
- E3_PROJECT S2 data_analyst base: impact ratio 0.143 (95% CI 0.026 to 0.250; n=100).
- E5 S2 backend PDF one-column: impact ratio 0.500 (95% CI 0.357 to 0.654; n=100).
- E5 S2 backend PDF two-column: impact ratio 0.500 (95% CI 0.357 to 0.654; n=100).
- E5 S2 full_stack PDF one-column: impact ratio 0.654 (95% CI 0.534 to 1.000; n=100).
- E5 S2 full_stack PDF two-column: impact ratio 0.654 (95% CI 0.534 to 1.000; n=100).
- E5 S2 data_analyst PDF one-column: impact ratio 0.750 (95% CI 0.571 to 1.000; n=100).
- E5 S2 data_analyst PDF two-column: impact ratio 0.750 (95% CI 0.571 to 1.000; n=100).
- E5 S2 backend DOCX one-column: impact ratio 0.571 (95% CI 0.409 to 0.750; n=100).
- E5 S2 backend DOCX two-column: impact ratio 0.571 (95% CI 0.409 to 0.750; n=100).
- E5 S2 full_stack DOCX table: impact ratio 0.609 (95% CI 0.500 to 1.000; n=100).
- E5 S2 data_analyst DOCX one-column: impact ratio 0.611 (95% CI 0.382 to 0.750; n=100).
- E5 S2 data_analyst DOCX two-column: impact ratio 0.611 (95% CI 0.382 to 0.750; n=100).
- E7 S1 backend base: impact ratio 0.141 (95% CI 0.041 to 0.290; n=100).
- E7 S1 full_stack base: impact ratio 0.463 (95% CI 0.325 to 0.622; n=100).
- E7 S1 data_analyst base: impact ratio 0.172 (95% CI 0.077 to 0.332; n=100).
- E7 S2 backend base: impact ratio 0.250 (95% CI 0.143 to 0.481; n=100).
- E7 S2 full_stack base: impact ratio 0.538 (95% CI 0.290 to 0.818; n=100).
- E7 S2 data_analyst base: impact ratio 0.333 (95% CI 0.212 to 0.538; n=100).
- E9 S1 full_stack base: impact ratio 0.778 (95% CI 0.630 to 0.920; n=100).
- E9 S2 backend base: impact ratio 0.379 (95% CI 0.250 to 0.739; n=100).
- E9 S2 full_stack base: impact ratio 0.538 (95% CI 0.333 to 0.818; n=100).
- E9 S2 data_analyst base: impact ratio 0.290 (95% CI 0.176 to 0.481; n=100).
- E10 S2 backend repeat_mean: impact ratio 0.714 (95% CI 0.500 to 0.875; n=100).
- E10 S2 backend section_reordering: impact ratio 0.000 (95% CI 0.000 to 0.000; n=100).
- E10 S2 full_stack section_reordering: impact ratio 0.129 (95% CI 0.030 to 0.321; n=100).
- E10 S2 data_analyst synonym_rewording: impact ratio 0.542 (95% CI 0.296 to 0.773; n=100).

## True Fit validation

| Screener | Role | n | Spearman ρ | 95% CI | Holm p |
|---|---|---:|---:|---:|---:|
| S1 | all_roles | 300 | 0.976 | [0.969, 0.981] | 0.0000 |
| S1 | backend | 100 | 0.984 | [0.972, 0.990] | 0.0000 |
| S1 | full_stack | 100 | 0.958 | [0.935, 0.971] | 0.0000 |
| S1 | data_analyst | 100 | 0.984 | [0.972, 0.990] | 0.0000 |
| S2 | all_roles | 300 | 0.643 | [0.570, 0.704] | 0.0000 |
| S2 | backend | 100 | 0.771 | [0.687, 0.830] | 0.0000 |
| S2 | full_stack | 100 | 0.756 | [0.648, 0.832] | 0.0000 |
| S2 | data_analyst | 100 | 0.497 | [0.329, 0.640] | 0.0000 |

True Fit is a synthetic research proxy, not real-world hiring truth. Pooled correlations may reflect role differences.

## E10 stability

| Screener | Role | n | Mean within-candidate SD | ICC(2,1) | Pairwise run ρ | Top-20 overlap |
|---|---|---:|---:|---:|---:|---:|
| S1 | backend | 100 | 0.000 | 1.000 | 1.000 | 1.000 |
| S1 | full_stack | 100 | 0.000 | 1.000 | 1.000 | 1.000 |
| S1 | data_analyst | 100 | 0.000 | 1.000 | 1.000 | 1.000 |
| S2 | backend | 100 | 0.000 | 1.000 | 1.000 | 1.000 |
| S2 | full_stack | 100 | 0.000 | 1.000 | 1.000 | 1.000 |
| S2 | data_analyst | 100 | 0.000 | 1.000 | 1.000 | 1.000 |

### Rank stability after input changes

| Screener | Role | Comparison | n | Spearman ρ (95% CI) | Top-20 overlap | Holm p |
|---|---|---|---:|---:|---:|---:|
| S1 | backend | repeat_mean_to_section_reordering | 100 | 1.000 [1.000, 1.000] | 1.000 | 0.0000 |
| S1 | backend | repeat_mean_to_synonym_rewording | 100 | 1.000 [1.000, 1.000] | 1.000 | 0.0000 |
| S1 | full_stack | repeat_mean_to_section_reordering | 100 | 1.000 [1.000, 1.000] | 1.000 | 0.0000 |
| S1 | full_stack | repeat_mean_to_synonym_rewording | 100 | 1.000 [1.000, 1.000] | 1.000 | 0.0000 |
| S1 | data_analyst | repeat_mean_to_section_reordering | 100 | 1.000 [1.000, 1.000] | 1.000 | 0.0000 |
| S1 | data_analyst | repeat_mean_to_synonym_rewording | 100 | 1.000 [1.000, 1.000] | 1.000 | 0.0000 |
| S2 | backend | repeat_mean_to_section_reordering | 100 | 0.898 [0.848, 0.930] | 0.650 | 0.0000 |
| S2 | backend | repeat_mean_to_synonym_rewording | 100 | 0.982 [0.965, 0.989] | 0.850 | 0.0000 |
| S2 | full_stack | repeat_mean_to_section_reordering | 100 | 0.883 [0.821, 0.921] | 0.650 | 0.0000 |
| S2 | full_stack | repeat_mean_to_synonym_rewording | 100 | 0.985 [0.970, 0.990] | 0.750 | 0.0000 |
| S2 | data_analyst | repeat_mean_to_section_reordering | 100 | 0.821 [0.740, 0.874] | 0.500 | 0.0000 |
| S2 | data_analyst | repeat_mean_to_synonym_rewording | 100 | 0.944 [0.900, 0.966] | 0.650 | 0.0000 |

## Figures and detailed results

- [Paired score changes](figures/paired_score_changes.svg)
- [True Fit correlations](figures/true_fit_correlations.svg)
- [E10 repeat variability](figures/e10_repeat_variability.svg)
- Detailed machine-readable estimates: `analysis_results.json`.
- Methods, tie policy, thresholds, and limitations: [methodology](methodology.md).
