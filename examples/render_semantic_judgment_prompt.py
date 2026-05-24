from __future__ import annotations

import argparse
from pathlib import Path

from helix.benchmark.prompt_rendering import render_semantic_judgment_prompt
from helix.extract.llm_semantic_extractor import SemanticExtractorMode


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True)
    parser.add_argument("--mode", choices=["generic", "contract_aware"], required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    prompt = render_semantic_judgment_prompt(
        cases_path=args.cases,
        mode=SemanticExtractorMode(args.mode),
    )

    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(prompt, encoding="utf-8")

    print(f"Wrote semantic judgment prompt to {target}")


if __name__ == "__main__":
    main()
