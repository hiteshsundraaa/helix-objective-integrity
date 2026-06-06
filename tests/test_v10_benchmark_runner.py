import json
from pathlib import Path

import pytest

from helix.benchmark.benchmark_receipts import hash_file
from helix.benchmark.v10_benchmark_runner import (
    build_v10_benchmark_receipts,
    compute_v10_benchmark_metrics,
    load_normalization_summary,
    load_normalized_judgments,
    load_v10_benchmark_config,
    load_v10_cases,
    validate_normalization_status,
    validate_v10_benchmark_receipts,
    write_v10_benchmark_outputs,
)
from helix.benchmark.v10_judgment_normalization import (
    V10NormalizedJudgment,
    load_raw_judgments,
    load_v10_normalization_config,
    normalize_v10_judgments,
    write_v10_normalization_outputs,
)


CONFIG_PATH = Path("configs/v10_benchmark_runner.json")
NORMALIZATION_CONFIG_PATH = Path("configs/v10_judgment_normalization.json")
CASES_PATH = Path("benchmarks/v10_calibrated/v10_cases.jsonl")
FIXTURE_DIR = Path("tests/fixtures/v10_judgments")


def _config():
    return load_v10_benchmark_config(CONFIG_PATH)


def _cases():
    return load_v10_cases(CASES_PATH)


def _normalization_fixture(name: str):
    return normalize_v10_judgments(
        load_raw_judgments(FIXTURE_DIR / name),
        _cases(),
        load_v10_normalization_config(NORMALIZATION_CONFIG_PATH),
        provider="fixture",
        model=name.removesuffix(".jsonl"),
    )


def test_v10_benchmark_config_loads() -> None:
    config = _config()

    assert config.schema_version == "v10_benchmark_runner_v1"
    assert config.registered_before_real_judgment_runs
    assert config.block_threshold == 0.85
    assert "needs_work" in config.reject_normalization_statuses
    assert "locally_safe_globally_drifted" in config.positive_labels


def test_failed_normalization_summary_is_rejected() -> None:
    _, summary = _normalization_fixture("invalid_judgments.jsonl")

    issues = validate_normalization_status(summary, _config())

    assert "normalization_status_rejected:failed" in issues
    assert "normalization_invalid_judgments_present" in issues


def test_needs_work_normalization_summary_is_rejected_by_default() -> None:
    _, summary = _normalization_fixture("binary_collapsed_judgments.jsonl")

    issues = validate_normalization_status(summary, _config())

    assert "normalization_status_rejected:needs_work" in issues
    assert "normalization_status_not_valid:needs_work" in issues


def test_valid_normalization_summary_runs_with_missing_coverage_reported() -> None:
    normalized, normalization_summary = _normalization_fixture("valid_continuous_judgments.jsonl")

    summary = compute_v10_benchmark_metrics(
        _cases(),
        normalized,
        _config(),
        normalization_summary=normalization_summary,
    )

    assert summary.status == "needs_work"
    assert summary.matched_case_count == 12
    assert summary.missing_judgment_case_count == 288
    assert "partial_case_coverage" in summary.warnings


def test_tpr_fpr_and_ambiguous_metrics_on_controlled_fixture() -> None:
    cases = _cases()
    safe_cases = [case for case in cases if case.label == "safe"][:2]
    unsafe_cases = [case for case in cases if case.label == "unsafe"][:2]
    ambiguous_case = [case for case in cases if case.label == "ambiguous"][0]
    selected_cases = [*safe_cases, *unsafe_cases, ambiguous_case]
    judgments = [
        _judgment(safe_cases[0].case_id, "ALLOW", 0.1),
        _judgment(
            safe_cases[1].case_id,
            "BLOCK",
            0.9,
            phrase=safe_cases[1].active_contract_rule_summary,
        ),
        _judgment(
            unsafe_cases[0].case_id,
            "BLOCK",
            0.9,
            phrase=unsafe_cases[0].active_contract_rule_summary,
        ),
        _judgment(unsafe_cases[1].case_id, "ALLOW", 0.2),
        _judgment(ambiguous_case.case_id, "ESCALATE_FOR_APPROVAL", 0.5),
    ]

    summary = compute_v10_benchmark_metrics(selected_cases, judgments, _config())

    assert summary.true_positive_count == 1
    assert summary.false_positive_count == 1
    assert summary.true_negative_count == 1
    assert summary.false_negative_count == 1
    assert summary.ambiguous_count == 1
    assert summary.tpr == 0.5
    assert summary.fpr == 0.5
    assert summary.precision == 0.5
    assert summary.unsafe_false_safe_rate == 0.5
    assert summary.safe_false_interruption_rate == 0.5


def test_high_risk_citation_metric_computed() -> None:
    cases = _cases()
    safe_case = [case for case in cases if case.label == "safe"][0]
    unsafe_case = [case for case in cases if case.label == "unsafe"][0]
    judgments = [
        _judgment(
            safe_case.case_id,
            "BLOCK",
            0.91,
            phrase=safe_case.active_contract_rule_summary,
            method="exact_substring",
        ),
        _judgment(
            unsafe_case.case_id,
            "BLOCK",
            0.92,
            phrase="",
            method="unverified",
        ).model_copy(update={"normalization_status": "valid"}),
    ]

    summary = compute_v10_benchmark_metrics([safe_case, unsafe_case], judgments, _config())

    assert summary.high_risk_count == 2
    assert summary.high_risk_invalid_citation_count == 1
    assert summary.exact_or_normalized_citation_rate_high_risk == 0.5
    assert summary.status == "failed"
    assert "high_risk_invalid_citations_present" in summary.failed_targets


def test_receipts_are_emitted_and_validate() -> None:
    normalized, _ = _normalization_fixture("valid_continuous_judgments.jsonl")
    receipts = build_v10_benchmark_receipts(
        _cases(),
        normalized,
        _config(),
        config_hash=hash_file(CONFIG_PATH),
        normalization_manifest_hash="sha256:fixture",
    )

    issues = validate_v10_benchmark_receipts(receipts, expected_count=12)

    assert len(receipts) == 12
    assert issues == []
    assert receipts[0].receipt_hash.startswith("sha256:")


def test_receipt_validation_catches_tampering() -> None:
    normalized, _ = _normalization_fixture("valid_continuous_judgments.jsonl")
    receipts = build_v10_benchmark_receipts(
        _cases(),
        normalized,
        _config(),
        config_hash=hash_file(CONFIG_PATH),
        normalization_manifest_hash="sha256:fixture",
    )
    tampered = receipts[0].model_copy(update={"decision": "BLOCK"})

    issues = validate_v10_benchmark_receipts([tampered, *receipts[1:]], expected_count=12)

    assert "receipt_hash_mismatch" in issues


def test_outputs_include_manifest_report_and_no_reportability_claim(tmp_path: Path) -> None:
    normalized, normalization_summary = _normalization_fixture("valid_continuous_judgments.jsonl")
    receipts = build_v10_benchmark_receipts(
        _cases(),
        normalized,
        _config(),
        config_hash=hash_file(CONFIG_PATH),
        normalization_manifest_hash="sha256:fixture",
    )
    summary = compute_v10_benchmark_metrics(
        _cases(),
        normalized,
        _config(),
        normalization_summary=normalization_summary,
        receipt_count=len(receipts),
        receipt_validation_issue_count=0,
    )
    normalized_path, summary_path, manifest_path = _write_normalization_fixture(tmp_path)

    paths = write_v10_benchmark_outputs(
        summary=summary,
        receipts=receipts,
        cases=_cases(),
        normalized_judgments=normalized,
        config_path=CONFIG_PATH,
        input_cases_path=CASES_PATH,
        normalized_judgments_path=normalized_path,
        normalization_summary_path=summary_path,
        normalization_manifest_path=manifest_path,
        out_dir=tmp_path / "benchmark",
        generated_at="2026-06-06T00:00:00Z",
    )

    for path in paths:
        assert path.exists()
    manifest = json.loads(paths[2].read_text(encoding="utf-8"))
    assert manifest["manifest_hash"].startswith("sha256:")
    report = paths[3].read_text(encoding="utf-8")
    assert "What This Does Not Yet Prove" in report
    assert "no final v10 reportability claim" in report.lower()
    assert "evaluation receipts, not runtime authorization receipts" in report


def test_loading_normalized_judgments_and_summary_round_trip(tmp_path: Path) -> None:
    normalized_path, summary_path, _ = _write_normalization_fixture(tmp_path)

    normalized = load_normalized_judgments(normalized_path)
    summary = load_normalization_summary(summary_path)

    assert len(normalized) == 12
    assert summary.status == "complete"


def _judgment(
    case_id: str,
    decision: str,
    score: float,
    *,
    phrase: str = "",
    method: str = "unverified",
) -> V10NormalizedJudgment:
    return V10NormalizedJudgment(
        case_id=case_id,
        decision=decision,
        violation_probability=score,
        cited_contract_phrase=phrase,
        citation_verification_method=method,
        reason_codes=["fixture.reason"],
        uncertainty_reason=None,
        provider="fixture",
        model="controlled",
        raw_judgment_hash="sha256:fixture",
        normalization_status="valid",
        normalization_issues=[],
    )


def _write_normalization_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    normalized, summary = _normalization_fixture("valid_continuous_judgments.jsonl")
    paths = write_v10_normalization_outputs(
        normalized_judgments=normalized,
        summary=summary,
        config_path=NORMALIZATION_CONFIG_PATH,
        input_cases_path=CASES_PATH,
        raw_judgments_path=FIXTURE_DIR / "valid_continuous_judgments.jsonl",
        provider="fixture",
        model="valid-continuous",
        out_dir=tmp_path / "normalization",
        generated_at="2026-06-06T00:00:00Z",
    )
    normalized_path, _, summary_path, manifest_path, _ = paths
    return normalized_path, summary_path, manifest_path
