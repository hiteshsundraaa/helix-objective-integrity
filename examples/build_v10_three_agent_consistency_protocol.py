from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.v10_three_agent_consistency_protocol import (
    build_metric_definitions,
    build_three_agent_protocol_receipt,
    load_v10_three_agent_consistency_protocol_config,
    validate_three_agent_system_specs,
    write_three_agent_protocol_artifacts,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build HELIX v10.16 three-agent consistency protocol artifacts."
    )
    parser.add_argument(
        "--config",
        default="configs/v10_three_agent_consistency_protocol.json",
    )
    parser.add_argument(
        "--out-dir",
        default="benchmarks/v10_calibrated/three_agent_consistency_protocol/v10_16",
    )
    args = parser.parse_args()

    config = load_v10_three_agent_consistency_protocol_config(args.config)
    validation = validate_three_agent_system_specs(
        config.recommended_initial_systems,
        config,
    )
    if not validation.valid:
        raise SystemExit(
            "v10.16 three-agent protocol validation failed: "
            + ", ".join(validation.issues)
        )

    paths = write_three_agent_protocol_artifacts(config, args.out_dir)
    receipt = build_three_agent_protocol_receipt(config)
    metrics = build_metric_definitions(config)

    print(f"config_path: {paths['config']}")
    print(f"metrics_path: {paths['metrics']}")
    print(f"receipt_path: {paths['receipt']}")
    print(f"report_path: {paths['report']}")
    print(f"receipt_id: {receipt.receipt_id}")
    print(f"protocol_hash: {receipt.protocol_hash}")
    print(f"minimum_independent_systems: {receipt.minimum_independent_systems}")
    print(f"live_calls_in_this_version: {receipt.live_calls_in_this_version}")
    print(f"provider_sdks_used: {receipt.provider_sdks_used}")
    print(f"secrets_included: {receipt.secrets_included}")
    print("consistency_evidence_produced: False")
    print("level_5_allowed: False")
    print(
        "metric_names: "
        + json.dumps([metric.name for metric in metrics], sort_keys=True)
    )


if __name__ == "__main__":
    main()
