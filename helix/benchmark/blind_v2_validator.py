from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from helix.benchmark.blind_case_schema import (
    BlindCase,
    BlindCaseLabel,
    ContractVariant,
    IntendedContractDependence,
)
from helix.benchmark.blind_loader import BlindCaseLoadError, load_blind_cases_jsonl


VALID_TOOLS = {"read_file", "summarize_file", "classify_finding", "draft_report"}


class BlindV2ValidationIssue(BaseModel):
    severity: str
    code: str
    message: str
    case_id: str | None = None


class BlindV2ValidationReport(BaseModel):
    path: str
    valid: bool
    total_cases: int
    unsafe_count: int
    safe_count: int
    tool_counts: dict[str, int]
    family_counts: dict[str, int]
    contract_variant_counts: dict[str, int]
    intended_contract_dependence_counts: dict[str, int]
    contract_rule_counts: dict[str, int]
    paired_rule_summary: dict[str, dict[str, int]]
    issues: list[BlindV2ValidationIssue]

    def to_markdown(self) -> str:
        lines = [
            "# HELIX blind_v2 Validation Report",
            "",
            f"Path: `{self.path}`",
            f"Valid: `{self.valid}`",
            f"Total cases: `{self.total_cases}`",
            f"Unsafe: `{self.unsafe_count}`",
            f"Safe: `{self.safe_count}`",
            "",
            "## Contract variants",
            "",
            "| Variant | Count |",
            "|---|---:|",
        ]
        for key, value in sorted(self.contract_variant_counts.items()):
            lines.append(f"| {key} | {value} |")

        lines.extend([
            "",
            "## Intended contract dependence",
            "",
            "| Level | Count |",
            "|---|---:|",
        ])
        for key, value in sorted(self.intended_contract_dependence_counts.items()):
            lines.append(f"| {key} | {value} |")

        lines.extend([
            "",
            "## Contract rule pairing",
            "",
            "| Rule ID | Safe | Unsafe | Total |",
            "|---|---:|---:|---:|",
        ])
        for rule_id, counts in sorted(self.paired_rule_summary.items()):
            lines.append(
                f"| {rule_id} | {counts.get('safe', 0)} | "
                f"{counts.get('unsafe', 0)} | {counts.get('total', 0)} |"
            )

        lines.extend([
            "",
            "## Issues",
            "",
        ])
        if not self.issues:
            lines.append("No validation issues.")
        else:
            lines.extend(["| Severity | Code | Case | Message |", "|---|---|---|---|"])
            for issue in self.issues:
                lines.append(
                    f"| {issue.severity} | {issue.code} | "
                    f"{issue.case_id or ''} | {issue.message} |"
                )

        return "\n".join(lines)


def validate_blind_v2_cases(
    path: str | Path,
    *,
    expected_total: int = 80,
    expected_unsafe: int = 40,
    expected_safe: int = 40,
    min_reversal: int = 20,
    min_idiosyncratic: int = 20,
    min_high_dependence: int = 20,
) -> BlindV2ValidationReport:
    issues: list[BlindV2ValidationIssue] = []

    try:
        cases = load_blind_cases_jsonl(path)
    except BlindCaseLoadError as exc:
        return BlindV2ValidationReport(
            path=str(path),
            valid=False,
            total_cases=0,
            unsafe_count=0,
            safe_count=0,
            tool_counts={},
            family_counts={},
            contract_variant_counts={},
            intended_contract_dependence_counts={},
            contract_rule_counts={},
            paired_rule_summary={},
            issues=[
                BlindV2ValidationIssue(
                    severity="error",
                    code="load_error",
                    message=str(exc),
                )
            ],
        )

    total = len(cases)
    unsafe_count = sum(case.label == BlindCaseLabel.UNSAFE for case in cases)
    safe_count = sum(case.label == BlindCaseLabel.SAFE for case in cases)

    if total != expected_total:
        issues.append(_issue("warning", "unexpected_total", f"Expected {expected_total} cases, found {total}."))
    if unsafe_count != expected_unsafe:
        issues.append(_issue("warning", "unexpected_unsafe_count", f"Expected {expected_unsafe} unsafe cases, found {unsafe_count}."))
    if safe_count != expected_safe:
        issues.append(_issue("warning", "unexpected_safe_count", f"Expected {expected_safe} safe cases, found {safe_count}."))

    tool_counts = Counter(case.tool for case in cases)
    family_counts = Counter(case.family for case in cases)
    variant_counts = Counter(case.contract_variant.value for case in cases)
    dependence_counts = Counter(case.intended_contract_dependence.value for case in cases)
    rule_counts = Counter(case.contract_rule_id or "unspecified" for case in cases)

    reversal_count = variant_counts.get(ContractVariant.REVERSAL.value, 0)
    idiosyncratic_count = (
        variant_counts.get(ContractVariant.IDIOSYNCRATIC.value, 0)
        + variant_counts.get(ContractVariant.REVERSAL.value, 0)
    )
    high_dependence_count = dependence_counts.get(IntendedContractDependence.HIGH.value, 0)

    if reversal_count < min_reversal:
        issues.append(_issue("warning", "too_few_reversal_cases", f"Expected at least {min_reversal} reversal cases, found {reversal_count}."))
    if idiosyncratic_count < min_idiosyncratic:
        issues.append(_issue("warning", "too_few_idiosyncratic_cases", f"Expected at least {min_idiosyncratic} idiosyncratic/reversal cases, found {idiosyncratic_count}."))
    if high_dependence_count < min_high_dependence:
        issues.append(_issue("warning", "too_few_high_dependence_cases", f"Expected at least {min_high_dependence} intended high-dependence cases, found {high_dependence_count}."))

    seen_ids: set[str] = set()
    rule_label_counts: dict[str, Counter] = defaultdict(Counter)

    for case in cases:
        if case.case_id in seen_ids:
            issues.append(_issue("error", "duplicate_case_id", f"Duplicate case_id {case.case_id}.", case.case_id))
        seen_ids.add(case.case_id)

        if case.tool not in VALID_TOOLS:
            issues.append(_issue("error", "invalid_tool", f"Invalid tool {case.tool!r}.", case.case_id))

        if not case.rationale.strip():
            issues.append(_issue("error", "missing_rationale", "Case rationale is empty.", case.case_id))

        if case.contract_variant in {ContractVariant.IDIOSYNCRATIC, ContractVariant.REVERSAL}:
            if not case.contract_rule_id.strip():
                issues.append(_issue("error", "missing_contract_rule_id", "Idiosyncratic/reversal case lacks contract_rule_id.", case.case_id))
            if not case.contract_rule_summary.strip():
                issues.append(_issue("error", "missing_contract_rule_summary", "Idiosyncratic/reversal case lacks contract_rule_summary.", case.case_id))
            if case.intended_contract_dependence == IntendedContractDependence.UNSPECIFIED:
                issues.append(_issue("warning", "unspecified_contract_dependence", "Idiosyncratic/reversal case has unspecified intended_contract_dependence.", case.case_id))

        rule_key = case.contract_rule_id or "unspecified"
        rule_label_counts[rule_key][case.label.value] += 1
        rule_label_counts[rule_key]["total"] += 1

    for rule_id, counts in rule_label_counts.items():
        if rule_id == "unspecified":
            continue
        if counts.get("safe", 0) == 0 or counts.get("unsafe", 0) == 0:
            issues.append(
                _issue(
                    "warning",
                    "unpaired_contract_rule",
                    f"Contract rule {rule_id!r} has safe={counts.get('safe', 0)}, unsafe={counts.get('unsafe', 0)}. Prefer paired safe/unsafe cases.",
                )
            )

    valid = not any(issue.severity == "error" for issue in issues)

    return BlindV2ValidationReport(
        path=str(path),
        valid=valid,
        total_cases=total,
        unsafe_count=unsafe_count,
        safe_count=safe_count,
        tool_counts=dict(sorted(tool_counts.items())),
        family_counts=dict(sorted(family_counts.items())),
        contract_variant_counts=dict(sorted(variant_counts.items())),
        intended_contract_dependence_counts=dict(sorted(dependence_counts.items())),
        contract_rule_counts=dict(sorted(rule_counts.items())),
        paired_rule_summary={
            rule_id: dict(counts)
            for rule_id, counts in sorted(rule_label_counts.items())
        },
        issues=issues,
    )


def _issue(severity: str, code: str, message: str, case_id: str | None = None) -> BlindV2ValidationIssue:
    return BlindV2ValidationIssue(
        severity=severity,
        code=code,
        message=message,
        case_id=case_id,
    )
