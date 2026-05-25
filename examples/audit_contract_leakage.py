from __future__ import annotations

import argparse
from pathlib import Path

from helix.benchmark.contract_leakage_audit import (
    audit_contract_leakage,
    write_contract_leakage_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True)
    parser.add_argument("--out-dir", default="outputs/contract_leakage_audit")
    args = parser.parse_args()

    report = audit_contract_leakage(args.cases)
    write_contract_leakage_outputs(report, args.out_dir)

    print("HELIX Contract Leakage Audit")
    print(f"Cases: {args.cases}")
    print(f"Total cases: {report.total_cases}")
    print(f"Leaked cases: {report.leaked_case_count}")
    print(f"Leaked fields: {report.leaked_field_count}")
    print(f"Leakage rate: {report.leakage_rate:.3f}")
    print()
    print("Findings by field:")
    for key, value in report.findings_by_field.items():
        print(f"- {key}: {value}")
    print()
    print("Findings by pattern:")
    for key, value in report.findings_by_pattern.items():
        print(f"- {key}: {value}")
    print()
    print(f"Wrote outputs to {Path(args.out_dir)}")


if __name__ == "__main__":
    main()
