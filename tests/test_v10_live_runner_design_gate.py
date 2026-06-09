import inspect
from pathlib import Path

from helix.benchmark import v10_live_runner_design_gate as design_gate
from helix.benchmark.v10_live_runner_design_gate import (
    REQUIRED_CONSTRAINTS,
    LiveExecutionBlocker,
    ProviderAdapter,
    ProviderResult,
    build_live_runner_design_receipt,
    load_v10_live_runner_design_config,
    validate_execution_mode_path,
    validate_live_authorization,
    validate_provider_model_allowed,
    validate_retry_policy,
    write_live_runner_design_receipt,
)


CONFIG_PATH = Path("configs/v10_live_provider_runner_design_gate.json")


def test_v10_live_runner_design_config_loads() -> None:
    config = load_v10_live_runner_design_config(CONFIG_PATH)

    assert config.schema_version == "v10_live_provider_runner_design_gate_v1"
    assert config.design_gate_only
    assert not config.live_calls_allowed_in_this_version
    assert not config.provider_sdks_allowed_in_this_version
    assert not config.api_keys_allowed_in_repo
    assert config.mode_parameter_required
    assert not config.mode_parameter_default_allowed
    assert config.unknown_model_behavior == "fail_loudly"
    assert config.three_agent_consistency_target.minimum_independent_agent_systems == 3


def test_provider_adapter_execute_signature_requires_mode_without_default() -> None:
    signature = inspect.signature(ProviderAdapter.execute)

    assert "mode" in signature.parameters
    assert signature.parameters["mode"].default is inspect._empty


def test_live_execution_blocker_raises_for_live() -> None:
    blocker = LiveExecutionBlocker()

    try:
        blocker.execute("prompt", "live")
    except AssertionError as exc:
        assert "Live execution is blocked" in str(exc)
    else:
        raise AssertionError("LiveExecutionBlocker did not block live execution")


def test_live_execution_blocker_returns_dry_run_result() -> None:
    blocker = LiveExecutionBlocker()

    result = blocker.execute("hello world", "dry_run")

    assert isinstance(result, ProviderResult)
    assert result.execution_mode == "dry_run"
    assert result.provider == "live_execution_blocker"
    assert result.response_hash.startswith("sha256:")
    assert result.raw_response["dry_run"] is True


def test_validate_live_authorization_requires_both_signals() -> None:
    assert not validate_live_authorization(True, {})
    assert not validate_live_authorization(
        False,
        {"HELIX_LIVE_EXECUTION_AUTHORIZED": "true"},
    )
    assert not validate_live_authorization(
        True,
        {"HELIX_LIVE_EXECUTION_AUTHORIZED": "false"},
    )
    assert validate_live_authorization(
        True,
        {"HELIX_LIVE_EXECUTION_AUTHORIZED": "true"},
    )


def test_unknown_provider_fails() -> None:
    config = load_v10_live_runner_design_config(CONFIG_PATH)

    result = validate_provider_model_allowed(config, "unknown", "model")

    assert not result.valid
    assert "unknown_provider" in result.issues


def test_unknown_model_fails() -> None:
    config = load_v10_live_runner_design_config(CONFIG_PATH)

    result = validate_provider_model_allowed(config, "google", "unknown-model")

    assert not result.valid
    assert "unknown_model" in result.issues


def test_allowed_provider_model_passes() -> None:
    config = load_v10_live_runner_design_config(CONFIG_PATH)

    result = validate_provider_model_allowed(config, "google", "gemini-flash-2.0")

    assert result.valid
    assert result.issues == []
    assert result.provider_allowed
    assert result.model_allowed


def test_execution_mode_path_validation_passes_for_expected_roots() -> None:
    config = load_v10_live_runner_design_config(CONFIG_PATH)

    assert validate_execution_mode_path(
        config,
        "dry_run",
        "benchmarks/v10_calibrated/provider_runs/dry_run/run_001",
    ).valid
    assert validate_execution_mode_path(
        config,
        "manual_import",
        "benchmarks/v10_calibrated/provider_runs/manual_import/run_001",
    ).valid
    assert validate_execution_mode_path(
        config,
        "live",
        "benchmarks/v10_calibrated/provider_runs/live/google/gemini-flash-2.0/run_001",
    ).valid


def test_execution_mode_path_mismatch_fails() -> None:
    config = load_v10_live_runner_design_config(CONFIG_PATH)

    result = validate_execution_mode_path(
        config,
        "dry_run",
        "benchmarks/v10_calibrated/provider_runs/live/google/gemini-flash-2.0/run_001",
    )
    live_result = validate_execution_mode_path(
        config,
        "live",
        "benchmarks/v10_calibrated/provider_runs/live/google",
    )

    assert not result.valid
    assert "dry_run_path_not_under_dry_run_root" in result.issues
    assert not live_result.valid
    assert "live_path_missing_provider_model_run_id" in live_result.issues


def test_retry_policy_validates_expected_fields() -> None:
    config = load_v10_live_runner_design_config(CONFIG_PATH)

    result = validate_retry_policy(config)

    assert result.valid
    assert config.retry_policy.max_retries == 3
    assert config.retry_policy.base_delay_seconds == 1.0
    assert config.retry_policy.jitter == "full"
    assert config.retry_policy.failure_budget_per_run == 0.05


def test_design_receipt_contains_required_constraints_and_false_live_claims() -> None:
    config = load_v10_live_runner_design_config(CONFIG_PATH)

    receipt = build_live_runner_design_receipt(config)

    assert receipt.receipt_type == "live_runner_design_gate"
    assert receipt.version == "v10.14"
    assert set(REQUIRED_CONSTRAINTS).issubset(set(receipt.constraints_codified))
    assert receipt.live_calls_in_this_version is False
    assert receipt.provider_sdks_used is False
    assert receipt.secrets_included is False
    assert receipt.design_gate_hash.startswith("sha256:")


def test_three_agent_consistency_target_declared() -> None:
    config = load_v10_live_runner_design_config(CONFIG_PATH)
    receipt = build_live_runner_design_receipt(config)

    target = receipt.three_agent_consistency_target

    assert target["enabled_as_future_target"] is True
    assert target["minimum_independent_agent_systems"] == 3
    assert target["majority_vote_truth_claim_allowed"] is False
    assert "three_agent_consistency_target_declared" in receipt.constraints_codified


def test_report_contains_what_this_does_not_yet_prove(tmp_path: Path) -> None:
    config = load_v10_live_runner_design_config(CONFIG_PATH)

    paths = write_live_runner_design_receipt(config, tmp_path)
    report = paths["report"].read_text(encoding="utf-8")

    assert paths["config"].exists()
    assert paths["receipt"].exists()
    assert "What This Does Not Yet Prove" in report
    assert "No live calls were made" in report
    assert "No provider SDKs were used" in report
    assert "not Level 4 or Level 5 evidence" in report


def test_live_authorization_does_not_need_os_environ_direct_dependency() -> None:
    source = inspect.getsource(design_gate)

    assert "os.environ" not in source
    assert not validate_live_authorization(
        True,
        {"OTHER": "true"},
    )
    assert validate_live_authorization(
        True,
        {"HELIX_LIVE_EXECUTION_AUTHORIZED": "true"},
    )
