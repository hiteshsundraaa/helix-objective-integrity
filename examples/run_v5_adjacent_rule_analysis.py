from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.adjacent_rule_analysis import (
    analyze_adjacent_rule_controls,
    awaiting_judgments_report,
    write_adjacent_rule_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze HELIX v5 adjacent-rule citation controls from frozen contract judgments."
    )
    parser.add_argument(
        "--cases",
        default="benchmarks/blind_cases/mock_workspace_blind_v5_adjacent_rule_controls.jsonl",
    )
    parser.add_argument(
        "--contract-judgments",
        "--judgments",
        dest="contract_judgments",
        default="benchmarks/semantic_judgments/blind_v5_adjacent_rule_contract_gpt5.jsonl",
    )
    parser.add_argument(
        "--out-dir",
        default="outputs/adjacent_rule_analysis/v5",
    )
    args = parser.parse_args()

    cases_path = Path(args.cases)
    judgments_path = Path(args.contract_judgments)
    out_dir = Path(args.out_dir)

    if not cases_path.exists():
        raise SystemExit(f"Adjacent-rule dataset does not exist: {cases_path}")

    if not judgments_path.exists():
        report = awaiting_judgments_report(cases_path=cases_path, judgments_path=judgments_path)
        write_adjacent_rule_outputs(report, out_dir)
        raise SystemExit(
            "awaiting_judgments: frozen adjacent-rule contract judgments are missing; "
            f"expected {judgments_path}"
        )

    report = analyze_adjacent_rule_controls(
        cases_path=cases_path,
        judgments_path=judgments_path,
    )
    write_adjacent_rule_outputs(report, out_dir)

    print(f"Status: {report.status}")
    print(f"Adjacent cases: {report.adjacent_case_count}")
    print(f"Wrong-rule citation rate: {report.wrong_rule_citation_rate:.3f}")
    print(f"Governing-rule citation rate: {report.governing_rule_citation_rate:.3f}")
    print(f"Adjacent-rule overblock rate: {report.adjacent_rule_overblock_rate:.3f}")
    print(f"Wrote outputs to {out_dir}")


if __name__ == "__main__":
    main()
