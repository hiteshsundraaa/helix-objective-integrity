from __future__ import annotations

import argparse
from pathlib import Path

from helix.benchmark.blind_case_sanitizer import sanitize_blind_cases


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--review-out", default="outputs/sanitization_review/review_findings.jsonl")
    parser.add_argument("--report-out", default="outputs/sanitization_review/report.md")
    parser.add_argument("--json-report-out", default="outputs/sanitization_review/report.json")
    args = parser.parse_args()

    report = sanitize_blind_cases(
        args.input,
        args.output,
        review_path=args.review_out,
    )

    report_md = Path(args.report_out)
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text(report.to_markdown(), encoding="utf-8")

    report_json = Path(args.json_report_out)
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    print("HELIX Split-View Sanitization")
    print(f"Input: {args.input}")
    print(f"Output: {args.output}")
    print(f"Total cases: {report.total_cases}")
    print(f"Auto-sanitized cases: {report.auto_sanitized_case_count}")
    print(f"Human-review cases: {report.human_review_case_count}")
    print(f"Explicit leak findings: {report.explicit_leak_count}")
    print(f"Structural contamination findings: {report.structural_contamination_count}")
    print(f"Label-leak findings: {report.label_leak_count}")
    print()
    print(f"Wrote review findings to {args.review_out}")
    print(f"Wrote report to {args.report_out}")


if __name__ == "__main__":
    main()
