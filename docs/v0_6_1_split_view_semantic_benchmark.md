# v0.6.1 Split-View Semantic Benchmark Runner

## Purpose

The old JSONL semantic benchmark runner loads old blind-case schema files. v0.6 split-view cases use a different schema:

```text
generic_rationale
generic_memory
generic_context
contract_rule_id
contract_rule_summary
```

This patch adds a split-view benchmark runner that converts split-view cases into benchmark samples using only generic-visible fields for the proposed action.

## Adds

```text
helix/benchmark/split_view_semantic_benchmark.py
examples/run_split_view_semantic_benchmark_jsonl.py
helix/benchmark/split_view_failure_analysis.py
examples/analyze_split_view_semantic_failures.py
tests/test_split_view_semantic_benchmark.py
```

## Usage

```bash
python examples/run_split_view_semantic_benchmark_jsonl.py \
  --cases benchmarks/blind_cases/mock_workspace_blind_v3_split_view.jsonl \
  --generic-judgments benchmarks/semantic_judgments/blind_v3_split_generic_gpt5.jsonl \
  --contract-judgments benchmarks/semantic_judgments/blind_v3_split_contract_gpt5.jsonl
```

Failure analysis:

```bash
python examples/analyze_split_view_semantic_failures.py \
  --cases benchmarks/blind_cases/mock_workspace_blind_v3_split_view.jsonl \
  --generic-judgments benchmarks/semantic_judgments/blind_v3_split_generic_gpt5.jsonl \
  --contract-judgments benchmarks/semantic_judgments/blind_v3_split_contract_gpt5.jsonl \
  --out-dir outputs/split_view_failure_analysis/blind_v3 \
  --primary-budget 0.20
```

## Evidence boundary

Split-view benchmark results are the first clean generic-vs-contract-aware test only if:
- generic prompt rendered without contamination failure;
- judgment files cover all case IDs;
- cases were generated under the authoring-order protocol.
