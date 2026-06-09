from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, Literal, Mapping, Protocol

from pydantic import BaseModel, Field

from helix.benchmark.benchmark_receipts import hash_text, stable_json_hash


ExecutionMode = Literal["dry_run", "manual_import", "live"]
ProviderExecutionMode = Literal["dry_run", "live"]


REQUIRED_CONSTRAINTS = [
    "explicit_mode_parameter_no_default",
    "execution_method_level_live_guard",
    "secrets_provider_injection",
    "dual_signal_live_authorization",
    "dry_run_live_path_separation",
    "execution_mode_manifest_field",
    "bridge_rejects_ambiguous_execution_mode",
    "allowed_model_list_validation",
    "retry_policy_with_failure_budget",
    "live_execution_blocker_in_tests",
    "no_live_tests_in_default_ci",
    "three_agent_consistency_target_declared",
]


@dataclass(frozen=True)
class ProviderResult:
    provider: str
    model: str
    execution_mode: ProviderExecutionMode
    raw_response: dict[str, Any] | str
    response_timestamp: str
    response_hash: str
    raw_text: str | None = None
    request_id: str | None = None
    latency_ms: float | None = None
    token_counts: dict[str, int] | None = None
    cost_estimate: float | None = None


class ProviderAdapter(Protocol):
    provider_name: str
    supported_models: tuple[str, ...]

    def execute(
        self,
        prompt: str,
        mode: ProviderExecutionMode,
        *,
        raw_preserve: bool = True,
        request_metadata: dict[str, Any] | None = None,
    ) -> ProviderResult:
        ...


class SecretsProvider(Protocol):
    def get_api_key(self, provider: str) -> str:
        ...

    def is_live_authorized(self) -> bool:
        ...


class V10AllowedProvider(BaseModel):
    allowed_models: list[str]
    rate_limit_rpm: int
    max_retries: int


class V10LiveRunnerSecretsPolicy(BaseModel):
    direct_environment_reads_allowed_in_runner: bool
    secrets_provider_required: bool
    dual_signal_live_authorization_required: bool
    required_live_flag: str
    required_authorization_env_var: str
    required_authorization_env_value: str
    api_key_presence_is_authorization: bool


class V10LiveRunnerOutputPathPolicy(BaseModel):
    dry_run_root: str
    manual_import_root: str
    live_root: str
    live_path_template: str
    execution_mode_manifest_field_required: bool
    ambiguous_execution_mode_behavior: str


class V10LiveRunnerRetryPolicy(BaseModel):
    max_retries: int
    base_delay_seconds: float
    jitter: str
    retryable_status_codes: list[int]
    non_retryable_status_codes: list[int]
    failure_budget_per_run: float


class V10LiveRunnerTestPolicy(BaseModel):
    live_execution_blocker_required: bool
    live_tests_directory: str
    live_test_marker: str
    run_live_tests_in_default_ci: bool


class V10ThreeAgentConsistencyTarget(BaseModel):
    enabled_as_future_target: bool
    minimum_independent_agent_systems: int
    majority_vote_truth_claim_allowed: bool
    consistency_receipt_required: bool


class V10LiveRunnerDesignConfig(BaseModel):
    schema_version: str
    design_gate_only: bool
    live_calls_allowed_in_this_version: bool
    provider_sdks_allowed_in_this_version: bool
    api_keys_allowed_in_repo: bool
    execution_modes: list[ExecutionMode]
    mode_parameter_required: bool
    mode_parameter_default_allowed: bool
    secrets_policy: V10LiveRunnerSecretsPolicy
    output_path_policy: V10LiveRunnerOutputPathPolicy
    allowed_providers: dict[str, V10AllowedProvider]
    unknown_model_behavior: str
    retry_policy: V10LiveRunnerRetryPolicy
    test_policy: V10LiveRunnerTestPolicy
    three_agent_consistency_target: V10ThreeAgentConsistencyTarget


class V10DesignValidationResult(BaseModel):
    valid: bool
    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class V10ProviderModelValidationResult(V10DesignValidationResult):
    provider: str
    model: str
    provider_allowed: bool
    model_allowed: bool


class V10ExecutionModePathValidationResult(V10DesignValidationResult):
    execution_mode: ExecutionMode
    output_path: str


class V10LiveRunnerDesignReceipt(BaseModel):
    receipt_id: str
    receipt_type: Literal["live_runner_design_gate"] = "live_runner_design_gate"
    version: str = "v10.14"
    constraints_codified: list[str]
    live_calls_in_this_version: bool
    provider_sdks_used: bool
    secrets_included: bool
    three_agent_consistency_target: dict[str, Any]
    design_gate_hash: str

    def to_markdown(
        self,
        *,
        config: V10LiveRunnerDesignConfig,
        validation_issues: list[str],
    ) -> str:
        lines = [
            "# HELIX v10.14 Live Provider Runner Design Gate Report",
            "",
            "## Executive Summary",
            "",
            f"- receipt_id: `{self.receipt_id}`",
            f"- live_calls_in_this_version: `{str(self.live_calls_in_this_version).lower()}`",
            f"- provider_sdks_used: `{str(self.provider_sdks_used).lower()}`",
            f"- secrets_included: `{str(self.secrets_included).lower()}`",
            f"- design_gate_hash: `{self.design_gate_hash}`",
            "",
            "This is a design gate and receipt layer. It does not execute provider APIs, import provider SDK clients, or collect provider judgments.",
            "",
            "## Threat Model",
            "",
            "- Prevent accidental live calls from tests importing runner code.",
            "- Prevent API-key presence from becoming live authorization.",
            "- Prevent dry-run outputs from being reused as live outputs.",
            "",
            "## Explicit Mode Guard",
            "",
            f"- mode_parameter_required: `{str(config.mode_parameter_required).lower()}`",
            f"- mode_parameter_default_allowed: `{str(config.mode_parameter_default_allowed).lower()}`",
            "- Provider adapter `execute` requires an explicit `mode` argument.",
            "",
            "## Secrets Isolation",
            "",
            f"- secrets_provider_required: `{str(config.secrets_policy.secrets_provider_required).lower()}`",
            f"- dual_signal_live_authorization_required: `{str(config.secrets_policy.dual_signal_live_authorization_required).lower()}`",
            f"- api_key_presence_is_authorization: `{str(config.secrets_policy.api_key_presence_is_authorization).lower()}`",
            "",
            "## Output Path Separation",
            "",
            f"- dry_run_root: `{config.output_path_policy.dry_run_root}`",
            f"- manual_import_root: `{config.output_path_policy.manual_import_root}`",
            f"- live_root: `{config.output_path_policy.live_root}`",
            "",
            "## Provider / Model Allowlist",
            "",
        ]
        for provider, provider_config in sorted(config.allowed_providers.items()):
            lines.append(
                f"- `{provider}` models `{provider_config.allowed_models}` "
                f"rate_limit_rpm `{provider_config.rate_limit_rpm}` max_retries `{provider_config.max_retries}`"
            )
        lines.extend(
            [
                "",
                "## Retry Policy and Failure Budget",
                "",
                f"- max_retries: `{config.retry_policy.max_retries}`",
                f"- base_delay_seconds: `{config.retry_policy.base_delay_seconds}`",
                f"- jitter: `{config.retry_policy.jitter}`",
                f"- failure_budget_per_run: `{config.retry_policy.failure_budget_per_run}`",
                "",
                "## Test Blocker Policy",
                "",
                f"- live_execution_blocker_required: `{str(config.test_policy.live_execution_blocker_required).lower()}`",
                f"- live_tests_directory: `{config.test_policy.live_tests_directory}`",
                f"- run_live_tests_in_default_ci: `{str(config.test_policy.run_live_tests_in_default_ci).lower()}`",
                "",
                "## Three-Agent Consistency Target",
                "",
                f"- enabled_as_future_target: `{str(config.three_agent_consistency_target.enabled_as_future_target).lower()}`",
                f"- minimum_independent_agent_systems: `{config.three_agent_consistency_target.minimum_independent_agent_systems}`",
                f"- majority_vote_truth_claim_allowed: `{str(config.three_agent_consistency_target.majority_vote_truth_claim_allowed).lower()}`",
                "",
                "## Receipt",
                "",
                f"- constraints_codified: `{self.constraints_codified}`",
                f"- validation_issues: `{validation_issues}`",
                "",
                "## What This Supports",
                "",
                "- This supports codifying the live execution boundary before implementation.",
                "- This supports auditable checks for mode, secrets, output paths, allowlists, retries, and test blockers.",
                "",
                "## What This Does Not Yet Prove",
                "",
                "- No live calls were made.",
                "- No provider SDKs were used.",
                "- No secrets were included.",
                "- This is not Level 4 or Level 5 evidence.",
                "- Three-agent consistency target is declared but not executed.",
                "",
                "## Limitations",
                "",
                "- This is design-gate evidence only.",
                "- It does not collect real provider judgments.",
                "- It does not validate provider behavior under network or API failures.",
                "- It does not prove cross-provider consistency.",
            ]
        )
        return "\n".join(lines)


class LiveExecutionBlocker:
    provider_name = "live_execution_blocker"
    supported_models = ("dry-run-blocker",)

    def execute(self, prompt: str, mode: ProviderExecutionMode, **kwargs: Any) -> ProviderResult:
        if mode == "live":
            raise AssertionError("Live execution is blocked in v10.14 design-gate tests.")
        if mode != "dry_run":
            raise ValueError(f"Unsupported execution mode for blocker: {mode}")
        raw_response = {
            "provider": self.provider_name,
            "model": self.supported_models[0],
            "execution_mode": "dry_run",
            "prompt_hash": hash_text(prompt),
            "dry_run": True,
        }
        raw_text = json.dumps(raw_response, sort_keys=True)
        return ProviderResult(
            provider=self.provider_name,
            model=self.supported_models[0],
            execution_mode="dry_run",
            raw_response=raw_response,
            raw_text=raw_text,
            response_timestamp="1970-01-01T00:00:00Z",
            response_hash=hash_text(raw_text),
            request_id="live-execution-blocker-dry-run",
            latency_ms=0.0,
            token_counts={"prompt": len(prompt.split()), "completion": 0},
            cost_estimate=0.0,
        )


def load_v10_live_runner_design_config(path: str | Path) -> V10LiveRunnerDesignConfig:
    return V10LiveRunnerDesignConfig.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def validate_provider_model_allowed(
    config: V10LiveRunnerDesignConfig,
    provider: str,
    model: str,
) -> V10ProviderModelValidationResult:
    issues: list[str] = []
    provider_config = config.allowed_providers.get(provider)
    provider_allowed = provider_config is not None
    model_allowed = bool(provider_config and model in set(provider_config.allowed_models))
    if not provider_allowed:
        issues.append("unknown_provider")
    elif not model_allowed:
        issues.append("unknown_model")
    if config.unknown_model_behavior != "fail_loudly":
        issues.append("unknown_model_behavior_not_fail_loudly")
    return V10ProviderModelValidationResult(
        valid=not issues,
        issues=issues,
        provider=provider,
        model=model,
        provider_allowed=provider_allowed,
        model_allowed=model_allowed,
    )


def validate_execution_mode_path(
    config: V10LiveRunnerDesignConfig,
    execution_mode: ExecutionMode,
    output_path: str | Path,
) -> V10ExecutionModePathValidationResult:
    policy = config.output_path_policy
    path = _normalized_parts(output_path)
    issues: list[str] = []
    if execution_mode == "dry_run":
        if not _parts_under(path, _normalized_parts(policy.dry_run_root)):
            issues.append("dry_run_path_not_under_dry_run_root")
    elif execution_mode == "manual_import":
        if not _parts_under(path, _normalized_parts(policy.manual_import_root)):
            issues.append("manual_import_path_not_under_manual_import_root")
    elif execution_mode == "live":
        root = _normalized_parts(policy.live_root)
        if not _parts_under(path, root):
            issues.append("live_path_not_under_live_root")
        remainder = path[len(root):] if _parts_under(path, root) else ()
        if len(remainder) < 3:
            issues.append("live_path_missing_provider_model_run_id")
    else:
        issues.append("unsupported_execution_mode")
    return V10ExecutionModePathValidationResult(
        valid=not issues,
        issues=issues,
        execution_mode=execution_mode,
        output_path=str(output_path),
    )


def validate_live_authorization(
    live_flag: bool,
    authorization_env: Mapping[str, str],
    *,
    env_var: str = "HELIX_LIVE_EXECUTION_AUTHORIZED",
    required_value: str = "true",
) -> bool:
    return bool(live_flag and authorization_env.get(env_var) == required_value)


def validate_retry_policy(config: V10LiveRunnerDesignConfig) -> V10DesignValidationResult:
    policy = config.retry_policy
    issues: list[str] = []
    if policy.max_retries < 0:
        issues.append("max_retries_negative")
    if policy.base_delay_seconds <= 0:
        issues.append("base_delay_seconds_not_positive")
    if policy.jitter not in {"none", "full", "equal"}:
        issues.append("unsupported_jitter")
    if not policy.retryable_status_codes:
        issues.append("missing_retryable_status_codes")
    if not policy.non_retryable_status_codes:
        issues.append("missing_non_retryable_status_codes")
    if set(policy.retryable_status_codes) & set(policy.non_retryable_status_codes):
        issues.append("retryable_and_non_retryable_status_overlap")
    if policy.failure_budget_per_run < 0 or policy.failure_budget_per_run > 1:
        issues.append("failure_budget_out_of_range")
    if 400 in set(policy.retryable_status_codes) or 401 in set(policy.retryable_status_codes) or 403 in set(policy.retryable_status_codes):
        issues.append("client_auth_errors_marked_retryable")
    return V10DesignValidationResult(valid=not issues, issues=issues)


def build_live_runner_design_receipt(
    config: V10LiveRunnerDesignConfig,
) -> V10LiveRunnerDesignReceipt:
    payload = {
        "receipt_id": "v10.14:live_runner_design_gate",
        "receipt_type": "live_runner_design_gate",
        "version": "v10.14",
        "constraints_codified": REQUIRED_CONSTRAINTS,
        "live_calls_in_this_version": config.live_calls_allowed_in_this_version,
        "provider_sdks_used": config.provider_sdks_allowed_in_this_version,
        "secrets_included": config.api_keys_allowed_in_repo,
        "three_agent_consistency_target": config.three_agent_consistency_target.model_dump(mode="json"),
    }
    return V10LiveRunnerDesignReceipt(
        **payload,
        design_gate_hash=stable_json_hash(payload),
    )


def write_live_runner_design_receipt(
    config: V10LiveRunnerDesignConfig,
    out_dir: str | Path,
    *,
    generated_at: str | None = None,
) -> dict[str, Path]:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    receipt = build_live_runner_design_receipt(config)
    validation_issues = _design_gate_issues(config)

    config_path = target / "live_runner_design_config.json"
    receipt_path = target / "live_runner_design_receipt.json"
    report_path = target / "live_runner_design_report.md"

    config_payload = {
        "schema_version": "v10_live_runner_design_gate_config_snapshot_v1",
        "generated_at": generated_at
        or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "config": config.model_dump(mode="json"),
        "validation_issues": validation_issues,
    }
    config_path.write_text(
        json.dumps(config_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    receipt_path.write_text(
        json.dumps(receipt.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(
        receipt.to_markdown(config=config, validation_issues=validation_issues) + "\n",
        encoding="utf-8",
    )
    return {
        "config": config_path,
        "receipt": receipt_path,
        "report": report_path,
    }


def provider_result_to_dict(result: ProviderResult) -> dict[str, Any]:
    return asdict(result)


def _design_gate_issues(config: V10LiveRunnerDesignConfig) -> list[str]:
    issues: list[str] = []
    if not config.design_gate_only:
        issues.append("design_gate_only_false")
    if config.live_calls_allowed_in_this_version:
        issues.append("live_calls_allowed_in_design_gate")
    if config.provider_sdks_allowed_in_this_version:
        issues.append("provider_sdks_allowed_in_design_gate")
    if config.api_keys_allowed_in_repo:
        issues.append("api_keys_allowed_in_repo")
    if not config.mode_parameter_required:
        issues.append("mode_parameter_not_required")
    if config.mode_parameter_default_allowed:
        issues.append("mode_parameter_default_allowed")
    if not config.secrets_policy.secrets_provider_required:
        issues.append("secrets_provider_not_required")
    if not config.secrets_policy.dual_signal_live_authorization_required:
        issues.append("dual_signal_live_authorization_not_required")
    if config.secrets_policy.direct_environment_reads_allowed_in_runner:
        issues.append("direct_environment_reads_allowed_in_runner")
    if config.secrets_policy.api_key_presence_is_authorization:
        issues.append("api_key_presence_authorizes_live_execution")
    if not config.output_path_policy.execution_mode_manifest_field_required:
        issues.append("execution_mode_manifest_field_not_required")
    if config.output_path_policy.ambiguous_execution_mode_behavior != "fail_loudly":
        issues.append("ambiguous_execution_mode_not_fail_loudly")
    if not config.test_policy.live_execution_blocker_required:
        issues.append("live_execution_blocker_not_required")
    if config.test_policy.run_live_tests_in_default_ci:
        issues.append("live_tests_run_in_default_ci")
    if not config.three_agent_consistency_target.enabled_as_future_target:
        issues.append("three_agent_consistency_target_not_declared")
    if config.three_agent_consistency_target.minimum_independent_agent_systems < 3:
        issues.append("three_agent_consistency_requires_fewer_than_three")
    if config.three_agent_consistency_target.majority_vote_truth_claim_allowed:
        issues.append("majority_vote_truth_claim_allowed")
    retry = validate_retry_policy(config)
    issues.extend(retry.issues)
    for provider, provider_config in sorted(config.allowed_providers.items()):
        if not provider_config.allowed_models:
            issues.append(f"provider_missing_allowed_models:{provider}")
        if provider_config.rate_limit_rpm <= 0:
            issues.append(f"provider_rate_limit_not_positive:{provider}")
        if provider_config.max_retries < 0:
            issues.append(f"provider_max_retries_negative:{provider}")
    return sorted(set(issues))


def _normalized_parts(path: str | Path) -> tuple[str, ...]:
    return tuple(part for part in Path(path).parts if part not in {"", "."})


def _parts_under(path: tuple[str, ...], root: tuple[str, ...]) -> bool:
    return len(path) >= len(root) and path[: len(root)] == root
