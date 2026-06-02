from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from helix.trajectory.contradiction_pressure import (
    ContradictionPressureConfig,
    ContradictionPressureRecord,
    analyze_cp_for_trajectories,
)
from helix.trajectory.generator import generate_neutral_trajectories
from helix.trajectory.perturbations import (
    build_perturbation_config_from_dose_level,
    inject_trajectory_perturbations,
)
from helix.trajectory.runner import DEFAULT_GATE_THRESHOLDS, run_trajectory_batch
from helix.trajectory.schema import TrajectoryRun, build_manifest_hash


class DoseLevelResult(BaseModel):
    dose_level: int
    dose_label: str
    trajectory_count: int
    step_count: int
    ground_truth_counts: dict[str, int]
    cp_decision_counts: dict[str, int]
    max_cp_t: float
    mean_final_cp_t: float
    crossed_warn_count: int
    crossed_degrade_count: int
    crossed_quarantine_count: int
    crossed_block_count: int
    first_warn_crossing_step_mean: float | None
    first_block_crossing_step_mean: float | None
    empirical_T_star_by_trajectory: dict[str, int | None]
    block_crossing_rate: float
    context_required_count: int
    intervention_necessary_count: int


class DoseLadderSummary(BaseModel):
    dose_level_count: int
    monotonic_max_cp_t: bool
    monotonic_mean_final_cp_t: bool
    first_block_dose_level: int | None
    first_quarantine_dose_level: int | None
    first_degrade_dose_level: int | None
    first_warn_dose_level: int | None
    cp_config_hash: str
    dose_config_hash: str
    dose_results: list[DoseLevelResult]
    limitations: list[str]


def load_dose_ladder_config(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_dose_ladder(
    *,
    dose_config: dict[str, Any],
    cp_config: ContradictionPressureConfig,
    cp_config_hash: str = "",
    dose_config_hash: str = "",
) -> tuple[DoseLadderSummary, list[dict[str, Any]], list[dict[str, Any]]]:
    dose_results: list[DoseLevelResult] = []
    record_rows: list[dict[str, Any]] = []
    step_rows: list[dict[str, Any]] = []
    base_seed = int(dose_config["base_seed"])
    trajectory_count = int(dose_config["trajectory_count"])
    steps_per_trajectory = int(dose_config["steps_per_trajectory"])

    for dose_level_config in dose_config["dose_levels"]:
        level = int(dose_level_config["level"])
        neutral = generate_neutral_trajectories(
            trajectory_count=trajectory_count,
            steps_per_trajectory=steps_per_trajectory,
            seed=base_seed + level,
        )
        perturbed = inject_trajectory_perturbations(
            neutral,
            perturbation_config=build_perturbation_config_from_dose_level(dose_level_config),
            seed=base_seed + level,
        )
        gated = run_trajectory_batch(
            perturbed,
            gate_thresholds=DEFAULT_GATE_THRESHOLDS,
        )
        cp_records, cp_summary = analyze_cp_for_trajectories(gated, cp_config)
        result = _dose_level_result(
            dose_level_config=dose_level_config,
            trajectories=gated,
            cp_records=cp_records,
            cp_summary=cp_summary.model_dump(mode="json", by_alias=True),
            cp_config=cp_config,
        )
        dose_results.append(result)
        record_rows.append(result.model_dump(mode="json"))
        step_rows.extend(
            _step_rows(
                dose_level_config=dose_level_config,
                trajectories=gated,
                cp_records=cp_records,
            )
        )

    summary = DoseLadderSummary(
        dose_level_count=len(dose_results),
        monotonic_max_cp_t=_is_monotonic(
            [result.max_cp_t for result in dose_results]
        ),
        monotonic_mean_final_cp_t=_is_monotonic(
            [result.mean_final_cp_t for result in dose_results]
        ),
        first_warn_dose_level=_first_dose_level(
            dose_results,
            "crossed_warn_count",
        ),
        first_degrade_dose_level=_first_dose_level(
            dose_results,
            "crossed_degrade_count",
        ),
        first_quarantine_dose_level=_first_dose_level(
            dose_results,
            "crossed_quarantine_count",
        ),
        first_block_dose_level=_first_dose_level(
            dose_results,
            "crossed_block_count",
        ),
        cp_config_hash=cp_config_hash,
        dose_config_hash=dose_config_hash,
        dose_results=dose_results,
        limitations=_limitations(),
    )
    return summary, record_rows, step_rows


def write_dose_ladder_outputs(
    *,
    dose_config: dict[str, Any],
    cp_config: ContradictionPressureConfig,
    out_dir: str | Path,
    dose_config_path: str | Path,
    cp_config_path: str | Path,
) -> DoseLadderSummary:
    dose_hash = stable_file_hash(dose_config_path)
    cp_hash = stable_file_hash(cp_config_path)
    summary, record_rows, step_rows = run_dose_ladder(
        dose_config=dose_config,
        cp_config=cp_config,
        dose_config_hash=dose_hash,
        cp_config_hash=cp_hash,
    )
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    manifest = _manifest(
        dose_config=dose_config,
        dose_config_path=dose_config_path,
        dose_config_hash=dose_hash,
        cp_config_path=cp_config_path,
        cp_config_hash=cp_hash,
    )
    (target / "dose_ladder_records.jsonl").write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in record_rows)
        + ("\n" if record_rows else ""),
        encoding="utf-8",
    )
    (target / "dose_ladder_steps.jsonl").write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in step_rows)
        + ("\n" if step_rows else ""),
        encoding="utf-8",
    )
    (target / "dose_ladder_summary.json").write_text(
        json.dumps(summary.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target / "dose_ladder_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target / "dose_ladder_report.md").write_text(
        dose_ladder_report_markdown(summary, manifest) + "\n",
        encoding="utf-8",
    )
    return summary


def stable_file_hash(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def dose_ladder_report_markdown(
    summary: DoseLadderSummary,
    manifest: dict[str, Any],
) -> str:
    lines = [
        "# HELIX v8.3 Perturbation Dose Ladder",
        "",
        "The CP configuration was fixed and pre-registered in `configs/cp_config_v8.json`; thresholds are not tuned for this run.",
        "Dose levels are controlled synthetic perturbation configs applied to neutral trajectories.",
        "",
        "## Summary",
        "",
        f"- dose_level_count: `{summary.dose_level_count}`",
        f"- first_warn_dose_level: `{_value(summary.first_warn_dose_level)}`",
        f"- first_degrade_dose_level: `{_value(summary.first_degrade_dose_level)}`",
        f"- first_quarantine_dose_level: `{_value(summary.first_quarantine_dose_level)}`",
        f"- first_block_dose_level: `{_value(summary.first_block_dose_level)}`",
        f"- monotonic_max_cp_t: `{str(summary.monotonic_max_cp_t).lower()}`",
        f"- monotonic_mean_final_cp_t: `{str(summary.monotonic_mean_final_cp_t).lower()}`",
        f"- manifest_hash: `{manifest['manifest_hash']}`",
        "",
        "## Dose Table",
        "",
        "| Dose | Label | Max CP_t | Mean Final CP_t | Warn | Degrade | Quarantine | Block |",
        "|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for result in summary.dose_results:
        lines.append(
            f"| {result.dose_level} | `{result.dose_label}` | "
            f"{result.max_cp_t:.6f} | {result.mean_final_cp_t:.6f} | "
            f"{result.crossed_warn_count} | {result.crossed_degrade_count} | "
            f"{result.crossed_quarantine_count} | {result.crossed_block_count} |"
        )
    lines.extend(
        [
            "",
            "## Monotonicity Notes",
            "",
            "- Monotonicity is reported, not forced. Discrete deterministic perturbation placement can create imperfect monotonicity.",
            "",
            "## Limitations",
            "",
        ]
    )
    lines.extend(f"- {limitation}" for limitation in summary.limitations)
    return "\n".join(lines)


def _dose_level_result(
    *,
    dose_level_config: dict[str, Any],
    trajectories: list[TrajectoryRun],
    cp_records: list[ContradictionPressureRecord],
    cp_summary: dict[str, Any],
    cp_config: ContradictionPressureConfig,
) -> DoseLevelResult:
    steps = [step for trajectory in trajectories for step in trajectory.steps]
    ground_truth_counts = Counter(step.ground_truth for step in steps)
    first_warn_steps = _first_crossing_steps(cp_records, cp_config.tau_warn)
    first_block_steps = _first_crossing_steps(cp_records, cp_config.tau_block)
    return DoseLevelResult(
        dose_level=int(dose_level_config["level"]),
        dose_label=str(dose_level_config["label"]),
        trajectory_count=len(trajectories),
        step_count=len(steps),
        ground_truth_counts=dict(sorted(ground_truth_counts.items())),
        cp_decision_counts=cp_summary["decision_counts"],
        max_cp_t=cp_summary["max_cp_t"],
        mean_final_cp_t=cp_summary["mean_final_cp_t"],
        crossed_warn_count=_crossed_count(cp_records, cp_config.tau_warn),
        crossed_degrade_count=_crossed_count(cp_records, cp_config.tau_degrade),
        crossed_quarantine_count=_crossed_count(cp_records, cp_config.tau_quarantine),
        crossed_block_count=_crossed_count(cp_records, cp_config.tau_block),
        first_warn_crossing_step_mean=_mean(list(first_warn_steps.values())),
        first_block_crossing_step_mean=_mean(list(first_block_steps.values())),
        empirical_T_star_by_trajectory=cp_summary["empirical_T_star_by_trajectory"],
        block_crossing_rate=_rate(
            _crossed_count(cp_records, cp_config.tau_block),
            len(trajectories),
        ),
        context_required_count=sum(
            step.ground_truth_requires_trajectory_context for step in steps
        ),
        intervention_necessary_count=sum(
            step.gate_intervention_was_necessary for step in steps
        ),
    )


def _step_rows(
    *,
    dose_level_config: dict[str, Any],
    trajectories: list[TrajectoryRun],
    cp_records: list[ContradictionPressureRecord],
) -> list[dict[str, Any]]:
    step_lookup = {
        (step.trajectory_id, step.step_index): step
        for trajectory in trajectories
        for step in trajectory.steps
    }
    rows = []
    for record in cp_records:
        step = step_lookup[(record.trajectory_id, record.step_index)]
        rows.append(
            {
                "dose_level": dose_level_config["level"],
                "dose_label": dose_level_config["label"],
                **record.model_dump(mode="json"),
                "helix_decision": step.helix_decision,
                "reason_codes": step.reason_codes,
            }
        )
    return rows


def _manifest(
    *,
    dose_config: dict[str, Any],
    dose_config_path: str | Path,
    dose_config_hash: str,
    cp_config_path: str | Path,
    cp_config_hash: str,
) -> dict[str, Any]:
    fields = {
        "manifest_hash": "",
        "dose_config_path": str(dose_config_path),
        "dose_config_hash": dose_config_hash,
        "cp_config_path": str(cp_config_path),
        "cp_config_hash": cp_config_hash,
        "base_seed": dose_config["base_seed"],
        "trajectory_count": dose_config["trajectory_count"],
        "steps_per_trajectory": dose_config["steps_per_trajectory"],
        "dose_level_count": len(dose_config["dose_levels"]),
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    fields["manifest_hash"] = build_manifest_hash(fields)
    return fields


def _first_dose_level(
    results: list[DoseLevelResult],
    field_name: str,
) -> int | None:
    for result in results:
        if getattr(result, field_name) > 0:
            return result.dose_level
    return None


def _first_crossing_steps(
    records: list[ContradictionPressureRecord],
    threshold: float,
) -> dict[str, int]:
    first_steps: dict[str, int] = {}
    for record in sorted(records, key=lambda item: (item.trajectory_id, item.step_index)):
        if record.cp_t >= threshold and record.trajectory_id not in first_steps:
            first_steps[record.trajectory_id] = record.step_index
    return first_steps


def _crossed_count(
    records: list[ContradictionPressureRecord],
    threshold: float,
) -> int:
    return len(
        {
            record.trajectory_id
            for record in records
            if record.cp_t >= threshold
        }
    )


def _is_monotonic(values: list[float]) -> bool:
    return all(current >= previous for previous, current in zip(values, values[1:]))


def _mean(values: list[int | float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _rate(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0.0
    return float(numerator) / float(denominator)


def _limitations() -> list[str]:
    return [
        "Deterministic scaffold trajectories are used.",
        "No live or stochastic agent behavior is measured yet.",
        "No self-audit baseline yet.",
        "No drift halflife yet.",
        "Dose levels are controlled synthetic perturbations.",
        "CP increment policy is deterministic in v8.2/v8.3.",
    ]


def _value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)
