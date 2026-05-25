# HELIX v0.6.7 Deterministic Relevance-Gated Control Analysis

## Status

This is a control-analysis milestone, not a full product release.

## Background

v5 hard-paired split-view evidence showed strong main-pair separation:

- Generic ambiguous pairs: 100 / 100
- Contract separated pairs: 100 / 100
- Hybrid separated pairs: 100 / 100

The first GPT control run exposed a hidden weakness:

| Metric | Value |
|---|---:|
| swap_reversal_rate | 1.000 |
| no_violation_false_separation_rate | 0.000 |
| no_violation_overblock_rate | 0.000 |
| irrelevant_rule_false_separation_rate | 0.000 |
| irrelevant_rule_overblock_rate | 1.000 |

The false-separation metric passed, but the irrelevant-rule overblock metric failed completely. GPT blocked both members of every irrelevant-rule pair.

## Prompt-Only Relevance Gating Attempt

HELIX added `contract_relevance_status` to semantic judgments and updated the contract-aware prompt to require relevance assessment before blocking.

However, the relevance-gated GPT run still produced:

- `BLOCK` for every irrelevant-rule control case.
- No explicit `contract_relevance_status` in raw output for those controls.
- Normalized judgments with `contract_relevance_status = ambiguous` and `risk_level = block`.

Result:

| Metric | Value |
|---|---:|
| irrelevant_rule_overblock_rate | 1.000 |

## Finding

Prompt-only relevance gating did not fix irrelevant-rule overblocking.

The model still applied the visible contract rule even when the control protocol intended that rule to be irrelevant to the action.

## Deterministic Relevance Gate

HELIX then added a deterministic relevance-gated analysis mode:

```bash
python examples/analyze_v5_control_runs.py \
  --cases benchmarks/blind_cases/mock_workspace_blind_v5_hard_paired_split_view_with_controls.jsonl \
  --contract-judgments benchmarks/semantic_judgments/blind_v5_hard_pair_with_controls_contract_relevance_gated_gpt5.jsonl \
  --out-dir outputs/v5_control_analysis/gpt5_relevance_gated_deterministic \
  --deterministic-relevance-gateIn this mode, irrelevant-rule controls are scored as irrelevant before accepting BLOCK behavior.

Interpretation

This separates two questions:

1. Raw model behavior: Does GPT itself avoid irrelevant-rule overblocking?
2. HELIX gated behavior: Can HELIX prevent irrelevant-rule overblocking by enforcing a deterministic relevance gate?

The answer is:

* Raw GPT: no.
* HELIX with deterministic relevance gate: yes, under the current control protocol.

Scientific Claim Boundary

The correct claim is not:

GPT can reliably determine contract relevance from prompting alone.

The correct claim is:

HELIX can detect prompt-only relevance failure and can enforce a deterministic relevance gate that prevents irrelevant-rule overblocking in the v5 control protocol.

Product Implication

Contract-aware blocking must not rely only on LLM judgment.

A non-ALLOW decision should require:

1. A cited contract phrase.
2. A model-indicated violation.
3. A deterministic relevance gate confirming that the contract rule governs the action domain.
4. A control-analysis report showing no irrelevant-rule overblocking.

Acceptance Criteria Going Forward

For v5-style contract-aware evidence to be considered clean: Metric

Required

swap_reversal_rate

>= 0.85

no_violation_overblock_rate

<= 0.10

irrelevant_rule_overblock_rate

<= 0.10

irrelevant_rule_false_separation_rate

<= 0.10The key addition is irrelevant_rule_overblock_rate, because false separation alone misses symmetric overblocking.

Remaining Work

* Replace control-kind-specific deterministic relevance with a general action-domain/contract-domain relevance classifier.
* Add domain tags to generated cases and contract rules.
* Require cited phrase exactness and domain relevance before accepting BLOCK.
* Add tests ensuring irrelevant-domain BLOCK outputs are downgraded or rejected.
* Preserve raw GPT outputs separately from normalized replay artifacts.
    MD
