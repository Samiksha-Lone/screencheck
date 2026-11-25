# Dataset provenance and status

This note records the dataset organization and the decisions used by the
statistical analysis. The Phase 6 JSONL and all candidate-level datasets remain
private and Git-ignored.

## Analysis inputs

| Current path | Purpose and analysis status |
|---|---|
| `data/private/experiments/experiment_results.jsonl` | Immutable Phase 6 source: 18,000 records, 6,000 completed S1, 6,000 completed S2, and 6,000 explicitly skipped S3. SHA-256: `2433a2925afbf55bc1108a31da1bd53a28d1da982980a1150171626c4d18e4c4`. |
| `data/private/analysis/s2_role_reference_normalized_v1.jsonl` | Derived S2 observations with fixed role-specific min/max references from 100 original base candidates per role. Used for non-E5 S2 analyses. Its legacy E5 rows are not used for E5 conclusions. |
| `data/private/analysis/e5_layout_aware_v1.jsonl` | Approved E5 dataset. S1 and S2 received text extracted from existing one-column, two-column, and table PDF/DOCX documents. Includes text hashes, source paths, layout, and format. |
| `data/private/analysis/e5_layout_aware_v1_manifest.json` | Coverage, status, model, and Phase 6 hash for the approved E5 dataset. |
| `data/private/analysis/e5_two_column_legacy_records_superseded.jsonl` | Preserved historical E5 rows. **Superseded and invalid for layout-effect conclusions:** S1 bypassed layout extraction and S2 similarities were copied from table-layout records. |
| `data/private/analysis/analysis_dataset_preparation_log.json` | Preserved log for the earlier analysis-data preparation. It records historical paths and the original Phase 6 hash. |

The role-normalized S2 file includes 600 rows from the superseded E5 preparation
in addition to the 6,000 Phase 6 S2 rows. Analysis uses the normalized S2
records only when their IDs correspond to non-E5 Phase 6 results. E5 analysis
uses only `e5_layout_aware_v1.jsonl`.

## Safe filename organization

The following private artifacts were moved without rewriting their contents;
their SHA-256 hashes were checked after the move:

| Historical path | Current path | SHA-256 |
|---|---|---|
| `data/private/analysis/e5_two_column_repair.jsonl` | `data/private/analysis/e5_two_column_legacy_records_superseded.jsonl` | `346af3e68b1b045df985222cb6810730399a363678ece4e00b6074af5f336e73` |
| `data/private/analysis/corrected_s2.jsonl` | `data/private/analysis/s2_role_reference_normalized_v1.jsonl` | `5120574c38c957298ab60c56ece2b499acd87fc722b8a7914158a88f181be2eb` |
| `data/private/phase7_repair_log.json` | `data/private/analysis/analysis_dataset_preparation_log.json` | `3d9911721ddbde853e99bdc36b873975de2f8c90ef3b3e9e4d8bb9d92a5bbfb3` |

The historical preparation module was moved from
`src/experiments/phase7_repair.py` to
`src/validation/prepare_analysis_datasets.py`. It refuses to overwrite the
preserved derived datasets. The earlier E5 output is retained only for
provenance and must not be used in statistical E5 reporting.

## Privacy

`data/private/` is excluded by `.gitignore`. Public-facing analysis tables,
reports, and figures contain aggregate estimates only; they do not contain
candidate IDs or synthetic candidate names.
