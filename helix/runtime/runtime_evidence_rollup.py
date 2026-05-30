from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


DEFAULT_RUNTIME_EVIDENCE_ARTIFACTS: dict[str, str] = {
    "runtime_summary": "outputs/v7_live_mock_harness/basic/runtime_summary.json",
    "runtime_receipts": "outputs/v7_live_mock_harness/basic/runtime_receipts.jsonl",
    "runtime_report": "outputs/v7_live_mock_harness/basic/runtime_report.md",
    "negative_control_summary": "outputs/v7_live_mock_harness/negative_controls/runtime_negative_control_summary.json",
    "negative_control_records": "outputs/v7_live_mock_harness/negative_controls/runtime_negative_control_records.jsonl",
    "negative_control_report": "outputs/v7_live_mock_harness/negative_controls/runtime_negative_control_report.md",
}


HEADLINE_METRIC_KEYS = [
    "runtime_receipt_count",
    "allow_count",
    "block_count",
    "escalate_count",
    "self_report_used_for_decision_count",
    "receipt_validation_issue_count",
    "exact_citation_rate_for_blocks",
    "mean_latency_ms",
    "max_latency_ms",
    "negative_control_count",
    "expected_failure_count",
    "observed_failure_count",
    "unexpected_pass_count",
    "unexpected_fail_count",
    "latency_only_mutation_valid",
    "issue_counts_by_code",
]


class RuntimeEvidenceArtifactStatus(BaseModel):
    name: str
    status: str
    path: str
    artifact_hash: str | None = None
    key_metrics: dict[str, Any] = Field(default_factory=dict)
    key_result: str = ""
    error: str | None = None


class RuntimeEvidenceRollupSummary(BaseModel):
    status: str
    generated_at: str
    artifact_count: int
    available_artifact_count: int
    missing_artifact_count: int
    artifact_hashes: dict[str, str]
    headline_metrics: dict[str, Any]
    strengths: list[str]
    limitations: list[str]
    missing_artifacts: list[str]
    recommended_next_steps: list[str]
    artifacts: list[RuntimeEvidenceArtifactStatus]

    def to_markdown(self) -> str:
        metrics = self.headline_metrics
        lines = [
            "# HELIX v7 Runtime Evidence Rollup",
            "",
            "## Executive Summary",
            "",
            _executive_summary(self),
            "",
            "## Evidence Inventory",
            "",
            "| Artifact | Status | Path | SHA256 | Key result |",
            "|---|---|---|---|---|",
        ]
        for artifact in self.artifacts:
            lines.append(
                f"| `{artifact.name}` | `{artifact.status}` | `{artifact.path}` | "
                f"`{artifact.artifact_hash or 'n/a'}` | {artifact.key_result or 'n/a'} |"
            )

        lines.extend(
            [
                "",
                "## Headline Runtime Results",
                "",
                f"- runtime_receipt_count: `{_value(metrics['runtime_receipt_count'])}`",
                f"- allow/block/escalate: `{_value(metrics['allow_count'])}` / "
                f"`{_value(metrics['block_count'])}` / `{_value(metrics['escalate_count'])}`",
                f"- self_report_used_for_decision_count: `{_value(metrics['self_report_used_for_decision_count'])}`",
                f"- receipt_validation_issue_count: `{_value(metrics['receipt_validation_issue_count'])}`",
                f"- exact_citation_rate_for_blocks: `{_value(metrics['exact_citation_rate_for_blocks'])}`",
                f"- mean_latency_ms: `{_value(metrics['mean_latency_ms'])}`",
                f"- max_latency_ms: `{_value(metrics['max_latency_ms'])}`",
                "",
                "## Runtime Negative Controls",
                "",
                f"- negative_control_count: `{_value(metrics['negative_control_count'])}`",
                f"- expected_failure_count: `{_value(metrics['expected_failure_count'])}`",
                f"- observed_failure_count: `{_value(metrics['observed_failure_count'])}`",
                f"- unexpected_pass_count: `{_value(metrics['unexpected_pass_count'])}`",
                f"- unexpected_fail_count: `{_value(metrics['unexpected_fail_count'])}`",
                f"- latency_only_mutation_valid: `{_value(metrics['latency_only_mutation_valid'])}`",
                f"- issue_counts_by_code: `{_value(metrics['issue_counts_by_code'])}`",
                "",
                "## What This Supports",
                "",
            ]
        )
        lines.extend(f"- {strength}" for strength in self.strengths)
        lines.extend(
            [
                "",
                "## What This Does Not Yet Prove",
                "",
                "- No live LLM agent loop yet.",
                "- No real external tools yet.",
                "- No OAuth/IAM integration yet.",
                "- No production proxy or broker yet.",
                "- Latency numbers are from deterministic mock logic, not production semantic evaluation.",
                "- No real enterprise workload validation yet.",
                "",
                "## Recommended Next Steps",
                "",
            ]
        )
        lines.extend(f"{index}. {step}" for index, step in enumerate(self.recommended_next_steps, start=1))
        if self.limitations:
            lines.extend(["", "## Rollup Limitations", ""])
            lines.extend(f"- {limitation}" for limitation in self.limitations)
        return "\n".join(lines)


def collect_v7_runtime_evidence_rollup(
    *,
    artifact_paths: dict[str, str | Path] | None = None,
    generated_at: str | None = None,
) -> RuntimeEvidenceRollupSummary:
    paths = {
        name: str(path)
        for name, path in (artifact_paths or DEFAULT_RUNTIME_EVIDENCE_ARTIFACTS).items()
    }
    artifacts = [_collect_artifact(name, path) for name, path in paths.items()]
    headline_metrics = _empty_headline_metrics()
    for artifact in artifacts:
        _merge_headline_metrics(headline_metrics, artifact)

    missing_artifacts = [
        f"{artifact.name}: {artifact.path}"
        for artifact in artifacts
        if artifact.status != "available"
    ]
    artifact_hashes = {
        artifact.name: artifact.artifact_hash
        for artifact in artifacts
        if artifact.artifact_hash is not None
    }
    available_count = sum(artifact.status == "available" for artifact in artifacts)
    missing_count = len(artifacts) - available_count
    return RuntimeEvidenceRollupSummary(
        status="complete" if missing_count == 0 else "partial",
        generated_at=generated_at or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        artifact_count=len(artifacts),
        available_artifact_count=available_count,
        missing_artifact_count=missing_count,
        artifact_hashes=artifact_hashes,
        headline_metrics=headline_metrics,
        strengths=_strengths(headline_metrics),
        limitations=_limitations(missing_artifacts),
        missing_artifacts=missing_artifacts,
        recommended_next_steps=_recommended_next_steps(),
        artifacts=artifacts,
    )


def write_v7_runtime_evidence_rollup_outputs(
    summary: RuntimeEvidenceRollupSummary,
    out_dir: str | Path,
) -> tuple[Path, Path]:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    summary_path = target / "helix_v7_runtime_summary.json"
    report_path = target / "helix_v7_runtime_report.md"
    summary_path.write_text(
        json.dumps(summary.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(summary.to_markdown() + "\n", encoding="utf-8")
    return summary_path, report_path


def stable_file_hash(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _collect_artifact(name: str, path: str | Path) -> RuntimeEvidenceArtifactStatus:
    target = Path(path)
    if not target.exists():
        return RuntimeEvidenceArtifactStatus(
            name=name,
            status="missing",
            path=str(target),
            key_result="missing",
        )

    artifact_hash = stable_file_hash(target)
    try:
        key_metrics = _extract_key_metrics(name, target)
    except Exception as exc:
        return RuntimeEvidenceArtifactStatus(
            name=name,
            status="invalid",
            path=str(target),
            artifact_hash=artifact_hash,
            key_result="invalid",
            error=str(exc),
        )

    return RuntimeEvidenceArtifactStatus(
        name=name,
        status="available",
        path=str(target),
        artifact_hash=artifact_hash,
        key_metrics=key_metrics,
        key_result=_key_result(name, key_metrics),
    )


def _extract_key_metrics(name: str, path: Path) -> dict[str, Any]:
    if name == "runtime_summary":
        data = json.loads(path.read_text(encoding="utf-8"))
        return {
            "receipt_count": data.get("receipt_count"),
            "allow_count": data.get("allow_count"),
            "block_count": data.get("block_count"),
            "escalate_count": data.get("escalate_count"),
            "self_report_used_for_decision_count": data.get("self_report_used_for_decision_count"),
            "receipt_validation_issue_count": data.get("receipt_validation_issue_count"),
            "exact_citation_rate_for_blocks": data.get("exact_citation_rate_for_blocks"),
            "mean_latency_ms": data.get("mean_latency_ms"),
            "max_latency_ms": data.get("max_latency_ms"),
        }
    if name == "runtime_receipts":
        return {"line_count": _count_jsonl_lines(path)}
    if name == "negative_control_summary":
        data = json.loads(path.read_text(encoding="utf-8"))
        return {
            "negative_control_count": data.get("negative_control_count"),
            "expected_failure_count": data.get("expected_failure_count"),
            "observed_failure_count": data.get("observed_failure_count"),
            "unexpected_pass_count": data.get("unexpected_pass_count"),
            "unexpected_fail_count": data.get("unexpected_fail_count"),
            "latency_only_mutation_valid": data.get("latency_only_mutation_valid"),
            "issue_counts_by_code": data.get("issue_counts_by_code"),
        }
    if name == "negative_control_records":
        return {"line_count": _count_jsonl_lines(path)}
    return {}


def _merge_headline_metrics(
    headline: dict[str, Any],
    artifact: RuntimeEvidenceArtifactStatus,
) -> None:
    metrics = artifact.key_metrics
    if artifact.name == "runtime_summary":
        headline["runtime_receipt_count"] = metrics.get("receipt_count")
        headline["allow_count"] = metrics.get("allow_count")
        headline["block_count"] = metrics.get("block_count")
        headline["escalate_count"] = metrics.get("escalate_count")
        headline["self_report_used_for_decision_count"] = metrics.get("self_report_used_for_decision_count")
        headline["receipt_validation_issue_count"] = metrics.get("receipt_validation_issue_count")
        headline["exact_citation_rate_for_blocks"] = metrics.get("exact_citation_rate_for_blocks")
        headline["mean_latency_ms"] = metrics.get("mean_latency_ms")
        headline["max_latency_ms"] = metrics.get("max_latency_ms")
    elif artifact.name == "runtime_receipts" and headline["runtime_receipt_count"] is None:
        headline["runtime_receipt_count"] = metrics.get("line_count")
    elif artifact.name == "negative_control_summary":
        headline["negative_control_count"] = metrics.get("negative_control_count")
        headline["expected_failure_count"] = metrics.get("expected_failure_count")
        headline["observed_failure_count"] = metrics.get("observed_failure_count")
        headline["unexpected_pass_count"] = metrics.get("unexpected_pass_count")
        headline["unexpected_fail_count"] = metrics.get("unexpected_fail_count")
        headline["latency_only_mutation_valid"] = metrics.get("latency_only_mutation_valid")
        headline["issue_counts_by_code"] = metrics.get("issue_counts_by_code")
    elif artifact.name == "negative_control_records" and headline["negative_control_count"] is None:
        line_count = metrics.get("line_count")
        headline["negative_control_count"] = line_count - 1 if isinstance(line_count, int) and line_count > 0 else line_count


def _key_result(name: str, metrics: dict[str, Any]) -> str:
    if name == "runtime_summary":
        return (
            f"receipts={_value(metrics.get('receipt_count'))}; "
            f"allow/block/escalate={_value(metrics.get('allow_count'))}/"
            f"{_value(metrics.get('block_count'))}/{_value(metrics.get('escalate_count'))}"
        )
    if name == "runtime_receipts":
        return f"receipt_lines={_value(metrics.get('line_count'))}"
    if name == "negative_control_summary":
        return (
            f"expected_failures={_value(metrics.get('expected_failure_count'))}; "
            f"unexpected_passes={_value(metrics.get('unexpected_pass_count'))}"
        )
    if name == "negative_control_records":
        return f"record_lines={_value(metrics.get('line_count'))}"
    return "available"


def _count_jsonl_lines(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _empty_headline_metrics() -> dict[str, Any]:
    return {key: None for key in HEADLINE_METRIC_KEYS}


def _strengths(metrics: dict[str, Any]) -> list[str]:
    strengths = [
        "HELIX can emit runtime authorization receipts from a deterministic mock tool-call loop.",
        "Runtime decisions are based on captured tool-call traces rather than the agent self-report.",
        "Hash-linked runtime receipts detect tampered receipt, contract, and tool-call evidence.",
        "BLOCK decisions are checked against exact active-rule citation requirements.",
        "Latency is measured in the mock deterministic harness.",
    ]
    if metrics.get("unexpected_pass_count") == 0:
        strengths.append("Runtime negative controls did not unexpectedly pass in the collected artifacts.")
    return strengths


def _limitations(missing_artifacts: list[str]) -> list[str]:
    limitations = [
        "This rollup reads existing v7 runtime artifacts only; it does not generate new runtime evidence.",
        "The runtime evidence is from a deterministic mock harness and must not be described as production-ready.",
    ]
    if missing_artifacts:
        limitations.append("One or more expected runtime artifacts are missing or invalid and are listed as next actions.")
    return limitations


def _recommended_next_steps() -> list[str]:
    return [
        "Build a v7.2 minimal real agent-loop adapter with mock tools.",
        "Add a runtime manifest and run hash for live harness outputs.",
        "Measure latency under repeated runtime harness runs.",
        "Define the integration boundary with OAuth/IAM.",
        "Collect an eventual human-audited set of runtime traces.",
    ]


def _executive_summary(summary: RuntimeEvidenceRollupSummary) -> str:
    if summary.status == "complete":
        return (
            "All expected v7 runtime artifacts were available and hashed. "
            "The rollup summarizes existing mock-runtime receipt evidence without creating new evidence."
        )
    return (
        f"The rollup is partial: {summary.available_artifact_count} of {summary.artifact_count} expected "
        "runtime artifacts were available and hashed. Missing artifacts are listed explicitly, and no absent "
        "metrics are fabricated."
    )


def _value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, float):
        return f"{value:.6f}"
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else "none"
    return str(value)
