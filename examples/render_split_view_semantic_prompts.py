from __future__ import annotations

import argparse
from pathlib import Path

from helix.benchmark.split_view_prompt_rendering import render_split_view_semantic_prompt
from helix.extract.llm_semantic_extractor import SemanticExtractorMode


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True)
    parser.add_argument("--mode", choices=["generic", "contract_aware"], required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--allow-contamination", action="store_true")
    args = parser.parse_args()

    prompt = render_split_view_semantic_prompt(
        cases_path=args.cases,
        mode=SemanticExtractorMode(args.mode),
        fail_on_contamination=not args.allow_contamination,
    )

    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(prompt, encoding="utf-8")
    print(f"Wrote split-view semantic prompt to {target}")


if __name__ == "__main__":
    main()
