from __future__ import annotations

import argparse
from pathlib import Path

from helix.benchmark.split_view_leakage_audit import (
    audit_split_view_leakage,
    write_split_view_leakage_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True)
    parser.add_argument("--out-dir", default="outputs/split_view_leakage_audit")
    args = parser.parse_args()

    report = audit_split_view_leakage(args.cases)
    write_split_view_leakage_outputs(report, args.out_dir)

    print("HELIX Split-View Leakage Audit")
    print(f"Cases: {args.cases}")
    print(f"Total cases: {report.total_cases}")
    print(f"Generic contaminated cases: {report.generic_contaminated_case_count}")
    print(f"Generic contaminated fields: {report.generic_contaminated_field_count}")
    print(f"Generic prompt renderable: {report.generic_prompt_renderable}")
    print(f"Contract-aware prompt renderable: {report.contract_aware_prompt_renderable}")
    print(f"Split-view receipt clean: {report.split_view_receipt_clean}")
    print()
    print("Generic contamination by pattern:")
    for key, value in report.generic_contamination_by_pattern.items():
        print(f"- {key}: {value}")
    print()
    print(f"Wrote outputs to {Path(args.out_dir)}")


if __name__ == "__main__":
    main()
