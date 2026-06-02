from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.performance.fast_path_latency import (
    run_fast_path_latency_benchmark,
    write_fast_path_latency_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run HELIX v8.5 deterministic fast-path latency benchmark."
    )
    parser.add_argument("--out-dir", default="outputs/performance/v8_fast_path")
    parser.add_argument("--iterations", type=int, default=5000)
    parser.add_argument("--warmup-iterations", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    summary = run_fast_path_latency_benchmark(
        iterations=args.iterations,
        warmup_iterations=args.warmup_iterations,
        seed=args.seed,
    )
    write_fast_path_latency_outputs(summary, out_dir=args.out_dir)
    slowest = next(
        record
        for record in summary.operations
        if record.operation == summary.slowest_operation_p99
    )
    fastest = next(
        record
        for record in summary.operations
        if record.operation == summary.fastest_operation_p50
    )

    print(f"Operation count: {summary.operation_count}")
    print(
        f"Fastest operation p50: {summary.fastest_operation_p50} "
        f"({fastest.p50_latency_ms:.6f} ms)"
    )
    print(
        f"Slowest operation p99: {summary.slowest_operation_p99} "
        f"({slowest.p99_latency_ms:.6f} ms)"
    )
    print(f"Heavy LLM calls per step: {summary.heavy_llm_calls_per_step}")
    print(f"Wrote outputs to {args.out_dir}")


if __name__ == "__main__":
    main()
