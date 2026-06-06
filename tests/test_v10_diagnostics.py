import json
from pathlib import Path

from helix.benchmark.benchmark_receipts import hash_file
from helix.benchmark.v10_benchmark_runner import (
    build_v10_benchmark_receipts,
    compute_v10_benchmark_metrics,
    write_v10_benchmark_outputs,
)
from helix.benchmark.v10_diagnostics import (
    bootstrap_v10_metric_cis,
    build_v10_diagnostics_summary,
    compute_internal_matched_random_selectivity,
    compute_shuffled_label_selectivity,
    compute_v10_selectivity_baselines,
    load_v10_benchmark_receipts,
    load_v10_benchmark_summary,
    load_v10_diagnostics_config,
    run_v10_integrity_diagnostic,
    run_v10_reportability_diagnostic,
    write_v10_diagnostics_outputs,
)
from helix.benchmark.v10_benchmark_runner import load_v10_benchmark_config, load_v10_cases
from helix.benchmark.v10_judgment_normalization import (
    load_raw_judgments,
    load_v10_normalization_config,
    normalize_v10_judgments,
    write_v10_normalization_outputs,
)


DIAGNOSTICS_CONFIG_PATH = Path("configs/v10_diagnostics.json")
BENCHMARK_CONFIG_PATH = Path("configs/v10_benchmark_runner.json")
NORMALIZATION_CONFIG_PATH = Path("configs/v10_judgment_normalization.json")
INTEGRITY_CONFIG_PATH = Path("configs/benchmark_integrity_v1.json")
REPORTABILITY_CONFIG_PATH = Path("configs/v10_reportability_gate.json")
CASES_PATH = Path("benchmarks/v10_calibrated/v10_cases.jsonl")
RAW_FIXTURE_PATH = Path("tests/fixtures/v10_judgments/valid_continuous_judgments.jsonl")
BALANCED_FIXTURE_PATH = Path("tests/fixtures/v10_judgments/balanced_continuous_judgments.jsonl")


def test_v10_diagnostics_config_loads() -> None:
    config = load_v10_diagnostics_config(DIAGNOSTICS_CONFIG_PATH)

    assert config.schema_version == "v10_diagnostics_v1"
    assert config.registered_before_real_judgment_runs
    assert config.bootstrap_seed == 42
    assert "tpr" in config.metrics_for_ci
    assert config.fixture_mode_must_not_claim_reportability


def test_bootstrap_cis_are_deterministic_and_small_sample_warns() -> None:
    summary, receipts = _benchmark_fixture()
    config = load_v10_diagnostics_config(DIAGNOSTICS_CONFIG_PATH)

    ci_a = bootstrap_v10_metric_cis(receipts, summary, config)
    ci_b = bootstrap_v10_metric_cis(receipts, summary, config)

    assert ci_a == ci_b
    assert ci_a["fpr"].warning == "small_sample_ci_unstable"
    assert ci_a["fpr"].valid_resample_count > 0


def test_zero_denominator_resamples_are_handled() -> None:
    summary, receipts = _benchmark_fixture()
    config = load_v10_diagnostics_config(DIAGNOSTICS_CONFIG_PATH)

    cis = bootstrap_v10_metric_cis(receipts, summary, config)

    assert cis["tpr"].valid_resample_count == 0
    assert cis["tpr"].lower is None
    assert cis["tpr"].upper is None
    assert "zero_valid_resamples" in (cis["tpr"].warning or "")


def test_matched_random_selectivity_is_deterministic() -> None:
    _, receipts = _benchmark_fixture(BALANCED_FIXTURE_PATH)
    config = load_v10_diagnostics_config(DIAGNOSTICS_CONFIG_PATH)

    first = compute_internal_matched_random_selectivity(
        receipts,
        budget=config.selectivity_budget,
        positive_labels=config.positive_labels_for_selectivity,
        n_trials=config.selectivity_baseline_trials,
        seed=config.selectivity_baseline_seed,
    )
    second = compute_internal_matched_random_selectivity(
        receipts,
        budget=config.selectivity_budget,
        positive_labels=config.positive_labels_for_selectivity,
        n_trials=config.selectivity_baseline_trials,
        seed=config.selectivity_baseline_seed,
    )

    assert first == second
    assert first["selectivity_delta_vs_random"] is not None


def test_shuffled_label_selectivity_is_deterministic() -> None:
    _, receipts = _benchmark_fixture(BALANCED_FIXTURE_PATH)
    config = load_v10_diagnostics_config(DIAGNOSTICS_CONFIG_PATH)

    first = compute_shuffled_label_selectivity(
        receipts,
        budget=config.selectivity_budget,
        positive_labels=config.positive_labels_for_selectivity,
        n_trials=config.selectivity_baseline_trials,
        seed=config.selectivity_baseline_seed,
    )
    second = compute_shuffled_label_selectivity(
        receipts,
        budget=config.selectivity_budget,
        positive_labels=config.positive_labels_for_selectivity,
        n_trials=config.selectivity_baseline_trials,
        seed=config.selectivity_baseline_seed,
    )

    assert first == second
    assert first["selectivity_delta_vs_shuffled"] is not None


def test_zero_positive_fixture_returns_unavailable_selectivity() -> None:
    _, receipts = _benchmark_fixture(RAW_FIXTURE_PATH)
    config = load_v10_diagnostics_config(DIAGNOSTICS_CONFIG_PATH)

    selectivity = compute_v10_selectivity_baselines(receipts, config)

    assert selectivity.selectivity_status == "unavailable_no_positive_labels"
    assert selectivity.selectivity_delta_vs_random is None
    assert selectivity.selectivity_delta_vs_shuffled is None
    assert "selectivity_unavailable_no_positive_labels" in selectivity.selectivity_warnings


def test_balanced_fixture_returns_non_null_selectivity_deltas() -> None:
    _, receipts = _benchmark_fixture(BALANCED_FIXTURE_PATH)
    config = load_v10_diagnostics_config(DIAGNOSTICS_CONFIG_PATH)

    selectivity = compute_v10_selectivity_baselines(receipts, config)

    assert selectivity.selectivity_status == "complete"
    assert selectivity.selectivity_positive_label_count == 6
    assert selectivity.selectivity_delta_vs_random is not None
    assert selectivity.selectivity_delta_vs_shuffled is not None


def test_integrity_diagnostic_writes_report(tmp_path: Path) -> None:
    _, receipts = _benchmark_fixture()

    report, json_path, markdown_path, warnings = run_v10_integrity_diagnostic(
        cases_path=CASES_PATH,
        receipts=receipts,
        integrity_config_path=INTEGRITY_CONFIG_PATH,
        out_dir=tmp_path,
    )

    assert report is not None
    assert json_path is not None and json_path.exists()
    assert markdown_path is not None and markdown_path.exists()
    assert (tmp_path / "v10_high_overlap_cases.jsonl").exists()
    assert isinstance(report.integrity_passed, bool)
    assert warnings == []


def test_reportability_diagnostic_fails_for_incomplete_fixture(tmp_path: Path) -> None:
    summary, receipts = _benchmark_fixture(BALANCED_FIXTURE_PATH)
    config = load_v10_diagnostics_config(DIAGNOSTICS_CONFIG_PATH)
    ci = bootstrap_v10_metric_cis(receipts, summary, config)
    selectivity = compute_v10_selectivity_baselines(receipts, config)
    integrity_report, _, _, _ = run_v10_integrity_diagnostic(
        cases_path=CASES_PATH,
        receipts=receipts,
        integrity_config_path=INTEGRITY_CONFIG_PATH,
        out_dir=tmp_path,
    )

    reportability, json_path, markdown_path = run_v10_reportability_diagnostic(
        integrity_report=integrity_report,
        benchmark_summary=summary,
        bootstrap_ci={
            "schema_version": "v10_bootstrap_ci_v1",
            "metrics": {key: value.model_dump(mode="json") for key, value in ci.items()},
        },
        reportability_config_path=REPORTABILITY_CONFIG_PATH,
        out_dir=tmp_path,
        receipts=receipts,
        selectivity_baselines=selectivity,
    )

    assert json_path.exists()
    assert markdown_path.exists()
    assert not reportability.reportability_passed
    assert reportability.evidence_level_allowed <= 3
    assert "missing_selectivity_delta_vs_random" not in reportability.failed_criteria
    assert "missing_selectivity_delta_vs_shuffled" not in reportability.failed_criteria


def test_diagnostics_outputs_manifest_report_and_fixture_limitations(tmp_path: Path) -> None:
    benchmark_dir, summary, receipts = _write_benchmark_fixture(tmp_path)
    config = load_v10_diagnostics_config(DIAGNOSTICS_CONFIG_PATH)
    ci = bootstrap_v10_metric_cis(receipts, summary, config)
    selectivity = compute_v10_selectivity_baselines(receipts, config)
    bootstrap_payload = {
        "schema_version": "v10_bootstrap_ci_v1",
        "confidence_level": config.confidence_level,
        "resamples": config.bootstrap_resamples,
        "metrics": {key: value.model_dump(mode="json") for key, value in ci.items()},
    }
    integrity_report, integrity_path, _, warnings = run_v10_integrity_diagnostic(
        cases_path=CASES_PATH,
        receipts=receipts,
        integrity_config_path=INTEGRITY_CONFIG_PATH,
        out_dir=benchmark_dir,
    )
    reportability, reportability_path, _ = run_v10_reportability_diagnostic(
        integrity_report=integrity_report,
        benchmark_summary=summary,
        bootstrap_ci=bootstrap_payload,
        reportability_config_path=REPORTABILITY_CONFIG_PATH,
        out_dir=benchmark_dir,
        receipts=receipts,
        selectivity_baselines=selectivity,
    )
    diagnostics_summary = build_v10_diagnostics_summary(
        benchmark_run_path=benchmark_dir,
        bootstrap_ci_path=benchmark_dir / "v10_bootstrap_ci.json",
        integrity_report_path=integrity_path or benchmark_dir / "v10_integrity_report.json",
        reportability_report_path=reportability_path,
        fixture_mode=True,
        benchmark_summary=summary,
        config=config,
        ci_metrics=ci,
        selectivity_baselines=selectivity,
        integrity_report=integrity_report,
        reportability_report=reportability,
        warnings=warnings,
    )

    paths = write_v10_diagnostics_outputs(
        benchmark_run_dir=benchmark_dir,
        diagnostics_config_path=DIAGNOSTICS_CONFIG_PATH,
        benchmark_summary_path=benchmark_dir / "v10_benchmark_summary.json",
        benchmark_receipts_path=benchmark_dir / "v10_benchmark_receipts.jsonl",
        benchmark_manifest_path=benchmark_dir / "v10_benchmark_manifest.json",
        summary=diagnostics_summary,
        bootstrap_ci=bootstrap_payload,
        generated_at="2026-06-06T00:00:00Z",
    )

    for path in paths:
        assert path.exists()
    manifest = json.loads(paths[2].read_text(encoding="utf-8"))
    assert manifest["manifest_hash"].startswith("sha256:")
    report = paths[3].read_text(encoding="utf-8")
    assert "What This Does Not Yet Prove" in report
    assert "Selectivity Baselines" in report
    assert "No live model APIs" in report
    assert "no final v10 reportability claim" in report.lower()
    assert diagnostics_summary.diagnostics_status == "needs_work"
    assert diagnostics_summary.selectivity_baselines.selectivity_status == "unavailable_no_positive_labels"
    assert "small_sample_ci_unstable" in diagnostics_summary.warnings


def test_loading_diagnostics_benchmark_artifacts_round_trip(tmp_path: Path) -> None:
    benchmark_dir, _, _ = _write_benchmark_fixture(tmp_path)

    summary = load_v10_benchmark_summary(benchmark_dir / "v10_benchmark_summary.json")
    receipts = load_v10_benchmark_receipts(benchmark_dir / "v10_benchmark_receipts.jsonl")

    assert summary.matched_case_count == 12
    assert len(receipts) == 12


def _benchmark_fixture(raw_fixture_path: Path = RAW_FIXTURE_PATH):
    cases = load_v10_cases(CASES_PATH)
    normalized, normalization_summary = _normalization_fixture(raw_fixture_path)
    benchmark_config = load_v10_benchmark_config(BENCHMARK_CONFIG_PATH)
    receipts = build_v10_benchmark_receipts(
        cases,
        normalized,
        benchmark_config,
        config_hash=hash_file(BENCHMARK_CONFIG_PATH),
        normalization_manifest_hash="sha256:test",
    )
    summary = compute_v10_benchmark_metrics(
        cases,
        normalized,
        benchmark_config,
        normalization_summary=normalization_summary,
        receipt_count=len(receipts),
        receipt_validation_issue_count=0,
    )
    return summary, receipts


def _normalization_fixture(raw_fixture_path: Path = RAW_FIXTURE_PATH):
    return normalize_v10_judgments(
        load_raw_judgments(raw_fixture_path),
        load_v10_cases(CASES_PATH),
        load_v10_normalization_config(NORMALIZATION_CONFIG_PATH),
        provider="fixture",
        model="valid-continuous",
    )


def _write_benchmark_fixture(tmp_path: Path, raw_fixture_path: Path = RAW_FIXTURE_PATH):
    cases = load_v10_cases(CASES_PATH)
    normalized, normalization_summary = _normalization_fixture(raw_fixture_path)
    normalization_paths = write_v10_normalization_outputs(
        normalized_judgments=normalized,
        summary=normalization_summary,
        config_path=NORMALIZATION_CONFIG_PATH,
        input_cases_path=CASES_PATH,
        raw_judgments_path=raw_fixture_path,
        provider="fixture",
        model="valid-continuous",
        out_dir=tmp_path / "normalization",
        generated_at="2026-06-06T00:00:00Z",
    )
    normalized_path, _, normalization_summary_path, normalization_manifest_path, _ = normalization_paths
    benchmark_config = load_v10_benchmark_config(BENCHMARK_CONFIG_PATH)
    receipts = build_v10_benchmark_receipts(
        cases,
        normalized,
        benchmark_config,
        config_hash=hash_file(BENCHMARK_CONFIG_PATH),
        normalization_manifest_hash=hash_file(normalization_manifest_path),
    )
    summary = compute_v10_benchmark_metrics(
        cases,
        normalized,
        benchmark_config,
        normalization_summary=normalization_summary,
        receipt_count=len(receipts),
        receipt_validation_issue_count=0,
    )
    benchmark_dir = tmp_path / "benchmark"
    write_v10_benchmark_outputs(
        summary=summary,
        receipts=receipts,
        cases=cases,
        normalized_judgments=normalized,
        config_path=BENCHMARK_CONFIG_PATH,
        input_cases_path=CASES_PATH,
        normalized_judgments_path=normalized_path,
        normalization_summary_path=normalization_summary_path,
        normalization_manifest_path=normalization_manifest_path,
        out_dir=benchmark_dir,
        generated_at="2026-06-06T00:00:00Z",
    )
    return benchmark_dir, summary, receipts
