from __future__ import annotations

import argparse
import json
from pathlib import Path


BLOCKING_RISK_LEVELS = {"warn", "degrade", "quarantine", "block"}


def _load_cases(path: Path) -> dict[str, dict]:
    cases: dict[str, dict] = {}
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        case_id = row.get("case_id")
        if not case_id:
            raise ValueError(f"Missing case_id in {path} line {line_no}")
        cases[case_id] = row
    return cases

@field_validator("violation_probability")
@classmethod
def violation_probability_must_be_unit_interval(cls, value: float | None) -> float | None:
    if value is None:
        return value
    if value < 0.0 or value > 1.0:
        raise ValueError("violation_probability must be between 0.0 and 1.0")
    return value

def _load_judgments(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        row["_line_no"] = line_no
        rows.append(row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True)
    parser.add_argument("--contract-judgments", required=True)
    parser.add_argument("--out-dir", default="outputs/contract_judgment_citations")
    args = parser.parse_args()

    cases = _load_cases(Path(args.cases))
    judgments = _load_judgments(Path(args.contract_judgments))

    issues: list[dict] = []
    checked = 0
    non_allow_checked = 0
    valid_citations = 0
    missing_probability = 0
    invalid_probability = 0
    missing_citation = 0
    citation_not_in_rule = 0

    for row in judgments:
        sample_id = row.get("sample_id")
        judgment = row.get("judgment", {})
        case = cases.get(sample_id)

        if case is None:
            issues.append(
                {
                    "severity": "error",
                    "code": "judgment_without_case",
                    "sample_id": sample_id,
                    "message": "Judgment sample_id does not exist in case file.",
                }
            )
            continue

        checked += 1
        risk_level = str(judgment.get("risk_level", "")).lower()
        probability = judgment.get("violation_probability")
        phrase = judgment.get("cited_contract_phrase")
        rule = case.get("contract_rule_summary", "")

        if probability is None:
            missing_probability += 1
            issues.append(
                {
                    "severity": "warning",
                    "code": "missing_violation_probability",
                    "sample_id": sample_id,
                    "message": "Judgment is missing violation_probability.",
                }
            )
        elif not isinstance(probability, (int, float)) or probability < 0.0 or probability > 1.0:
            invalid_probability += 1
            issues.append(
                {
                    "severity": "error",
                    "code": "invalid_violation_probability",
                    "sample_id": sample_id,
                    "message": "violation_probability must be numeric and between 0.0 and 1.0.",
                }
            )

        if risk_level in BLOCKING_RISK_LEVELS:
            non_allow_checked += 1
            if not phrase:
                missing_citation += 1
                issues.append(
                    {
                        "severity": "error",
                        "code": "missing_cited_contract_phrase",
                        "sample_id": sample_id,
                        "message": "Non-ALLOW contract-aware judgment must cite exact contract phrase.",
                    }
                )
            elif str(phrase) not in rule:
                citation_not_in_rule += 1
                issues.append(
                    {
                        "severity": "error",
                        "code": "cited_phrase_not_in_contract_rule",
                        "sample_id": sample_id,
                        "message": "cited_contract_phrase does not appear exactly inside contract_rule_summary.",
                        "cited_contract_phrase": phrase,
                        "contract_rule_summary": rule,
                    }
                )
            else:
                valid_citations += 1

    summary = {
        "checked": checked,
        "non_allow_checked": non_allow_checked,
        "valid_citations": valid_citations,
        "missing_probability": missing_probability,
        "invalid_probability": invalid_probability,
        "missing_citation": missing_citation,
        "citation_not_in_rule": citation_not_in_rule,
        "issue_count": len(issues),
        "valid": not any(issue["severity"] == "error" for issue in issues),
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    report_json = {"summary": summary, "issues": issues}
    (out_dir / "report.json").write_text(json.dumps(report_json, indent=2), encoding="utf-8")

    lines = [
        "# HELIX Contract Judgment Citation Validation",
        "",
        "## Summary",
        "",
        f"- checked: `{checked}`",
        f"- non_allow_checked: `{non_allow_checked}`",
        f"- valid_citations: `{valid_citations}`",
        f"- missing_probability: `{missing_probability}`",
        f"- invalid_probability: `{invalid_probability}`",
        f"- missing_citation: `{missing_citation}`",
        f"- citation_not_in_rule: `{citation_not_in_rule}`",
        f"- valid: `{summary['valid']}`",
        "",
        "## Issues",
        "",
    ]

    if issues:
        lines.extend(["| Severity | Code | Sample | Message |", "|---|---|---|---|"])
        for issue in issues:
            lines.append(
                f"| {issue['severity']} | {issue['code']} | {issue.get('sample_id', '')} | {issue['message']} |"
            )
    else:
        lines.append("No issues.")

    (out_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")

    print("HELIX Contract Judgment Citation Validation")
    for key, value in summary.items():
        print(f"- {key}: {value}")
    print(f"Wrote outputs to {out_dir}")

    raise SystemExit(0 if summary["valid"] else 1)


if __name__ == "__main__":
    main()
