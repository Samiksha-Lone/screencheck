# ScreenCheck

ScreenCheck is a controlled research project for evaluating simple resume
screeners on synthetic candidates. Results describe these in-house test
systems only; they are not evidence about commercial hiring products or real
people.

## Project structure

- `src/factory/` — synthetic candidate scoring, resume rendering, and extraction.
- `src/screeners/` — keyword, embedding, and configurable LLM screeners.
- `src/experiments/` — experiment construction and execution.
- `src/validation/` — dataset integrity checks and analysis-input preparation.
- `src/stats/` — paired statistical methods, analysis orchestration, and reports.
- `data/` — job definitions and generated candidate inputs.
- `reports/analysis/` — aggregate, reproducible research outputs.
- `data/private/` — ignored experiment results and candidate-level analysis data.

## Reproduce the analysis

Install the pinned dependencies and run the test suite:

```powershell
python -m pip install -r requirements.txt
python -m pytest -q
```

With the private datasets available locally, regenerate aggregate analysis
reports using:

```powershell
python -m src.stats.run_analysis
```

The analysis validates source hashes and coverage before running. It uses
`data/private/analysis/e5_layout_aware_v1.jsonl` for E5; superseded E5 records
are excluded. All S3 results remain explicitly skipped when no LLM is
configured. See [data provenance](docs/data_provenance.md), the original
[research plan](PLAN.md), and generated
[analysis reports](reports/analysis/summary.md).
