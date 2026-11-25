"""Command-line entry point for reproducible aggregate analysis."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from src.stats.experiment_analysis import run_analysis
from src.stats.reporting import DEFAULT_REPORT_DIR, write_analysis_outputs
from src.validation.analysis_inputs import load_analysis_datasets


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze validated ScreenCheck synthetic screening results."
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_REPORT_DIR)
    args = parser.parse_args()

    datasets = load_analysis_datasets()
    result = run_analysis(datasets)
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    report = write_analysis_outputs(result, args.output_dir)
    print(
        json.dumps(
            {
                "report_dir": report["output_dir"],
                "paired_comparisons": len(result["paired_comparisons"]),
                "shortlist_group_rows": len(result["shortlist"]["groups"]),
                "true_fit_rows": len(result["true_fit_validation"]),
                "e10_repeat_rows": len(result["stability"]["repeated_runs"]),
                "phase6_sha256": result["data_audit"]["phase6"]["sha256"],
                "e5_layout_sha256": result["data_audit"]["genuine_e5_layout"]["sha256"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
