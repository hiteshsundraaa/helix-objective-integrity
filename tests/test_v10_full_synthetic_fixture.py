import importlib.util
import json
from pathlib import Path

from helix.benchmark.benchmark_receipts import hash_file
from helix.benchmark.v10_benchmark_runner import (
    build_v10_benchmark_receipts,
    compute_v10_benchmark_metrics,
    load_v10_benchmark_config,
    validate_v10_benchmark_receipts,
)
from helix.benchmark.v10_diagnostics import (
    bootstrap_v10_metric_cis,
    build_v10_diagnostics_summary,
    compute_v10_selectivity_baselines,
    load_v10_diagnostics_config,
)
from helix.benchmark.v10_judgment_normalization import (
    load_v10_normalization_config,
    normalize_v10_judgments,
)
from helix.benchmark.v10_synthetic_fixture import (
    generate_v10_full_synthetic_raw_judgments,
    load_v10_cases,
    load_v10_synthetic_fixture_config,
    write_v10_synthetic_fixture_outputs,
)


CASES_PATH = Path("benchmarks/v10_calibrated/v10_cases.jsonl")
SYNTHETIC_CONFIG_PATH = Path("configs/v10_full_synthetic_fixture.json")
NORMALIZATION_CONFIG_PATH = Path("configs/v10_judgment_normalization.json")
BENCHMARK_CONFIG_PATH = Path("configs/v10_benchmark_runner.json")
DIAGNOSTICS_CONFIG_PATH = Path("configs/v10_diagnostics.json")
INTEGRITY_CONFIG_PATH = Path("configs/benchmark_integrity_v1.json")
REPORTABILITY_CONFIG_PATH = Path("configs/v10_reportability_gate.json")


def test_v10_full_synthetic_config_loads_and_caps_evidence() -> None:
    config = load_v10_synthetic_fixture_config(SYNTHETIC_CONFIG_PATH)

    assert config.schema_version == "v10_full_synthetic_fixture_v1"
    assert config.registered_before_generation
    assert config.expected_pipeline.raw_judgment_count == 300
    assert config.evidence_policy.synthetic_fixture_evidence_level_cap == 3
    assert not config.evidence_policy.level_5_allowed
    assert config.provider == "synthetic_fixture"


def test_v10_full_synthetic_generation_is_deterministic_and_full_coverage() -> None:
    config = load_v10_synthetic_fixture_config(SYNTHETIC_CONFIG_PATH)
    cases = load_v10_cases(CASES_PATH)

    first = generate_v10_full_synthetic_raw_judgments(cases, config)
    second = generate_v10_full_synthetic_raw_judgments(cases, config)
    case_ids = {case.case_id for case in cases}
    generated_ids = [row["case_id"] for row in first]

    assert first == second
    assert len(first) == 300
    assert len(set(generated_ids)) == 300
    assert set(generated_ids) == case_ids
    assert all(row["provider"] == "synthetic_fixture" for row in first)
    assert all(row["model"] == "deterministic_target_band_sampler" for row in first)


def test_v10_full_synthetic_scores_stay_in_target_bands_and_avoid_binary() -> None:
    config = load_v10_synthetic_fixture_config(SYNTHETIC_CONFIG_PATH)
    cases = load_v10_cases(CASES_PATH)
    cases_by_id = {case.case_id: case for case in cases}
    rows = generate_v10_full_synthetic_raw_judgments(cases, config)

    for row in rows:
        score = row["violation_probability"]
        lower, upper = cases_by_id[row["case_id"]].target_score_range
        assert lower <= score <= upper
        assert score not in {0.0, 1.0}


def test_v10_full_synthetic_outputs_manifest_and_method_limits(tmp_path: Path) -> None:
    config = load_v10_synthetic_fixture_config(SYNTHETIC_CONFIG_PATH)
    cases = load_v10_cases(CASES_PATH)
    rows = generate_v10_full_synthetic_raw_judgments(cases, config)

    raw_path, summary_path, manifest_path, report_path = write_v10_synthetic_fixture_outputs(
        cases=cases,
        raw_judgments=rows,
        config=config,
        config_path=SYNTHETIC_CONFIG_PATH,
        input_cases_path=CASES_PATH,
        out_dir=tmp_path,
        generated_at="2026-06-06T00:00:00Z",
    )

    assert raw_path.exists()
    assert summary_path.exists()
    assert manifest_path.exists()
    assert report_path.exists()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = report_path.read_text(encoding="utf-8")
    assert summary["raw_judgment_count"] == 300
    assert summary["binary_score_fraction"] == 0.0
    assert manifest["manifest_hash"].startswith("sha256:")
    assert "What This Does Not Yet Prove" in report
    assert "not independent model evidence" in report


def test_v10_full_synthetic_normalizes_cleanly_without_score_collapse() -> None:
    _, _, normalized_summary = _normalized_fixture()

    assert normalized_summary.status == "complete"
    assert normalized_summary.raw_count == 300
    assert normalized_summary.valid_count == 300
    assert normalized_summary.invalid_count == 0
    assert normalized_summary.binary_score_fraction == 0.0
    assert not normalized_summary.score_collapse_detected


def test_v10_full_synthetic_benchmark_matches_all_cases_and_receipts() -> None:
    cases, normalized, normalized_summary = _normalized_fixture()
    benchmark_config = load_v10_benchmark_config(BENCHMARK_CONFIG_PATH)
    receipts = build_v10_benchmark_receipts(
        cases,
        normalized,
        benchmark_config,
        config_hash=hash_file(BENCHMARK_CONFIG_PATH),
        normalization_manifest_hash="sha256:test",
    )
    receipt_issues = validate_v10_benchmark_receipts(
        receipts,
        expected_count=len(cases),
    )
    benchmark_summary = compute_v10_benchmark_metrics(
        cases,
        normalized,
        benchmark_config,
        normalization_summary=normalized_summary,
        receipt_count=len(receipts),
        receipt_validation_issue_count=len(receipt_issues),
    )

    assert receipt_issues == []
    assert len(receipts) == 300
    assert benchmark_summary.status == "complete"
    assert benchmark_summary.matched_case_count == 300
    assert benchmark_summary.missing_judgment_case_count == 0
    assert benchmark_summary.receipt_validation_issue_count == 0


def test_v10_full_synthetic_diagnostics_include_selectivity_fields() -> None:
    cases, normalized, normalized_summary = _normalized_fixture()
    benchmark_config = load_v10_benchmark_config(BENCHMARK_CONFIG_PATH)
    diagnostics_config = load_v10_diagnostics_config(DIAGNOSTICS_CONFIG_PATH)
    receipts = build_v10_benchmark_receipts(
        cases,
        normalized,
        benchmark_config,
        config_hash=hash_file(BENCHMARK_CONFIG_PATH),
        normalization_manifest_hash="sha256:test",
    )
    benchmark_summary = compute_v10_benchmark_metrics(
        cases,
        normalized,
        benchmark_config,
        normalization_summary=normalized_summary,
        receipt_count=len(receipts),
        receipt_validation_issue_count=0,
    )
    ci = bootstrap_v10_metric_cis(receipts, benchmark_summary, diagnostics_config)
    selectivity = compute_v10_selectivity_baselines(receipts, diagnostics_config)
    diagnostics_summary = build_v10_diagnostics_summary(
        benchmark_run_path="synthetic",
        bootstrap_ci_path="synthetic/v10_bootstrap_ci.json",
        integrity_report_path="synthetic/v10_integrity_report.json",
        reportability_report_path="synthetic/v10_reportability_report.json",
        fixture_mode=True,
        benchmark_summary=benchmark_summary,
        config=diagnostics_config,
        ci_metrics=ci,
        selectivity_baselines=selectivity,
        integrity_report=None,
        reportability_report=None,
        warnings=[],
    )

    assert selectivity.selectivity_status == "complete"
    assert selectivity.selectivity_delta_vs_random is not None
    assert selectivity.selectivity_delta_vs_shuffled is not None
    assert diagnostics_summary.selectivity_baselines.selectivity_status == "complete"


def test_v10_full_synthetic_pipeline_caps_final_evidence_level(tmp_path: Path) -> None:
    runner = _load_pipeline_runner()

    summary = runner.run_full_synthetic_pipeline(
        cases_path=CASES_PATH,
        synthetic_config_path=SYNTHETIC_CONFIG_PATH,
        normalization_config_path=NORMALIZATION_CONFIG_PATH,
        benchmark_config_path=BENCHMARK_CONFIG_PATH,
        diagnostics_config_path=DIAGNOSTICS_CONFIG_PATH,
        integrity_config_path=INTEGRITY_CONFIG_PATH,
        reportability_config_path=REPORTABILITY_CONFIG_PATH,
        out_root=tmp_path,
    )

    assert summary["raw_judgment_count"] == 300
    assert summary["normalization_status"] == "complete"
    assert summary["benchmark_status"] == "complete"
    assert summary["matched_case_count"] == 300
    assert summary["missing_judgment_case_count"] == 0
    assert summary["score_collapse_detected"] is False
    assert summary["binary_score_fraction"] == 0.0
    assert summary["synthetic_fixture_evidence_level_cap"] == 3
    assert summary["final_evidence_level"] <= 3
    assert summary["level_5_allowed"] is False
    assert summary["selectivity_delta_vs_random"] is not None
    assert summary["selectivity_delta_vs_shuffled"] is not None
    assert (tmp_path / "full_synthetic_pipeline_summary.json").exists()
    report = (tmp_path / "full_synthetic_pipeline_report.md").read_text(encoding="utf-8")
    assert "What This Does Not Yet Prove" in report
    assert "Level 5 is never allowed" in report


def _normalized_fixture():
    config = load_v10_synthetic_fixture_config(SYNTHETIC_CONFIG_PATH)
    cases = load_v10_cases(CASES_PATH)
    raw_rows = generate_v10_full_synthetic_raw_judgments(cases, config)
    return (
        cases,
        *normalize_v10_judgments(
            raw_rows,
            cases,
            load_v10_normalization_config(NORMALIZATION_CONFIG_PATH),
            provider=config.provider,
            model=config.model,
        ),
    )


def _load_pipeline_runner():
    path = Path("examples/run_v10_full_synthetic_pipeline.py")
    spec = importlib.util.spec_from_file_location("run_v10_full_synthetic_pipeline", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module
