from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.oar_360_generator import (
    generate_oar_360_cases,
    load_oar_360_blueprint,
    load_oar_360_config,
    write_oar_360_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate deterministic OAR-360 benchmark cases."
    )
    parser.add_argument(
        "--config",
        default="configs/oar_360_generator.json",
        help="OAR-360 generator config JSON.",
    )
    parser.add_argument(
        "--blueprint",
        default="paper/helix_v4_1/experiments/oar_360_case_blueprint.json",
        help="OAR-360 blueprint JSON.",
    )
    parser.add_argument(
        "--out-dir",
        default="benchmarks/oar_360",
        help="Output directory for generated OAR-360 artifacts.",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    blueprint_path = Path(args.blueprint)
    config = load_oar_360_config(config_path)
    config_payload = json.loads(config_path.read_text(encoding="utf-8"))
    blueprint = load_oar_360_blueprint(blueprint_path)
    cases = generate_oar_360_cases(config, blueprint)
    result = write_oar_360_outputs(
        cases,
        config=config,
        config_payload=config_payload,
        blueprint=blueprint,
        out_dir=args.out_dir,
    )

    summary = result["summary"]
    print(f"Generated OAR-360 cases: {summary['total_cases']}")
    print(f"Output directory: {Path(args.out_dir)}")
    print(f"Family distribution: {summary['family_distribution']}")
    print(f"Domain distribution: {summary['domain_distribution']}")
    print(f"Label distribution: {summary['label_distribution']}")
    print(f"Risk band distribution: {summary['risk_band_distribution']}")
    print(f"Expected decision distribution: {summary['expected_decision_distribution']}")
    print(f"Distinct edge tags: {summary['distinct_edge_tag_count']}")
    print(f"Case file hash: {result['case_file_hash']}")
    print(f"Manifest hash: {result['manifest_hash']}")
    print(f"Validation issues: {summary['validation_issues']}")
    print(f"Cases: {result['case_path']}")
    print(f"Manifest: {result['manifest_path']}")
    print(f"Report: {result['report_path']}")
    if summary["validation_issues"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
