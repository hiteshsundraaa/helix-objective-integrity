from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.v10_generator import V10Case
from helix.benchmark.v10_judgment_normalization import V10NormalizedJudgment
from helix.benchmark.v10_pilot_evidence_assessor import (
    assess_v10_pilot_evidence,
    load_allowed_provider_model_config,
    load_v10_pilot_evidence_assessment_config,
    write_v10_pilot_evidence_assessment,
)
from helix.benchmark.v10_receipt_chain import (
    V10ReceiptChainConfig,
    build_receipt_chain,
    write_receipt_chain_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Assess v10 pilot evidence level from existing pipeline artifacts."
    )
    parser.add_argument(
        "--config",
        default="configs/v10_pilot_evidence_assessment.json",
    )
    parser.add_argument(
        "--live-design-config",
        default="configs/v10_live_provider_runner_design_gate.json",
    )
    parser.add_argument("--provider-run-dir", required=True)
    parser.add_argument(
        "--execution-mode",
        required=True,
        choices=["dry_run", "manual_import", "live"],
    )
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--out-subdir", default="pilot_evidence")
    args = parser.parse_args()

    run_dir = Path(args.provider_run_dir)
    if not run_dir.exists():
        raise SystemExit(f"Provider run directory does not exist: {run_dir}")

    assessment_config = load_v10_pilot_evidence_assessment_config(args.config)
    live_design_config = load_allowed_provider_model_config(args.live_design_config)
    out_dir = run_dir / args.out_subdir
    run_id = args.run_id or _infer_run_id(run_dir)

    cases, case_issues = _load_cases(run_dir)
    judgments, judgment_issues = _load_judgments(run_dir)
    receipt_chain_config = V10ReceiptChainConfig.model_validate(
        assessment_config.receipt_chain.model_dump(mode="json")
    )
    records, receipt_chain_summary = build_receipt_chain(
        cases,
        judgments,
        execution_mode=args.execution_mode,
        provider=args.provider,
        model=args.model,
        raw_hashes_by_case_id={},
        config=receipt_chain_config,
        run_id=run_id,
    )
    if case_issues or judgment_issues:
        receipt_chain_summary = receipt_chain_summary.model_copy(
            update={
                "issues": sorted(set(receipt_chain_summary.issues + case_issues + judgment_issues)),
                "receipt_chain_complete": False,
            }
        )
    write_receipt_chain_outputs(records, receipt_chain_summary, out_dir)

    artifacts = _load_pipeline_artifacts(run_dir)
    assessment = assess_v10_pilot_evidence(
        run_id=run_id,
        execution_mode=args.execution_mode,
        provider=args.provider,
        model=args.model,
        case_count=len(cases),
        receipt_chain_summary=receipt_chain_summary,
        normalization_status=artifacts["normalization_status"],
        benchmark_status=artifacts["benchmark_status"],
        diagnostics_status=artifacts["diagnostics_status"],
        integrity_summary=artifacts["integrity_summary"],
        reportability_summary=artifacts["reportability_summary"],
        live_design_config=live_design_config,
        assessment_config=assessment_config,
    )
    paths = write_v10_pilot_evidence_assessment(
        assessment,
        out_dir,
        config=assessment_config,
        receipt_chain_summary=receipt_chain_summary,
    )
    print(f"run_id: {assessment.run_id}")
    print(f"execution_mode: {assessment.execution_mode}")
    print(f"final_evidence_level: {assessment.final_evidence_level}")
    print(f"level_4_criteria_met: {assessment.level_4_criteria_met}")
    print(f"level_5_allowed: {assessment.level_5_allowed}")
    print(f"blocking_issues: {json.dumps(assessment.blocking_issues, sort_keys=True)}")
    print(f"non_blocking_warnings: {json.dumps(assessment.non_blocking_warnings, sort_keys=True)}")
    print(f"receipt_chain_hash: {receipt_chain_summary.chain_hash}")
    print(f"assessment_hash: {assessment.assessment_hash}")
    print(f"assessment_path: {paths['assessment']}")
    print(f"report_path: {paths['report']}")


def _infer_run_id(run_dir: Path) -> str:
    for path in [
        run_dir / "bridge_summary.json",
        run_dir / "imported_pipeline_bridge" / "bridge_summary.json",
        run_dir / "pipeline_bridge" / "bridge_summary.json",
        run_dir / "raw_import_validation_summary.json",
        run_dir / "provider_dry_run_summary.json",
    ]:
        if path.exists():
            payload = _read_json(path)
            run_id = payload.get("run_id")
            if isinstance(run_id, str) and run_id:
                return run_id
    return run_dir.name


def _load_cases(run_dir: Path) -> tuple[list[V10Case], list[str]]:
    issues: list[str] = []
    candidates = [
        run_dir / "filtered_imported_cases.jsonl",
        run_dir / "imported_pipeline_bridge" / "filtered_imported_cases.jsonl",
        run_dir / "pipeline_bridge" / "filtered_imported_cases.jsonl",
        Path("benchmarks/v10_calibrated/v10_cases.jsonl"),
    ]
    for path in candidates:
        if path.exists():
            return [
                V10Case.model_validate_json(line)
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ], issues
    issues.append("missing_cases_file")
    return [], issues


def _load_judgments(run_dir: Path) -> tuple[list[V10NormalizedJudgment | dict[str, Any]], list[str]]:
    issues: list[str] = []
    normalized_candidates = [
        run_dir / "normalized_judgments" / "v10_normalized_judgments.jsonl",
        run_dir / "imported_pipeline_bridge" / "normalized_judgments" / "v10_normalized_judgments.jsonl",
        run_dir / "pipeline_bridge" / "normalized_judgments" / "v10_normalized_judgments.jsonl",
    ]
    for path in normalized_candidates:
        if path.exists():
            return [
                V10NormalizedJudgment.model_validate_json(line)
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ], issues
    raw_candidates = [
        run_dir / "parsed_raw_judgments.jsonl",
        run_dir / "imported_pipeline_bridge" / "parsed_raw_judgments.jsonl",
        run_dir / "pipeline_bridge" / "parsed_raw_judgments.jsonl",
    ]
    for path in raw_candidates:
        if path.exists():
            return _load_jsonl_dicts(path), issues
    issues.append("missing_judgments_file")
    return [], issues


def _load_pipeline_artifacts(run_dir: Path) -> dict[str, Any]:
    bridge_summary = _first_json(
        [
            run_dir / "bridge_summary.json",
            run_dir / "imported_pipeline_bridge" / "bridge_summary.json",
            run_dir / "pipeline_bridge" / "bridge_summary.json",
        ]
    )
    normalization_summary = _first_json(
        [
            run_dir / "normalized_judgments" / "v10_normalization_summary.json",
            run_dir / "imported_pipeline_bridge" / "normalized_judgments" / "v10_normalization_summary.json",
            run_dir / "pipeline_bridge" / "normalized_judgments" / "v10_normalization_summary.json",
        ]
    )
    benchmark_summary = _first_json(
        [
            run_dir / "benchmark_run" / "v10_benchmark_summary.json",
            run_dir / "imported_pipeline_bridge" / "benchmark_run" / "v10_benchmark_summary.json",
            run_dir / "pipeline_bridge" / "benchmark_run" / "v10_benchmark_summary.json",
        ]
    )
    diagnostics_summary = _first_json(
        [
            run_dir / "diagnostics" / "v10_diagnostics_summary.json",
            run_dir / "imported_pipeline_bridge" / "diagnostics" / "v10_diagnostics_summary.json",
            run_dir / "pipeline_bridge" / "diagnostics" / "v10_diagnostics_summary.json",
        ]
    )
    integrity_summary = _first_json(
        [
            run_dir / "diagnostics" / "v10_integrity_report.json",
            run_dir / "imported_pipeline_bridge" / "diagnostics" / "v10_integrity_report.json",
            run_dir / "pipeline_bridge" / "diagnostics" / "v10_integrity_report.json",
        ]
    )
    reportability_summary = _first_json(
        [
            run_dir / "reportability" / "v10_reportability_report.json",
            run_dir / "imported_pipeline_bridge" / "reportability" / "v10_reportability_report.json",
            run_dir / "pipeline_bridge" / "reportability" / "v10_reportability_report.json",
        ]
    )
    if integrity_summary is not None and "score_collapse_detected" not in integrity_summary:
        source = normalization_summary or benchmark_summary or {}
        if "score_collapse_detected" in source:
            integrity_summary = {
                **integrity_summary,
                "score_collapse_detected": source["score_collapse_detected"],
            }
        elif "score_entropy" in integrity_summary:
            integrity_summary = {
                **integrity_summary,
                "score_collapse_detected": False,
            }
    return {
        "normalization_status": (
            bridge_summary.get("normalization_status")
            if bridge_summary
            else normalization_summary.get("status")
            if normalization_summary
            else None
        ),
        "benchmark_status": (
            bridge_summary.get("benchmark_status")
            if bridge_summary
            else benchmark_summary.get("status")
            if benchmark_summary
            else None
        ),
        "diagnostics_status": (
            bridge_summary.get("diagnostics_status")
            if bridge_summary
            else diagnostics_summary.get("diagnostics_status")
            if diagnostics_summary
            else None
        ),
        "integrity_summary": integrity_summary,
        "reportability_summary": reportability_summary,
    }


def _first_json(paths: list[Path]) -> dict[str, Any] | None:
    for path in paths:
        if path.exists():
            return _read_json(path)
    return None


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return payload


def _load_jsonl_dicts(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            records.append(payload)
    return records


if __name__ == "__main__":
    main()
