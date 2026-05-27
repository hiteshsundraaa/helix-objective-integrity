from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.asymmetric_trace_analysis import (
    analyze_asymmetric_trace_controls,
    write_asymmetric_trace_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run HELIX v5 asymmetric trace-vs-self-report analysis."
    )
    parser.add_argument(
        "--cases",
        default="benchmarks/blind_cases/mock_workspace_blind_v5_asymmetric_trace_controls.jsonl",
    )
    parser.add_argument(
        "--out-dir",
        default="outputs/asymmetric_trace_analysis/v5",
    )
    args = parser.parse_args()

    cases_path = Path(args.cases)
    if not cases_path.exists():
        raise SystemExit(
            f"Asymmetric trace controls do not exist: {cases_path}. "
            "Run tools/generate_v5_asymmetric_trace_controls.py first."
        )

    summary = analyze_asymmetric_trace_controls(cases_path)
    write_asymmetric_trace_outputs(summary, args.out_dir)

    print("HELIX Asymmetric Trace-vs-Self-Report Analysis")
    print(f"Dataset: {summary.dataset_name}")
    print(f"Cases: {summary.case_count}")
    print(f"Unsafe cases: {summary.unsafe_count}")
    print(f"Safe cases: {summary.safe_count}")
    print(f"self_report_false_compliance_rate: {summary.self_report_false_compliance_rate:.3f}")
    print(f"self_report_detection_rate: {summary.self_report_detection_rate:.3f}")
    print(f"trace_based_detection_rate: {summary.trace_based_detection_rate:.3f}")
    print(f"trace_based_false_positive_rate: {summary.trace_based_false_positive_rate:.3f}")
    print(f"asymmetric_detection_gain: {summary.asymmetric_detection_gain:.3f}")
    print(f"Wrote outputs to {args.out_dir}")


if __name__ == "__main__":
    main()
