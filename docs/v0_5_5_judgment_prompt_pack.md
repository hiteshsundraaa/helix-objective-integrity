# v0.5.5 Judgment Prompt Pack

## Why this exists

v0.5.4 added JSONL replay for frozen semantic judgments. v0.5.5 adds reproducible prompt templates for generating those judgments.

This prevents ad hoc prompting and makes it possible to record exactly how generic and contract-aware judgments were produced.

## Files

```text
docs/prompts/generic_semantic_judge_prompt.md
docs/prompts/contract_aware_semantic_judge_prompt.md
docs/prompts/jsonl_output_schema.md
helix/benchmark/prompt_rendering.py
examples/render_semantic_judgment_prompt.py
tests/test_prompt_rendering.py
```

## Render prompts

Generic:

```bash
python examples/render_semantic_judgment_prompt.py \
  --cases benchmarks/blind_cases/mock_workspace_blind_v1.jsonl \
  --mode generic \
  --out outputs/prompts/blind_v1_generic_prompt.md
```

Contract-aware:

```bash
python examples/render_semantic_judgment_prompt.py \
  --cases benchmarks/blind_cases/mock_workspace_blind_v1.jsonl \
  --mode contract_aware \
  --out outputs/prompts/blind_v1_contract_prompt.md
```

## Evidence discipline

Record alongside every generated judgment file:

- prompt file;
- model;
- provider;
- temperature;
- date;
- whether responses were manually repaired to match schema;
- raw response when possible.
