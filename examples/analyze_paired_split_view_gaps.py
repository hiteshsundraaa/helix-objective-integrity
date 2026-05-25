from __future__ import annotations

import argparse
from pathlib import Path

from helix.benchmark.paired_split_view_analysis import run_paired_split_view_gap_analysis, write_paired_gap_outputs
from helix.contracts.build_contract import load_contract_yaml


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True)
    parser.add_argument("--generic-judgments", required=True)
    parser.add_argument("--contract-judgments", required=True)
    parser.add_argument("--generic-gap-threshold", type=float, default=0.15)
    parser.add_argument("--contract-gap-threshold", type=float, default=0.30)
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args()

    contract = load_contract_yaml("scenarios/mock_workspace/contract.yaml")
    report = run_paired_split_view_gap_analysis(
        contract,
        cases_path=args.cases,
        generic_judgments_path=args.generic_judgments,
        contract_judgments_path=args.contract_judgments,
        generic_gap_threshold=args.generic_gap_threshold,
        contract_gap_threshold=args.contract_gap_threshold,
    )
    out_dir = args.out_dir or str(Path("outputs/paired_split_view_gap_analysis") / Path(args.cases).stem)
    write_paired_gap_outputs(report, out_dir)

    print("HELIX Paired Split-View Gap Analysis")
    print(f"Dataset: {Path(args.cases).stem}")
    print(f"Pairs: {report.pair_count}")
    print(f"Generic ambiguous pairs: {report.generic_ambiguous_pair_count}")
    print(f"Contract separated pairs: {report.contract_separated_pair_count}")
    print(f"Hybrid separated pairs: {report.hybrid_separated_pair_count}")
    print(f"Contract success on generic-ambiguous pairs: {report.contract_success_on_generic_ambiguous_count}")
    print(f"Hybrid success on generic-ambiguous pairs: {report.hybrid_success_on_generic_ambiguous_count}")
    print()
    print(f"Wrote outputs to {out_dir}")


if __name__ == "__main__":
    main()
