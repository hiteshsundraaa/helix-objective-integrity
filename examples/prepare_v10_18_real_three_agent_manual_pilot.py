from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.v10_real_three_agent_manual_pilot import (
    load_v10_real_three_agent_manual_pilot_config,
    prepare_real_three_agent_manual_pilot,
    run_real_three_agent_manual_pilot_if_ready,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare the HELIX v10.18 real three-agent manual pilot artifact flow."
    )
    parser.add_argument(
        "--config",
        default="configs/v10_real_three_agent_manual_pilot.json",
    )
    parser.add_argument("--run-if-ready", action="store_true")
    args = parser.parse_args()

    config = load_v10_real_three_agent_manual_pilot_config(args.config)
    if args.run_if_ready:
        summary, _ = run_real_three_agent_manual_pilot_if_ready(config)
    else:
        summary = prepare_real_three_agent_manual_pilot(config)

    print(f"consistency_run_id: {summary.consistency_run_id}")
    print(f"prompt_pack_dir: {summary.prompt_pack_dir}")
    print(f"raw_output_dir: {summary.raw_output_dir}")
    print(f"systems_json_path: {summary.system_json_path}")
    print(f"ready_to_run_consistency: {str(summary.ready_to_run_consistency).lower()}")
    print(f"status: {summary.status}")
    print(f"preparation_hash: {summary.preparation_hash}")
    if not summary.ready_to_run_consistency:
        print("Manual provider outputs are not collected yet. Prompt pack is ready.")


if __name__ == "__main__":
    main()
