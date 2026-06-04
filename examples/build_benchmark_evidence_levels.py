from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.evidence_levels import (
    collect_benchmark_evidence_levels,
    write_benchmark_evidence_levels_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build HELIX benchmark evidence-level governance outputs."
    )
    parser.add_argument("--out-dir", default="outputs/evidence_levels")
    args = parser.parse_args()

    summary = collect_benchmark_evidence_levels()
    json_path, markdown_path = write_benchmark_evidence_levels_outputs(
        summary,
        args.out_dir,
    )
    print(f"Protocol count: {summary.protocol_count}")
    print(f"Max assigned level: {summary.max_assigned_level}")
    print(f"Failed or missing integrity audits: {summary.failed_or_missing_integrity_count}")
    for record in summary.records:
        print(
            f"{record.protocol_name}: Level {record.evidence_level} "
            f"({record.evidence_level_name})"
        )
    print(f"JSON output: {json_path}")
    print(f"Markdown output: {markdown_path}")


if __name__ == "__main__":
    main()
