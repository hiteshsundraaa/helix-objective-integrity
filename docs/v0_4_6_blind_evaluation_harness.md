# v0.4.6 Blind Evaluation Harness

## Why this exists

v0.4.5 is a positive result, but it is still synthetic and co-designed with the scorer. v0.4.6 adds the machinery to evaluate HELIX on externally authored blind cases.

## What this patch does

Adds:

```text
helix/benchmark/blind_case_schema.py
helix/benchmark/blind_loader.py
helix/benchmark/blind_evaluator.py
examples/run_blind_type_b_budget_sweep.py
benchmarks/blind_cases/
docs/blind_case_generation_protocol.md
```

## What this patch does not do

It does not change HELIX scoring.

The point is to freeze the current scorer and evaluate it against cases that were not written around the scorer.

## Usage

```bash
python examples/run_blind_type_b_budget_sweep.py \
  --cases benchmarks/blind_cases/mock_workspace_blind_v1.jsonl
```

Smoke test:

```bash
python examples/run_blind_type_b_budget_sweep.py \
  --cases benchmarks/blind_cases/mock_workspace_blind_smoke.jsonl \
  --budgets 0.50
```

## Interpretation

If HELIX beats matched random and prompt-filter on blind cases, the heuristic result is stronger.

If HELIX collapses, that is not a failure of the project. It is evidence that deterministic heuristic scoring has reached its ceiling and that the LLM-assisted semantic extractor is necessary.
