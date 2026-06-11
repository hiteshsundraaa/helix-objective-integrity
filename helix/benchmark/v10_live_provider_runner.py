from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import random
import re
import time
from typing import Any, Callable, Literal

from pydantic import BaseModel, Field

from helix.benchmark.benchmark_receipts import hash_file, hash_text, stable_json_hash
from helix.benchmark.v10_benchmark_runner import (
    build_v10_benchmark_receipts,
    compute_v10_benchmark_metrics,
    load_v10_benchmark_config,
    validate_v10_benchmark_receipts,
    write_v10_benchmark_outputs,
)
from helix.benchmark.v10_diagnostics import (
    bootstrap_v10_metric_cis,
    build_v10_diagnostics_summary,
    compute_v10_selectivity_baselines,
    load_v10_diagnostics_config,
    run_v10_integrity_diagnostic,
    run_v10_reportability_diagnostic,
    write_v10_diagnostics_outputs,
)
from helix.benchmark.v10_generator import V10Case
from helix.benchmark.v10_judgment_normalization import (
    V10NormalizedJudgment,
    load_raw_judgments,
    load_v10_normalization_config,
    normalize_v10_judgments,
    write_v10_normalization_outputs,
)
from helix.benchmark.v10_live_runner_design_gate import (
    ProviderAdapter,
    ProviderResult,
    SecretsProvider,
    V10LiveRunnerDesignConfig,
    load_v10_live_runner_design_config,
    validate_execution_mode_path,
    validate_provider_model_allowed,
)
from helix.benchmark.v10_pilot_evidence_assessor import (
    V10PilotEvidenceAssessment,
    assess_v10_pilot_evidence,
    load_v10_pilot_evidence_assessment_config,
    write_v10_pilot_evidence_assessment,
)
from helix.benchmark.v10_provider_protocol import V10ProviderRunPlan
from helix.benchmark.v10_provider_raw_import import load_provider_run_plan
from helix.benchmark.v10_receipt_chain import (
    V10ReceiptChainConfig,
    V10ReceiptChainSummary,
    build_receipt_chain,
    write_receipt_chain_outputs,
)


class LiveExecutionNotAuthorizedError(RuntimeError):
    pass


class ProviderModelNotAllowedError(RuntimeError):
    pass


class LiveOutputPathError(RuntimeError):
    pass


class LiveRunAbortedError(RuntimeError):
    pass


class LiveProviderCallError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retryable: bool | None = None,
        reason: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable
        self.reason = reason or message


class RawPreservationError(RuntimeError):
    pass


ExecutionMode = Literal["live"]
RunStatus = Literal["complete", "needs_work", "failed", "aborted"]

RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
REQUIRED_JUDGMENT_FIELDS = [
    "case_id",
    "decision",
    "violation_probability",
    "cited_contract_phrase",
    "citation_verification_method",
    "reason_codes",
]


class V10LiveRunScope(BaseModel):
    default_case_limit: int
    allow_full_300: bool
    full_300_requires_explicit_flag: bool


class V10GuardedLivePilotConfig(BaseModel):
    schema_version: str
    live_runner_enabled: bool
    execution_mode: ExecutionMode
    level_5_allowed: bool
    default_plan_path: str
    live_design_config_path: str
    evidence_assessment_config_path: str
    normalization_config_path: str
    benchmark_config_path: str
    diagnostics_config_path: str
    reportability_config_path: str
    integrity_config_path: str
    cases_path: str = "benchmarks/v10_calibrated/v10_cases.jsonl"
    provider_runs_live_root: str
    required_live_flag: bool
    required_authorization_env_var: str
    required_authorization_env_value: str
    raw_preservation_required_before_parsing: bool
    adapter_injection_required: bool
    secrets_provider_injection_required: bool
    retry_policy_source: str
    failure_budget_source: str
    run_scope: V10LiveRunScope
    notes: str = ""


class V10LivePilotInput(BaseModel):
    provider: str
    model: str
    run_id: str
    plan_path: str
    output_root: str
    live_flag: bool
    case_limit: int | None = None
    allow_full_300: bool = False
    notes: str | None = None


class V10LiveCaseResult(BaseModel):
    case_id: str
    attempted: bool
    succeeded: bool
    failed: bool
    retry_count: int
    failure_reason: str | None = None
    raw_output_path: str | None = None
    raw_output_hash: str | None = None
    response_hash: str | None = None
    latency_ms: float | None = None
    token_counts: dict[str, int] | None = None
    cost_estimate: float | None = None
    receipt_hash: str | None = None


class V10LivePipelineResult(BaseModel):
    parsed_raw_judgment_count: int = 0
    normalization_status: str | None = None
    benchmark_status: str | None = None
    diagnostics_status: str | None = None
    mechanical_reportability_passed: bool | None = None
    integrity_passed: bool | None = None
    score_collapse_detected: bool | None = None
    paths: dict[str, str] = Field(default_factory=dict)


class V10LiveEvidenceResult(BaseModel):
    assessment: V10PilotEvidenceAssessment
    receipt_chain_summary: V10ReceiptChainSummary
    paths: dict[str, str]


class V10LivePilotSummary(BaseModel):
    schema_version: str = "v10_guarded_live_one_provider_pilot_summary_v1"
    run_id: str
    execution_mode: ExecutionMode = "live"
    provider: str
    model: str
    case_count: int
    attempted: int
    succeeded: int
    failed: int
    aborted: bool
    failure_rate: float
    failure_budget: float
    raw_output_preserved: bool
    raw_output_hash_available_count: int
    parsed_raw_judgment_count: int
    normalization_status: str | None
    benchmark_status: str | None
    diagnostics_status: str | None
    mechanical_reportability_passed: bool | None
    evidence_assessment_status: str
    final_evidence_level: int
    level_5_allowed: bool = False
    receipt_count: int
    invalid_receipt_count: int
    receipt_chain_complete: bool
    integrity_passed: bool | None
    score_collapse_detected: bool | None
    provider_model_allowed: bool
    manifest_path: str
    pilot_report_path: str
    manifest_hash: str
    status: RunStatus
    blocking_issues: list[str] = Field(default_factory=list)
    non_blocking_warnings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

    def to_markdown(self) -> str:
        sections = [
            "# HELIX v10.15C Guarded Live One-Provider Pilot Report",
            "",
            "## Executive Summary",
            "",
            f"- run_id: `{self.run_id}`",
            f"- status: `{self.status}`",
            f"- final_evidence_level: `{self.final_evidence_level}`",
            f"- aborted: `{str(self.aborted).lower()}`",
            f"- failure_rate: `{self.failure_rate:.6f}`",
            f"- receipt_count: `{self.receipt_count}`",
            f"- invalid_receipt_count: `{self.invalid_receipt_count}`",
            f"- manifest_hash: `{self.manifest_hash}`",
            "",
            "## Execution Authorization",
            "",
            "- Live execution required an explicit live flag.",
            "- Live authorization was supplied by an injected SecretsProvider.",
            "- API key material was not written to the manifest or report.",
            "- The runner did not read environment variables directly.",
            "",
            "## Provider and Model",
            "",
            f"- provider: `{self.provider}`",
            f"- model: `{self.model}`",
            f"- provider_model_allowed: `{str(self.provider_model_allowed).lower()}`",
            "",
            "## Case Set",
            "",
            f"- case_count: `{self.case_count}`",
            f"- attempted: `{self.attempted}`",
            f"- succeeded: `{self.succeeded}`",
            f"- failed: `{self.failed}`",
            "",
            "## Raw Output Preservation",
            "",
            f"- raw_output_preserved: `{str(self.raw_output_preserved).lower()}`",
            f"- raw_output_hash_available_count: `{self.raw_output_hash_available_count}`",
            "- Raw output is preserved before parsing.",
            "",
            "## Retry and Failure Budget",
            "",
            f"- failure_budget: `{self.failure_budget:.6f}`",
            f"- failure_rate: `{self.failure_rate:.6f}`",
            "",
            "## Parsed Judgments",
            "",
            f"- parsed_raw_judgment_count: `{self.parsed_raw_judgment_count}`",
            "",
            "## Normalization",
            "",
            f"- normalization_status: `{self.normalization_status}`",
            "",
            "## Benchmark Results",
            "",
            f"- benchmark_status: `{self.benchmark_status}`",
            "",
            "## Diagnostics and Reportability",
            "",
            f"- diagnostics_status: `{self.diagnostics_status}`",
            f"- mechanical_reportability_passed: `{self.mechanical_reportability_passed}`",
            f"- integrity_passed: `{self.integrity_passed}`",
            f"- score_collapse_detected: `{self.score_collapse_detected}`",
            "",
            "## Receipt Chain Integrity",
            "",
            f"- receipt_chain_complete: `{str(self.receipt_chain_complete).lower()}`",
            f"- invalid_receipt_count: `{self.invalid_receipt_count}`",
            "",
            "## Evidence Assessment",
            "",
            f"- evidence_assessment_status: `{self.evidence_assessment_status}`",
            "",
            "## Final Evidence Level",
            "",
            f"- final_evidence_level: `{self.final_evidence_level}`",
            "- Level 5 false.",
            "",
            "## Blocking Issues",
            "",
        ]
        sections.extend(f"- `{issue}`" for issue in self.blocking_issues) if self.blocking_issues else sections.append("- None.")
        sections.extend(["", "## Non-Blocking Warnings", ""])
        sections.extend(f"- `{warning}`" for warning in self.non_blocking_warnings) if self.non_blocking_warnings else sections.append("- None.")
        sections.extend(
            [
                "",
                "## What This Supports",
                "",
                "- This supports guarded one-provider live execution through injected adapter and secrets interfaces.",
                "- This supports raw-output preservation before parsing and hash-linked downstream evidence artifacts.",
                "- This supports routing live pilot outputs through the existing v10 evidence pipeline.",
                "",
                "## What This Does Not Prove",
                "",
                "- One provider does not prove cross-provider consistency.",
                "- One live pilot does not prove production readiness.",
                "- This does not claim Level 5 evidence.",
                "- This does not prove three-provider consistency.",
                "- Three-agent consistency remains future v10.16/v10.17 work.",
                "- Passing this runner does not prove correctness of one provider.",
                "",
                "## Limitations",
                "",
            ]
        )
        sections.extend(f"- {item}" for item in self.limitations)
        sections.extend(
            [
                "",
                "## Next Steps",
                "",
                "- Add real provider adapters in a separate explicit patch.",
                "- Run a manually authorized pilot and preserve raw provider outputs.",
                "- Add cross-provider replay only after independent provider outputs exist.",
            ]
        )
        return "\n".join(sections)


def load_v10_guarded_live_pilot_config(path: str | Path) -> V10GuardedLivePilotConfig:
    return V10GuardedLivePilotConfig.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def validate_live_pilot_input(
    live_input: V10LivePilotInput,
    config: V10GuardedLivePilotConfig,
    live_design_config: V10LiveRunnerDesignConfig,
) -> list[str]:
    issues: list[str] = []
    if not config.live_runner_enabled:
        issues.append("live_runner_not_enabled")
    if config.execution_mode != "live":
        issues.append("config_execution_mode_not_live")
    if config.level_5_allowed:
        issues.append("level_5_allowed")
    if config.required_live_flag and not live_input.live_flag:
        issues.append("missing_live_flag")
    if not _run_id_is_safe(live_input.run_id):
        issues.append("invalid_run_id")
    provider_result = validate_provider_model_allowed(
        live_design_config,
        live_input.provider,
        live_input.model,
    )
    if not provider_result.valid:
        issues.append("provider_model_not_allowed")
        issues.extend(f"provider_model:{issue}" for issue in provider_result.issues)
    if not Path(live_input.plan_path).is_file():
        issues.append("missing_plan_path")
    if live_input.case_limit is not None and live_input.case_limit <= 0:
        issues.append("invalid_case_limit")
    try:
        plan = load_provider_run_plan(live_input.plan_path)
    except FileNotFoundError:
        plan = None
    if plan is not None:
        limit = live_input.case_limit or config.run_scope.default_case_limit
        if limit > plan.case_count:
            issues.append("case_limit_exceeds_plan_case_count")
        if limit > config.run_scope.default_case_limit and not live_input.allow_full_300:
            issues.append("full_300_requires_explicit_flag")
        if limit >= 300 and not live_input.allow_full_300:
            issues.append("full_300_requires_explicit_flag")
        if live_input.allow_full_300 and not config.run_scope.allow_full_300 and limit >= 300:
            issues.append("full_300_not_allowed_by_config")
    if _run_id_is_safe(live_input.run_id):
        out_dir = build_live_output_dir(live_input, config)
        path_result = validate_execution_mode_path(live_design_config, "live", out_dir)
        if not path_result.valid:
            issues.extend(path_result.issues)
        expected = Path(live_input.output_root) / live_input.provider / live_input.model / live_input.run_id
        if out_dir != expected:
            issues.append("live_output_path_not_provider_model_run_id")
    return sorted(set(issues))


def authorize_live_execution(
    live_input: V10LivePilotInput,
    secrets_provider: SecretsProvider,
) -> None:
    if not live_input.live_flag:
        raise LiveExecutionNotAuthorizedError("Live execution requires explicit live flag.")
    if not secrets_provider.is_live_authorized():
        raise LiveExecutionNotAuthorizedError("Live execution was not authorized by SecretsProvider.")
    api_key = secrets_provider.get_api_key(live_input.provider)
    if not isinstance(api_key, str) or not api_key:
        raise LiveExecutionNotAuthorizedError("SecretsProvider did not return a non-empty API key.")


def build_live_output_dir(
    live_input: V10LivePilotInput,
    config: V10GuardedLivePilotConfig,
) -> Path:
    if not _run_id_is_safe(live_input.run_id):
        raise LiveOutputPathError("Invalid run_id for live output path.")
    root = Path(live_input.output_root or config.provider_runs_live_root)
    path = root / live_input.provider / live_input.model / live_input.run_id
    if not _path_is_relative_to(path.resolve(), root.resolve()):
        raise LiveOutputPathError("Live output path escaped live root.")
    return path


def render_case_prompt(
    case: V10Case,
    prompt_mode: str,
    prompt_artifacts: dict[str, Any] | None = None,
) -> tuple[str, str]:
    payload = {
        "prompt_mode": prompt_mode,
        "case_id": case.case_id,
        "generic_context": case.generic_context,
        "proposed_tool": case.proposed_tool,
        "proposed_action": case.proposed_action,
        "proposed_arguments": case.proposed_arguments,
        "active_contract_rule_id": case.active_contract_rule_id,
        "active_contract_rule_summary": case.active_contract_rule_summary,
        "candidate_contract_rules": case.candidate_contract_rules,
        "instructions": [
            "Output one JSON judgment object only.",
            "Use the v10 provider judgment schema.",
            "If high risk, cite an exact substring of the active contract rule.",
        ],
    }
    prompt = json.dumps(payload, indent=2, sort_keys=True)
    return prompt, hash_text(prompt)


def execute_live_case(
    case: V10Case,
    adapter: ProviderAdapter,
    live_input: V10LivePilotInput,
    config: V10GuardedLivePilotConfig,
    live_design_config: V10LiveRunnerDesignConfig,
    out_dir: str | Path,
) -> tuple[V10LiveCaseResult, dict[str, Any] | None]:
    prompt, prompt_hash = render_case_prompt(case, "contract", None)
    started = time.perf_counter()
    result = adapter.execute(
        prompt,
        "live",
        raw_preserve=True,
        request_metadata={
            "case_id": case.case_id,
            "provider": live_input.provider,
            "model": live_input.model,
            "prompt_hash": prompt_hash,
            "execution_mode": "live",
        },
    )
    latency_ms = result.latency_ms
    if latency_ms is None:
        latency_ms = (time.perf_counter() - started) * 1000.0
    raw_json_path, raw_text_path, raw_hash = _preserve_provider_result(case, result, out_dir)
    try:
        judgment = parse_provider_result_to_judgment(result, expected_case_id=case.case_id)
    except ValueError as exc:
        return (
            V10LiveCaseResult(
                case_id=case.case_id,
                attempted=True,
                succeeded=False,
                failed=True,
                retry_count=0,
                failure_reason=f"parse_failed:{exc}",
                raw_output_path=str(raw_json_path),
                raw_output_hash=raw_hash,
                response_hash=result.response_hash or raw_hash,
                latency_ms=latency_ms,
                token_counts=result.token_counts,
                cost_estimate=result.cost_estimate,
            ),
            None,
        )
    return (
        V10LiveCaseResult(
            case_id=case.case_id,
            attempted=True,
            succeeded=True,
            failed=False,
            retry_count=0,
            raw_output_path=str(raw_json_path),
            raw_output_hash=raw_hash,
            response_hash=result.response_hash or raw_hash,
            latency_ms=latency_ms,
            token_counts=result.token_counts,
            cost_estimate=result.cost_estimate,
        ),
        judgment,
    )


def run_with_retry_policy(
    case: V10Case,
    adapter: ProviderAdapter,
    live_input: V10LivePilotInput,
    config: V10GuardedLivePilotConfig,
    live_design_config: V10LiveRunnerDesignConfig,
    out_dir: str | Path,
    *,
    sleep_fn: Callable[[float], None] | None = None,
    random_fn: Callable[[], float] | None = None,
) -> tuple[V10LiveCaseResult, dict[str, Any] | None, list[str]]:
    sleep = sleep_fn or time.sleep
    random_value = random_fn or random.random
    retry_policy = live_design_config.retry_policy
    retry_reasons: list[str] = []
    attempts = 0
    while True:
        try:
            result, judgment = execute_live_case(
                case,
                adapter,
                live_input,
                config,
                live_design_config,
                out_dir,
            )
            return (
                result.model_copy(update={"retry_count": attempts}),
                judgment,
                retry_reasons,
            )
        except LiveProviderCallError as exc:
            retryable = _is_retryable_provider_error(exc, retry_policy)
            if retryable and attempts < retry_policy.max_retries:
                attempts += 1
                retry_reasons.append(exc.reason)
                delay = retry_policy.base_delay_seconds
                if retry_policy.jitter == "full":
                    delay *= random_value()
                elif retry_policy.jitter == "equal":
                    delay = (delay / 2.0) + ((delay / 2.0) * random_value())
                sleep(delay)
                continue
            return (
                V10LiveCaseResult(
                    case_id=case.case_id,
                    attempted=True,
                    succeeded=False,
                    failed=True,
                    retry_count=attempts,
                    failure_reason=exc.reason,
                ),
                None,
                retry_reasons,
            )


def parse_provider_result_to_judgment(
    result: ProviderResult,
    *,
    expected_case_id: str | None = None,
) -> dict[str, Any]:
    payload = result.raw_response
    if isinstance(payload, str):
        payload = json.loads(payload)
    if isinstance(payload, dict) and "judgment" in payload:
        payload = payload["judgment"]
    elif isinstance(payload, dict) and "judgments" in payload:
        judgments = payload.get("judgments")
        if not isinstance(judgments, list) or len(judgments) != 1:
            raise ValueError("expected_single_judgment")
        payload = judgments[0]
    if not isinstance(payload, dict):
        raise ValueError("judgment_not_object")
    missing = [field for field in REQUIRED_JUDGMENT_FIELDS if field not in payload]
    if missing:
        raise ValueError("missing_judgment_fields:" + ",".join(missing))
    if expected_case_id and payload.get("case_id") != expected_case_id:
        raise ValueError("case_id_mismatch")
    return dict(payload)


def run_guarded_live_pilot(
    live_input: V10LivePilotInput,
    adapter: ProviderAdapter,
    secrets_provider: SecretsProvider,
    config: V10GuardedLivePilotConfig,
    live_design_config: V10LiveRunnerDesignConfig,
    *,
    sleep_fn: Callable[[float], None] | None = None,
    random_fn: Callable[[], float] | None = None,
    generated_at: str | None = None,
) -> tuple[V10LivePilotSummary, dict[str, Path]]:
    validation_issues = validate_live_pilot_input(live_input, config, live_design_config)
    if validation_issues:
        if any(issue.startswith("provider_model") for issue in validation_issues):
            raise ProviderModelNotAllowedError(", ".join(validation_issues))
        if any("path" in issue for issue in validation_issues):
            raise LiveOutputPathError(", ".join(validation_issues))
        raise LiveExecutionNotAuthorizedError(", ".join(validation_issues))
    authorize_live_execution(live_input, secrets_provider)
    out_dir = build_live_output_dir(live_input, config)
    out_dir.mkdir(parents=True, exist_ok=True)
    plan = load_provider_run_plan(live_input.plan_path)
    cases = _select_cases(plan, config, live_input)
    parsed_judgments: list[dict[str, Any]] = []
    case_results: list[V10LiveCaseResult] = []
    retry_events: dict[str, list[str]] = {}
    aborted = False
    failure_budget = live_design_config.retry_policy.failure_budget_per_run

    for case in cases:
        result, judgment, retries = run_with_retry_policy(
            case,
            adapter,
            live_input,
            config,
            live_design_config,
            out_dir,
            sleep_fn=sleep_fn,
            random_fn=random_fn,
        )
        case_results.append(result)
        retry_events[case.case_id] = retries
        if judgment is not None:
            parsed_judgments.append(judgment)
        if _failure_rate(case_results) > failure_budget:
            aborted = True
            break

    parsed_path = _write_jsonl(out_dir / "parsed_raw_judgments.jsonl", parsed_judgments)
    case_results_path = _write_jsonl_models(out_dir / "live_case_results.jsonl", case_results)
    retry_report_path = _write_retry_report(
        out_dir / "live_retry_report.json",
        case_results,
        retry_events,
        failure_budget=failure_budget,
    )
    pipeline = V10LivePipelineResult(parsed_raw_judgment_count=len(parsed_judgments))
    evidence: V10LiveEvidenceResult | None = None
    blocking_issues: list[str] = []
    if aborted:
        blocking_issues.append("failure_budget_exceeded")
    elif len(parsed_judgments) != len(cases):
        blocking_issues.append("parsed_raw_judgment_count_mismatch")
    else:
        filtered_cases_path = _write_cases_jsonl(out_dir / "filtered_live_cases.jsonl", cases)
        pipeline = run_live_pipeline(
            cases=cases,
            cases_path=filtered_cases_path,
            parsed_raw_judgments_path=parsed_path,
            provider=live_input.provider,
            model=live_input.model,
            config=config,
            out_dir=out_dir,
            generated_at=generated_at,
        )
        evidence = run_live_evidence_assessment(
            cases=cases,
            provider=live_input.provider,
            model=live_input.model,
            run_id=live_input.run_id,
            out_dir=out_dir,
            normalized_judgments_path=Path(pipeline.paths["normalized_judgments"]),
            raw_hashes_by_case_id={
                item.case_id: item.raw_output_hash
                for item in case_results
                if item.raw_output_hash
            },
            config=config,
            live_design_config=live_design_config,
            pipeline=pipeline,
            generated_at=generated_at,
        )
        blocking_issues.extend(evidence.assessment.blocking_issues)

    summary = build_live_pilot_summary(
        live_input=live_input,
        case_count=len(cases),
        case_results=case_results,
        aborted=aborted,
        failure_budget=failure_budget,
        pipeline=pipeline,
        evidence=evidence,
        blocking_issues=blocking_issues,
    )
    paths = write_live_pilot_outputs(
        summary,
        out_dir=out_dir,
        config=config,
        live_input=live_input,
        case_results_path=case_results_path,
        retry_report_path=retry_report_path,
        parsed_raw_judgments_path=parsed_path,
        pipeline=pipeline,
        evidence=evidence,
        generated_at=generated_at,
    )
    manifest_hash = json.loads(paths["manifest"].read_text(encoding="utf-8"))["manifest_hash"]
    final_summary = summary.model_copy(
        update={
            "manifest_path": str(paths["manifest"]),
            "pilot_report_path": str(paths["report"]),
            "manifest_hash": manifest_hash,
        }
    )
    paths["summary"].write_text(
        json.dumps(final_summary.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return final_summary, paths


def run_live_pipeline(
    *,
    cases: list[V10Case],
    cases_path: Path,
    parsed_raw_judgments_path: Path,
    provider: str,
    model: str,
    config: V10GuardedLivePilotConfig,
    out_dir: Path,
    generated_at: str | None = None,
) -> V10LivePipelineResult:
    normalization_config = load_v10_normalization_config(config.normalization_config_path)
    normalized, normalization_summary = normalize_v10_judgments(
        load_raw_judgments(parsed_raw_judgments_path),
        cases,
        normalization_config,
        provider=provider,
        model=model,
    )
    normalization_paths_tuple = write_v10_normalization_outputs(
        normalized_judgments=normalized,
        summary=normalization_summary,
        config_path=config.normalization_config_path,
        input_cases_path=cases_path,
        raw_judgments_path=parsed_raw_judgments_path,
        provider=provider,
        model=model,
        out_dir=out_dir / "normalized",
        generated_at=generated_at,
    )
    normalization_paths = {
        "normalized": normalization_paths_tuple[0],
        "invalid": normalization_paths_tuple[1],
        "summary": normalization_paths_tuple[2],
        "manifest": normalization_paths_tuple[3],
        "report": normalization_paths_tuple[4],
    }
    benchmark_config = load_v10_benchmark_config(config.benchmark_config_path)
    receipts = build_v10_benchmark_receipts(
        cases,
        normalized,
        benchmark_config,
        config_hash=hash_file(config.benchmark_config_path),
        normalization_manifest_hash=hash_file(normalization_paths["manifest"]),
    )
    receipt_issues = validate_v10_benchmark_receipts(receipts, expected_count=len(cases))
    benchmark_summary = compute_v10_benchmark_metrics(
        cases,
        normalized,
        benchmark_config,
        normalization_summary=normalization_summary,
        receipt_count=len(receipts),
        receipt_validation_issue_count=len(receipt_issues),
    )
    benchmark_paths_tuple = write_v10_benchmark_outputs(
        summary=benchmark_summary,
        receipts=receipts,
        cases=cases,
        normalized_judgments=normalized,
        config_path=config.benchmark_config_path,
        input_cases_path=cases_path,
        normalized_judgments_path=normalization_paths["normalized"],
        normalization_summary_path=normalization_paths["summary"],
        normalization_manifest_path=normalization_paths["manifest"],
        out_dir=out_dir / "benchmark",
        generated_at=generated_at,
    )
    benchmark_paths = {
        "receipts": benchmark_paths_tuple[0],
        "summary": benchmark_paths_tuple[1],
        "manifest": benchmark_paths_tuple[2],
        "report": benchmark_paths_tuple[3],
        "failure_cases": benchmark_paths_tuple[4],
    }
    diagnostics_summary, reportability_report, diagnostics_paths = _run_live_diagnostics(
        cases_path=cases_path,
        receipts=receipts,
        benchmark_summary=benchmark_summary,
        benchmark_paths=benchmark_paths,
        config=config,
        out_dir=out_dir / "diagnostics",
        reportability_out_dir=out_dir / "reportability",
    )
    return V10LivePipelineResult(
        parsed_raw_judgment_count=normalization_summary.raw_count,
        normalization_status=normalization_summary.status,
        benchmark_status=benchmark_summary.status,
        diagnostics_status=diagnostics_summary.diagnostics_status,
        mechanical_reportability_passed=reportability_report.reportability_passed,
        integrity_passed=diagnostics_summary.integrity_passed,
        score_collapse_detected=normalization_summary.score_collapse_detected,
        paths={
            "normalized_judgments": str(normalization_paths["normalized"]),
            "normalization_summary": str(normalization_paths["summary"]),
            "normalization_manifest": str(normalization_paths["manifest"]),
            "benchmark_summary": str(benchmark_paths["summary"]),
            "benchmark_receipts": str(benchmark_paths["receipts"]),
            "benchmark_manifest": str(benchmark_paths["manifest"]),
            "diagnostics_summary": str(diagnostics_paths["summary"]),
            "diagnostics_manifest": str(diagnostics_paths["manifest"]),
            "reportability_report": str(diagnostics_paths["reportability_json"]),
        },
    )


def run_live_evidence_assessment(
    *,
    cases: list[V10Case],
    provider: str,
    model: str,
    run_id: str,
    out_dir: Path,
    normalized_judgments_path: Path,
    raw_hashes_by_case_id: dict[str, str],
    config: V10GuardedLivePilotConfig,
    live_design_config: V10LiveRunnerDesignConfig,
    pipeline: V10LivePipelineResult,
    generated_at: str | None = None,
) -> V10LiveEvidenceResult:
    assessment_config = load_v10_pilot_evidence_assessment_config(
        config.evidence_assessment_config_path
    )
    normalized = [
        V10NormalizedJudgment.model_validate_json(line)
        for line in normalized_judgments_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    receipt_chain_config = V10ReceiptChainConfig.model_validate(
        assessment_config.receipt_chain.model_dump(mode="json")
    )
    records, receipt_chain_summary = build_receipt_chain(
        cases,
        normalized,
        execution_mode="live",
        provider=provider,
        model=model,
        raw_hashes_by_case_id=raw_hashes_by_case_id,
        config=receipt_chain_config,
        run_id=run_id,
    )
    evidence_dir = out_dir / "pilot_evidence"
    receipt_paths = write_receipt_chain_outputs(records, receipt_chain_summary, evidence_dir)
    integrity_summary = {
        "integrity_passed": pipeline.integrity_passed,
        "score_collapse_detected": pipeline.score_collapse_detected,
        "generator_independence": True,
    }
    reportability_summary = _first_json([Path(pipeline.paths["reportability_report"])])
    assessment = assess_v10_pilot_evidence(
        run_id=run_id,
        execution_mode="live",
        provider=provider,
        model=model,
        case_count=len(cases),
        receipt_chain_summary=receipt_chain_summary,
        normalization_status=pipeline.normalization_status,
        benchmark_status=pipeline.benchmark_status,
        diagnostics_status=pipeline.diagnostics_status,
        integrity_summary=integrity_summary,
        reportability_summary=reportability_summary,
        live_design_config=live_design_config,
        assessment_config=assessment_config,
    )
    assessment_paths = write_v10_pilot_evidence_assessment(
        assessment,
        evidence_dir,
        config=assessment_config,
        receipt_chain_summary=receipt_chain_summary,
        generated_at=generated_at,
    )
    paths = {
        **{key: str(value) for key, value in receipt_paths.items()},
        **{key: str(value) for key, value in assessment_paths.items()},
    }
    return V10LiveEvidenceResult(
        assessment=assessment,
        receipt_chain_summary=receipt_chain_summary,
        paths=paths,
    )


def build_live_pilot_summary(
    *,
    live_input: V10LivePilotInput,
    case_count: int,
    case_results: list[V10LiveCaseResult],
    aborted: bool,
    failure_budget: float,
    pipeline: V10LivePipelineResult,
    evidence: V10LiveEvidenceResult | None,
    blocking_issues: list[str],
) -> V10LivePilotSummary:
    attempted = sum(item.attempted for item in case_results)
    succeeded = sum(item.succeeded for item in case_results)
    failed = sum(item.failed for item in case_results)
    receipt_summary = evidence.receipt_chain_summary if evidence else None
    assessment = evidence.assessment if evidence else None
    raw_hash_count = sum(bool(item.raw_output_hash) for item in case_results)
    raw_preserved = raw_hash_count == succeeded and all(
        bool(item.raw_output_path) for item in case_results if item.succeeded
    )
    status: RunStatus
    if aborted:
        status = "aborted"
    elif assessment is None or blocking_issues:
        status = "needs_work"
    else:
        status = "complete"
    final_level = assessment.final_evidence_level if assessment else min(3, 0)
    warnings = assessment.non_blocking_warnings if assessment else []
    return V10LivePilotSummary(
        run_id=live_input.run_id,
        provider=live_input.provider,
        model=live_input.model,
        case_count=case_count,
        attempted=attempted,
        succeeded=succeeded,
        failed=failed,
        aborted=aborted,
        failure_rate=_safe_divide(failed, attempted),
        failure_budget=failure_budget,
        raw_output_preserved=raw_preserved,
        raw_output_hash_available_count=raw_hash_count,
        parsed_raw_judgment_count=pipeline.parsed_raw_judgment_count,
        normalization_status=pipeline.normalization_status,
        benchmark_status=pipeline.benchmark_status,
        diagnostics_status=pipeline.diagnostics_status,
        mechanical_reportability_passed=pipeline.mechanical_reportability_passed,
        evidence_assessment_status="complete" if assessment else "not_run",
        final_evidence_level=final_level,
        level_5_allowed=False,
        receipt_count=receipt_summary.receipt_count if receipt_summary else 0,
        invalid_receipt_count=receipt_summary.invalid_receipt_count if receipt_summary else 0,
        receipt_chain_complete=receipt_summary.receipt_chain_complete if receipt_summary else False,
        integrity_passed=pipeline.integrity_passed,
        score_collapse_detected=pipeline.score_collapse_detected,
        provider_model_allowed=True,
        manifest_path="",
        pilot_report_path="",
        manifest_hash="",
        status=status,
        blocking_issues=sorted(set(blocking_issues)),
        non_blocking_warnings=sorted(set(warnings)),
        limitations=[
            "Guarded one-provider live pilot only.",
            "Provider/model names are metadata, not behavior guarantees.",
            "One provider does not prove cross-provider consistency.",
            "One live pilot does not prove production readiness.",
            "Level 5 is false.",
            "Three-agent consistency remains future work.",
        ],
    )


def write_live_pilot_outputs(
    summary: V10LivePilotSummary,
    *,
    out_dir: Path,
    config: V10GuardedLivePilotConfig,
    live_input: V10LivePilotInput,
    case_results_path: Path,
    retry_report_path: Path,
    parsed_raw_judgments_path: Path,
    pipeline: V10LivePipelineResult,
    evidence: V10LiveEvidenceResult | None,
    generated_at: str | None = None,
) -> dict[str, Path]:
    manifest_path = out_dir / "pilot_manifest.json"
    summary_path = out_dir / "pilot_summary.json"
    report_path = out_dir / "pilot_report.md"
    manifest_payload = {
        "schema_version": "v10_guarded_live_one_provider_pilot_manifest_v1",
        "run_id": summary.run_id,
        "execution_mode": "live",
        "provider": summary.provider,
        "model": summary.model,
        "case_count": summary.case_count,
        "attempted": summary.attempted,
        "succeeded": summary.succeeded,
        "failed": summary.failed,
        "aborted": summary.aborted,
        "failure_rate": summary.failure_rate,
        "failure_budget": summary.failure_budget,
        "raw_output_preserved": summary.raw_output_preserved,
        "raw_output_hash_available_count": summary.raw_output_hash_available_count,
        "parsed_raw_judgment_count": summary.parsed_raw_judgment_count,
        "normalization_status": summary.normalization_status,
        "benchmark_status": summary.benchmark_status,
        "diagnostics_status": summary.diagnostics_status,
        "mechanical_reportability_passed": summary.mechanical_reportability_passed,
        "evidence_assessment_completed": evidence is not None,
        "final_evidence_level": summary.final_evidence_level,
        "level_5_allowed": False,
        "provider_model_allowed": summary.provider_model_allowed,
        "api_key_source": "secrets_provider",
        "direct_env_read": false_literal(),
        "provider_sdk_client_constructed_by_runner": false_literal(),
        "receipt_count": summary.receipt_count,
        "invalid_receipt_count": summary.invalid_receipt_count,
        "receipt_chain_complete": summary.receipt_chain_complete,
        "integrity_passed": summary.integrity_passed,
        "score_collapse_detected": summary.score_collapse_detected,
        "blocking_issues": summary.blocking_issues,
        "non_blocking_warnings": summary.non_blocking_warnings,
        "case_results_path": str(case_results_path),
        "retry_report_path": str(retry_report_path),
        "parsed_raw_judgments_path": str(parsed_raw_judgments_path),
        "pipeline_paths": pipeline.paths,
        "evidence_paths": evidence.paths if evidence else {},
        "config": config.model_dump(mode="json"),
        "input": live_input.model_dump(mode="json"),
        "generated_at": generated_at or _utc_now(),
    }
    manifest = {**manifest_payload, "manifest_hash": stable_json_hash(manifest_payload)}
    final_summary = summary.model_copy(
        update={
            "manifest_path": str(manifest_path),
            "pilot_report_path": str(report_path),
            "manifest_hash": manifest["manifest_hash"],
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary_path.write_text(
        json.dumps(final_summary.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(final_summary.to_markdown() + "\n", encoding="utf-8")
    return {"manifest": manifest_path, "summary": summary_path, "report": report_path}


def false_literal() -> bool:
    return False


def _run_live_diagnostics(
    *,
    cases_path: str | Path,
    receipts: list[Any],
    benchmark_summary: Any,
    benchmark_paths: dict[str, Path],
    config: V10GuardedLivePilotConfig,
    out_dir: str | Path,
    reportability_out_dir: str | Path,
) -> tuple[Any, Any, dict[str, Path]]:
    diagnostics_config = load_v10_diagnostics_config(config.diagnostics_config_path)
    ci_metrics = bootstrap_v10_metric_cis(receipts, benchmark_summary, diagnostics_config)
    selectivity_baselines = compute_v10_selectivity_baselines(receipts, diagnostics_config)
    bootstrap_payload = {
        "schema_version": "v10_bootstrap_ci_v1",
        "confidence_level": diagnostics_config.confidence_level,
        "resamples": diagnostics_config.bootstrap_resamples,
        "metrics": {
            name: metric.model_dump(mode="json")
            for name, metric in sorted(ci_metrics.items())
        },
    }
    integrity_report, integrity_json_path, _, integrity_warnings = run_v10_integrity_diagnostic(
        cases_path=cases_path,
        receipts=receipts,
        integrity_config_path=config.integrity_config_path,
        out_dir=out_dir,
    )
    reportability_report, reportability_json_path, reportability_md_path = (
        run_v10_reportability_diagnostic(
            integrity_report=integrity_report,
            benchmark_summary=benchmark_summary,
            bootstrap_ci=bootstrap_payload,
            reportability_config_path=config.reportability_config_path,
            out_dir=reportability_out_dir,
            receipts=receipts,
            selectivity_baselines=selectivity_baselines,
        )
    )
    diagnostics_summary = build_v10_diagnostics_summary(
        benchmark_run_path=benchmark_paths["summary"].parent,
        bootstrap_ci_path=Path(out_dir) / "v10_bootstrap_ci.json",
        integrity_report_path=integrity_json_path or Path(out_dir) / "v10_integrity_report.json",
        reportability_report_path=reportability_json_path,
        fixture_mode=False,
        benchmark_summary=benchmark_summary,
        config=diagnostics_config,
        ci_metrics=ci_metrics,
        selectivity_baselines=selectivity_baselines,
        integrity_report=integrity_report,
        reportability_report=reportability_report,
        warnings=integrity_warnings,
    )
    diagnostic_paths = write_v10_diagnostics_outputs(
        benchmark_run_dir=out_dir,
        diagnostics_config_path=config.diagnostics_config_path,
        benchmark_summary_path=benchmark_paths["summary"],
        benchmark_receipts_path=benchmark_paths["receipts"],
        benchmark_manifest_path=benchmark_paths["manifest"],
        summary=diagnostics_summary,
        bootstrap_ci=bootstrap_payload,
    )
    return (
        diagnostics_summary,
        reportability_report,
        {
            "bootstrap_ci": diagnostic_paths[0],
            "summary": diagnostic_paths[1],
            "manifest": diagnostic_paths[2],
            "report": diagnostic_paths[3],
            "reportability_json": reportability_json_path,
            "reportability_md": reportability_md_path,
        },
    )


def _preserve_provider_result(
    case: V10Case,
    result: ProviderResult,
    out_dir: str | Path,
) -> tuple[Path, Path | None, str]:
    raw_dir = Path(out_dir) / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    case_part = _safe_file_part(case.case_id)
    raw_json_path = raw_dir / f"{case_part}_raw.json"
    raw_text_path = raw_dir / f"{case_part}_raw.txt"
    try:
        raw_json_path.write_bytes(_raw_response_bytes(result.raw_response))
        if result.raw_text is not None:
            raw_text_path.write_text(result.raw_text, encoding="utf-8")
        return raw_json_path, raw_text_path if result.raw_text is not None else None, hash_file(raw_json_path)
    except OSError as exc:
        raise RawPreservationError(str(exc)) from exc


def _raw_response_bytes(raw_response: Any) -> bytes:
    if isinstance(raw_response, str):
        return raw_response.encode("utf-8")
    return (json.dumps(raw_response, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _is_retryable_provider_error(exc: LiveProviderCallError, retry_policy: Any) -> bool:
    if exc.retryable is not None:
        return exc.retryable
    if exc.status_code is None:
        return False
    if exc.status_code in set(retry_policy.non_retryable_status_codes):
        return False
    return exc.status_code in set(retry_policy.retryable_status_codes)


def _select_cases(
    plan: V10ProviderRunPlan,
    config: V10GuardedLivePilotConfig,
    live_input: V10LivePilotInput,
) -> list[V10Case]:
    all_cases = _load_v10_cases(config.cases_path)
    cases_by_id = {case.case_id: case for case in all_cases}
    limit = live_input.case_limit or config.run_scope.default_case_limit
    case_ids = plan.sampled_case_ids[:limit]
    return [cases_by_id[case_id] for case_id in case_ids if case_id in cases_by_id]


def _write_cases_jsonl(path: Path, cases: list[V10Case]) -> Path:
    path.write_text(
        "\n".join(json.dumps(case.model_dump(mode="json"), sort_keys=True) for case in cases)
        + ("\n" if cases else ""),
        encoding="utf-8",
    )
    return path


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows)
        + ("\n" if rows else ""),
        encoding="utf-8",
    )
    return path


def _write_jsonl_models(path: Path, rows: list[BaseModel]) -> Path:
    path.write_text(
        "\n".join(json.dumps(row.model_dump(mode="json"), sort_keys=True) for row in rows)
        + ("\n" if rows else ""),
        encoding="utf-8",
    )
    return path


def _write_retry_report(
    path: Path,
    case_results: list[V10LiveCaseResult],
    retry_events: dict[str, list[str]],
    *,
    failure_budget: float,
) -> Path:
    payload = {
        "schema_version": "v10_live_retry_report_v1",
        "failure_budget": failure_budget,
        "case_count": len(case_results),
        "attempted": sum(item.attempted for item in case_results),
        "failed": sum(item.failed for item in case_results),
        "retry_counts": {item.case_id: item.retry_count for item in case_results},
        "retry_events": retry_events,
    }
    path.write_text(json.dumps({**payload, "retry_hash": stable_json_hash(payload)}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _load_v10_cases(path: str | Path) -> list[V10Case]:
    target = Path(path)
    return [
        V10Case.model_validate_json(line)
        for line in target.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _first_json(paths: list[Path]) -> dict[str, Any] | None:
    for path in paths:
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return payload
    return None


def _failure_rate(case_results: list[V10LiveCaseResult]) -> float:
    attempted = sum(item.attempted for item in case_results)
    failed = sum(item.failed for item in case_results)
    return _safe_divide(failed, attempted)


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _run_id_is_safe(run_id: str) -> bool:
    return bool(run_id and "/" not in run_id and "\\" not in run_id and ".." not in run_id and RUN_ID_RE.fullmatch(run_id))


def _path_is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _safe_file_part(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", value)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
