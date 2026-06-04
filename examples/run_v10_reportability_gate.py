from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.v10_reportability import (
    evaluate_v10_reportability,
    load_v10_reportability_config,
    write_v10_reportability_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate future v10 outputs against the preregistered reportability gate."
    )
    parser.add_argument("--integrity-report", required=True)
    parser.add_argument("--benchmark-summary")
    parser.add_argument("--bootstrap-ci")
    parser.add_argument("--config", default="configs/v10_reportability_gate.json")
    parser.add_argument("--out-dir", default="outputs/v10_reportability/default")
    args = parser.parse_args()

    integrity_report = _load_required_json(
        Path(args.integrity_report),
        "integrity report",
    )
    benchmark_summary = _load_optional_json(
        Path(args.benchmark_summary) if args.benchmark_summary else None,
        "benchmark summary",
    )
    bootstrap_ci = _load_optional_json(
        Path(args.bootstrap_ci) if args.bootstrap_ci else None,
        "bootstrap CI",
    )
    config = load_v10_reportability_config(args.config)
    report = evaluate_v10_reportability(
        integrity_report=integrity_report,
        benchmark_summary=benchmark_summary,
        bootstrap_ci=bootstrap_ci,
        config=config,
    )
    json_path, markdown_path = write_v10_reportability_outputs(report, args.out_dir)

    print(f"Reportability passed: {report.reportability_passed}")
    print(f"Failed criteria: {report.failed_criteria}")
    print(f"Evidence level allowed: {report.evidence_level_allowed}")
    print(f"Level 5 allowed: {report.level_5_allowed}")
    print(f"Reportability hash: {report.reportability_hash}")
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {markdown_path}")


def _load_required_json(path: Path, description: str) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Required {description} does not exist: {path}")
    return _read_json_object(path, description)


def _load_optional_json(
    path: Path | None,
    description: str,
) -> dict[str, Any] | None:
    if path is None:
        return None
    if not path.exists():
        raise SystemExit(f"Supplied {description} does not exist: {path}")
    return _read_json_object(path, description)


def _read_json_object(path: Path, description: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"Expected {description} to contain a JSON object: {path}")
    return payload


if __name__ == "__main__":
    main()
