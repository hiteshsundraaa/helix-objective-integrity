from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.paraphrase_prompt_rendering import write_paraphrase_prompts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render HELIX v6 paraphrase prompts for external model judgment."
    )
    parser.add_argument(
        "--cases",
        default="benchmarks/blind_cases/mock_workspace_blind_v6_paraphrase_controls.jsonl",
    )
    parser.add_argument(
        "--contract-out",
        default="outputs/prompts/blind_v6_paraphrase_contract_prompt.md",
    )
    parser.add_argument(
        "--generic-out",
        default="outputs/prompts/blind_v6_paraphrase_generic_prompt.md",
    )
    args = parser.parse_args()

    contract_path, generic_path = write_paraphrase_prompts(
        cases_path=args.cases,
        contract_out=args.contract_out,
        generic_out=args.generic_out,
    )
    print(f"Wrote contract-aware prompt to {contract_path}")
    if generic_path is not None:
        print(f"Wrote generic prompt to {generic_path}")


if __name__ == "__main__":
    main()
