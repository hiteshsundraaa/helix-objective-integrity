import json
from pathlib import Path

from helix.performance.fast_path_latency import (
    REQUIRED_FAST_PATH_OPERATIONS,
    percentile,
    run_fast_path_latency_benchmark,
    write_fast_path_latency_outputs,
)


def test_percentile_helper_known_values() -> None:
    values = [1, 2, 3, 4, 5]

    assert percentile(values, 0) == 1
    assert percentile(values, 50) == 3
    assert percentile(values, 95) == 4.8
    assert percentile(values, 100) == 5


def test_benchmark_runs_with_small_iteration_count() -> None:
    summary = run_fast_path_latency_benchmark(
        iterations=7,
        warmup_iterations=2,
        seed=42,
    )

    assert summary.iterations == 7
    assert summary.warmup_iterations == 2
    assert summary.operation_count == len(REQUIRED_FAST_PATH_OPERATIONS)
    assert {record.operation for record in summary.operations} == set(REQUIRED_FAST_PATH_OPERATIONS)
    assert all(record.count == 7 for record in summary.operations)
    assert all(record.p50_latency_ms >= 0 for record in summary.operations)
    assert all(record.ops_per_second >= 0 for record in summary.operations)


def test_cost_budget_has_zero_llm_calls_and_token_cost() -> None:
    summary = run_fast_path_latency_benchmark(
        iterations=5,
        warmup_iterations=1,
        seed=42,
    )

    assert summary.heavy_llm_calls_per_step == 0
    assert summary.estimated_llm_token_cost_per_1000_steps_usd == 0.0
    assert summary.estimated_fast_path_compute_cost_per_1000_steps_usd is None


def test_output_files_and_manifest_are_written(tmp_path: Path) -> None:
    summary = run_fast_path_latency_benchmark(
        iterations=5,
        warmup_iterations=1,
        seed=42,
    )

    manifest = write_fast_path_latency_outputs(summary, out_dir=tmp_path)
    records = [
        json.loads(line)
        for line in (tmp_path / "fast_path_latency_records.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    manifest_payload = json.loads(
        (tmp_path / "fast_path_latency_manifest.json").read_text(encoding="utf-8")
    )

    assert (tmp_path / "fast_path_latency_summary.json").exists()
    assert (tmp_path / "fast_path_latency_report.md").exists()
    assert len(records) == len(REQUIRED_FAST_PATH_OPERATIONS)
    assert manifest["manifest_hash"].startswith("sha256:")
    assert manifest_payload["manifest_hash"] == manifest["manifest_hash"]
    assert manifest_payload["measured_operations"] == REQUIRED_FAST_PATH_OPERATIONS


def test_report_includes_non_proof_section(tmp_path: Path) -> None:
    summary = run_fast_path_latency_benchmark(
        iterations=5,
        warmup_iterations=1,
        seed=42,
    )

    write_fast_path_latency_outputs(summary, out_dir=tmp_path)
    report = (tmp_path / "fast_path_latency_report.md").read_text(encoding="utf-8")

    assert "What This Does Not Yet Prove" in report
    assert "not a production proxy benchmark" in report
    assert "No semantic slow-path extraction overhead is included." in report


def test_module_has_no_provider_specific_branching() -> None:
    source = Path("helix/performance/fast_path_latency.py").read_text(encoding="utf-8").lower()

    for forbidden in ["openai", "gpt", "gemini", "claude", "anthropic"]:
        assert forbidden not in source


def test_benchmark_does_not_require_network_or_api_keys() -> None:
    source = Path("helix/performance/fast_path_latency.py").read_text(encoding="utf-8").lower()

    for forbidden in ["requests", "urllib", "socket", "api_key", "api key"]:
        assert forbidden not in source
