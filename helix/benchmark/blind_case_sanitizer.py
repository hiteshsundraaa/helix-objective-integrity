from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from pydantic import BaseModel

from helix.benchmark.blind_case_schema import BlindCase
from helix.benchmark.blind_loader import load_blind_cases_jsonl


EXPLICIT_LEAK_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("signed_contract_clause", re.compile(r"\bSigned contract:\s*", re.IGNORECASE)),
    ("contract_reference", re.compile(r"\b(the\s+)?signed\s+contract\b|\bcontract\b", re.IGNORECASE)),
    ("per_contract", re.compile(r"\bper\s+contract\b|\baccording\s+to\s+the\s+contract\b", re.IGNORECASE)),
    ("contract_forbids", re.compile(r"\bcontract\s+(forbids|prohibits|requires|allows|permits|states|says)\b", re.IGNORECASE)),
)

STRUCTURAL_CONTAMINATION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("restriction_revealed", re.compile(r"\b(restricted|restriction|forbidden|prohibited|unauthorized|not\s+authorized|must\s+not|must\s+never)\b", re.IGNORECASE)),
    ("policy_exception_revealed", re.compile(r"\b(allowed\s+only|only\s+allowed|exception|waiver|approved\s+recipient|excluded\s+recipient)\b", re.IGNORECASE)),
    ("project_specific_rule_hint", re.compile(r"\b(Project\s+Atlas|Project\s+Borealis|Partner\s+A|Partner\s+B|red_team_fixtures|training_fixture|incident_archive)\b", re.IGNORECASE)),
)

LABEL_LEAKING_CONTEXT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("explicit_expected_label", re.compile(r"\b(otherwise\s+normal.*unsafe|generic.*might|contract-specific|reverses?\s+the\s+expected|correctly\s+excludes|contrary\s+to)\b", re.IGNORECASE)),
    ("label_reasoning_terms", re.compile(r"\b(violates|violation|safe\s+because|unsafe\s+because|expected\s+label|ground\s+truth)\b", re.IGNORECASE)),
)


class SanitizationFinding(BaseModel):
    case_id: str
    field: str
    category: str
    pattern: str
    matched_text: str
    requires_human_review: bool


class SanitizedCaseRecord(BaseModel):
    case_id: str
    label: str
    tool: str
    rationale: str
    memory: str
    context: str
    label_reason: str
    family: str
    author: str
    notes: str
    intended_contract_dependence: str
    contract_variant: str
    contract_rule_id: str
    contract_rule_summary: str


class SanitizationReport(BaseModel):
    input_path: str
    output_path: str
    total_cases: int
    auto_sanitized_case_count: int
    human_review_case_count: int
    explicit_leak_count: int
    structural_contamination_count: int
    label_leak_count: int
    findings_by_category: dict[str, int]
    findings_by_field: dict[str, int]
    findings: list[SanitizationFinding]

    def to_markdown(self) -> str:
        lines = [
            "# HELIX Split-View Sanitization Report",
            "",
            f"Input: `{self.input_path}`",
            f"Output: `{self.output_path}`",
            f"Total cases: `{self.total_cases}`",
            f"Auto-sanitized cases: `{self.auto_sanitized_case_count}`",
            f"Human-review cases: `{self.human_review_case_count}`",
            "",
            "## Finding counts",
            "",
            f"- Explicit leak findings: `{self.explicit_leak_count}`",
            f"- Structural contamination findings: `{self.structural_contamination_count}`",
            f"- Label-leak findings: `{self.label_leak_count}`",
            "",
            "## Findings by category",
            "",
            "| Category | Count |",
            "|---|---:|",
        ]
        for key, value in sorted(self.findings_by_category.items()):
            lines.append(f"| {key} | {value} |")
        lines.extend(["", "## Findings by field", "", "| Field | Count |", "|---|---:|"])
        for key, value in sorted(self.findings_by_field.items()):
            lines.append(f"| {key} | {value} |")
        lines.extend(
            [
                "",
                "## Required interpretation",
                "",
                "This sanitizer creates a candidate split-view dataset. It does not certify the dataset as experimentally clean.",
                "Any case with structural or label-leaking contamination must be manually reviewed before being used for a clean generic-vs-contract-aware claim.",
            ]
        )
        return "\n".join(lines)


def sanitize_blind_cases(
    input_path: str | Path,
    output_path: str | Path,
    *,
    review_path: str | Path | None = None,
) -> SanitizationReport:
    cases = load_blind_cases_jsonl(input_path)
    sanitized_rows: list[SanitizedCaseRecord] = []
    findings: list[SanitizationFinding] = []

    for case in cases:
        clean = _sanitize_case(case)
        sanitized_rows.append(clean)

        for field in ("rationale", "memory", "context"):
            original = getattr(case, field, "") or ""
            sanitized = getattr(clean, field, "") or ""

            findings.extend(_find_explicit_leaks(case.case_id, field, original, sanitized))
            findings.extend(_find_structural_contamination(case.case_id, field, sanitized))
            findings.extend(_find_label_leaks(case.case_id, field, sanitized))

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "\n".join(json.dumps(row.model_dump(mode="json"), ensure_ascii=False, sort_keys=True) for row in sanitized_rows) + "\n",
        encoding="utf-8",
    )

    if review_path is not None:
        review = Path(review_path)
        review.parent.mkdir(parents=True, exist_ok=True)
        review.write_text(
            "\n".join(json.dumps(f.model_dump(mode="json"), sort_keys=True) for f in findings) + ("\n" if findings else ""),
            encoding="utf-8",
        )

    by_category = Counter(f.category for f in findings)
    by_field = Counter(f.field for f in findings)
    auto_cases = {f.case_id for f in findings if f.category == "explicit_leak"}
    review_cases = {f.case_id for f in findings if f.requires_human_review}

    return SanitizationReport(
        input_path=str(input_path),
        output_path=str(output_path),
        total_cases=len(cases),
        auto_sanitized_case_count=len(auto_cases),
        human_review_case_count=len(review_cases),
        explicit_leak_count=by_category.get("explicit_leak", 0),
        structural_contamination_count=by_category.get("structural_contamination", 0),
        label_leak_count=by_category.get("label_leak", 0),
        findings_by_category=dict(sorted(by_category.items())),
        findings_by_field=dict(sorted(by_field.items())),
        findings=findings,
    )


def _sanitize_case(case: BlindCase) -> SanitizedCaseRecord:
    rationale = _sanitize_text(case.rationale, field="rationale")
    memory = _sanitize_text(case.memory, field="memory")
    context = _sanitize_text(case.context, field="context")

    return SanitizedCaseRecord(
        case_id=case.case_id,
        label=case.label.value,
        tool=case.tool,
        rationale=rationale,
        memory=memory,
        context=context,
        label_reason=case.label_reason,
        family=case.family,
        author=case.author,
        notes=(case.notes + " | sanitized_candidate_requires_label_review").strip(" |"),
        intended_contract_dependence=case.intended_contract_dependence.value,
        contract_variant=case.contract_variant.value,
        contract_rule_id=case.contract_rule_id,
        contract_rule_summary=case.contract_rule_summary,
    )


def _sanitize_text(text: str, *, field: str) -> str:
    value = text or ""

    # Remove explicit leading contract authority fragments.
    value = re.sub(r"\bSigned contract:\s*", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\bAccording to the signed contract[:,]?\s*", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\bPer the signed contract[:,]?\s*", "", value, flags=re.IGNORECASE)

    # Rewrite common rationale leakage forms into action-only descriptions.
    value = re.sub(
        r"\s+even though the signed contract forbids that tool for Atlas",
        "",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        r",?\s+which is explicitly unauthorized by the contract",
        "",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        r"\s+where the contract permits only SHA-256 token hashes",
        "",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        r"\s+contrary to the signed contract",
        "",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        r"\s+despite the contract allowing only summaries of those files",
        "",
        value,
        flags=re.IGNORECASE,
    )

    # Remove generic contract nouns but leave action content.
    value = re.sub(r"\b(the\s+)?signed\s+contract\b", "the policy source", value, flags=re.IGNORECASE)
    value = re.sub(r"\bcontract\b", "policy source", value, flags=re.IGNORECASE)

    # Avoid leaving doubled spaces.
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _find_explicit_leaks(case_id: str, field: str, original: str, sanitized: str) -> list[SanitizationFinding]:
    findings: list[SanitizationFinding] = []
    for name, pattern in EXPLICIT_LEAK_PATTERNS:
        for match in pattern.finditer(original):
            findings.append(
                SanitizationFinding(
                    case_id=case_id,
                    field=field,
                    category="explicit_leak",
                    pattern=name,
                    matched_text=match.group(0),
                    requires_human_review=False,
                )
            )
    return findings


def _find_structural_contamination(case_id: str, field: str, sanitized: str) -> list[SanitizationFinding]:
    findings: list[SanitizationFinding] = []
    for name, pattern in STRUCTURAL_CONTAMINATION_PATTERNS:
        for match in pattern.finditer(sanitized):
            findings.append(
                SanitizationFinding(
                    case_id=case_id,
                    field=field,
                    category="structural_contamination",
                    pattern=name,
                    matched_text=match.group(0),
                    requires_human_review=True,
                )
            )
    return findings


def _find_label_leaks(case_id: str, field: str, sanitized: str) -> list[SanitizationFinding]:
    findings: list[SanitizationFinding] = []
    for name, pattern in LABEL_LEAKING_CONTEXT_PATTERNS:
        for match in pattern.finditer(sanitized):
            findings.append(
                SanitizationFinding(
                    case_id=case_id,
                    field=field,
                    category="label_leak",
                    pattern=name,
                    matched_text=match.group(0),
                    requires_human_review=True,
                )
            )
    return findings
