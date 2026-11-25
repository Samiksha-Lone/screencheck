# E10 — Screening stability

All tables contain aggregate results only. Candidate IDs and names are not published.

## Matched score comparisons

| Comparison | Screener | Format | n / expected | Mean Δ (95% CI) | Median Δ | Spread units | Rank-biserial | Wilcoxon p (Holm) | Sign p |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| repeat_mean_to_section_reordering | S1 | — | 300 / 300 | 0.000 [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 1.0000 (1.0000) | 1.0000 |
| repeat_mean_to_section_reordering | S2 | — | 300 / 300 | -11.500 [-12.835, -10.171] | -13.570 | -0.517 | -0.747 | 0.0000 (0.0000) | 0.0000 |
| repeat_mean_to_synonym_rewording | S1 | — | 300 / 300 | 0.000 [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 1.0000 (1.0000) | 1.0000 |
| repeat_mean_to_synonym_rewording | S2 | — | 300 / 300 | 1.208 [0.701, 1.708] | 2.165 | 0.054 | 0.355 | 0.0000 (0.0000) | 0.0000 |

Role-stratified estimates and all missing-pair counts are available in `analysis_results.json`.

## Top-20% shortlist rates and impact ratios

| Screener | Role | Format | Condition | n | Rate | Impact ratio | 95% CI |
|---|---|---|---|---:|---:|---:|---:|
| S1 | backend | — | repeat_mean | 100/100 | 20.0% | 1.000 | [1.000, 1.000] |
| S1 | backend | — | section_reordering | 100/100 | 20.0% | 1.000 | [1.000, 1.000] |
| S1 | backend | — | synonym_rewording | 100/100 | 20.0% | 1.000 | [1.000, 1.000] |
| S1 | full_stack | — | repeat_mean | 100/100 | 20.0% | 1.000 | [1.000, 1.000] |
| S1 | full_stack | — | section_reordering | 100/100 | 20.0% | 1.000 | [1.000, 1.000] |
| S1 | full_stack | — | synonym_rewording | 100/100 | 20.0% | 1.000 | [1.000, 1.000] |
| S1 | data_analyst | — | repeat_mean | 100/100 | 20.0% | 1.000 | [1.000, 1.000] |
| S1 | data_analyst | — | section_reordering | 100/100 | 20.0% | 1.000 | [1.000, 1.000] |
| S1 | data_analyst | — | synonym_rewording | 100/100 | 20.0% | 1.000 | [1.000, 1.000] |
| S2 | backend | — | repeat_mean | 100/100 | 25.0% | 0.714 | [0.500, 0.875] |
| S2 | backend | — | section_reordering | 100/100 | 0.0% | 0.000 | [0.000, 0.000] |
| S2 | backend | — | synonym_rewording | 100/100 | 35.0% | 1.000 | [1.000, 1.000] |
| S2 | full_stack | — | repeat_mean | 100/100 | 25.0% | 0.806 | [0.657, 1.000] |
| S2 | full_stack | — | section_reordering | 100/100 | 4.0% | 0.129 | [0.030, 0.321] |
| S2 | full_stack | — | synonym_rewording | 100/100 | 31.0% | 1.000 | [1.000, 1.000] |
| S2 | data_analyst | — | repeat_mean | 100/100 | 23.0% | 0.958 | [0.630, 1.000] |
| S2 | data_analyst | — | section_reordering | 100/100 | 24.0% | 1.000 | [0.704, 1.000] |
| S2 | data_analyst | — | synonym_rewording | 100/100 | 13.0% | 0.542 | [0.296, 0.773] |

## Repeated-run variability

| Screener | Role | n | Mean within-candidate SD | ICC(2,1) | Pairwise run ρ | Top-20 overlap |
|---|---|---:|---:|---:|---:|---:|
| S1 | backend | 100 | 0.000 | 1.000 | 1.000 | 1.000 |
| S1 | full_stack | 100 | 0.000 | 1.000 | 1.000 | 1.000 |
| S1 | data_analyst | 100 | 0.000 | 1.000 | 1.000 | 1.000 |
| S2 | backend | 100 | 0.000 | 1.000 | 1.000 | 1.000 |
| S2 | full_stack | 100 | 0.000 | 1.000 | 1.000 | 1.000 |
| S2 | data_analyst | 100 | 0.000 | 1.000 | 1.000 | 1.000 |

## Rank stability after input changes

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
