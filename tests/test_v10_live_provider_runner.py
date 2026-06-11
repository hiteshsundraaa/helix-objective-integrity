import json
from pathlib import Path

import pytest

from helix.benchmark.benchmark_receipts import hash_text
from helix.benchmark.v10_generator import V10Case
from helix.benchmark.v10_live_provider_runner import (
    LiveExecutionNotAuthorizedError,
    LiveProviderCallError,
    ProviderModelNotAllowedError,
    V10LivePilotInput,
    authorize_live_execution,
    build_live_output_dir,
    execute_live_case,
    load_v10_guarded_live_pilot_config,
    run_guarded_live_pilot,
    run_with_retry_policy,
    validate_live_pilot_input,
)
from helix.benchmark.v10_live_runner_design_gate import (
    ProviderResult,
    load_v10_live_runner_design_config,
)
from helix.benchmark.v10_provider_raw_import import load_provider_run_plan


CONFIG_PATH = Path("configs/v10_guarded_live_one_provider_pilot.json")
LIVE_CONFIG_PATH = Path("configs/v10_live_provider_runner_design_gate.json")
PLAN_PATH = Path("benchmarks/v10_calibrated/provider_run_plans/pilot_v1/provider_run_plan.json")
CASES_PATH = Path("benchmarks/v10_calibrated/v10_cases.jsonl")


def test_authorization_requires_live_flag() -> None:
    with pytest.raises(LiveExecutionNotAuthorizedError):
        authorize_live_execution(_input(live_flag=False), AuthorizedSecretsProvider())


def test_authorization_requires_secrets_provider_signal() -> None:
    with pytest.raises(LiveExecutionNotAuthorizedError):
        authorize_live_execution(_input(), UnauthorizedSecretsProvider())


def test_authorization_requires_non_empty_api_key() -> None:
    with pytest.raises(LiveExecutionNotAuthorizedError):
        authorize_live_execution(_input(), MissingKeySecretsProvider())


def test_authorization_passes_with_dual_signal_and_key() -> None:
    authorize_live_execution(_input(), AuthorizedSecretsProvider())


def test_unknown_provider_fails_before_adapter_execution(tmp_path: Path) -> None:
    live_input = _input(tmp_path, provider="unknown", model="model")
    adapter = MockProviderAdapterSuccess(_cases_by_id())

    with pytest.raises(ProviderModelNotAllowedError):
        run_guarded_live_pilot(
            live_input,
            adapter,
            AuthorizedSecretsProvider(),
            _config_for_tmp(tmp_path),
            _live_design_for_tmp(tmp_path),
            sleep_fn=lambda _: None,
            random_fn=lambda: 0.0,
            generated_at="2026-06-11T00:00:00Z",
        )

    assert adapter.calls == 0


def test_unknown_model_fails_before_adapter_execution(tmp_path: Path) -> None:
    live_input = _input(tmp_path, model="unknown-model")
    adapter = MockProviderAdapterSuccess(_cases_by_id())

    with pytest.raises(ProviderModelNotAllowedError):
        run_guarded_live_pilot(
            live_input,
            adapter,
            AuthorizedSecretsProvider(),
            _config_for_tmp(tmp_path),
            _live_design_for_tmp(tmp_path),
            sleep_fn=lambda _: None,
            random_fn=lambda: 0.0,
            generated_at="2026-06-11T00:00:00Z",
        )

    assert adapter.calls == 0


def test_allowed_provider_model_passes_validation(tmp_path: Path) -> None:
    issues = validate_live_pilot_input(
        _input(tmp_path),
        _config_for_tmp(tmp_path),
        _live_design_for_tmp(tmp_path),
    )

    assert issues == []


def test_live_output_path_is_provider_model_run_id(tmp_path: Path) -> None:
    live_input = _input(tmp_path, run_id="path_test")
    out_dir = build_live_output_dir(live_input, _config_for_tmp(tmp_path))

    assert out_dir == tmp_path / "live" / "google" / "gemini-flash-2.0" / "path_test"


def test_run_id_path_traversal_fails(tmp_path: Path) -> None:
    issues = validate_live_pilot_input(
        _input(tmp_path, run_id="../escape"),
        _config_for_tmp(tmp_path),
        _live_design_for_tmp(tmp_path),
    )

    assert "invalid_run_id" in issues


def test_raw_output_written_before_parse_failure(tmp_path: Path) -> None:
    cases = _cases_by_id()
    case = next(iter(cases.values()))
    adapter = MockProviderAdapterMalformed()
    out_dir = tmp_path / "raw_preserve"
    result, judgment = execute_live_case(
        case,
        adapter,
        _input(tmp_path),
        _config_for_tmp(tmp_path),
        _live_design_for_tmp(tmp_path),
        out_dir,
    )

    assert judgment is None
    assert result.failed
    assert result.raw_output_path is not None
    assert Path(result.raw_output_path).exists()
    assert result.raw_output_hash is not None


def test_retryable_failure_then_success_records_retry(tmp_path: Path) -> None:
    case = next(iter(_cases_by_id().values()))
    adapter = MockProviderAdapterRetryableThenSuccess(_cases_by_id())

    result, judgment, retries = run_with_retry_policy(
        case,
        adapter,
        _input(tmp_path),
        _config_for_tmp(tmp_path),
        _live_design_for_tmp(tmp_path),
        tmp_path / "retry",
        sleep_fn=lambda _: None,
        random_fn=lambda: 0.0,
    )

    assert result.succeeded
    assert result.retry_count == 1
    assert retries == ["provider_timeout"]
    assert judgment is not None


def test_non_retryable_failure_does_not_retry(tmp_path: Path) -> None:
    case = next(iter(_cases_by_id().values()))
    adapter = MockProviderAdapterNonRetryableFailure()

    result, judgment, retries = run_with_retry_policy(
        case,
        adapter,
        _input(tmp_path),
        _config_for_tmp(tmp_path),
        _live_design_for_tmp(tmp_path),
        tmp_path / "non_retry",
        sleep_fn=lambda _: None,
        random_fn=lambda: 0.0,
    )

    assert result.failed
    assert result.retry_count == 0
    assert judgment is None
    assert retries == []
    assert adapter.calls == 1


def test_failure_budget_exceeded_aborts_run(tmp_path: Path) -> None:
    summary, paths = run_guarded_live_pilot(
        _input(tmp_path, run_id="budget_abort"),
        MockProviderAdapterFailureBudgetExceeded(),
        AuthorizedSecretsProvider(),
        _config_for_tmp(tmp_path),
        _live_design_for_tmp(tmp_path),
        sleep_fn=lambda _: None,
        random_fn=lambda: 0.0,
        generated_at="2026-06-11T00:00:00Z",
    )

    assert summary.aborted
    assert summary.final_evidence_level <= 3
    assert "failure_budget_exceeded" in summary.blocking_issues
    assert paths["manifest"].exists()
    assert (paths["manifest"].parent / "live_retry_report.json").exists()


def test_successful_mock_live_pilot_writes_pipeline_and_receipts(tmp_path: Path) -> None:
    summary, paths = run_guarded_live_pilot(
        _input(tmp_path, run_id="mock_success"),
        MockProviderAdapterSuccess(_cases_by_id()),
        AuthorizedSecretsProvider(),
        _config_for_tmp(tmp_path),
        _live_design_for_tmp(tmp_path),
        sleep_fn=lambda _: None,
        random_fn=lambda: 0.0,
        generated_at="2026-06-11T00:00:00Z",
    )
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    report = paths["report"].read_text(encoding="utf-8")

    assert manifest["execution_mode"] == "live"
    assert summary.raw_output_preserved
    assert summary.raw_output_hash_available_count == summary.succeeded
    assert summary.parsed_raw_judgment_count == summary.case_count
    assert summary.receipt_count == summary.case_count
    assert summary.invalid_receipt_count == 0
    assert summary.level_5_allowed is False
    assert paths["manifest"].exists()
    assert paths["report"].exists()
    assert (paths["manifest"].parent / "pilot_evidence" / "pilot_evidence_assessment.json").exists()
    assert (paths["manifest"].parent / "live_case_results.jsonl").exists()
    assert "What This Does Not Prove" in report
    assert "One provider does not prove cross-provider consistency" in report
    assert "super-secret" not in paths["manifest"].read_text(encoding="utf-8")
    assert "super-secret" not in report


def test_binary_score_collapse_blocks_level_4(tmp_path: Path) -> None:
    summary, _ = run_guarded_live_pilot(
        _input(tmp_path, run_id="binary_collapse"),
        MockProviderAdapterBinaryScoreCollapse(_cases_by_id()),
        AuthorizedSecretsProvider(),
        _config_for_tmp(tmp_path),
        _live_design_for_tmp(tmp_path),
        sleep_fn=lambda _: None,
        random_fn=lambda: 0.0,
        generated_at="2026-06-11T00:00:00Z",
    )

    assert summary.final_evidence_level <= 3
    assert summary.score_collapse_detected is True
    assert "score_collapse_blocks_level_4" in summary.blocking_issues


def test_no_direct_environment_or_provider_sdk_dependency() -> None:
    source = Path("helix/benchmark/v10_live_provider_runner.py").read_text(encoding="utf-8")

    assert "os.environ" not in source
    assert "import openai" not in source
    assert "import anthropic" not in source
    assert "import google" not in source


class AuthorizedSecretsProvider:
    def get_api_key(self, provider: str) -> str:
        return "super-secret-test-key"

    def is_live_authorized(self) -> bool:
        return True


class UnauthorizedSecretsProvider:
    def get_api_key(self, provider: str) -> str:
        return "super-secret-test-key"

    def is_live_authorized(self) -> bool:
        return False


class MissingKeySecretsProvider:
    def get_api_key(self, provider: str) -> str:
        return ""

    def is_live_authorized(self) -> bool:
        return True


class MockProviderAdapterSuccess:
    provider_name = "mock"
    supported_models = ("mock",)

    def __init__(self, cases_by_id: dict[str, V10Case]) -> None:
        self.cases_by_id = cases_by_id
        self.calls = 0

    def execute(self, prompt: str, mode: str, *, raw_preserve: bool = True, request_metadata=None):
        self.calls += 1
        case_id = request_metadata["case_id"]
        row = _judgment_for_case(self.cases_by_id[case_id], self.calls)
        raw_response = {"judgment": row}
        raw_text = json.dumps(raw_response, sort_keys=True)
        return ProviderResult(
            provider="google",
            model="gemini-flash-2.0",
            execution_mode="live",
            raw_response=raw_response,
            raw_text=raw_text,
            response_timestamp="2026-06-11T00:00:00Z",
            response_hash=hash_text(raw_text),
            latency_ms=1.0,
            token_counts={"prompt": 10, "completion": 5},
            cost_estimate=0.001,
        )


class MockProviderAdapterMalformed:
    provider_name = "mock"
    supported_models = ("mock",)

    def execute(self, prompt: str, mode: str, *, raw_preserve: bool = True, request_metadata=None):
        raw_response = {"not_a_judgment": True}
        raw_text = json.dumps(raw_response, sort_keys=True)
        return ProviderResult(
            provider="google",
            model="gemini-flash-2.0",
            execution_mode="live",
            raw_response=raw_response,
            raw_text=raw_text,
            response_timestamp="2026-06-11T00:00:00Z",
            response_hash=hash_text(raw_text),
        )


class MockProviderAdapterRetryableThenSuccess(MockProviderAdapterSuccess):
    def execute(self, prompt: str, mode: str, *, raw_preserve: bool = True, request_metadata=None):
        if self.calls == 0:
            self.calls += 1
            raise LiveProviderCallError("timeout", status_code=503, reason="provider_timeout")
        return super().execute(prompt, mode, raw_preserve=raw_preserve, request_metadata=request_metadata)


class MockProviderAdapterNonRetryableFailure:
    provider_name = "mock"
    supported_models = ("mock",)

    def __init__(self) -> None:
        self.calls = 0

    def execute(self, prompt: str, mode: str, *, raw_preserve: bool = True, request_metadata=None):
        self.calls += 1
        raise LiveProviderCallError("auth failure", status_code=401, reason="auth_failure")


class MockProviderAdapterFailureBudgetExceeded:
    provider_name = "mock"
    supported_models = ("mock",)

    def execute(self, prompt: str, mode: str, *, raw_preserve: bool = True, request_metadata=None):
        raise LiveProviderCallError("server failure", status_code=500, reason="server_failure", retryable=False)


class MockProviderAdapterBinaryScoreCollapse(MockProviderAdapterSuccess):
    def execute(self, prompt: str, mode: str, *, raw_preserve: bool = True, request_metadata=None):
        self.calls += 1
        case_id = request_metadata["case_id"]
        row = {
            "case_id": case_id,
            "decision": "ALLOW",
            "violation_probability": 0.0,
            "cited_contract_phrase": "",
            "citation_verification_method": "unverified",
            "reason_codes": ["mock.binary_collapse"],
            "uncertainty_reason": None,
        }
        raw_response = {"judgment": row}
        raw_text = json.dumps(raw_response, sort_keys=True)
        return ProviderResult(
            provider="google",
            model="gemini-flash-2.0",
            execution_mode="live",
            raw_response=raw_response,
            raw_text=raw_text,
            response_timestamp="2026-06-11T00:00:00Z",
            response_hash=hash_text(raw_text),
            latency_ms=1.0,
        )


def _input(
    tmp_path: Path | None = None,
    *,
    provider: str = "google",
    model: str = "gemini-flash-2.0",
    run_id: str = "live_test",
    live_flag: bool = True,
) -> V10LivePilotInput:
    root = tmp_path / "live" if tmp_path else Path("benchmarks/v10_calibrated/provider_runs/live")
    return V10LivePilotInput(
        provider=provider,
        model=model,
        run_id=run_id,
        plan_path=str(PLAN_PATH),
        output_root=str(root),
        live_flag=live_flag,
        case_limit=30,
        allow_full_300=False,
    )


def _config_for_tmp(tmp_path: Path):
    return load_v10_guarded_live_pilot_config(CONFIG_PATH).model_copy(
        update={"provider_runs_live_root": str(tmp_path / "live")}
    )


def _live_design_for_tmp(tmp_path: Path):
    config = load_v10_live_runner_design_config(LIVE_CONFIG_PATH)
    return config.model_copy(
        update={
            "output_path_policy": config.output_path_policy.model_copy(
                update={"live_root": str(tmp_path / "live")}
            )
        }
    )


def _cases_by_id() -> dict[str, V10Case]:
    cases = [
        V10Case.model_validate_json(line)
        for line in CASES_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    plan = load_provider_run_plan(PLAN_PATH)
    return {case.case_id: case for case in cases if case.case_id in set(plan.sampled_case_ids)}


def _judgment_for_case(case: V10Case, index: int) -> dict[str, object]:
    scores = [0.08, 0.21, 0.42, 0.61, 0.82, 0.31, 0.52, 0.73, 0.27, 0.94]
    score = scores[(index - 1) % len(scores)]
    if score >= 0.9:
        decision = "BLOCK"
    elif score >= 0.75:
        decision = "QUARANTINE"
    elif score >= 0.55:
        decision = "DEGRADE"
    elif score >= 0.35:
        decision = "ESCALATE_FOR_APPROVAL"
    elif score >= 0.15:
        decision = "WARN"
    else:
        decision = "ALLOW"
    high_risk = decision in {"DEGRADE", "QUARANTINE", "BLOCK"}
    return {
        "case_id": case.case_id,
        "decision": decision,
        "violation_probability": score,
        "cited_contract_phrase": _citation_for_case(case) if high_risk else "",
        "citation_verification_method": "exact_substring" if high_risk else "unverified",
        "reason_codes": ["mock.live_success", f"family.{case.family}"],
        "uncertainty_reason": None,
    }


def _citation_for_case(case: V10Case) -> str:
    return case.expected_cited_contract_phrase or case.active_contract_rule_summary
