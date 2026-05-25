from __future__ import annotations

GENERIC_IDENTITY_FIELDS = (
    "tool",
    "generic_rationale",
    "generic_memory",
    "generic_context",
)

LABEL_LEAK_TOKENS = (
    "safe",
    "unsafe",
    "allow",
    "allowed",
    "block",
    "blocked",
    "violation",
    "violating",
    "compliant",
    "noncompliant",
    "benign",
    "malicious",
)

def _case_value(case: object, field: str) -> object:
    if isinstance(case, dict):
        return case.get(field)
    return getattr(case, field)


from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

from pydantic import BaseModel

from helix.benchmark.blind_case_schema import BlindCaseLabel
from helix.benchmark.split_view_loader import SplitViewBlindCaseLoadError, load_split_view_cases_jsonl
from helix.benchmark.split_view_prompt_rendering import check_generic_prompt_contamination
from helix.benchmark.split_view_schema import SplitViewBlindCase


class PairedSplitViewValidationIssue(BaseModel):
    severity: str
    code: str
    message: str
    pair_id: str | None = None
    case_id: str | None = None


class PairSummary(BaseModel):
    pair_id: str
    case_ids: list[str]
    safe_count: int
    unsafe_count: int
    tool_count: int
    family_count: int
    stratum_count: int
    rationale_similarity: float
    memory_similarity: float
    context_similarity: float
    contract_rule_summaries_distinct: bool


class PairedSplitViewValidationReport(BaseModel):
    path: str
    valid: bool
    total_cases: int
    pair_count: int
    safe_count: int
    unsafe_count: int
    pair_summaries: list[PairSummary]
    issues: list[PairedSplitViewValidationIssue]

    def to_markdown(self) -> str:
        lines = [
            "# HELIX Paired Split-View Dataset Validation Report",
            "",
            f"Path: `{self.path}`",
            f"Valid: `{self.valid}`",
            f"Total cases: `{self.total_cases}`",
            f"Pairs: `{self.pair_count}`",
            f"Unsafe: `{self.unsafe_count}`",
            f"Safe: `{self.safe_count}`",
            "",
            "## Pair summaries",
            "",
            "| Pair | Cases | Safe | Unsafe | Rationale sim | Memory sim | Context sim | Contract rules distinct |",
            "|---|---:|---:|---:|---:|---:|---:|---|",
        ]
        for pair in self.pair_summaries:
            lines.append(
                f"| {pair.pair_id} | {len(pair.case_ids)} | {pair.safe_count} | {pair.unsafe_count} | "
                f"{pair.rationale_similarity:.3f} | {pair.memory_similarity:.3f} | {pair.context_similarity:.3f} | "
                f"{pair.contract_rule_summaries_distinct} |"
            )

        lines.extend(["", "## Issues", ""])
        if not self.issues:
            lines.append("No validation issues.")
        else:
            lines.extend(["| Severity | Code | Pair | Case | Message |", "|---|---|---|---|---|"])
            for issue in self.issues:
                lines.append(
                    f"| {issue.severity} | {issue.code} | {issue.pair_id or ''} | {issue.case_id or ''} | {issue.message} |"
                )

        return "\n".join(lines)


def validate_paired_split_view_cases(
    path: str | Path,
    *,
    min_pairs: int = 50,
    min_generic_similarity: float = 0.90,
    require_exact_generic_identity: bool = False,
    require_exact_same_tool: bool = True,
    require_same_family: bool = True,
    require_same_stratum: bool = True,
    require_distinct_contract_rules: bool = True,
    require_no_generic_contamination: bool = True,
) -> PairedSplitViewValidationReport:
    issues: list[PairedSplitViewValidationIssue] = []

    try:
        cases = load_split_view_cases_jsonl(path)
    except SplitViewBlindCaseLoadError as exc:
        return PairedSplitViewValidationReport(
            path=str(path),
            valid=False,
            total_cases=0,
            pair_count=0,
            unsafe_count=0,
            safe_count=0,
            pair_summaries=[],
            issues=[_issue("error", "load_error", str(exc))],
        )

    for case in cases:
        case_id_lower = case.case_id.lower()
        leaked_tokens = [token for token in LABEL_LEAK_TOKENS if token in case_id_lower]

        if leaked_tokens:
            issues.append(
                _issue(
                    "error",
                    "case_id_label_leak",
                    (
                        f"case_id contains label-bearing token(s): {', '.join(leaked_tokens)}. "
                        "Case identifiers must be opaque and must not reveal safe/unsafe status."
                    ),
                    case_id=case.case_id,
                )
            )

    grouped: dict[str, list[SplitViewBlindCase]] = defaultdict(list)
    for case in cases:
        pair_id = _pair_id(case)
        if not pair_id:
            issues.append(_issue("error", "missing_pair_id", "Case metadata must contain pair_id or notes must include pair_id=...", case_id=case.case_id))
            continue
        grouped[pair_id].append(case)

    if len(grouped) < min_pairs:
        issues.append(_issue("warning", "too_few_pairs", f"Expected at least {min_pairs} pairs, found {len(grouped)}."))

    if require_no_generic_contamination:
        contamination = check_generic_prompt_contamination(cases)
        for item in contamination:
            issues.append(
                _issue(
                    "error",
                    "generic_contract_contamination",
                    f"Generic field leaks contract rule: field={item.get('field')} pattern={item.get('pattern')} match={item.get('match')}",
                    case_id=item.get("case_id"),
                )
            )

    pair_summaries: list[PairSummary] = []

    for pair_id, members in sorted(grouped.items()):
        labels = Counter(member.label.value for member in members)
        tools = {member.tool for member in members}
        families = {member.family.value for member in members}
        strata = {member.contract_information_stratum.value for member in members}
        rule_summaries = {member.contract_rule_summary for member in members}

        if len(members) != 2:
            issues.append(_issue("error", "pair_wrong_size", f"Pair must contain exactly 2 cases, found {len(members)}.", pair_id=pair_id))
        if labels.get("safe", 0) != 1 or labels.get("unsafe", 0) != 1:
            issues.append(_issue("error", "pair_label_not_one_safe_one_unsafe", f"Pair must have one safe and one unsafe case, got safe={labels.get('safe', 0)}, unsafe={labels.get('unsafe', 0)}.", pair_id=pair_id))
        if require_exact_same_tool and len(tools) != 1:
            issues.append(_issue("error", "pair_tool_mismatch", f"Pair must use the same tool, got {sorted(tools)}.", pair_id=pair_id))
        if require_same_family and len(families) != 1:
            issues.append(_issue("error", "pair_family_mismatch", f"Pair must use same family, got {sorted(families)}.", pair_id=pair_id))
        if require_same_stratum and len(strata) != 1:
            issues.append(_issue("error", "pair_stratum_mismatch", f"Pair must use same stratum, got {sorted(strata)}.", pair_id=pair_id))
        if require_distinct_contract_rules and len(rule_summaries) != len(members):
            issues.append(_issue("error", "pair_contract_rules_not_distinct", "Safe/unsafe cases must have different contract_rule_summary values.", pair_id=pair_id))

        sim = _pair_similarities(members)
        if len(members) == 2:
            for field, value in sim.items():
                if value < min_generic_similarity:
                    issues.append(
                        _issue(
                            "error",
                            "pair_generic_fields_not_similar",
                            f"{field} similarity {value:.3f} is below required {min_generic_similarity:.3f}.",
                            pair_id=pair_id,
                        )
                    )

        if require_exact_generic_identity and len(members) == 2:
            safe_members = [member for member in members if member.label == BlindCaseLabel.SAFE]
            unsafe_members = [member for member in members if member.label == BlindCaseLabel.UNSAFE]

            if len(safe_members) == 1 and len(unsafe_members) == 1:
                safe_case = safe_members[0]
                unsafe_case = unsafe_members[0]

                for field in GENERIC_IDENTITY_FIELDS:
                    safe_value = _case_value(safe_case, field)
                    unsafe_value = _case_value(unsafe_case, field)

                    if safe_value != unsafe_value:
                        issues.append(
                            _issue(
                                "error",
                                "generic_identity_violation",
                                (
                                    f"Unsafe/safe generic-visible field differs for {field}. "
                                    "This pair cannot support a contract-dependence claim."
                                ),
                                pair_id=pair_id,
                            )
                        )

        pair_summaries.append(
            PairSummary(
                pair_id=pair_id,
                case_ids=[member.case_id for member in members],
                safe_count=labels.get("safe", 0),
                unsafe_count=labels.get("unsafe", 0),
                tool_count=len(tools),
                family_count=len(families),
                stratum_count=len(strata),
                rationale_similarity=sim.get("generic_rationale", 0.0),
                memory_similarity=sim.get("generic_memory", 0.0),
                context_similarity=sim.get("generic_context", 0.0),
                contract_rule_summaries_distinct=len(rule_summaries) == len(members),
            )
        )

    unsafe_count = sum(case.label == BlindCaseLabel.UNSAFE for case in cases)
    safe_count = sum(case.label == BlindCaseLabel.SAFE for case in cases)

    valid = not any(issue.severity == "error" for issue in issues)

    return PairedSplitViewValidationReport(
        path=str(path),
        valid=valid,
        total_cases=len(cases),
        pair_count=len(grouped),
        unsafe_count=unsafe_count,
        safe_count=safe_count,
        pair_summaries=pair_summaries,
        issues=issues,
    )


def _pair_id(case: SplitViewBlindCase) -> str:
    metadata_pair_id = getattr(case, "pair_id", None)
    if metadata_pair_id:
        return str(metadata_pair_id)

    # The current SplitViewBlindCase schema does not yet have a dedicated pair_id field.
    # To avoid a disruptive schema migration, v0.6.3b accepts pair_id=... inside notes.
    if case.notes:
        for part in case.notes.replace(";", " ").split():
            if part.startswith("pair_id="):
                return part.split("=", 1)[1].strip()
    return ""


def _pair_similarities(members: list[SplitViewBlindCase]) -> dict[str, float]:
    if len(members) != 2:
        return {"generic_rationale": 0.0, "generic_memory": 0.0, "generic_context": 0.0}

    a, b = members
    return {
        "generic_rationale": _similarity(a.generic_rationale, b.generic_rationale),
        "generic_memory": _similarity(a.generic_memory, b.generic_memory),
        "generic_context": _similarity(a.generic_context, b.generic_context),
    }


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, " ".join(a.lower().split()), " ".join(b.lower().split())).ratio()


def _issue(
    severity: str,
    code: str,
    message: str,
    *,
    pair_id: str | None = None,
    case_id: str | None = None,
) -> PairedSplitViewValidationIssue:
    return PairedSplitViewValidationIssue(
        severity=severity,
        code=code,
        message=message,
        pair_id=pair_id,
        case_id=case_id,
    )
