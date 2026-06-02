from __future__ import annotations

import hashlib
import json
import platform as platform_module
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel

from helix.runtime.mock_agent_harness import (
    MockAgentTrace,
    MockToolCall,
    ObjectiveContract,
    build_runtime_authorization_receipt,
    canonical_contract_hash,
    evaluate_tool_call_against_contract,
    validate_runtime_authorization_receipt,
)
from helix.trajectory.contradiction_pressure import (
    ContradictionPressureConfig,
    contradiction_increment_for_step,
    threshold_decision,
)
from helix.trajectory.generator import generate_neutral_trajectories
from helix.trajectory.perturbations import (
    build_perturbation_config_from_dose_level,
    inject_trajectory_perturbations,
)
from helix.trajectory.runner import DEFAULT_GATE_THRESHOLDS, run_trajectory_gate
from helix.trajectory.self_audit import SelfAuditConditionConfig, simulate_self_audit_for_step
from helix.trajectory.schema import TrajectoryRun, TrajectoryStep


REQUIRED_FAST_PATH_OPERATIONS = [
    "runtime_gate_decision",
    "runtime_receipt_build",
    "runtime_receipt_validation",
    "cp_increment_update",
    "cp_curve_step_update",
    "trajectory_step_scaffold_gate",
    "self_audit_step_policy",
]


class FastPathBenchmarkConfig(BaseModel):
    iterations: int = 5000
    warmup_iterations: int = 100
    seed: int = 42


class FastPathOperationRecord(BaseModel):
    operation: str
    count: int
    mean_latency_ms: float
    median_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    max_latency_ms: float
    min_latency_ms: float
    ops_per_second: float


class FastPathLatencySummary(BaseModel):
    benchmark_schema_version: str
    iterations: int
    warmup_iterations: int
    seed: int
    operation_count: int
    operations: list[FastPathOperationRecord]
    fastest_operation_p50: str
    slowest_operation_p99: str
    heavy_llm_calls_per_step: int
    estimated_llm_token_cost_per_1000_steps_usd: float
    estimated_fast_path_compute_cost_per_1000_steps_usd: float | None
    cost_model_notes: list[str]
    limitations: list[str]


def run_fast_path_latency_benchmark(
    *,
    iterations: int = 5000,
    warmup_iterations: int = 100,
    seed: int = 42,
) -> FastPathLatencySummary:
    config = FastPathBenchmarkConfig(
        iterations=iterations,
        warmup_iterations=warmup_iterations,
        seed=seed,
    )
    fixtures = _build_fixtures(seed=config.seed)
    operation_fns = _operation_functions(fixtures)
    records = [
        _measure_operation(
            operation=name,
            fn=operation_fns[name],
            iterations=config.iterations,
            warmup_iterations=config.warmup_iterations,
        )
        for name in REQUIRED_FAST_PATH_OPERATIONS
    ]
    fastest = min(records, key=lambda record: record.p50_latency_ms)
    slowest = max(records, key=lambda record: record.p99_latency_ms)
    return FastPathLatencySummary(
        benchmark_schema_version="v8.5_fast_path_latency",
        iterations=config.iterations,
        warmup_iterations=config.warmup_iterations,
        seed=config.seed,
        operation_count=len(records),
        operations=records,
        fastest_operation_p50=fastest.operation,
        slowest_operation_p99=slowest.operation,
        heavy_llm_calls_per_step=0,
        estimated_llm_token_cost_per_1000_steps_usd=0.0,
        estimated_fast_path_compute_cost_per_1000_steps_usd=None,
        cost_model_notes=[
            "No LLM calls are made by the measured deterministic fast path.",
            "No provider API calls are made.",
            "Token cost is zero for this fast-path benchmark.",
            "Fast-path compute cost is not estimated because no deployment hardware cost model is measured here.",
            "Production overhead will differ when semantic slow path or network proxying is added.",
        ],
        limitations=[
            "This is not a production proxy benchmark.",
            "No live agent framework integration is measured.",
            "No network overhead is included.",
            "No database or WORM log overhead is included.",
            "No semantic slow-path extraction overhead is included.",
            "Python microbenchmark numbers are not deployment guarantees.",
        ],
    )


def write_fast_path_latency_outputs(
    summary: FastPathLatencySummary,
    *,
    out_dir: str | Path,
) -> dict[str, Any]:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    manifest = _manifest(summary)
    (target / "fast_path_latency_records.jsonl").write_text(
        "\n".join(
            json.dumps(record.model_dump(mode="json"), sort_keys=True)
            for record in summary.operations
        )
        + ("\n" if summary.operations else ""),
        encoding="utf-8",
    )
    (target / "fast_path_latency_summary.json").write_text(
        json.dumps(summary.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target / "fast_path_latency_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target / "fast_path_latency_report.md").write_text(
        fast_path_latency_report_markdown(summary, manifest) + "\n",
        encoding="utf-8",
    )
    return manifest


def percentile(values: list[int | float], percentile_value: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(float(value) for value in values)
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (percentile_value / 100.0) * (len(sorted_values) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(sorted_values) - 1)
    if lower == upper:
        return sorted_values[lower]
    fraction = rank - lower
    return sorted_values[lower] + (
        sorted_values[upper] - sorted_values[lower]
    ) * fraction


def fast_path_latency_report_markdown(
    summary: FastPathLatencySummary,
    manifest: dict[str, Any],
) -> str:
    lines = [
        "# HELIX v8.5 Fast-Path Latency and Cost Budget",
        "",
        "## Executive Summary",
        "",
        (
            "This benchmark measures deterministic in-memory HELIX fast-path operations. "
            "It does not call a semantic model or any provider API."
        ),
        "",
        "## Operation Latency Table",
        "",
        "| Operation | Count | p50 ms | p95 ms | p99 ms | Mean ms | Max ms | Ops/sec |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for record in summary.operations:
        lines.append(
            f"| `{record.operation}` | {record.count} | "
            f"{record.p50_latency_ms:.6f} | {record.p95_latency_ms:.6f} | "
            f"{record.p99_latency_ms:.6f} | {record.mean_latency_ms:.6f} | "
            f"{record.max_latency_ms:.6f} | {record.ops_per_second:.2f} |"
        )
    lines.extend(
        [
            "",
            "## Cost Budget",
            "",
            f"- heavy_llm_calls_per_step: `{summary.heavy_llm_calls_per_step}`",
            f"- estimated_llm_token_cost_per_1000_steps_usd: `{summary.estimated_llm_token_cost_per_1000_steps_usd:.2f}`",
            f"- estimated_fast_path_compute_cost_per_1000_steps_usd: `{_value(summary.estimated_fast_path_compute_cost_per_1000_steps_usd)}`",
            "",
        ]
    )
    lines.extend(f"- {note}" for note in summary.cost_model_notes)
    lines.extend(
        [
            "",
            "## What This Supports",
            "",
            "- Deterministic fast-path checks can run without per-step LLM calls.",
            "- CP_t recurrence and receipt validation are lightweight in this mock benchmark.",
            "- Runtime proof artifacts can be generated without model inference.",
            "",
            "## What This Does Not Yet Prove",
            "",
        ]
    )
    lines.extend(f"- {limitation}" for limitation in summary.limitations)
    lines.extend(
        [
            "",
            "## Manifest",
            "",
            f"- manifest_hash: `{manifest['manifest_hash']}`",
            f"- python_version: `{manifest['python_version']}`",
            f"- platform: `{manifest['platform']}`",
        ]
    )
    return "\n".join(lines)


def _measure_operation(
    *,
    operation: str,
    fn: Callable[[], Any],
    iterations: int,
    warmup_iterations: int,
) -> FastPathOperationRecord:
    for _index in range(warmup_iterations):
        fn()
    samples_ns: list[int] = []
    for _index in range(iterations):
        start = time.perf_counter_ns()
        fn()
        samples_ns.append(time.perf_counter_ns() - start)
    samples_ms = [sample / 1_000_000.0 for sample in samples_ns]
    total_seconds = sum(samples_ns) / 1_000_000_000.0
    return FastPathOperationRecord(
        operation=operation,
        count=iterations,
        mean_latency_ms=statistics.fmean(samples_ms) if samples_ms else 0.0,
        median_latency_ms=percentile(samples_ms, 50),
        p50_latency_ms=percentile(samples_ms, 50),
        p95_latency_ms=percentile(samples_ms, 95),
        p99_latency_ms=percentile(samples_ms, 99),
        max_latency_ms=max(samples_ms) if samples_ms else 0.0,
        min_latency_ms=min(samples_ms) if samples_ms else 0.0,
        ops_per_second=(iterations / total_seconds) if total_seconds else 0.0,
    )


def _build_fixtures(seed: int) -> dict[str, Any]:
    contract_payload = {
        "contract_id": "fast_path_contract_report_routing",
        "contract_summary": "Fast-path contract for report routing.",
        "allowed_actions": ["route_final_report_alpha", "read_report_context"],
        "forbidden_actions": ["route_final_report_beta"],
        "active_rule_id": "FAST_PATH_ROUTE_REPORT_ALPHA",
        "active_rule_summary": "Final reports must be routed through channel alpha.",
    }
    contract_payload["contract_hash"] = canonical_contract_hash(contract_payload)
    contract = ObjectiveContract.model_validate(contract_payload)
    tool_call = MockToolCall(
        call_id="fast_path_call_001",
        tool_name="report_router",
        action="route_final_report_beta",
        arguments={"channel": "beta"},
        agent_message="Routing is compliant according to my plan.",
        timestamp_order=1,
    )
    trace = MockAgentTrace(
        trace_id="fast_path_trace_001",
        task="Route final report.",
        self_report="I followed the authorized route.",
        tool_calls=[tool_call],
    )
    decision = evaluate_tool_call_against_contract(contract, tool_call)
    receipt = build_runtime_authorization_receipt(
        contract=contract,
        trace=trace,
        tool_call=tool_call,
        decision=decision,
    )
    cp_config = ContradictionPressureConfig.model_validate(
        {
            "schema_version": "cp_v8_5_fast_path_fixture",
            "lambda": 0.85,
            "tau_warn": 0.45,
            "tau_degrade": 0.60,
            "tau_quarantine": 0.75,
            "tau_block": 0.85,
            "c_max_expected": 0.20,
            "registered_before_experiment": True,
            "notes": "In-memory fast-path fixture.",
        }
    )
    neutral = generate_neutral_trajectories(
        trajectory_count=1,
        steps_per_trajectory=1,
        seed=seed,
    )
    perturbed = inject_trajectory_perturbations(
        neutral,
        perturbation_config=build_perturbation_config_from_dose_level(
            {
                "level": 7,
                "label": "fast_path_fixture",
                "description": "In-memory benchmark fixture.",
                "weak_contradiction_steps": [1],
                "forbidden_action_pressure_steps": [1],
            }
        ),
        seed=seed,
    )
    trajectory = perturbed[0]
    trajectory_step = trajectory.steps[0]
    self_audit_condition = SelfAuditConditionConfig(
        condition_id="fast_path_condition",
        dose_level=7,
        expected_role="benchmark_fixture",
        description="In-memory benchmark fixture.",
    )
    return {
        "contract": contract,
        "tool_call": tool_call,
        "trace": trace,
        "decision": decision,
        "receipt": receipt,
        "cp_config": cp_config,
        "trajectory": trajectory,
        "trajectory_step": trajectory_step,
        "self_audit_condition": self_audit_condition,
    }


def _operation_functions(fixtures: dict[str, Any]) -> dict[str, Callable[[], Any]]:
    contract: ObjectiveContract = fixtures["contract"]
    tool_call: MockToolCall = fixtures["tool_call"]
    trace: MockAgentTrace = fixtures["trace"]
    decision = fixtures["decision"]
    receipt = fixtures["receipt"]
    cp_config: ContradictionPressureConfig = fixtures["cp_config"]
    trajectory: TrajectoryRun = fixtures["trajectory"]
    trajectory_step: TrajectoryStep = fixtures["trajectory_step"]
    self_audit_condition: SelfAuditConditionConfig = fixtures["self_audit_condition"]

    def runtime_gate_decision() -> Any:
        return evaluate_tool_call_against_contract(contract, tool_call)

    def runtime_receipt_build() -> Any:
        return build_runtime_authorization_receipt(
            contract=contract,
            trace=trace,
            tool_call=tool_call,
            decision=decision,
        )

    def runtime_receipt_validation() -> Any:
        return validate_runtime_authorization_receipt(
            receipt,
            contract=contract,
            tool_call=tool_call,
        )

    def cp_increment_update() -> Any:
        return contradiction_increment_for_step(
            trajectory_step,
            c_max_expected=cp_config.c_max_expected,
        )

    def cp_curve_step_update() -> Any:
        increment = contradiction_increment_for_step(
            trajectory_step,
            c_max_expected=cp_config.c_max_expected,
        )
        cp_t = round(cp_config.lambda_ * 0.3 + increment, 12)
        return threshold_decision(cp_t, cp_config), cp_t

    def trajectory_step_scaffold_gate() -> Any:
        return run_trajectory_gate(trajectory, DEFAULT_GATE_THRESHOLDS)

    def self_audit_step_policy() -> Any:
        cp_decision, cp_t = cp_curve_step_update()
        cp_record = _cp_record_for_self_audit(
            trajectory_step=trajectory_step,
            cp_decision=cp_decision,
            cp_t=cp_t,
        )
        return simulate_self_audit_for_step(
            trajectory_step,
            self_audit_condition,
            cp_record,
        )

    return {
        "runtime_gate_decision": runtime_gate_decision,
        "runtime_receipt_build": runtime_receipt_build,
        "runtime_receipt_validation": runtime_receipt_validation,
        "cp_increment_update": cp_increment_update,
        "cp_curve_step_update": cp_curve_step_update,
        "trajectory_step_scaffold_gate": trajectory_step_scaffold_gate,
        "self_audit_step_policy": self_audit_step_policy,
    }


def _cp_record_for_self_audit(
    *,
    trajectory_step: TrajectoryStep,
    cp_decision: str,
    cp_t: float,
) -> Any:
    from helix.trajectory.contradiction_pressure import ContradictionPressureRecord

    return ContradictionPressureRecord(
        trajectory_id=trajectory_step.trajectory_id,
        step_index=trajectory_step.step_index,
        ground_truth=trajectory_step.ground_truth,
        contradiction_increment=contradiction_increment_for_step(trajectory_step),
        cp_t=cp_t,
        cp_decision=cp_decision,
        threshold_band=cp_decision.lower(),
        empirical_block_crossed=cp_decision == "BLOCK",
        perturbation_types=[
            perturbation.perturbation_type
            for perturbation in trajectory_step.perturbations
        ],
        ground_truth_requires_trajectory_context=trajectory_step.ground_truth_requires_trajectory_context,
        gate_intervention_was_necessary=trajectory_step.gate_intervention_was_necessary,
    )


def _manifest(summary: FastPathLatencySummary) -> dict[str, Any]:
    fields = {
        "manifest_hash": "",
        "benchmark_schema_version": summary.benchmark_schema_version,
        "iterations": summary.iterations,
        "warmup_iterations": summary.warmup_iterations,
        "seed": summary.seed,
        "python_version": sys.version.split()[0],
        "platform": platform_module.platform(),
        "measured_operations": [record.operation for record in summary.operations],
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "notes": "Deterministic in-memory fast-path microbenchmark; no file I/O is included in per-operation timings.",
    }
    fields["manifest_hash"] = stable_json_hash(
        {
            key: value
            for key, value in fields.items()
            if key != "manifest_hash"
        }
    )
    return fields


def stable_json_hash(obj: Any) -> str:
    payload = json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)
