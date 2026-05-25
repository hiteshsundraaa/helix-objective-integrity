from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from pydantic import BaseModel

from helix.benchmark.blind_loader import load_blind_cases_jsonl


GENERIC_VISIBLE_FIELDS = ("rationale", "memory", "context")

LEAK_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("signed_contract_phrase", re.compile(r"\bsigned\s+contract\b", re.IGNORECASE)),
    ("contract_says_phrase", re.compile(r"\bcontract\s+(says|states|requires|permits|allows|forbids|prohibits)\b", re.IGNORECASE)),
    ("explicit_contract_reference", re.compile(r"\b(contract|contractual)\b", re.IGNORECASE)),
    ("allowed_only_phrase", re.compile(r"\ballowed\s+only\b|\bonly\s+allowed\b", re.IGNORECASE)),
    ("forbidden_phrase", re.compile(r"\b(forbidden|prohibited|must\s+not|must\s+never|never\s+receive|explicitly\s+unauthorized)\b", re.IGNORECASE)),
    ("contract_rule_id_like", re.compile(r"\bR_[A-Z0-9_]+\b|\bcontract_rule_id\b", re.IGNORECASE)),
    ("rule_authority_phrase", re.compile(r"\brule\s+(says|states|requires|permits|allows|forbids|prohibits)\b", re.IGNORECASE)),
    ("partner_rule_phrase", re.compile(r"\bPartner\s+A\b|\bPartner\s+B\b", re.IGNORECASE)),
    ("project_rule_phrase", re.compile(r"\bProject\s+Atlas\b|\bProject\s+Borealis\b", re.IGNORECASE)),
    ("fixture_rule_phrase", re.compile(r"\bred_team_fixtures\b|\btraining_fixture\b", re.IGNORECASE)),
)


class ContractLeakageFinding(BaseModel):
    case_id: str
    label: str
    field: str
    pattern: str
    matched_text: str
    contract_variant: str
    intended_contract_dependence: str
    contract_rule_id: str
    family: str


class ContractLeakageAuditReport(BaseModel):
    path: str
    total_cases: int
    leaked_case_count: int
    leaked_field_count: int
    leakage_rate: float
    findings_by_pattern: dict[str, int]
    findings_by_field: dict[str, int]
    findings_by_variant: dict[str, int]
    findings: list[ContractLeakageFinding]

    def to_markdown(self) -> str:
        lines = [
            "# HELIX Contract Leakage Audit",
            "",
            f"Path: `{self.path}`",
            f"Total cases: `{self.total_cases}`",
            f"Leaked cases: `{self.leaked_case_count}`",
            f"Leaked fields: `{self.leaked_field_count}`",
            f"Leakage rate: `{self.leakage_rate:.3f}`",
            "",
            "## Findings by field",
            "",
            "| Field | Count |",
            "|---|---:|",
        ]
        for key, value in sorted(self.findings_by_field.items()):
            lines.append(f"| {key} | {value} |")

        lines.extend(["", "## Findings by pattern", "", "| Pattern | Count |", "|---|---:|"])
        for key, value in sorted(self.findings_by_pattern.items()):
            lines.append(f"| {key} | {value} |")

        lines.extend(["", "## Findings by variant", "", "| Variant | Count |", "|---|---:|"])
        for key, value in sorted(self.findings_by_variant.items()):
            lines.append(f"| {key} | {value} |")

        lines.extend(
            [
                "",
                "## Interpretation",
                "",
                "Contract leakage in generic-visible fields means the generic semantic judge may be seeing signed-contract information.",
                "If leakage is high, generic-vs-contract-aware decision comparisons are contaminated and should not be used as clean evidence of generic equivalence.",
            ]
        )
        return "\n".join(lines)


def audit_contract_leakage(path: str | Path) -> ContractLeakageAuditReport:
    cases = load_blind_cases_jsonl(path)
    findings: list[ContractLeakageFinding] = []

    for case in cases:
        for field in GENERIC_VISIBLE_FIELDS:
            value = getattr(case, field, "") or ""
            for pattern_name, pattern in LEAK_PATTERNS:
                for match in pattern.finditer(value):
                    findings.append(
                        ContractLeakageFinding(
                            case_id=case.case_id,
                            label=case.label.value,
                            field=field,
                            pattern=pattern_name,
                            matched_text=match.group(0),
                            contract_variant=case.contract_variant.value,
                            intended_contract_dependence=case.intended_contract_dependence.value,
                            contract_rule_id=case.contract_rule_id,
                            family=case.family,
                        )
                    )

    leaked_cases = {finding.case_id for finding in findings}
    by_pattern = Counter(f.pattern for f in findings)
    by_field = Counter(f.field for f in findings)
    by_variant = Counter(f.contract_variant for f in findings)

    return ContractLeakageAuditReport(
        path=str(path),
        total_cases=len(cases),
        leaked_case_count=len(leaked_cases),
        leaked_field_count=len(findings),
        leakage_rate=len(leaked_cases) / max(len(cases), 1),
        findings_by_pattern=dict(sorted(by_pattern.items())),
        findings_by_field=dict(sorted(by_field.items())),
        findings_by_variant=dict(sorted(by_variant.items())),
        findings=findings,
    )


def write_contract_leakage_outputs(report: ContractLeakageAuditReport, out_dir: str | Path) -> None:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)

    (target / "contract_leakage_report.json").write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (target / "contract_leakage_report.md").write_text(
        report.to_markdown(),
        encoding="utf-8",
    )
    (target / "contract_leakage_findings.jsonl").write_text(
        "\n".join(json.dumps(f.model_dump(mode="json"), sort_keys=True) for f in report.findings)
        + ("\n" if report.findings else ""),
        encoding="utf-8",
    )
