from helix.benchmark.v10_live_runner_design_gate import load_v10_live_runner_design_config
from helix.benchmark.v10_pilot_evidence_assessor import (
    assess_v10_pilot_evidence,
    load_v10_pilot_evidence_assessment_config,
)
from helix.benchmark.v10_receipt_chain import V10ReceiptChainSummary


ASSESSMENT_CONFIG = "configs/v10_pilot_evidence_assessment.json"
LIVE_CONFIG = "configs/v10_live_provider_runner_design_gate.json"


def test_v10_pilot_evidence_assessment_config_loads() -> None:
    config = load_v10_pilot_evidence_assessment_config(ASSESSMENT_CONFIG)

    assert config.schema_version == "v10_pilot_evidence_assessment_v1"
    assert config.assessment_only
    assert config.execution_mode_caps["dry_run"] == 2
    assert config.execution_mode_caps["manual_import"] == 3
    assert config.execution_mode_caps["live"] == 4
    assert not config.level_5_allowed


def test_live_run_with_all_criteria_met_gets_level_4() -> None:
    assessment = _assess(execution_mode="live")

    assert assessment.final_evidence_level == 4
    assert assessment.level_4_criteria_met
    assert not assessment.level_5_allowed


def test_manual_import_with_all_mechanical_criteria_gets_level_3_cap() -> None:
    assessment = _assess(execution_mode="manual_import")

    assert assessment.final_evidence_level == 3
    assert not assessment.level_4_criteria_met
    assert "mechanical_gates_passed_but_manual_import_cap_applied" in assessment.non_blocking_warnings
    assert "execution_mode_not_live_blocks_level_4" in assessment.blocking_issues


def test_dry_run_with_all_mechanical_criteria_gets_level_2_cap() -> None:
    assessment = _assess(execution_mode="dry_run")

    assert assessment.final_evidence_level == 2
    assert not assessment.level_4_criteria_met
    assert "mechanical_gates_passed_but_dry_run_cap_applied" in assessment.non_blocking_warnings


def test_score_collapse_detected_blocks_level_4() -> None:
    assessment = _assess(score_collapse_detected=True)

    assert assessment.final_evidence_level == 3
    assert "score_collapse_blocks_level_4" in assessment.blocking_issues
    assert not assessment.level_4_criteria_results.score_collapse_clear


def test_integrity_failed_blocks_level_4() -> None:
    assessment = _assess(integrity_passed=False)

    assert assessment.final_evidence_level == 3
    assert "integrity_failure_blocks_level_4" in assessment.blocking_issues


def test_receipt_chain_incomplete_blocks_level_4() -> None:
    assessment = _assess(receipt_chain_summary=_chain(complete=False, invalid=1))

    assert assessment.final_evidence_level == 3
    assert "receipt_chain_incomplete_blocks_level_4" in assessment.blocking_issues
    assert "invalid_receipts_block_level_4" in assessment.blocking_issues


def test_unknown_provider_blocks_level_4() -> None:
    assessment = _assess(provider="unknown")

    assert assessment.final_evidence_level == 3
    assert "provider_model_not_allowed_blocks_level_4" in assessment.blocking_issues


def test_unknown_model_blocks_level_4() -> None:
    assessment = _assess(model="unknown")

    assert assessment.final_evidence_level == 3
    assert "provider_model_not_allowed_blocks_level_4" in assessment.blocking_issues


def test_missing_raw_output_hash_for_live_blocks_level_4() -> None:
    assessment = _assess(receipt_chain_summary=_chain(raw_available=0))

    assert assessment.final_evidence_level == 3
    assert "missing_raw_output_hash_for_live_blocks_level_4" in assessment.blocking_issues


def test_missing_normalization_status_fails_closed() -> None:
    assessment = _assess(normalization_status=None)

    assert assessment.final_evidence_level == 0
    assert "missing_normalization_status" in assessment.blocking_issues


def test_level_5_always_false() -> None:
    assessment = _assess()

    assert assessment.level_5_allowed is False
    assert assessment.level_4_criteria_results.level_5_not_claimed


def test_assessment_hash_deterministic() -> None:
    first = _assess()
    second = _assess()

    assert first.assessment_hash == second.assessment_hash


def test_blocking_issues_are_specific_not_generic_only() -> None:
    assessment = _assess(score_collapse_detected=True, integrity_passed=False)

    assert "score_collapse_blocks_level_4" in assessment.blocking_issues
    assert "integrity_failure_blocks_level_4" in assessment.blocking_issues


def _assess(
    *,
    execution_mode: str = "live",
    provider: str = "google",
    model: str = "gemini-flash-2.0",
    normalization_status: str | None = "complete",
    benchmark_status: str | None = "complete",
    diagnostics_status: str | None = "complete",
    integrity_passed: bool = True,
    score_collapse_detected: bool = False,
    receipt_chain_summary: V10ReceiptChainSummary | None = None,
) :
    return assess_v10_pilot_evidence(
        run_id="pilot_test",
        execution_mode=execution_mode,
        provider=provider,
        model=model,
        case_count=2,
        receipt_chain_summary=receipt_chain_summary or _chain(),
        normalization_status=normalization_status,
        benchmark_status=benchmark_status,
        diagnostics_status=diagnostics_status,
        integrity_summary={
            "integrity_passed": integrity_passed,
            "score_collapse_detected": score_collapse_detected,
            "generator_independence": True,
        },
        reportability_summary={
            "reportability_passed": True,
            "evidence_level_allowed": 4,
        },
        live_design_config=load_v10_live_runner_design_config(LIVE_CONFIG),
        assessment_config=load_v10_pilot_evidence_assessment_config(ASSESSMENT_CONFIG),
    )


def _chain(
    *,
    complete: bool = True,
    invalid: int = 0,
    raw_available: int = 2,
) -> V10ReceiptChainSummary:
    return V10ReceiptChainSummary(
        run_id="pilot_test",
        execution_mode="live",
        provider="google",
        model="gemini-flash-2.0",
        case_count=2,
        receipt_count=2,
        valid_receipt_count=2 - invalid,
        invalid_receipt_count=invalid,
        missing_receipt_count=0 if complete else 1,
        raw_output_hash_available_count=raw_available,
        raw_output_hash_missing_count=2 - raw_available,
        receipt_chain_complete=complete and invalid == 0,
        receipt_hashes=["sha256:a", "sha256:b"],
        chain_hash="sha256:chain",
        issues=[],
        warnings=[],
    )
