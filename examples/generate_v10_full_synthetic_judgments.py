from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.v10_synthetic_fixture import (
    generate_v10_full_synthetic_raw_judgments,
    load_v10_cases,
    load_v10_synthetic_fixture_config,
    write_v10_synthetic_fixture_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate deterministic full-coverage v10 synthetic raw judgments."
    )
    parser.add_argument("--cases", default="benchmarks/v10_calibrated/v10_cases.jsonl")
    parser.add_argument("--config", default="configs/v10_full_synthetic_fixture.json")
    parser.add_argument(
        "--out-dir",
        default="benchmarks/v10_calibrated/raw_judgments/full_synthetic_calibration",
    )
    args = parser.parse_args()

    config = load_v10_synthetic_fixture_config(args.config)
    cases = load_v10_cases(args.cases)
    raw_judgments = generate_v10_full_synthetic_raw_judgments(cases, config)
    _, summary_path, _, _ = write_v10_synthetic_fixture_outputs(
        cases=cases,
        raw_judgments=raw_judgments,
        config=config,
        config_path=args.config,
        input_cases_path=args.cases,
        out_dir=args.out_dir,
    )
    import json

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    print(f"fixture_id: {summary['fixture_id']}")
    print(f"raw_judgment_count: {summary['raw_judgment_count']}")
    print(f"score_entropy: {summary['score_entropy']:.6f}")
    print(f"binary_score_fraction: {summary['binary_score_fraction']:.6f}")
    print(f"max_score_bin_fraction: {summary['max_score_bin_fraction']:.6f}")
    print(f"decision_counts: {summary['decision_counts']}")
    print(f"output_path: {Path(args.out_dir)}")


if __name__ == "__main__":
    main()
