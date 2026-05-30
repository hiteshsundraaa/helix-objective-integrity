from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.paraphrase_analysis import (
    analyze_paraphrase_controls,
    awaiting_judgments_report,
    write_paraphrase_analysis_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze HELIX v6 paraphrase robustness controls from frozen contract judgments."
    )
    parser.add_argument(
        "--cases",
        default="benchmarks/blind_cases/mock_workspace_blind_v6_paraphrase_controls.jsonl",
    )
    parser.add_argument(
        "--contract-judgments",
        "--judgments",
        dest="contract_judgments",
        default="benchmarks/semantic_judgments/blind_v6_paraphrase_contract_normalized.jsonl",
    )
    parser.add_argument(
        "--out-dir",
        default="outputs/paraphrase_analysis/v6",
    )
    args = parser.parse_args()

    cases_path = Path(args.cases)
    judgments_path = Path(args.contract_judgments)
    out_dir = Path(args.out_dir)

    if not cases_path.exists():
        raise SystemExit(
            "Paraphrase controls dataset does not exist: "
            f"{cases_path}. Generate it with: python tools/generate_v6_paraphrase_controls.py "
            f"--out {cases_path}"
        )

    if not judgments_path.exists():
        report = awaiting_judgments_report(cases_path=cases_path, judgments_path=judgments_path)
        write_paraphrase_analysis_outputs(report, out_dir)
        raise SystemExit(
            "awaiting_judgments: frozen v6 paraphrase contract judgments are missing; "
            f"expected {judgments_path}"
        )

    report = analyze_paraphrase_controls(
        cases_path=cases_path,
        contract_judgments_path=judgments_path,
    )
    write_paraphrase_analysis_outputs(report, out_dir)

    print(f"Status: {report.status}")
    print(f"Paraphrase cases: {report.paraphrase_case_count}")
    print(f"Paraphrase pairs: {report.paraphrase_pair_count}")
    print(f"Main TPR: {report.main_tpr:.3f}")
    print(f"Main FPR: {report.main_fpr:.3f}")
    print(f"Exact citation rate: {report.exact_citation_rate:.3f}")
    print(f"Invalid citation rate: {report.invalid_citation_rate:.3f}")
    print(f"Wrote outputs to {out_dir}")


if __name__ == "__main__":
    main()
