from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.v10_provider_raw_import import (
    load_provider_run_plan,
    load_v10_provider_raw_import_config,
    write_imported_provider_run_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate and import externally saved HELIX v10 provider raw outputs."
    )
    parser.add_argument(
        "--config",
        default="configs/v10_provider_raw_import_validator.json",
    )
    parser.add_argument(
        "--plan",
        default="benchmarks/v10_calibrated/provider_run_plans/pilot_v1/provider_run_plan.json",
    )
    parser.add_argument("--import-dir", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--out-root",
        default="benchmarks/v10_calibrated/provider_runs",
    )
    args = parser.parse_args()

    config = load_v10_provider_raw_import_config(args.config)
    plan = load_provider_run_plan(args.plan)
    paths = write_imported_provider_run_outputs(
        config=config,
        config_path=args.config,
        plan=plan,
        plan_path=args.plan,
        import_dir=args.import_dir,
        run_id=args.run_id,
        out_root=args.out_root,
    )
    summary = json.loads(paths["raw_import_validation_summary"].read_text(encoding="utf-8"))
    print(f"run_id: {summary['run_id']}")
    print(f"validation_status: {summary['validation_status']}")
    print(f"expected_case_count: {summary['expected_case_count']}")
    print(f"imported_case_count: {summary['imported_case_count']}")
    print(f"missing_case_count: {summary['missing_case_count']}")
    print(f"duplicate_case_count: {summary['duplicate_case_count']}")
    print(f"unexpected_case_count: {summary['unexpected_case_count']}")
    print(f"malformed_judgment_count: {summary['malformed_judgment_count']}")
    print(f"api_key_observed: {summary['api_key_observed']}")
    print(f"parsed_raw_judgments_written: {summary['parsed_raw_judgments_written']}")
    print(f"evidence_level_cap: {summary['evidence_level_cap']}")
    print(f"output_path: {paths['output_provider_run_dir']}")


if __name__ == "__main__":
    main()
