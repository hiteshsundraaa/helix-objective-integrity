# v0.5.3 Semantic Benchmark Runner

v0.5.3 adds a benchmark runner that compares the full v0.5 system list using deterministic fake semantic extractors.

## Systems compared

```text
heuristic_only
generic_semantic
contract_aware_semantic
hybrid_semantic
matched_random
prompt_filter_rank
allowlist_only
```

## Evidence boundary

This is still not empirical LLM evidence. The fake semantic extractor exists only to wire the benchmark architecture.

## Usage

Smoke blind run:

```bash
python examples/run_semantic_benchmark_fake.py \
  --dataset blind \
  --cases benchmarks/blind_cases/mock_workspace_blind_smoke.jsonl \
  --budgets 0.50
```

Subtle synthetic wiring run:

```bash
python examples/run_semantic_benchmark_fake.py --dataset subtle_synthetic
```

## Next step

v0.5.4 should add provider-backed LLM extraction and run the pre-registered blind_v1 comparison.
