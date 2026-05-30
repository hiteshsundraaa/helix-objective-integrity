from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.trace_noise_analysis import (
    analyze_trace_noise_controls,
    awaiting_judgments_report,
    write_trace_noise_analysis_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze HELIX v6 trace-noise robustness controls from frozen contract judgments."
    )
    parser.add_argument(
        "--cases",
        default="benchmarks/blind_cases/mock_workspace_blind_v6_trace_noise_controls.jsonl",
    )
    parser.add_argument(
        "--contract-judgments",
        "--judgments",
        dest="contract_judgments",
        default="benchmarks/semantic_judgments/blind_v6_trace_noise_contract_normalized.jsonl",
    )
    parser.add_argument(
        "--out-dir",
        default="outputs/trace_noise_analysis/v6",
    )
    args = parser.parse_args()

    cases_path = Path(args.cases)
    judgments_path = Path(args.contract_judgments)
    out_dir = Path(args.out_dir)

    if not cases_path.exists():
        raise SystemExit(
            "Trace-noise controls dataset does not exist: "
            f"{cases_path}. Generate it with: python tools/generate_v6_trace_noise_controls.py "
            f"--out {cases_path}"
        )

    if not judgments_path.exists():
        report = awaiting_judgments_report(cases_path=cases_path, judgments_path=judgments_path)
        write_trace_noise_analysis_outputs(report, out_dir)
        raise SystemExit(
            "awaiting_judgments: frozen v6 trace-noise contract judgments are missing; "
            f"expected {judgments_path}"
        )

    report = analyze_trace_noise_controls(
        cases_path=cases_path,
        contract_judgments_path=judgments_path,
    )
    write_trace_noise_analysis_outputs(report, out_dir)

    print(f"Status: {report.status}")
    print(f"Trace-noise cases: {report.trace_noise_case_count}")
    print(f"Trace-noise pairs: {report.trace_noise_pair_count}")
    print(f"Main TPR: {report.main_tpr:.3f}")
    print(f"Main FPR: {report.main_fpr:.3f}")
    print(f"Active-rule citation rate: {report.active_rule_citation_rate:.3f}")
    print(f"Stale-rule citation rate: {report.stale_rule_citation_rate:.3f}")
    print(f"Wrote outputs to {out_dir}")


if __name__ == "__main__":
    main()
