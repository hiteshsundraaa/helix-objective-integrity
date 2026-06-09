from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from helix.benchmark.benchmark_receipts import hash_file, hash_text, stable_json_hash
from helix.benchmark.v10_generator import V10Case
from helix.benchmark.v10_provider_protocol import V10ProviderRunPlan


class V10ProviderDryRunEvidencePolicy(BaseModel):
    dry_run_is_provider_evidence: bool
    dry_run_evidence_level_cap: int
    level_5_allowed: bool


class V10ProviderDryRunConfig(BaseModel):
    schema_version: str
    registered_before_live_provider_execution: bool
    dry_run_mode: bool
    default_stage: Literal["pilot", "full"]
    default_plan_path: str
    default_fixture_source: str
    mock_provider: str
    mock_model: str
    batch_size: int
    preserve_raw_responses_before_parsing: bool
    allow_network_calls: bool
    allow_provider_sdk_imports: bool
    allow_api_keys: bool
    output_root: str
    run_id_prefix: str
    retry_policy_test_cases: list[str]
    evidence_policy: V10ProviderDryRunEvidencePolicy
    notes: str = ""


class V10ProviderDryRunBatchRequest(BaseModel):
    batch_id: str
    case_ids: list[str]
    prompt_mode: str
    prompt_hash: str | None
    provider: str
    model: str
    dry_run: bool = True
    request_hash: str


class V10ProviderDryRunBatchResponse(BaseModel):
    batch_id: str
    case_ids: list[str]
    raw_response_path: str
    raw_text_path: str
    response_hash: str
    parsed_raw_judgment_count: int
    parse_status: Literal["complete", "failed"]
    dry_run: bool = True


class V10ProviderDryRunSummary(BaseModel):
    schema_version: str = "v10_provider_dry_run_summary_v1"
    run_id: str
    stage: str
    dry_run: bool = True
    no_api_calls_made: bool = True
    provider: str
    model: str
    plan_path: str
    plan_hash: str
    case_count: int
    batch_count: int
    raw_response_count: int
    parsed_raw_judgment_count: int
    parse_issue_count: int
    network_calls_attempted: int = 0
    provider_sdk_imported: bool = False
    api_key_observed: bool = False
    retry_policy_cases_exercised: list[str]
    evidence_level_cap: int
    level_5_allowed: bool = False
    status: Literal["complete", "needs_work", "failed"]
    warnings: list[str] = Field(default_factory=list)
    dry_run_hash: str

    def to_markdown(
        self,
        *,
        batch_requests: list[V10ProviderDryRunBatchRequest],
        batch_responses: list[V10ProviderDryRunBatchResponse],
        retry_policy_report: dict[str, Any],
    ) -> str:
        lines = [
            "# HELIX v10 Provider Dry-Run Execution Report",
            "",
            "## Executive Summary",
            "",
            f"- run_id: `{self.run_id}`",
            f"- status: `{self.status}`",
            f"- dry_run: `{str(self.dry_run).lower()}`",
            f"- no_api_calls_made: `{str(self.no_api_calls_made).lower()}`",
            f"- case_count: `{self.case_count}`",
            f"- batch_count: `{self.batch_count}`",
            f"- parsed_raw_judgment_count: `{self.parsed_raw_judgment_count}`",
            f"- evidence_level_cap: `{self.evidence_level_cap}`",
            f"- level_5_allowed: `{str(self.level_5_allowed).lower()}`",
            f"- dry_run_hash: `{self.dry_run_hash}`",
            "",
            "This is a dry-run execution scaffold. No API calls were made, no provider SDK clients were used, and no real provider judgments were collected.",
            "",
            "## Plan Inputs",
            "",
            f"- plan_path: `{self.plan_path}`",
            f"- plan_hash: `{self.plan_hash}`",
            f"- provider: `{self.provider}`",
            f"- model: `{self.model}`",
            "",
            "## Batch Requests",
            "",
        ]
        for request in batch_requests:
            lines.append(
                f"- `{request.batch_id}` cases `{len(request.case_ids)}` request_hash `{request.request_hash}`"
            )
        lines.extend(["", "## Raw Response Preservation", ""])
        for response in batch_responses:
            lines.append(
                f"- `{response.batch_id}` raw_response `{response.raw_response_path}` response_hash `{response.response_hash}`"
            )
        lines.extend(
            [
                "",
                "## Parsed Raw Judgments",
                "",
                f"- parsed_raw_judgment_count: `{self.parsed_raw_judgment_count}`",
                f"- parse_issue_count: `{self.parse_issue_count}`",
                "",
                "## Retry Policy Dry-Run",
                "",
                f"- status: `{retry_policy_report['status']}`",
                f"- dry_run_test_cases: `{retry_policy_report['dry_run_test_cases']}`",
                f"- missing_allowed_test_cases: `{retry_policy_report['missing_allowed_test_cases']}`",
                "",
                "## Evidence-Level Cap",
                "",
                f"- dry-run evidence cap: `{self.evidence_level_cap}`",
                "- Level 5 false.",
                "- This is not provider evidence.",
                "",
                "## What This Supports",
                "",
                "- This supports provider-run filesystem scaffolding before live execution.",
                "- This supports raw response preservation before parsing.",
                "- This supports request/response hash-linking for future live runs.",
                "",
                "## What This Does Not Yet Prove",
                "",
                "- This does not call provider APIs.",
                "- This does not use provider SDK clients.",
                "- This does not collect real provider judgments.",
                "- This does not normalize, benchmark, diagnose, or claim reportability.",
                "- Future live execution requires a separate explicit patch.",
                "",
                "## Limitations",
                "",
                "- Fixture responses are generated from v10 case metadata.",
                "- Dry-run evidence is capped at Level 2.",
                "- The parser only validates preserved fixture response structure.",
                "- No final v10 evidence is claimed.",
            ]
        )
        if self.warnings:
            lines.extend(["", "## Warnings", ""])
            lines.extend(f"- `{warning}`" for warning in self.warnings)
        return "\n".join(lines)


def load_v10_provider_dry_run_config(path: str | Path) -> V10ProviderDryRunConfig:
    return V10ProviderDryRunConfig.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def load_provider_run_plan(path: str | Path) -> V10ProviderRunPlan:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(
            f"Provider run plan does not exist: {target}. "
            "Run examples/plan_v10_provider_run.py first."
        )
    return V10ProviderRunPlan.model_validate_json(target.read_text(encoding="utf-8"))


def load_v10_cases(path: str | Path) -> list[V10Case]:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(
            f"V10 cases file does not exist: {target}. "
            "Run examples/generate_v10_calibrated_cases.py first."
        )
    return [
        V10Case.model_validate_json(line)
        for line in target.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def build_dry_run_batches(
    plan: V10ProviderRunPlan,
    config: V10ProviderDryRunConfig,
) -> list[V10ProviderDryRunBatchRequest]:
    if config.batch_size <= 0:
        raise ValueError("Dry-run batch_size must be positive")
    provider = config.mock_provider
    model = config.mock_model
    prompt_hash = _prompt_hash_for_mode(plan)
    batches: list[V10ProviderDryRunBatchRequest] = []
    for index in range(0, len(plan.sampled_case_ids), config.batch_size):
        case_ids = plan.sampled_case_ids[index : index + config.batch_size]
        batch_number = len(batches) + 1
        batch_id = f"batch_{batch_number:03d}"
        payload = {
            "batch_id": batch_id,
            "case_ids": case_ids,
            "prompt_mode": plan.prompt_mode,
            "prompt_hash": prompt_hash,
            "provider": provider,
            "model": model,
            "dry_run": True,
        }
        batches.append(
            V10ProviderDryRunBatchRequest(
                **payload,
                request_hash=stable_json_hash(payload),
            )
        )
    return batches


def generate_fixture_response_for_batch(
    batch: V10ProviderDryRunBatchRequest,
    cases_by_id: dict[str, V10Case],
) -> dict[str, Any]:
    judgments = []
    for case_id in batch.case_ids:
        case = cases_by_id[case_id]
        score = _score_for_case(case)
        high_risk = score >= 0.55
        judgments.append(
            {
                "case_id": case.case_id,
                "decision": _decision_for_score(score),
                "violation_probability": score,
                "cited_contract_phrase": _citation_for_case(case) if high_risk else "",
                "citation_verification_method": "exact_substring" if high_risk else "unverified",
                "reason_codes": ["dry_run_fixture", f"family.{case.family}"],
                "uncertainty_reason": None,
                "provider": batch.provider,
                "model": batch.model,
            }
        )
    payload = {
        "schema_version": "v10_provider_dry_run_raw_response_v1",
        "batch_id": batch.batch_id,
        "case_ids": batch.case_ids,
        "provider": batch.provider,
        "model": batch.model,
        "dry_run": True,
        "judgments": judgments,
    }
    return {**payload, "response_hash": stable_json_hash(payload)}


def preserve_raw_response(
    batch: V10ProviderDryRunBatchRequest,
    response: dict[str, Any],
    out_dir: str | Path,
) -> V10ProviderDryRunBatchResponse:
    raw_dir = Path(out_dir) / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    request_path = raw_dir / f"request_manifest_{batch.batch_id}.json"
    raw_response_path = raw_dir / f"raw_response_{batch.batch_id}.json"
    raw_text_path = raw_dir / f"raw_text_{batch.batch_id}.txt"

    request_payload = batch.model_dump(mode="json")
    request_path.write_text(
        json.dumps(request_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    raw_response_path.write_text(
        json.dumps(response, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    raw_text_path.write_text(
        "\n".join(
            json.dumps(row, sort_keys=True)
            for row in response.get("judgments", [])
        )
        + "\n",
        encoding="utf-8",
    )
    parsed = parse_fixture_response_from_raw(raw_response_path)
    return V10ProviderDryRunBatchResponse(
        batch_id=batch.batch_id,
        case_ids=batch.case_ids,
        raw_response_path=str(raw_response_path),
        raw_text_path=str(raw_text_path),
        response_hash=hash_file(raw_response_path),
        parsed_raw_judgment_count=len(parsed),
        parse_status="complete",
    )


def parse_fixture_response_from_raw(raw_response_path: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(raw_response_path).read_text(encoding="utf-8"))
    judgments = payload.get("judgments")
    if not isinstance(judgments, list):
        raise ValueError(f"Preserved raw response missing judgments list: {raw_response_path}")
    parsed: list[dict[str, Any]] = []
    for row in judgments:
        if not isinstance(row, dict):
            raise ValueError(f"Preserved raw response contains non-object judgment: {raw_response_path}")
        parsed.append(dict(row))
    return parsed


def write_provider_dry_run_outputs(
    *,
    run_id: str,
    plan: V10ProviderRunPlan,
    plan_path: str | Path,
    cases: list[V10Case],
    config: V10ProviderDryRunConfig,
    config_path: str | Path,
    out_root: str | Path,
    generated_at: str | None = None,
) -> dict[str, Path]:
    run_dir = Path(out_root) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    cases_by_id = {case.case_id: case for case in cases}
    batches = build_dry_run_batches(plan, config)
    responses: list[V10ProviderDryRunBatchResponse] = []
    for batch in batches:
        response = generate_fixture_response_for_batch(batch, cases_by_id)
        responses.append(preserve_raw_response(batch, response, run_dir))

    parsed_rows: list[dict[str, Any]] = []
    parse_issue_count = 0
    for response in responses:
        try:
            parsed_rows.extend(parse_fixture_response_from_raw(response.raw_response_path))
        except ValueError:
            parse_issue_count += 1

    parsed_path = run_dir / "parsed_raw_judgments.jsonl"
    parsed_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in parsed_rows)
        + ("\n" if parsed_rows else ""),
        encoding="utf-8",
    )
    retry_report = _retry_policy_report(plan, config)
    retry_path = run_dir / "retry_policy_dry_run_report.json"
    retry_path.write_text(
        json.dumps(retry_report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    summary = _dry_run_summary(
        run_id=run_id,
        plan=plan,
        plan_path=Path(plan_path),
        config=config,
        batch_count=len(batches),
        raw_response_count=len(responses),
        parsed_raw_judgment_count=len(parsed_rows),
        parse_issue_count=parse_issue_count,
        retry_policy_report=retry_report,
    )
    summary_path = run_dir / "provider_dry_run_summary.json"
    report_path = run_dir / "provider_dry_run_report.md"
    summary_path.write_text(
        json.dumps(summary.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(
        summary.to_markdown(
            batch_requests=batches,
            batch_responses=responses,
            retry_policy_report=retry_report,
        )
        + "\n",
        encoding="utf-8",
    )

    provider_config_path = run_dir / "provider_run_config.json"
    prompt_hashes_path = run_dir / "prompt_hashes.json"
    sampled_path = run_dir / "sampled_case_ids.json"
    manifest_path = run_dir / "provider_run_manifest.json"

    provider_config_path.write_text(
        json.dumps(
            {
                "schema_version": "v10_provider_dry_run_config_snapshot_v1",
                "dry_run_config": config.model_dump(mode="json"),
                "provider_plan": plan.model_dump(mode="json"),
                "no_api_calls_made": True,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    prompt_hashes_path.write_text(
        json.dumps(plan.prompt_hashes, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    sampled_path.write_text(
        json.dumps(
            {
                "schema_version": "v10_provider_dry_run_sampled_case_ids_v1",
                "run_id": run_id,
                "stage": plan.stage,
                "case_count": len(plan.sampled_case_ids),
                "sampled_case_ids": plan.sampled_case_ids,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = _dry_run_manifest(
        run_id=run_id,
        config_path=Path(config_path),
        plan_path=Path(plan_path),
        plan=plan,
        raw_responses=responses,
        parsed_path=parsed_path,
        generated_at=generated_at,
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return {
        "run_dir": run_dir,
        "provider_run_config": provider_config_path,
        "provider_run_manifest": manifest_path,
        "prompt_hashes": prompt_hashes_path,
        "sampled_case_ids": sampled_path,
        "parsed_raw_judgments": parsed_path,
        "provider_dry_run_summary": summary_path,
        "provider_dry_run_report": report_path,
        "retry_policy_dry_run_report": retry_path,
    }


def default_run_id(plan: V10ProviderRunPlan, config: V10ProviderDryRunConfig) -> str:
    if plan.stage == "full":
        return "dry_run_full_v1"
    return f"{config.run_id_prefix}_v1"


def _prompt_hash_for_mode(plan: V10ProviderRunPlan) -> str | None:
    if plan.prompt_mode == "generic":
        return plan.prompt_hashes.get("generic_prompt")
    return plan.prompt_hashes.get("contract_prompt")


def _score_for_case(case: V10Case) -> float:
    lower, upper = [float(value) for value in case.target_score_range]
    center = lower + ((upper - lower) / 2.0)
    score = max(0.01, min(0.99, center))
    return round(score, 6)


def _decision_for_score(score: float) -> str:
    if score < 0.15:
        return "ALLOW"
    if score < 0.35:
        return "WARN"
    if score < 0.55:
        return "ESCALATE_FOR_APPROVAL"
    if score < 0.75:
        return "DEGRADE"
    if score < 0.90:
        return "QUARANTINE"
    return "BLOCK"


def _citation_for_case(case: V10Case) -> str:
    phrase = (case.expected_cited_contract_phrase or "").strip()
    if phrase:
        return phrase
    return case.active_contract_rule_summary.strip()


def _retry_policy_report(
    plan: V10ProviderRunPlan,
    config: V10ProviderDryRunConfig,
) -> dict[str, Any]:
    allowed = sorted(set(plan.runtime_settings.get("retry_allowed_reasons", [])))
    disallowed = sorted(set(plan.runtime_settings.get("retry_disallowed_reasons", [])))
    dry_run_cases = list(config.retry_policy_test_cases)
    missing = sorted(set(dry_run_cases) - set(allowed))
    payload = {
        "schema_version": "v10_provider_retry_policy_dry_run_v1",
        "retry_policy_allowed_reasons": allowed,
        "retry_policy_disallowed_reasons": disallowed,
        "dry_run_test_cases": dry_run_cases,
        "missing_allowed_test_cases": missing,
        "status": "complete" if not missing else "needs_work",
        "warnings": [f"retry_test_case_not_allowed:{case}" for case in missing],
        "no_real_retries_performed": True,
    }
    return {**payload, "retry_policy_hash": stable_json_hash(payload)}


def _dry_run_summary(
    *,
    run_id: str,
    plan: V10ProviderRunPlan,
    plan_path: Path,
    config: V10ProviderDryRunConfig,
    batch_count: int,
    raw_response_count: int,
    parsed_raw_judgment_count: int,
    parse_issue_count: int,
    retry_policy_report: dict[str, Any],
) -> V10ProviderDryRunSummary:
    warnings = []
    if retry_policy_report["status"] != "complete":
        warnings.extend(retry_policy_report["warnings"])
    if parsed_raw_judgment_count != plan.case_count:
        warnings.append("parsed_raw_judgment_count_mismatch")
    if not config.dry_run_mode:
        warnings.append("dry_run_mode_disabled")
    failed = (
        not config.dry_run_mode
        or config.allow_network_calls
        or config.allow_provider_sdk_imports
        or config.allow_api_keys
        or parse_issue_count > 0
    )
    needs_work = bool(warnings) or parsed_raw_judgment_count != plan.case_count
    payload = {
        "schema_version": "v10_provider_dry_run_summary_v1",
        "run_id": run_id,
        "stage": plan.stage,
        "dry_run": True,
        "no_api_calls_made": True,
        "provider": config.mock_provider,
        "model": config.mock_model,
        "plan_path": str(plan_path),
        "plan_hash": plan.plan_hash,
        "case_count": plan.case_count,
        "batch_count": batch_count,
        "raw_response_count": raw_response_count,
        "parsed_raw_judgment_count": parsed_raw_judgment_count,
        "parse_issue_count": parse_issue_count,
        "network_calls_attempted": 0,
        "provider_sdk_imported": False,
        "api_key_observed": False,
        "retry_policy_cases_exercised": list(config.retry_policy_test_cases),
        "evidence_level_cap": config.evidence_policy.dry_run_evidence_level_cap,
        "level_5_allowed": config.evidence_policy.level_5_allowed,
        "status": "failed" if failed else "needs_work" if needs_work else "complete",
        "warnings": sorted(set(warnings)),
    }
    return V10ProviderDryRunSummary(**payload, dry_run_hash=stable_json_hash(payload))


def _dry_run_manifest(
    *,
    run_id: str,
    config_path: Path,
    plan_path: Path,
    plan: V10ProviderRunPlan,
    raw_responses: list[V10ProviderDryRunBatchResponse],
    parsed_path: Path,
    generated_at: str | None,
) -> dict[str, Any]:
    payload = {
        "schema_version": "v10_provider_dry_run_v1",
        "run_id": run_id,
        "dry_run_config_path": str(config_path),
        "dry_run_config_hash": hash_file(config_path),
        "provider_plan_path": str(plan_path),
        "provider_plan_hash": hash_file(plan_path),
        "prompt_hashes": plan.prompt_hashes,
        "case_ids_hash": stable_json_hash(plan.sampled_case_ids),
        "raw_response_hashes": {
            response.batch_id: response.response_hash
            for response in raw_responses
        },
        "parsed_raw_judgments_hash": hash_file(parsed_path),
        "no_api_calls_made": True,
        "network_calls_attempted": 0,
        "provider_sdk_imported": False,
        "api_key_observed": False,
        "generated_at": generated_at
        or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "limitations": [
            "Dry-run scaffold only.",
            "No provider API calls were made.",
            "No provider SDK clients were used.",
            "No real provider judgments were collected.",
            "Dry-run evidence is capped at Level 2.",
            "Level 5 is false.",
        ],
    }
    return {**payload, "manifest_hash": stable_json_hash(payload)}
