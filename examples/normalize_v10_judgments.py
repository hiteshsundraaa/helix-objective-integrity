from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.v10_judgment_normalization import (
    load_raw_judgments,
    load_v10_cases,
    load_v10_normalization_config,
    normalize_v10_judgments,
    write_v10_normalization_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normalize supplied raw v10 judgment JSONL and audit score collapse."
    )
    parser.add_argument("--cases", default="benchmarks/v10_calibrated/v10_cases.jsonl")
    parser.add_argument("--raw", required=True)
    parser.add_argument("--config", default="configs/v10_judgment_normalization.json")
    parser.add_argument("--provider", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument(
        "--out-dir",
        default="benchmarks/v10_calibrated/normalized_judgments/demo",
    )
    args = parser.parse_args()

    try:
        cases = load_v10_cases(args.cases)
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc

    config = load_v10_normalization_config(args.config)
    raw_judgments = load_raw_judgments(args.raw)
    normalized, summary = normalize_v10_judgments(
        raw_judgments,
        cases,
        config,
        provider=args.provider,
        model=args.model,
    )
    write_v10_normalization_outputs(
        normalized_judgments=normalized,
        summary=summary,
        config_path=args.config,
        input_cases_path=args.cases,
        raw_judgments_path=args.raw,
        provider=args.provider,
        model=args.model,
        out_dir=args.out_dir,
    )

    print(f"raw_count: {summary.raw_count}")
    print(f"valid_count: {summary.valid_count}")
    print(f"invalid_count: {summary.invalid_count}")
    print(f"status: {summary.status}")
    print(f"score_entropy: {summary.score_entropy:.6f}")
    print(f"binary_score_fraction: {summary.binary_score_fraction:.6f}")
    print(f"score_collapse_detected: {summary.score_collapse_detected}")
    print(f"decision_score_coupling_detected: {summary.decision_score_coupling_detected}")
    print(f"output_path: {Path(args.out_dir)}")


if __name__ == "__main__":
    main()
