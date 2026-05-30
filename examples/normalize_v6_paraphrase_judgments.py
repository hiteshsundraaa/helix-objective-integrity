from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.paraphrase_normalization import (
    ParaphraseNormalizationError,
    normalize_paraphrase_judgments,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normalize raw v6 paraphrase JSONL judgments into HELIX semantic judgment JSONL."
    )
    parser.add_argument(
        "--cases",
        default="benchmarks/blind_cases/mock_workspace_blind_v6_paraphrase_controls.jsonl",
    )
    parser.add_argument("--raw", required=True)
    parser.add_argument(
        "--out",
        default="benchmarks/semantic_judgments/blind_v6_paraphrase_contract_normalized.jsonl",
    )
    parser.add_argument("--provider", default="external")
    parser.add_argument("--model", default="external")
    parser.add_argument("--mode", default="contract_aware")
    args = parser.parse_args()

    try:
        records = normalize_paraphrase_judgments(
            cases_path=args.cases,
            raw_path=args.raw,
            out_path=args.out,
            provider=args.provider,
            model=args.model,
            mode=args.mode,
        )
    except ParaphraseNormalizationError as exc:
        raise SystemExit(f"normalization failed: {exc}") from exc

    print(f"Wrote {len(records)} normalized v6 paraphrase judgments to {args.out}")


if __name__ == "__main__":
    main()
