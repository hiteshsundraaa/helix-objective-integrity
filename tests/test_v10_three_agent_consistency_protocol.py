import inspect
from pathlib import Path

from helix.benchmark import v10_three_agent_consistency_protocol as protocol
from helix.benchmark.v10_three_agent_consistency_protocol import (
    THREE_AGENT_PROTOCOL_CONSTRAINTS,
    V10ThreeAgentSystemSpec,
    build_metric_definitions,
    build_three_agent_protocol_receipt,
    classify_decision_distance,
    classify_risk_band,
    is_severe_disagreement,
    load_v10_three_agent_consistency_protocol_config,
    validate_three_agent_system_specs,
    write_three_agent_protocol_artifacts,
)


CONFIG_PATH = Path("configs/v10_three_agent_consistency_protocol.json")


def _config():
    return load_v10_three_agent_consistency_protocol_config(CONFIG_PATH)


def test_config_loads() -> None:
    config = _config()

    assert config.schema_version == "v10_three_agent_consistency_protocol_v1"
    assert config.protocol_only
    assert config.minimum_independent_systems == 3
    assert not config.majority_vote_truth_claim_allowed
    assert config.consistency_not_correctness
    assert not config.level_5_allowed


def test_recommended_systems_count_at_least_three() -> None:
    config = _config()

    assert len(config.recommended_initial_systems) >= 3
    assert validate_three_agent_system_specs(
        config.recommended_initial_systems,
        config,
    ).valid


def test_fewer_than_three_systems_fails_validation() -> None:
    config = _config()
    systems = config.recommended_initial_systems[:2]

    result = validate_three_agent_system_specs(systems, config)

    assert not result.valid
    assert "fewer_than_minimum_systems" in result.issues
    assert "fewer_than_three_independent_systems" in result.issues


def test_duplicate_role_fails_validation() -> None:
    config = _config()
    systems = [
        config.recommended_initial_systems[0],
        config.recommended_initial_systems[1].model_copy(update={"role": "system_a"}),
        config.recommended_initial_systems[2],
    ]

    result = validate_three_agent_system_specs(systems, config)

    assert not result.valid
    assert "duplicate_role" in result.issues


def test_duplicate_provider_model_combination_fails_validation() -> None:
    config = _config()
    duplicate = config.recommended_initial_systems[0].model_copy(update={"role": "system_d"})
    systems = [
        config.recommended_initial_systems[0],
        config.recommended_initial_systems[1],
        duplicate,
    ]

    result = validate_three_agent_system_specs(systems, config)

    assert not result.valid
    assert "duplicate_provider_model" in result.issues
    assert "fewer_than_three_independent_systems" in result.issues


def test_majority_vote_truth_claim_allowed_false_required() -> None:
    config = _config().model_copy(update={"majority_vote_truth_claim_allowed": True})

    result = validate_three_agent_system_specs(config.recommended_initial_systems, config)

    assert not result.valid
    assert "majority_vote_truth_claim_allowed" in result.issues


def test_consistency_not_correctness_true_required() -> None:
    config = _config().model_copy(update={"consistency_not_correctness": False})

    result = validate_three_agent_system_specs(config.recommended_initial_systems, config)

    assert not result.valid
    assert "consistency_not_correctness_false" in result.issues


def test_level_5_allowed_false_required() -> None:
    config = _config().model_copy(update={"level_5_allowed": True})

    result = validate_three_agent_system_specs(config.recommended_initial_systems, config)

    assert not result.valid
    assert "level_5_allowed" in result.issues


def test_classify_risk_band_works_at_boundaries() -> None:
    config = _config()

    assert classify_risk_band(0.0, config) == "clearly_safe"
    assert classify_risk_band(0.15, config) == "low_risk_benign_noise"
    assert classify_risk_band(0.75, config) == "high_risk"
    assert classify_risk_band(0.9, config) == "severe_direct_violation"
    assert classify_risk_band(1.0, config) == "severe_direct_violation"


def test_invalid_score_returns_invalid_band() -> None:
    config = _config()

    assert classify_risk_band(-0.1, config) == "invalid"
    assert classify_risk_band(1.1, config) == "invalid"
    assert classify_risk_band("0.5", config) == "invalid"
    assert classify_risk_band(True, config) == "invalid"


def test_decision_distance_works() -> None:
    config = _config()

    assert classify_decision_distance("ALLOW", "ALLOW", config) == 0
    assert classify_decision_distance("ALLOW", "WARN", config) == 1
    assert classify_decision_distance("ALLOW", "BLOCK", config) == 5
    assert classify_decision_distance("ALLOW", "UNKNOWN", config) == -1


def test_allow_vs_block_is_severe() -> None:
    config = _config()

    assert is_severe_disagreement(
        {"decision": "ALLOW", "violation_probability": 0.05},
        {"decision": "BLOCK", "violation_probability": 0.9},
        config,
    )


def test_allow_vs_quarantine_is_severe() -> None:
    config = _config()

    assert is_severe_disagreement(
        {"decision": "ALLOW", "violation_probability": 0.05},
        {"decision": "QUARANTINE", "violation_probability": 0.82},
        config,
    )


def test_score_distance_above_threshold_is_severe() -> None:
    config = _config()

    assert is_severe_disagreement(
        {"decision": "WARN", "violation_probability": 0.1},
        {"decision": "WARN", "violation_probability": 0.61},
        config,
    )


def test_high_risk_citation_mismatch_is_severe() -> None:
    config = _config()

    assert is_severe_disagreement(
        {
            "decision": "BLOCK",
            "violation_probability": 0.9,
            "citation_verification_method": "exact_substring",
            "cited_contract_phrase": "Use channel alpha.",
        },
        {
            "decision": "BLOCK",
            "violation_probability": 0.88,
            "citation_verification_method": "unverified",
            "cited_contract_phrase": "",
        },
        config,
    )


def test_parse_failure_against_valid_output_is_severe() -> None:
    config = _config()

    assert is_severe_disagreement(
        {"decision": "ALLOW", "parse_success": False},
        {"decision": "ALLOW", "parse_success": True},
        config,
    )


def test_metric_definitions_include_required_per_case_and_aggregate_metrics() -> None:
    config = _config()
    metrics = build_metric_definitions(config)
    names = {metric.name for metric in metrics}
    levels = {metric.name: metric.level for metric in metrics}

    assert "unanimous_decision_agreement" in names
    assert "majority_decision_agreement" in names
    assert "severe_disagreement_rate" in names
    assert levels["unanimous_decision_agreement"] == "per_case"
    assert levels["severe_disagreement_rate"] == "aggregate"
    assert all(metric.required for metric in metrics)


def test_protocol_receipt_contains_all_required_constraints() -> None:
    config = _config()

    receipt = build_three_agent_protocol_receipt(config)

    assert receipt.receipt_type == "three_agent_consistency_protocol"
    assert receipt.version == "v10.16"
    assert set(THREE_AGENT_PROTOCOL_CONSTRAINTS).issubset(
        set(receipt.constraints_codified)
    )
    assert receipt.protocol_hash.startswith("sha256:")


def test_protocol_receipt_contains_false_live_and_secret_claims() -> None:
    config = _config()

    receipt = build_three_agent_protocol_receipt(config)

    assert receipt.live_calls_in_this_version is False
    assert receipt.provider_sdks_used is False
    assert receipt.secrets_included is False
    assert receipt.majority_vote_truth_claim_allowed is False
    assert receipt.provider_outputs_combined_for_truth is False
    assert receipt.consistency_not_correctness is True


def test_report_contains_what_this_does_not_yet_prove(tmp_path: Path) -> None:
    config = _config()

    paths = write_three_agent_protocol_artifacts(
        config,
        tmp_path,
        generated_at="2026-06-11T00:00:00Z",
    )
    report = paths["report"].read_text(encoding="utf-8")

    assert paths["config"].exists()
    assert paths["metrics"].exists()
    assert paths["receipt"].exists()
    assert "What This Does Not Yet Prove" in report
    assert "No provider calls were made" in report
    assert "No provider SDKs were used" in report
    assert "No secrets were included" in report


def test_report_states_majority_vote_is_not_truth(tmp_path: Path) -> None:
    config = _config()

    paths = write_three_agent_protocol_artifacts(config, tmp_path)
    report = paths["report"].read_text(encoding="utf-8")

    assert "Majority vote is not truth" in report
    assert "Agreement is consistency evidence, not correctness evidence" in report
    assert "Level 5 is false" in report


def test_unknown_provider_model_is_checked_against_allowlist() -> None:
    config = _config()
    systems = [
        V10ThreeAgentSystemSpec(role="system_a", provider="unknown", model="model"),
        V10ThreeAgentSystemSpec(role="system_b", provider="anthropic", model="claude-sonnet-4-6"),
        V10ThreeAgentSystemSpec(role="system_c", provider="openai", model="gpt-4o"),
    ]

    result = validate_three_agent_system_specs(systems, config)

    assert not result.valid
    assert any(issue.startswith("provider_model_not_allowed:system_a") for issue in result.issues)


def test_no_provider_specific_branching_in_protocol_logic() -> None:
    source = inspect.getsource(protocol)

    assert 'provider == "google"' not in source
    assert 'provider == "anthropic"' not in source
    assert 'provider == "openai"' not in source
