# v0.5.4 JSONL Semantic Judgment Importer

## Why this exists

Before provider-backed live API extraction, HELIX needs a reproducible semantic-judgment replay layer.

Live LLM calls are not stable evidence unless the outputs are frozen. The JSONL importer lets externally generated judgments become benchmark artifacts.

## Files

```text
helix/extract/jsonl_semantic_extractor.py
examples/run_semantic_benchmark_jsonl.py
benchmarks/semantic_judgments/
tests/test_jsonl_semantic_extractor.py
tests/test_semantic_benchmark_jsonl.py
```

## Usage

Smoke run:

```bash
python examples/run_semantic_benchmark_jsonl.py \
  --dataset blind \
  --cases benchmarks/blind_cases/mock_workspace_blind_smoke.jsonl \
  --generic-judgments benchmarks/semantic_judgments/mock_workspace_blind_smoke_generic.jsonl \
  --contract-judgments benchmarks/semantic_judgments/mock_workspace_blind_smoke_contract.jsonl \
  --budgets 0.50
```

## Evidence boundary

JSONL replay is reproducible, but validity still depends on how the judgments were generated.

For empirical claims, record:

- provider;
- model;
- prompt;
- temperature;
- date;
- raw response;
- schema validation status.
