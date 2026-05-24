# v0.5.6a Score Distribution Diagnostics

## Purpose

v0.5.6 showed that many q=0.20 "false negatives" were unsafe cases with high hybrid scores but outside the selected budget.

v0.5.6a distinguishes:

```text
budget-excluded high-rank unsafe cases
true low-rank unsafe cases
```

without using an arbitrary fixed threshold.

## No fixed threshold

Instead of saying "hybrid_score >= 0.60 means high risk," this patch compares unselected unsafe cases against selected safe near-misses.

If an unselected unsafe case scores above selected safe cases, it is a budget-excluded ranking/capacity issue, not necessarily a semantic failure.

## Adds diagnostic precision metrics

This patch also counts cases where:

```text
generic = uncertain / needs human review
contract-aware = specific mechanism codes
```

This quantifies contract-aware diagnostic precision advantage even when generic and contract-aware tie on top-k TPR.

## Outputs

```text
budget_excluded_high_rank_unsafe.jsonl
true_low_rank_unsafe.jsonl
diagnostic_precision_advantage_cases.jsonl
generic_uncertain_contract_specific_unsafe.jsonl
top_risk_safe_near_misses.jsonl
score_band_summary.json
README.md
```

## Usage

```bash
python examples/analyze_score_distributions.py \
  --cases benchmarks/blind_cases/mock_workspace_blind_v1.jsonl \
  --generic-judgments benchmarks/semantic_judgments/blind_v1_generic_gpt5.jsonl \
  --contract-judgments benchmarks/semantic_judgments/blind_v1_contract_gpt5.jsonl \
  --out-dir outputs/score_distribution/blind_v1 \
  --primary-budget 0.20
```

## Warning

Do not tune hybrid weights on blind_v1 to push authority-laundering cases over the q=0.20 cutoff. That would overfit a 40-case set. Use this analysis to design blind_v2.
