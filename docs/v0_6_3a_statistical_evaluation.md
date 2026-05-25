# v0.6.3a Statistical Evaluation Layer

## Purpose

Previous benchmark results reported point estimates only. That is insufficient for research claims because small datasets and small selected budgets make single-case swings large.

## Adds

```text
helix/analysis/bootstrap.py
helix/analysis/roc.py
helix/analysis/benchmark_statistics.py
examples/analyze_benchmark_statistics.py
tests/test_bootstrap_analysis.py
tests/test_roc_analysis.py
tests/test_benchmark_statistics.py
```

## Metrics

The statistical evaluator reports:

```text
AUC-ROC per method
95% bootstrap CI for TPR
95% bootstrap CI for FPR
95% bootstrap CI for precision
paired bootstrap CI for method deltas
```

## Usage

```bash
python examples/analyze_benchmark_statistics.py \
  --cases benchmarks/blind_cases/mock_workspace_blind_v3_split_view.jsonl \
  --generic-judgments benchmarks/semantic_judgments/blind_v3_split_generic_gpt5.jsonl \
  --contract-judgments benchmarks/semantic_judgments/blind_v3_split_contract_gpt5.jsonl \
  --out-dir outputs/statistical_evaluation/blind_v3 \
  --bootstrap 2000
```

## Interpretation boundary

Bootstrap intervals are case-level nonparametric intervals over the evaluated dataset. They quantify finite-sample uncertainty for the benchmark sample, not deployment generalization.

If a delta confidence interval crosses zero, do not claim a reliable advantage for that delta.
