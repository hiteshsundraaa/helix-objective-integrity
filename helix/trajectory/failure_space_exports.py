from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from helix.trajectory.schema import build_manifest_hash


EXPORT_SCHEMA_VERSION = "v8.8_failure_space_exports"
PLOT_FILENAMES = [
    "cp_vs_dg_scatter.png",
    "dose_vs_max_cp.png",
    "failure_mode_counts.png",
]

STEP_TABLE_COLUMNS = [
    "dose_level",
    "trajectory_id",
    "step_index",
    "ground_truth",
    "D_G",
    "CSR",
    "D_Q",
    "FAP",
    "CP_t",
    "dominant_failure_mode",
    "failure_mode_confidence",
    "competing_failure_modes",
    "cp_decision",
    "ground_truth_requires_trajectory_context",
    "gate_intervention_was_necessary",
]

TRAJECTORY_CURVE_COLUMNS = [
    "dose_level",
    "trajectory_id",
    "step_index",
    "D_G",
    "CSR",
    "D_Q",
    "FAP",
    "CP_t",
    "dominant_failure_trajectory",
    "gate_first_non_allow_step",
    "gate_first_block_step",
]

FAILURE_MODE_COLUMNS = [
    "dominant_failure_mode",
    "count",
    "fraction",
]

CONFIDENCE_COLUMNS = [
    "failure_mode_confidence",
    "count",
    "fraction",
]

DOSE_METRIC_COLUMNS = [
    "dose_level",
    "mean_D_G",
    "mean_CSR",
    "mean_D_Q",
    "mean_FAP",
    "mean_CP_t",
    "max_CP_t",
    "step_count",
    "dominant_failure_mode_top",
    "low_confidence_step_count",
]


class FailureSpaceExportSummary(BaseModel):
    status: str
    step_row_count: int
    trajectory_curve_row_count: int
    failure_mode_count_rows: int
    confidence_count_rows: int
    dose_metric_rows: int
    generated_plot_files: list[str] = Field(default_factory=list)
    skipped_plot_files: list[str] = Field(default_factory=list)
    plot_generation_status: str
    warnings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


def load_failure_space_records(path: str | Path) -> list[dict[str, Any]]:
    return _read_jsonl(_require_input_file(path))


def load_failure_space_trajectory_records(path: str | Path) -> list[dict[str, Any]]:
    return _read_jsonl(_require_input_file(path))


def export_failure_space_tables(
    *,
    records: list[dict[str, Any]],
    trajectory_records: list[dict[str, Any]],
    summary: dict[str, Any],
    out_dir: str | Path,
) -> tuple[dict[str, Path], dict[str, int], list[str]]:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []

    step_rows = _step_table_rows(records, warnings)
    trajectory_rows = _trajectory_curve_rows(trajectory_records, warnings)
    failure_mode_rows = _count_rows(
        summary.get("dominant_failure_mode_counts"),
        name_field="dominant_failure_mode",
        denominator=summary.get("step_count"),
        warnings=warnings,
        warning_name="dominant_failure_mode_counts",
    )
    confidence_rows = _count_rows(
        summary.get("failure_mode_confidence_counts"),
        name_field="failure_mode_confidence",
        denominator=summary.get("step_count"),
        warnings=warnings,
        warning_name="failure_mode_confidence_counts",
    )
    dose_rows = _dose_metric_rows(records, summary, warnings)

    paths = {
        "failure_space_step_table": target / "failure_space_step_table.csv",
        "failure_space_trajectory_curves": target / "failure_space_trajectory_curves.csv",
        "failure_mode_counts": target / "failure_mode_counts.csv",
        "confidence_counts": target / "confidence_counts.csv",
        "dose_metric_summary": target / "dose_metric_summary.csv",
    }
    _write_csv(paths["failure_space_step_table"], STEP_TABLE_COLUMNS, step_rows)
    _write_csv(paths["failure_space_trajectory_curves"], TRAJECTORY_CURVE_COLUMNS, trajectory_rows)
    _write_csv(paths["failure_mode_counts"], FAILURE_MODE_COLUMNS, failure_mode_rows)
    _write_csv(paths["confidence_counts"], CONFIDENCE_COLUMNS, confidence_rows)
    _write_csv(paths["dose_metric_summary"], DOSE_METRIC_COLUMNS, dose_rows)

    row_counts = {
        "step_row_count": len(step_rows),
        "trajectory_curve_row_count": len(trajectory_rows),
        "failure_mode_count_rows": len(failure_mode_rows),
        "confidence_count_rows": len(confidence_rows),
        "dose_metric_rows": len(dose_rows),
    }
    return paths, row_counts, warnings


def write_failure_space_export_outputs(
    *,
    records_path: str | Path,
    trajectories_path: str | Path,
    summary_path: str | Path,
    manifest_path: str | Path,
    out_dir: str | Path,
    generate_plots: bool = True,
) -> FailureSpaceExportSummary:
    records_file = _require_input_file(records_path)
    trajectories_file = _require_input_file(trajectories_path)
    summary_file = _require_input_file(summary_path)
    manifest_file = _require_input_file(manifest_path)

    records = load_failure_space_records(records_file)
    trajectory_records = load_failure_space_trajectory_records(trajectories_file)
    summary_payload = _read_json(summary_file)
    _input_manifest = _read_json(manifest_file)

    target = Path(out_dir)
    table_paths, row_counts, warnings = export_failure_space_tables(
        records=records,
        trajectory_records=trajectory_records,
        summary=summary_payload,
        out_dir=target,
    )
    generated_plot_files, skipped_plot_files, plot_status, plot_warnings = _maybe_generate_plots(
        records=records,
        summary=summary_payload,
        out_dir=target,
        generate_plots=generate_plots,
    )
    warnings.extend(plot_warnings)

    status = "partial" if warnings else "complete"
    export_summary = FailureSpaceExportSummary(
        status=status,
        **row_counts,
        generated_plot_files=[path.name for path in generated_plot_files],
        skipped_plot_files=skipped_plot_files,
        plot_generation_status=plot_status,
        warnings=warnings,
        limitations=_limitations(),
    )

    summary_output_path = target / "export_summary.json"
    report_output_path = target / "export_report.md"
    manifest_output_path = target / "export_manifest.json"
    generated_files = [
        *(path.name for path in table_paths.values()),
        *(path.name for path in generated_plot_files),
        manifest_output_path.name,
        summary_output_path.name,
        report_output_path.name,
    ]
    manifest = _export_manifest(
        records_path=records_file,
        trajectories_path=trajectories_file,
        summary_path=summary_file,
        manifest_path=manifest_file,
        generated_files=generated_files,
    )

    summary_output_path.write_text(
        json.dumps(export_summary.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest_output_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_output_path.write_text(
        export_report_markdown(
            export_summary,
            manifest,
            table_paths=table_paths,
        )
        + "\n",
        encoding="utf-8",
    )
    return export_summary


def export_report_markdown(
    summary: FailureSpaceExportSummary,
    manifest: dict[str, Any],
    *,
    table_paths: dict[str, Path],
) -> str:
    lines = [
        "# HELIX v8.8 Failure-Space Export Report",
        "",
        "## Executive Summary",
        "",
        "This export reads existing v8.7 failure-space artifacts and writes reproducible table and optional figure inputs. It does not recompute failure-space metrics or create new evidence.",
        "",
        "## Input Artifacts",
        "",
        f"- failure_space_records: `{manifest['input_failure_space_records_path']}`",
        f"- failure_space_trajectories: `{manifest['input_failure_space_trajectories_path']}`",
        f"- failure_space_summary: `{manifest['input_failure_space_summary_path']}`",
        f"- failure_space_manifest: `{manifest['input_failure_space_manifest_path']}`",
        "",
        "## Generated Tables",
        "",
        f"- failure_space_step_table.csv: `{summary.step_row_count}` rows",
        f"- failure_space_trajectory_curves.csv: `{summary.trajectory_curve_row_count}` rows",
        f"- failure_mode_counts.csv: `{summary.failure_mode_count_rows}` rows",
        f"- confidence_counts.csv: `{summary.confidence_count_rows}` rows",
        f"- dose_metric_summary.csv: `{summary.dose_metric_rows}` rows",
        "",
        "## Generated Plots",
        "",
        f"- plot_generation_status: `{summary.plot_generation_status}`",
        f"- generated_plot_files: `{_list_value(summary.generated_plot_files)}`",
        f"- skipped_plot_files: `{_list_value(summary.skipped_plot_files)}`",
        "",
        "## What This Supports",
        "",
        "- Failure-space records can be exported into reproducible table and figure inputs without regenerating or modifying the underlying v8.7 evidence.",
        "- CSV tables preserve step-level, trajectory-curve, failure-mode, confidence, and dose-summary views for inspection.",
        "",
        "## What This Does Not Yet Prove",
        "",
        "- Exports are derived from deterministic v8.7 proxy metrics.",
        "- Tables and plots are inspection aids, not statistical validation.",
        "- No embeddings or live trajectories are introduced by this export layer.",
        "- No objective curvature is implemented here.",
        "",
        "## Limitations",
        "",
    ]
    lines.extend(f"- {limitation}" for limitation in summary.limitations)
    if summary.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in summary.warnings)
    lines.extend(
        [
            "",
            "## Manifest",
            "",
            f"- manifest_hash: `{manifest['manifest_hash']}`",
            f"- export_schema_version: `{manifest['export_schema_version']}`",
            f"- generated_files: `{_list_value(manifest['generated_files'])}`",
        ]
    )
    return "\n".join(lines)


def stable_file_hash(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _step_table_rows(
    records: list[dict[str, Any]],
    warnings: list[str],
) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        rows.append(
            {
                "dose_level": record.get("dose_level", ""),
                "trajectory_id": record.get("trajectory_id", ""),
                "step_index": record.get("step_index", ""),
                "ground_truth": record.get("ground_truth", ""),
                "D_G": record.get("D_G", ""),
                "CSR": record.get("CSR", ""),
                "D_Q": record.get("D_Q", ""),
                "FAP": record.get("FAP", ""),
                "CP_t": record.get("CP_t", ""),
                "dominant_failure_mode": record.get("dominant_failure_mode", ""),
                "failure_mode_confidence": record.get("failure_mode_confidence", ""),
                "competing_failure_modes": _list_value(record.get("competing_failure_modes", [])),
                "cp_decision": record.get("cp_decision", ""),
                "ground_truth_requires_trajectory_context": record.get("ground_truth_requires_trajectory_context", ""),
                "gate_intervention_was_necessary": record.get("gate_intervention_was_necessary", ""),
            }
        )
    _warn_missing_columns(records, STEP_TABLE_COLUMNS, warnings, "failure_space_records")
    return rows


def _trajectory_curve_rows(
    trajectory_records: list[dict[str, Any]],
    warnings: list[str],
) -> list[dict[str, Any]]:
    rows = []
    required_arrays = [
        "D_G_trajectory",
        "CSR_trajectory",
        "D_Q_trajectory",
        "FAP_trajectory",
        "CP_t_trajectory",
    ]
    for record in trajectory_records:
        arrays = {
            name: record.get(name) if isinstance(record.get(name), list) else []
            for name in required_arrays
        }
        if any(not arrays[name] for name in required_arrays):
            warnings.append(f"trajectory_record_missing_curve_array:{record.get('trajectory_id', '')}")
        row_count = max((len(values) for values in arrays.values()), default=0)
        for index in range(row_count):
            rows.append(
                {
                    "dose_level": record.get("dose_level", ""),
                    "trajectory_id": record.get("trajectory_id", ""),
                    "step_index": index + 1,
                    "D_G": _list_get(arrays["D_G_trajectory"], index),
                    "CSR": _list_get(arrays["CSR_trajectory"], index),
                    "D_Q": _list_get(arrays["D_Q_trajectory"], index),
                    "FAP": _list_get(arrays["FAP_trajectory"], index),
                    "CP_t": _list_get(arrays["CP_t_trajectory"], index),
                    "dominant_failure_trajectory": record.get("dominant_failure_trajectory", ""),
                    "gate_first_non_allow_step": record.get("gate_first_non_allow_step", ""),
                    "gate_first_block_step": record.get("gate_first_block_step", ""),
                }
            )
    return rows


def _count_rows(
    counts: Any,
    *,
    name_field: str,
    denominator: Any,
    warnings: list[str],
    warning_name: str,
) -> list[dict[str, Any]]:
    if not isinstance(counts, dict):
        warnings.append(f"missing_summary_field:{warning_name}")
        return []
    total = float(denominator or sum(int(value) for value in counts.values()) or 0)
    rows = []
    for name, count in sorted(counts.items()):
        rows.append(
            {
                name_field: name,
                "count": count,
                "fraction": _rate(float(count), total),
            }
        )
    return rows


def _dose_metric_rows(
    records: list[dict[str, Any]],
    summary: dict[str, Any],
    warnings: list[str],
) -> list[dict[str, Any]]:
    metric_maps = {
        "mean_D_G": summary.get("mean_D_G_by_dose"),
        "mean_CSR": summary.get("mean_CSR_by_dose"),
        "mean_D_Q": summary.get("mean_D_Q_by_dose"),
        "mean_FAP": summary.get("mean_FAP_by_dose"),
        "mean_CP_t": summary.get("mean_CP_t_by_dose"),
        "max_CP_t": summary.get("max_CP_t_by_dose"),
    }
    for name, value in metric_maps.items():
        if not isinstance(value, dict):
            warnings.append(f"missing_summary_field:{name}_by_dose")
            metric_maps[name] = {}

    records_by_dose: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        dose = str(record.get("dose_level", ""))
        records_by_dose.setdefault(dose, []).append(record)

    doses = sorted(
        {
            *records_by_dose,
            *(key for metric_map in metric_maps.values() for key in metric_map),
        },
        key=_dose_sort_key,
    )
    rows = []
    for dose in doses:
        dose_records = records_by_dose.get(dose, [])
        dominant_mode_counts = Counter(
            record.get("dominant_failure_mode", "")
            for record in dose_records
            if record.get("dominant_failure_mode", "") != ""
        )
        top_mode = ""
        if dominant_mode_counts:
            top_mode = sorted(
                dominant_mode_counts,
                key=lambda item: (-dominant_mode_counts[item], item),
            )[0]
        rows.append(
            {
                "dose_level": dose,
                "mean_D_G": metric_maps["mean_D_G"].get(dose, ""),
                "mean_CSR": metric_maps["mean_CSR"].get(dose, ""),
                "mean_D_Q": metric_maps["mean_D_Q"].get(dose, ""),
                "mean_FAP": metric_maps["mean_FAP"].get(dose, ""),
                "mean_CP_t": metric_maps["mean_CP_t"].get(dose, ""),
                "max_CP_t": metric_maps["max_CP_t"].get(dose, ""),
                "step_count": len(dose_records),
                "dominant_failure_mode_top": top_mode,
                "low_confidence_step_count": sum(
                    record.get("failure_mode_confidence") == "low"
                    for record in dose_records
                ),
            }
        )
    return rows


def _maybe_generate_plots(
    *,
    records: list[dict[str, Any]],
    summary: dict[str, Any],
    out_dir: Path,
    generate_plots: bool,
) -> tuple[list[Path], list[str], str, list[str]]:
    if not generate_plots:
        return [], list(PLOT_FILENAMES), "skipped_disabled", []
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return [], list(PLOT_FILENAMES), "skipped_matplotlib_unavailable", [
            "plot_generation_status:skipped_matplotlib_unavailable"
        ]

    generated: list[Path] = []
    skipped: list[str] = []
    warnings: list[str] = []
    _plot_cp_vs_dg(records, out_dir / "cp_vs_dg_scatter.png", plt, generated, skipped, warnings)
    _plot_dose_vs_max_cp(summary, out_dir / "dose_vs_max_cp.png", plt, generated, skipped, warnings)
    _plot_failure_mode_counts(summary, out_dir / "failure_mode_counts.png", plt, generated, skipped, warnings)
    status = "generated" if generated and not skipped else "partial"
    return generated, skipped, status, warnings


def _plot_cp_vs_dg(
    records: list[dict[str, Any]],
    path: Path,
    plt: Any,
    generated: list[Path],
    skipped: list[str],
    warnings: list[str],
) -> None:
    points = [
        (record.get("D_G"), record.get("CP_t"), record.get("dose_level"))
        for record in records
        if record.get("D_G") is not None and record.get("CP_t") is not None
    ]
    if not points:
        skipped.append(path.name)
        warnings.append("plot_skipped:no_cp_vs_dg_points")
        return
    xs, ys, doses = zip(*points)
    plt.figure(figsize=(6, 4))
    plt.scatter(xs, ys, c=doses)
    plt.xlabel("D_G")
    plt.ylabel("CP_t")
    plt.title("CP_t vs D_G")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    generated.append(path)


def _plot_dose_vs_max_cp(
    summary: dict[str, Any],
    path: Path,
    plt: Any,
    generated: list[Path],
    skipped: list[str],
    warnings: list[str],
) -> None:
    values = summary.get("max_CP_t_by_dose")
    if not isinstance(values, dict) or not values:
        skipped.append(path.name)
        warnings.append("plot_skipped:missing_max_CP_t_by_dose")
        return
    doses = sorted(values, key=_dose_sort_key)
    plt.figure(figsize=(6, 4))
    plt.plot([int(dose) for dose in doses], [values[dose] for dose in doses], marker="o")
    plt.xlabel("Dose level")
    plt.ylabel("Max CP_t")
    plt.title("Dose vs Max CP_t")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    generated.append(path)


def _plot_failure_mode_counts(
    summary: dict[str, Any],
    path: Path,
    plt: Any,
    generated: list[Path],
    skipped: list[str],
    warnings: list[str],
) -> None:
    counts = summary.get("dominant_failure_mode_counts")
    if not isinstance(counts, dict) or not counts:
        skipped.append(path.name)
        warnings.append("plot_skipped:missing_dominant_failure_mode_counts")
        return
    labels = list(sorted(counts))
    plt.figure(figsize=(8, 4))
    plt.bar(labels, [counts[label] for label in labels])
    plt.xticks(rotation=30, ha="right")
    plt.ylabel("Count")
    plt.title("Dominant Failure Mode Counts")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    generated.append(path)


def _export_manifest(
    *,
    records_path: Path,
    trajectories_path: Path,
    summary_path: Path,
    manifest_path: Path,
    generated_files: list[str],
) -> dict[str, Any]:
    fields = {
        "manifest_hash": "",
        "export_schema_version": EXPORT_SCHEMA_VERSION,
        "input_failure_space_records_path": str(records_path),
        "input_failure_space_records_hash": stable_file_hash(records_path),
        "input_failure_space_trajectories_path": str(trajectories_path),
        "input_failure_space_trajectories_hash": stable_file_hash(trajectories_path),
        "input_failure_space_summary_path": str(summary_path),
        "input_failure_space_summary_hash": stable_file_hash(summary_path),
        "input_failure_space_manifest_path": str(manifest_path),
        "input_failure_space_manifest_hash": stable_file_hash(manifest_path),
        "generated_files": sorted(generated_files),
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    fields["manifest_hash"] = build_manifest_hash(fields)
    return fields


def _write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _csv_value(row.get(column, "")) for column in columns})


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_input_file(path: str | Path) -> Path:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(
            f"Missing failure-space input: {target}. Run examples/run_v8_failure_space_analysis.py first."
        )
    return target


def _csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, list):
        return _list_value(value)
    if isinstance(value, bool):
        return str(value).lower()
    return value


def _list_value(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, list):
        return ";".join(str(item) for item in value)
    return str(value)


def _list_get(values: list[Any], index: int) -> Any:
    if index >= len(values):
        return ""
    return values[index]


def _warn_missing_columns(
    records: list[dict[str, Any]],
    columns: list[str],
    warnings: list[str],
    source_name: str,
) -> None:
    if not records:
        warnings.append(f"empty_input:{source_name}")
        return
    observed = set().union(*(record.keys() for record in records))
    missing = [
        column
        for column in columns
        if column not in observed
    ]
    for column in missing:
        warnings.append(f"missing_record_field:{source_name}.{column}")


def _dose_sort_key(value: Any) -> tuple[int, str]:
    try:
        return int(value), str(value)
    except (TypeError, ValueError):
        return 10_000, str(value)


def _rate(numerator: float, denominator: float) -> float:
    if not denominator:
        return 0.0
    return numerator / denominator


def _limitations() -> list[str]:
    return [
        "Exports are derived from deterministic v8.7 proxy metrics.",
        "No new evidence is generated.",
        "Plots and tables are inspection aids, not statistical validation.",
        "No embeddings or live trajectories yet.",
        "No objective curvature yet.",
    ]
