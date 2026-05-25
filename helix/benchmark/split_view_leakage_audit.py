from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from pydantic import BaseModel

from helix.benchmark.split_view_loader import load_split_view_cases_jsonl
from helix.benchmark.split_view_prompt_rendering import (
    check_generic_prompt_contamination,
    render_split_view_semantic_prompt,
)


class SplitViewLeakageAuditReport(BaseModel):
    path: str
    total_cases: int

    generic_contaminated_case_count: int
    generic_contaminated_field_count: int
    generic_contamination_by_pattern: dict[str, int]
    generic_contamination_by_field: dict[str, int]
    generic_contamination_findings: list[dict[str, str]]

    generic_prompt_renderable: bool
    generic_prompt_error: str | None = None

    generic_hides_contract_rule_id: bool
    generic_hides_contract_rule_summary: bool
    generic_hides_label: bool
    generic_hides_label_reason: bool

    contract_aware_prompt_renderable: bool
    contract_aware_prompt_error: str | None = None

    contract_aware_exposes_contract_rule_id: bool
    contract_aware_exposes_contract_rule_summary: bool
    contract_aware_hides_label: bool
    contract_aware_hides_label_reason: bool

    split_view_receipt_clean: bool

    def to_markdown(self) -> str:
        lines = [
            "# HELIX Split-View Leakage Audit",
            "",
            f"Path: `{self.path}`",
            f"Total cases: `{self.total_cases}`",
            "",
            "## Generic contamination guard",
            "",
            f"Contaminated cases: `{self.generic_contaminated_case_count}`",
            f"Contaminated fields: `{self.generic_contaminated_field_count}`",
            "",
            "| Pattern | Count |",
            "|---|---:|",
        ]

        for key, value in sorted(self.generic_contamination_by_pattern.items()):
            lines.append(f"| {key} | {value} |")

        lines.extend(
            [
                "",
                "## Prompt-surface checks",
                "",
                "| Check | Result |",
                "|---|---:|",
                f"| Generic prompt renderable | `{self.generic_prompt_renderable}` |",
                f"| Generic hides contract_rule_id | `{self.generic_hides_contract_rule_id}` |",
                f"| Generic hides contract_rule_summary | `{self.generic_hides_contract_rule_summary}` |",
                f"| Generic hides label | `{self.generic_hides_label}` |",
                f"| Generic hides label_reason | `{self.generic_hides_label_reason}` |",
                f"| Contract-aware prompt renderable | `{self.contract_aware_prompt_renderable}` |",
                f"| Contract-aware exposes contract_rule_id | `{self.contract_aware_exposes_contract_rule_id}` |",
                f"| Contract-aware exposes contract_rule_summary | `{self.contract_aware_exposes_contract_rule_summary}` |",
                f"| Contract-aware hides label | `{self.contract_aware_hides_label}` |",
                f"| Contract-aware hides label_reason | `{self.contract_aware_hides_label_reason}` |",
                "",
                "## Receipt verdict",
                "",
                f"Split-view receipt clean: `{self.split_view_receipt_clean}`",
                "",
                "## Interpretation",
                "",
                "A clean split-view receipt means the generic prompt surface was checked for contract leakage before contract-aware lift is measured.",
                "If this report is not clean, generic-vs-contract-aware comparisons should not be treated as clean evidence of contract dependence.",
            ]
        )

        if self.generic_prompt_error:
            lines.extend(["", "## Generic prompt error", "", f"`{self.generic_prompt_error}`"])

        if self.contract_aware_prompt_error:
            lines.extend(["", "## Contract-aware prompt error", "", f"`{self.contract_aware_prompt_error}`"])

        return "\n".join(lines)



def _input_payload_text(prompt: str) -> str:
    marker = "Input cases:"
    if marker not in prompt:
        return prompt
    return prompt.split(marker, 1)[1]


def _contains_any(prompt: str, values: list[str]) -> bool:
    return any(value and value in prompt for value in values)


def audit_split_view_leakage(path: str | Path) -> SplitViewLeakageAuditReport:
    cases = load_split_view_cases_jsonl(path)
    contamination = check_generic_prompt_contamination(cases)

    contaminated_cases = {issue["case_id"] for issue in contamination}
    by_pattern = Counter(issue["pattern"] for issue in contamination)
    by_field = Counter(issue["field"] for issue in contamination)

    contract_rule_ids = [case.contract_rule_id for case in cases]
    contract_rule_summaries = [case.contract_rule_summary for case in cases]
    label_payload_markers = ['"label"', "'label'"]
    label_reason_payload_markers = ['"label_reason"', "'label_reason'"]

    generic_prompt = ""
    generic_prompt_renderable = True
    generic_prompt_error = None
    try:
        generic_prompt = render_split_view_semantic_prompt(path, mode="generic")
    except Exception as exc:  # audit must report failure, not hide it
        generic_prompt_renderable = False
        generic_prompt_error = f"{type(exc).__name__}: {exc}"

    contract_prompt = ""
    contract_aware_prompt_renderable = True
    contract_aware_prompt_error = None
    try:
        contract_prompt = render_split_view_semantic_prompt(path, mode="contract_aware")
    except Exception as exc:  # audit must report failure, not hide it
        contract_aware_prompt_renderable = False
        contract_aware_prompt_error = f"{type(exc).__name__}: {exc}"

    generic_payload_text = _input_payload_text(generic_prompt)
    contract_payload_text = _input_payload_text(contract_prompt)

    generic_hides_contract_rule_id = not _contains_any(generic_payload_text, contract_rule_ids)
    generic_hides_contract_rule_summary = not _contains_any(generic_payload_text, contract_rule_summaries)
    generic_hides_label = not _contains_any(generic_payload_text, label_payload_markers)
    generic_hides_label_reason = not _contains_any(generic_payload_text, label_reason_payload_markers)

    contract_aware_exposes_contract_rule_id = _contains_any(contract_payload_text, contract_rule_ids)
    contract_aware_exposes_contract_rule_summary = _contains_any(contract_payload_text, contract_rule_summaries)
    contract_aware_hides_label = not _contains_any(contract_payload_text, label_payload_markers)
    contract_aware_hides_label_reason = not _contains_any(contract_payload_text, label_reason_payload_markers)

    split_view_receipt_clean = all(
        [
            len(contamination) == 0,
            generic_prompt_renderable,
            generic_hides_contract_rule_id,
            generic_hides_contract_rule_summary,
            generic_hides_label,
            generic_hides_label_reason,
            contract_aware_prompt_renderable,
            contract_aware_exposes_contract_rule_id,
            contract_aware_exposes_contract_rule_summary,
            contract_aware_hides_label,
            contract_aware_hides_label_reason,
        ]
    )

    return SplitViewLeakageAuditReport(
        path=str(path),
        total_cases=len(cases),
        generic_contaminated_case_count=len(contaminated_cases),
        generic_contaminated_field_count=len(contamination),
        generic_contamination_by_pattern=dict(sorted(by_pattern.items())),
        generic_contamination_by_field=dict(sorted(by_field.items())),
        generic_contamination_findings=contamination,
        generic_prompt_renderable=generic_prompt_renderable,
        generic_prompt_error=generic_prompt_error,
        generic_hides_contract_rule_id=generic_hides_contract_rule_id,
        generic_hides_contract_rule_summary=generic_hides_contract_rule_summary,
        generic_hides_label=generic_hides_label,
        generic_hides_label_reason=generic_hides_label_reason,
        contract_aware_prompt_renderable=contract_aware_prompt_renderable,
        contract_aware_prompt_error=contract_aware_prompt_error,
        contract_aware_exposes_contract_rule_id=contract_aware_exposes_contract_rule_id,
        contract_aware_exposes_contract_rule_summary=contract_aware_exposes_contract_rule_summary,
        contract_aware_hides_label=contract_aware_hides_label,
        contract_aware_hides_label_reason=contract_aware_hides_label_reason,
        split_view_receipt_clean=split_view_receipt_clean,
    )


def write_split_view_leakage_outputs(report: SplitViewLeakageAuditReport, out_dir: str | Path) -> None:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)

    (target / "split_view_leakage_report.json").write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (target / "split_view_leakage_report.md").write_text(
        report.to_markdown(),
        encoding="utf-8",
    )
    (target / "split_view_leakage_findings.jsonl").write_text(
        "\n".join(json.dumps(finding, sort_keys=True) for finding in report.generic_contamination_findings)
        + ("\n" if report.generic_contamination_findings else ""),
        encoding="utf-8",
    )
