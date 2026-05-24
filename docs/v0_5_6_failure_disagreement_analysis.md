# v0.5.6 Failure + Disagreement Analysis

## Purpose

v0.5 JSONL semantic results showed that semantic judgment improved over the heuristic baseline, but generic and contract-aware judgments tied at the pre-registered q=0.20 budget.

This patch adds analysis tooling to distinguish three hypotheses:

```text
A. blind_v1 does not require contract context.
B. the contract-aware prompt is not using the contract strongly enough.
C. generic and contract-aware select the same cases but for different reasons.
```

## Files

```text
helix/benchmark/failure_analysis.py
examples/analyze_semantic_benchmark_failures.py
tests/test_failure_analysis.py
```

## Outputs

```text
case_diagnostics.jsonl
false_positive_cases.jsonl
false_negative_cases.jsonl
top_risk_safe_cases.jsonl
low_risk_unsafe_cases.jsonl
method_disagreements.jsonl
reason_code_overlap.json
reason_code_distribution.json
contract_value_candidates.jsonl
failure_analysis_report.json
README.md
```

## Reason-code overlap

The important metric is not only whether generic and contract-aware judgments choose the same cases. They may choose the same cases for different reasons.

This patch computes:

```text
reason_code_overlap_count
reason_code_union_count
reason_code_jaccard
same_risk_level
same_allowed_tool_misuse
contract_score_minus_generic
hybrid_score_minus_heuristic
```

## Contract-value candidates

A case is flagged as a contract-value candidate when:

- contract-aware selects an unsafe case generic does not;
- contract-aware avoids selecting a safe case generic selects;
- generic and contract-aware have the same risk level but different reason codes.

## Usage

```bash
python examples/analyze_semantic_benchmark_failures.py \
  --cases benchmarks/blind_cases/mock_workspace_blind_v1.jsonl \
  --generic-judgments benchmarks/semantic_judgments/blind_v1_generic_promptv1_gpt5_2026-05-24.jsonl \
  --contract-judgments benchmarks/semantic_judgments/blind_v1_contract_promptv1_gpt5_2026-05-24.jsonl \
  --out-dir outputs/failure_analysis/blind_v1 \
  --primary-budget 0.20
```

## Methodological warning

A perfect q=0.50 result on N=40 has weak generalization value. It may mean the set is easy or saturated, not that the architecture generalizes. Use this tool to inspect failure modes before making architectural claims.
