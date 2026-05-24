# v0.5.7 Blind v2 Contract-Dependence Protocol

## Why this patch exists

v0.5.6a showed:

```text
true_low_rank_unsafe_count = 0
diagnostic_precision_advantage_count = 10
generic_uncertain_contract_specific_unsafe_count = 10
```

That means the semantic ranker worked well on blind_v1, and contract-aware judgment added diagnostic precision in half of unsafe cases. But contract-aware decision advantage over generic judgment remains unproven at the primary q=0.20 budget.

blind_v2 must therefore isolate cases where the signed contract provides information the generic judge cannot infer.

## What this patch adds

```text
docs/blind_v2_contract_dependence_protocol.md
benchmarks/blind_cases/blind_v2_schema_notes.md
docs/prompts/blind_v2_case_generation_prompt.md
```

It also extends `BlindCase` with optional metadata:

```text
intended_contract_dependence
contract_variant
contract_rule_id
contract_rule_summary
```

## Scientific rule

Generator labels are not final truth.

```text
intended_contract_dependence != empirical_contract_dependence
```

Empirical contract-dependence is measured after comparing generic and contract-aware judgments.

## Core target

blind_v2 should include idiosyncratic reversal cases:

```text
generic likely wrong, contract-aware should be right
```

This is the actual test of the contract-bound architecture.
