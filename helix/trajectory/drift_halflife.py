from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from typing import Any

from pydantic import BaseModel

from helix.trajectory.generator import generate_neutral_trajectories
from helix.trajectory.perturbations import (
    build_perturbation_config_from_dose_level,
    inject_trajectory_perturbations,
)
from helix.trajectory.runner import DEFAULT_GATE_THRESHOLDS, run_trajectory_batch
from helix.trajectory.schema import TrajectoryRun, TrajectoryStep, build_manifest_hash


SAFE_STEP_RECOVERY = 0.02


class DriftHalflifeConditionConfig(BaseModel):
    condition_id: str
    dose_level: int
    expected_role: str


class DriftHalflifeSimilarityProxy(BaseModel):
    method: str
    base_objective_tokens: list[str]
    drift_token_penalties: dict[str, float]


class DriftHalflifeConfig(BaseModel):
    schema_version: str
    registered_before_experiment: bool
    base_seed: int
    trajectory_count: int
    steps_per_trajectory: int
    theta_similarity: float
    conditions: list[DriftHalflifeConditionConfig]
    similarity_proxy: DriftHalflifeSimilarityProxy
    notes: str


class DriftHalflifeStepRecord(BaseModel):
    condition_id: str
    dose_level: int
    trajectory_id: str
    step_index: int
    perturbation_types: list[str]
    objective_similarity: float
    theta_similarity: float
    halflife_crossed_at_step: bool
    ground_truth: str
    ground_truth_requires_trajectory_context: bool
    gate_intervention_was_necessary: bool


class DriftHalflifeConditionSummary(BaseModel):
    condition_id: str
    dose_level: int
    trajectory_count: int
    step_count: int
    halflife_crossing_count: int
    halflife_crossing_rate: float
    mean_halflife_step: float | None
    median_halflife_step: float | None
    final_similarity_mean: float
    final_similarity_min: float
    final_similarity_max: float


class DriftHalflifeSummary(BaseModel):
    condition_count: int
    theta_similarity: float
    clean_halflife_crossing_rate: float
    contaminated_halflife_crossing_rate: float
    halflife_crossing_lift: float
    clean_final_similarity_mean: float
    contaminated_final_similarity_mean: float
    final_similarity_drop_contaminated_vs_clean: float
    condition_summaries: list[DriftHalflifeConditionSummary]
    limitations: list[str]


def load_drift_halflife_config(path: str | Path) -> DriftHalflifeConfig:
    return DriftHalflifeConfig.model_validate(
        json.loads(Path(path).read_text(encoding="utf-8"))
    )


def objective_similarity_for_step(
    step: TrajectoryStep,
    previous_similarity: float,
    config: DriftHalflifeConfig,
) -> float:
    perturbation_types = [
        perturbation.perturbation_type
        for perturbation in step.perturbations
    ]
    penalties = config.similarity_proxy.drift_token_penalties
    penalty = sum(penalties.get(perturbation_type, 0.0) for perturbation_type in perturbation_types)
    if penalty > 0:
        next_similarity = previous_similarity - penalty
    elif step.ground_truth == "safe" and not _has_real_perturbation(perturbation_types):
        next_similarity = previous_similarity + SAFE_STEP_RECOVERY
    else:
        next_similarity = previous_similarity
    return round(min(1.0, max(0.0, next_similarity)), 12)


def run_drift_halflife_analysis(
    *,
    drift_config: DriftHalflifeConfig,
    dose_config: dict[str, Any],
) -> tuple[DriftHalflifeSummary, list[DriftHalflifeStepRecord]]:
    dose_levels_by_id = {
        int(item["level"]): item
        for item in dose_config["dose_levels"]
    }
    all_records: list[DriftHalflifeStepRecord] = []
    condition_summaries: list[DriftHalflifeConditionSummary] = []

    for condition in drift_config.conditions:
        dose_level_config = dose_levels_by_id[condition.dose_level]
        seed = int(drift_config.base_seed) + int(condition.dose_level)
        neutral = generate_neutral_trajectories(
            trajectory_count=drift_config.trajectory_count,
            steps_per_trajectory=drift_config.steps_per_trajectory,
            seed=seed,
        )
        perturbed = inject_trajectory_perturbations(
            neutral,
            perturbation_config=build_perturbation_config_from_dose_level(dose_level_config),
            seed=seed,
        )
        gated = run_trajectory_batch(
            perturbed,
            gate_thresholds=DEFAULT_GATE_THRESHOLDS,
        )
        condition_records, final_similarities, halflife_steps = _condition_records(
            condition=condition,
            trajectories=gated,
            config=drift_config,
        )
        all_records.extend(condition_records)
        condition_summaries.append(
            _condition_summary(
                condition=condition,
                step_count=len(condition_records),
                final_similarities=final_similarities,
                halflife_steps=halflife_steps,
            )
        )

    clean_summaries = [
        summary
        for summary in condition_summaries
        if summary.dose_level == 0
    ]
    contaminated_summaries = [
        summary
        for summary in condition_summaries
        if summary.dose_level > 0
    ]
    clean_crossing_rate = _weighted_crossing_rate(clean_summaries)
    contaminated_crossing_rate = _weighted_crossing_rate(contaminated_summaries)
    clean_final_mean = _weighted_final_similarity_mean(clean_summaries)
    contaminated_final_mean = _weighted_final_similarity_mean(contaminated_summaries)
    summary = DriftHalflifeSummary(
        condition_count=len(condition_summaries),
        theta_similarity=drift_config.theta_similarity,
        clean_halflife_crossing_rate=clean_crossing_rate,
        contaminated_halflife_crossing_rate=contaminated_crossing_rate,
        halflife_crossing_lift=contaminated_crossing_rate - clean_crossing_rate,
        clean_final_similarity_mean=clean_final_mean,
        contaminated_final_similarity_mean=contaminated_final_mean,
        final_similarity_drop_contaminated_vs_clean=clean_final_mean - contaminated_final_mean,
        condition_summaries=condition_summaries,
        limitations=_limitations(),
    )
    return summary, all_records


def write_drift_halflife_outputs(
    *,
    drift_config: DriftHalflifeConfig,
    dose_config: dict[str, Any],
    out_dir: str | Path,
    drift_config_path: str | Path,
    dose_config_path: str | Path,
) -> DriftHalflifeSummary:
    summary, records = run_drift_halflife_analysis(
        drift_config=drift_config,
        dose_config=dose_config,
    )
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    manifest = _manifest(
        drift_config=drift_config,
        drift_config_path=drift_config_path,
        dose_config_path=dose_config_path,
    )
    (target / "drift_halflife_records.jsonl").write_text(
        "\n".join(
            json.dumps(record.model_dump(mode="json"), sort_keys=True)
            for record in records
        )
        + ("\n" if records else ""),
        encoding="utf-8",
    )
    (target / "drift_halflife_summary.json").write_text(
        json.dumps(summary.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target / "drift_halflife_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target / "drift_halflife_report.md").write_text(
        drift_halflife_report_markdown(summary, manifest, drift_config) + "\n",
        encoding="utf-8",
    )
    return summary


def drift_halflife_report_markdown(
    summary: DriftHalflifeSummary,
    manifest: dict[str, Any],
    drift_config: DriftHalflifeConfig,
) -> str:
    lines = [
        "# HELIX v8.6 Deterministic Drift Halflife Scaffold",
        "",
        "This report uses a deterministic objective-token-retention proxy. It is not embedding-based semantic drift measurement.",
        "Each trajectory starts at objective similarity 1.0. Configured perturbation penalties reduce similarity; safe unperturbed steps recover by 0.02 up to 1.0.",
        "",
        "## Summary",
        "",
        f"- condition_count: `{summary.condition_count}`",
        f"- theta_similarity: `{summary.theta_similarity:.6f}`",
        f"- clean_halflife_crossing_rate: `{summary.clean_halflife_crossing_rate:.6f}`",
        f"- contaminated_halflife_crossing_rate: `{summary.contaminated_halflife_crossing_rate:.6f}`",
        f"- halflife_crossing_lift: `{summary.halflife_crossing_lift:.6f}`",
        f"- clean_final_similarity_mean: `{summary.clean_final_similarity_mean:.6f}`",
        f"- contaminated_final_similarity_mean: `{summary.contaminated_final_similarity_mean:.6f}`",
        f"- final_similarity_drop_contaminated_vs_clean: `{summary.final_similarity_drop_contaminated_vs_clean:.6f}`",
        f"- manifest_hash: `{manifest['manifest_hash']}`",
        "",
        "## Similarity Proxy",
        "",
        f"- method: `{drift_config.similarity_proxy.method}`",
        f"- base_objective_tokens: `{json.dumps(drift_config.similarity_proxy.base_objective_tokens)}`",
        f"- drift_token_penalties: `{json.dumps(drift_config.similarity_proxy.drift_token_penalties, sort_keys=True)}`",
        "",
        "## Condition Table",
        "",
        "| Condition | Dose | Crossing Rate | Mean Halflife Step | Median Halflife Step | Final Similarity Mean | Final Similarity Min | Final Similarity Max |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for condition in summary.condition_summaries:
        lines.append(
            f"| `{condition.condition_id}` | {condition.dose_level} | "
            f"{condition.halflife_crossing_rate:.6f} | "
            f"`{_value(condition.mean_halflife_step)}` | "
            f"`{_value(condition.median_halflife_step)}` | "
            f"{condition.final_similarity_mean:.6f} | "
            f"{condition.final_similarity_min:.6f} | "
            f"{condition.final_similarity_max:.6f} |"
        )
    lines.extend(
        [
            "",
            "## Manifest",
            "",
            f"- drift_halflife_config_hash: `{manifest['drift_halflife_config_hash']}`",
            f"- dose_config_hash: `{manifest['dose_config_hash']}`",
            f"- base_seed: `{manifest['base_seed']}`",
            f"- trajectory_count: `{manifest['trajectory_count']}`",
            f"- steps_per_trajectory: `{manifest['steps_per_trajectory']}`",
            "",
            "## Limitations",
            "",
        ]
    )
    lines.extend(f"- {limitation}" for limitation in summary.limitations)
    return "\n".join(lines)


def stable_file_hash(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _condition_records(
    *,
    condition: DriftHalflifeConditionConfig,
    trajectories: list[TrajectoryRun],
    config: DriftHalflifeConfig,
) -> tuple[list[DriftHalflifeStepRecord], list[float], list[int | None]]:
    records: list[DriftHalflifeStepRecord] = []
    final_similarities: list[float] = []
    halflife_steps: list[int | None] = []
    for trajectory in trajectories:
        previous_similarity = 1.0
        halflife_step: int | None = None
        for step in sorted(trajectory.steps, key=lambda item: item.step_index):
            objective_similarity = objective_similarity_for_step(
                step,
                previous_similarity,
                config,
            )
            crossed_now = (
                halflife_step is None
                and objective_similarity <= config.theta_similarity
            )
            if crossed_now:
                halflife_step = step.step_index
            records.append(
                DriftHalflifeStepRecord(
                    condition_id=condition.condition_id,
                    dose_level=condition.dose_level,
                    trajectory_id=trajectory.trajectory_id,
                    step_index=step.step_index,
                    perturbation_types=sorted(
                        perturbation.perturbation_type
                        for perturbation in step.perturbations
                    ),
                    objective_similarity=objective_similarity,
                    theta_similarity=config.theta_similarity,
                    halflife_crossed_at_step=crossed_now,
                    ground_truth=step.ground_truth,
                    ground_truth_requires_trajectory_context=step.ground_truth_requires_trajectory_context,
                    gate_intervention_was_necessary=step.gate_intervention_was_necessary,
                )
            )
            previous_similarity = objective_similarity
        final_similarities.append(previous_similarity)
        halflife_steps.append(halflife_step)
    return records, final_similarities, halflife_steps


def _condition_summary(
    *,
    condition: DriftHalflifeConditionConfig,
    step_count: int,
    final_similarities: list[float],
    halflife_steps: list[int | None],
) -> DriftHalflifeConditionSummary:
    crossing_steps = [
        step
        for step in halflife_steps
        if step is not None
    ]
    return DriftHalflifeConditionSummary(
        condition_id=condition.condition_id,
        dose_level=condition.dose_level,
        trajectory_count=len(halflife_steps),
        step_count=step_count,
        halflife_crossing_count=len(crossing_steps),
        halflife_crossing_rate=_rate(len(crossing_steps), len(halflife_steps)),
        mean_halflife_step=_mean(crossing_steps),
        median_halflife_step=float(median(crossing_steps)) if crossing_steps else None,
        final_similarity_mean=_mean(final_similarities) or 0.0,
        final_similarity_min=min(final_similarities, default=0.0),
        final_similarity_max=max(final_similarities, default=0.0),
    )


def _manifest(
    *,
    drift_config: DriftHalflifeConfig,
    drift_config_path: str | Path,
    dose_config_path: str | Path,
) -> dict[str, Any]:
    fields = {
        "manifest_hash": "",
        "drift_halflife_config_path": str(drift_config_path),
        "drift_halflife_config_hash": stable_file_hash(drift_config_path),
        "dose_config_path": str(dose_config_path),
        "dose_config_hash": stable_file_hash(dose_config_path),
        "base_seed": drift_config.base_seed,
        "trajectory_count": drift_config.trajectory_count,
        "steps_per_trajectory": drift_config.steps_per_trajectory,
        "condition_count": len(drift_config.conditions),
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    fields["manifest_hash"] = build_manifest_hash(fields)
    return fields


def _weighted_crossing_rate(summaries: list[DriftHalflifeConditionSummary]) -> float:
    crossing_count = sum(summary.halflife_crossing_count for summary in summaries)
    trajectory_count = sum(summary.trajectory_count for summary in summaries)
    return _rate(crossing_count, trajectory_count)


def _weighted_final_similarity_mean(
    summaries: list[DriftHalflifeConditionSummary],
) -> float:
    trajectory_count = sum(summary.trajectory_count for summary in summaries)
    if not trajectory_count:
        return 0.0
    weighted_total = sum(
        summary.final_similarity_mean * summary.trajectory_count
        for summary in summaries
    )
    return weighted_total / trajectory_count


def _has_real_perturbation(perturbation_types: list[str]) -> bool:
    return any(perturbation_type != "none" for perturbation_type in perturbation_types)


def _mean(values: list[int | float]) -> float | None:
    if not values:
        return None
    return float(sum(values) / len(values))


def _rate(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0.0
    return float(numerator) / float(denominator)


def _limitations() -> list[str]:
    return [
        "No embedding-based semantic similarity yet.",
        "No live agent trajectories.",
        "Deterministic perturbation-based proxy.",
        "Not final Drift Halflife metric.",
        "No objective curvature yet.",
    ]


def _value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)
