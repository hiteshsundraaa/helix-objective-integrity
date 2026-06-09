from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.v10_live_runner_design_gate import (
    build_live_runner_design_receipt,
    load_v10_live_runner_design_config,
    validate_execution_mode_path,
    validate_provider_model_allowed,
    validate_retry_policy,
    write_live_runner_design_receipt,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the HELIX v10.14 live-provider runner design-gate receipt."
    )
    parser.add_argument(
        "--config",
        default="configs/v10_live_provider_runner_design_gate.json",
    )
    parser.add_argument(
        "--out-dir",
        default="benchmarks/v10_calibrated/live_runner_design_gate/v10_14",
    )
    args = parser.parse_args()

    config = load_v10_live_runner_design_config(args.config)
    validation_issues = []
    retry = validate_retry_policy(config)
    validation_issues.extend(retry.issues)
    for provider, provider_config in sorted(config.allowed_providers.items()):
        for model in provider_config.allowed_models:
            validation_issues.extend(
                validate_provider_model_allowed(config, provider, model).issues
            )
    path_policy = config.output_path_policy
    representative_paths = {
        "dry_run": f"{path_policy.dry_run_root}/design_gate_check",
        "manual_import": f"{path_policy.manual_import_root}/design_gate_check",
        "live": f"{path_policy.live_root}/google/gemini-flash-2.0/design_gate_check",
    }
    for mode, output_path in representative_paths.items():
        validation_issues.extend(
            validate_execution_mode_path(config, mode, output_path).issues
        )
    if validation_issues:
        raise SystemExit(
            "v10.14 design-gate validation failed: "
            + ", ".join(sorted(set(validation_issues)))
        )

    paths = write_live_runner_design_receipt(config, args.out_dir)
    receipt = build_live_runner_design_receipt(config)
    print(f"receipt_path: {paths['receipt']}")
    print(f"report_path: {paths['report']}")
    print(f"receipt_id: {receipt.receipt_id}")
    print(f"live_calls_in_this_version: {receipt.live_calls_in_this_version}")
    print(f"provider_sdks_used: {receipt.provider_sdks_used}")
    print(f"secrets_included: {receipt.secrets_included}")
    print(f"design_gate_hash: {receipt.design_gate_hash}")
    print(
        "constraints_codified: "
        + json.dumps(receipt.constraints_codified, sort_keys=True)
    )


if __name__ == "__main__":
    main()
