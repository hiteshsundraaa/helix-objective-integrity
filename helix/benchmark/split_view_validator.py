from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from pydantic import BaseModel

from helix.benchmark.blind_case_schema import BlindCaseLabel
from helix.benchmark.split_view_loader import SplitViewBlindCaseLoadError, load_split_view_cases_jsonl
from helix.benchmark.split_view_schema import (
    ContractInformationStratum,
    SplitViewFamily,
)


VALID_TOOLS = {"read_file", "summarize_file", "classify_finding", "draft_report"}


class SplitViewValidationIssue(BaseModel):
    severity: str
    code: str
    message: str
    case_id: str | None = None


class SplitViewValidationReport(BaseModel):
    path: str
    valid: bool
    total_cases: int
    unsafe_count: int
    safe_count: int
    tool_counts: dict[str, int]
    family_counts: dict[str, int]
    family_label_counts: dict[str, dict[str, int]]
    stratum_counts: dict[str, int]
    stratum_label_counts: dict[str, dict[str, int]]
    contract_rule_counts: dict[str, int]
    contract_rule_label_counts: dict[str, dict[str, int]]
    issues: list[SplitViewValidationIssue]

    def to_markdown(self) -> str:
        lines = [
            "# HELIX Split-View Dataset Validation Report",
            "",
            f"Path: `{self.path}`",
            f"Valid: `{self.valid}`",
            f"Total cases: `{self.total_cases}`",
            f"Unsafe: `{self.unsafe_count}`",
            f"Safe: `{self.safe_count}`",
            "",
            "## Family balance",
            "",
            "| Family | Safe | Unsafe | Total |",
            "|---|---:|---:|---:|",
        ]
        for family, counts in sorted(self.family_label_counts.items()):
            lines.append(
                f"| {family} | {counts.get('safe', 0)} | {counts.get('unsafe', 0)} | {counts.get('total', 0)} |"
            )

        lines.extend([
            "",
            "## Stratum balance",
            "",
            "| Stratum | Safe | Unsafe | Total |",
            "|---|---:|---:|---:|",
        ])
        for stratum, counts in sorted(self.stratum_label_counts.items()):
            lines.append(
                f"| {stratum} | {counts.get('safe', 0)} | {counts.get('unsafe', 0)} | {counts.get('total', 0)} |"
            )

        lines.extend([
            "",
            "## Contract rule pairing",
            "",
            "| Rule ID | Safe | Unsafe | Total |",
            "|---|---:|---:|---:|",
        ])
        for rule_id, counts in sorted(self.contract_rule_label_counts.items()):
            lines.append(
                f"| {rule_id} | {counts.get('safe', 0)} | {counts.get('unsafe', 0)} | {counts.get('total', 0)} |"
            )

        lines.extend(["", "## Issues", ""])
        if not self.issues:
            lines.append("No validation issues.")
        else:
            lines.extend(["| Severity | Code | Case | Message |", "|---|---|---|---|"])
            for issue in self.issues:
                lines.append(
                    f"| {issue.severity} | {issue.code} | {issue.case_id or ''} | {issue.message} |"
                )

        return "\n".join(lines)


def validate_split_view_cases(
    path: str | Path,
    *,
    expected_min_total: int = 100,
    expected_min_safe: int = 50,
    expected_min_unsafe: int = 50,
    max_label_imbalance_ratio: float = 0.60,
    min_cases_per_family: int = 10,
    require_each_family_has_safe_and_unsafe: bool = True,
    require_each_stratum_has_safe_and_unsafe: bool = True,
) -> SplitViewValidationReport:
    issues: list[SplitViewValidationIssue] = []

    try:
        cases = load_split_view_cases_jsonl(path)
    except SplitViewBlindCaseLoadError as exc:
        return SplitViewValidationReport(
            path=str(path),
            valid=False,
            total_cases=0,
            unsafe_count=0,
            safe_count=0,
            tool_counts={},
            family_counts={},
            family_label_counts={},
            stratum_counts={},
            stratum_label_counts={},
            contract_rule_counts={},
            contract_rule_label_counts={},
            issues=[_issue("error", "load_error", str(exc))],
        )

    total = len(cases)
    unsafe = sum(case.label == BlindCaseLabel.UNSAFE for case in cases)
    safe = sum(case.label == BlindCaseLabel.SAFE for case in cases)

    if total < expected_min_total:
        issues.append(_issue("warning", "too_few_cases", f"Expected at least {expected_min_total} cases, found {total}."))
    if unsafe < expected_min_unsafe:
        issues.append(_issue("error", "too_few_unsafe_cases", f"Expected at least {expected_min_unsafe} unsafe cases, found {unsafe}."))
    if safe < expected_min_safe:
        issues.append(_issue("error", "too_few_safe_cases", f"Expected at least {expected_min_safe} safe cases, found {safe}."))

    if total > 0:
        largest_label_fraction = max(safe, unsafe) / total
        if largest_label_fraction > max_label_imbalance_ratio:
            issues.append(
                _issue(
                    "error",
                    "label_imbalance_too_high",
                    f"Largest label fraction is {largest_label_fraction:.3f}; max allowed is {max_label_imbalance_ratio:.3f}.",
                )
            )

    seen: set[str] = set()
    tool_counts = Counter()
    family_counts = Counter()
    stratum_counts = Counter()
    rule_counts = Counter()
    family_label_counts: dict[str, Counter] = defaultdict(Counter)
    stratum_label_counts: dict[str, Counter] = defaultdict(Counter)
    rule_label_counts: dict[str, Counter] = defaultdict(Counter)

    for case in cases:
        if case.case_id in seen:
            issues.append(_issue("error", "duplicate_case_id", f"Duplicate case_id {case.case_id}.", case.case_id))
        seen.add(case.case_id)

        if case.tool not in VALID_TOOLS:
            issues.append(_issue("error", "invalid_tool", f"Invalid tool {case.tool!r}.", case.case_id))

        if not case.generic_rationale.strip():
            issues.append(_issue("error", "missing_generic_rationale", "generic_rationale is empty.", case.case_id))
        if not case.contract_rule_id.strip():
            issues.append(_issue("error", "missing_contract_rule_id", "contract_rule_id is empty.", case.case_id))
        if not case.contract_rule_summary.strip():
            issues.append(_issue("error", "missing_contract_rule_summary", "contract_rule_summary is empty.", case.case_id))
        if not case.authoring_order_certified:
            issues.append(_issue("warning", "authoring_order_not_certified", "authoring_order_certified is false.", case.case_id))
        if not case.generic_fields_leakage_checked:
            issues.append(_issue("warning", "generic_fields_not_leakage_checked", "generic_fields_leakage_checked is false.", case.case_id))

        label = case.label.value
        family = case.family.value
        stratum = case.contract_information_stratum.value
        rule = case.contract_rule_id

        tool_counts[case.tool] += 1
        family_counts[family] += 1
        stratum_counts[stratum] += 1
        rule_counts[rule] += 1

        family_label_counts[family][label] += 1
        family_label_counts[family]["total"] += 1
        stratum_label_counts[stratum][label] += 1
        stratum_label_counts[stratum]["total"] += 1
        rule_label_counts[rule][label] += 1
        rule_label_counts[rule]["total"] += 1

    for family in SplitViewFamily:
        count = family_counts.get(family.value, 0)
        if count < min_cases_per_family:
            issues.append(
                _issue(
                    "warning",
                    "too_few_cases_for_family",
                    f"Family {family.value!r} has {count} cases; expected at least {min_cases_per_family}.",
                )
            )

    if require_each_family_has_safe_and_unsafe:
        for family, counts in family_label_counts.items():
            if counts.get("safe", 0) == 0 or counts.get("unsafe", 0) == 0:
                issues.append(
                    _issue(
                        "error",
                        "family_missing_label",
                        f"Family {family!r} has safe={counts.get('safe', 0)}, unsafe={counts.get('unsafe', 0)}.",
                    )
                )

    if require_each_stratum_has_safe_and_unsafe:
        for stratum in ContractInformationStratum:
            counts = stratum_label_counts.get(stratum.value, Counter())
            if counts.get("safe", 0) == 0 or counts.get("unsafe", 0) == 0:
                issues.append(
                    _issue(
                        "error",
                        "stratum_missing_label",
                        f"Stratum {stratum.value!r} has safe={counts.get('safe', 0)}, unsafe={counts.get('unsafe', 0)}.",
                    )
                )

    for rule_id, counts in rule_label_counts.items():
        if counts.get("safe", 0) == 0 or counts.get("unsafe", 0) == 0:
            issues.append(
                _issue(
                    "warning",
                    "unpaired_contract_rule",
                    f"Rule {rule_id!r} has safe={counts.get('safe', 0)}, unsafe={counts.get('unsafe', 0)}. Paired rules are preferred.",
                )
            )

    valid = not any(issue.severity == "error" for issue in issues)

    return SplitViewValidationReport(
        path=str(path),
        valid=valid,
        total_cases=total,
        unsafe_count=unsafe,
        safe_count=safe,
        tool_counts=dict(sorted(tool_counts.items())),
        family_counts=dict(sorted(family_counts.items())),
        family_label_counts={k: dict(v) for k, v in sorted(family_label_counts.items())},
        stratum_counts=dict(sorted(stratum_counts.items())),
        stratum_label_counts={k: dict(v) for k, v in sorted(stratum_label_counts.items())},
        contract_rule_counts=dict(sorted(rule_counts.items())),
        contract_rule_label_counts={k: dict(v) for k, v in sorted(rule_label_counts.items())},
        issues=issues,
    )


def _issue(severity: str, code: str, message: str, case_id: str | None = None) -> SplitViewValidationIssue:
    return SplitViewValidationIssue(
        severity=severity,
        code=code,
        message=message,
        case_id=case_id,
    )
