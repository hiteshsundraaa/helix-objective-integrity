from __future__ import annotations

import json
from pathlib import Path

from helix.benchmark.blind_loader import load_blind_cases_jsonl
from helix.extract.llm_semantic_extractor import SemanticExtractorMode


GENERIC_PROMPT_PATH = Path("docs/prompts/generic_semantic_judge_prompt.md")
CONTRACT_PROMPT_PATH = Path("docs/prompts/contract_aware_semantic_judge_prompt.md")


def render_semantic_judgment_prompt(
    *,
    cases_path: str | Path,
    mode: SemanticExtractorMode,
    prompt_path: str | Path | None = None,
) -> str:
    cases = load_blind_cases_jsonl(cases_path)

    if prompt_path is None:
        prompt_path = GENERIC_PROMPT_PATH if mode == SemanticExtractorMode.GENERIC else CONTRACT_PROMPT_PATH

    base_prompt = Path(prompt_path).read_text(encoding="utf-8").strip()

    payload_rows = []
    for case in cases:
        payload_rows.append(
            {
                "sample_id": case.case_id,
                "tool": case.tool,
                "rationale": case.rationale,
                "memory": case.memory,
                "context": case.context,
            }
        )

    payload = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in payload_rows)

    return (
        f"{base_prompt}\n\n"
        "## Input samples\n\n"
        "Convert each input sample into one JSONL semantic judgment.\n\n"
        "```jsonl\n"
        f"{payload}\n"
        "```\n"
    )
