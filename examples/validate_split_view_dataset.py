from __future__ import annotations

import argparse
from pathlib import Path

from helix.benchmark.split_view_validator import validate_split_view_cases


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True)
    parser.add_argument("--out", default="outputs/split_view_validation/report.md")
    parser.add_argument("--json-out", default="outputs/split_view_validation/report.json")
    args = parser.parse_args()

    report = validate_split_view_cases(args.cases)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report.to_markdown(), encoding="utf-8")

    json_out = Path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    print("HELIX Split-View Dataset Validation")
    print(f"Cases: {args.cases}")
    print(f"Valid: {report.valid}")
    print(f"Total: {report.total_cases}")
    print(f"Unsafe: {report.unsafe_count}")
    print(f"Safe: {report.safe_count}")
    print()
    if report.issues:
        print("Issues:")
        for issue in report.issues:
            case = f" case={issue.case_id}" if issue.case_id else ""
            print(f"- [{issue.severity}] {issue.code}{case}: {issue.message}")
    else:
        print("No validation issues.")
    print()
    print(f"Wrote markdown report to {out}")
    print(f"Wrote JSON report to {json_out}")

    raise SystemExit(0 if report.valid else 1)


if __name__ == "__main__":
    main()
