# HELIX v0.6.5 Hard-Paired Split-View Evidence

## Dataset

`mock_workspace_blind_v5_hard_paired_split_view.jsonl`

- Cases: 200
- Pairs: 100
- Safe: 100
- Unsafe: 100
- Design: hard-paired neutral generic actions with contract-dependent slot/token rules
- Generic-visible fields are pair-identical or near-identical by construction.
- Contract-aware fields expose only `contract_rule_id` and `contract_rule_summary`.

## Motivation

v4 showed that contract-aware judgments could separate generic-ambiguous pairs, but only 10 / 100 pairs were generic-ambiguous. v5 was built to remove that weakness by making the generic-visible action text neutral and contract-dependent across the full dataset.

## v5 Result

Gap analysis:

- Generic ambiguous pairs: 100 / 100
- Contract separated pairs: 100 / 100
- Hybrid separated pairs: 100 / 100
- Contract success on generic-ambiguous pairs: 100 / 100
- Hybrid success on generic-ambiguous pairs: 100 / 100

Pair-level pattern:

- Generic gap: 0.000
- Contract gap: 1.000
- Hybrid gap: 0.450

## Interpretation

v5 demonstrates the intended split-view effect:

> When the generic-visible action is semantically neutral and the operative rule is only visible in the contract, generic judgments remain ambiguous while contract-aware judgments separate safe and unsafe paired cases.

This is stronger than v3 and v4 because all 100 pairs are generic-ambiguous under the configured threshold.

## Important Caveat

The generic frozen judgments were normalized into HELIX schema after the model produced schema-invalid but conceptually consistent uncertainty judgments. The raw model output used values such as `unclear` and `investigate`, which are not valid HELIX enum values. These were normalized to:

- `goal_alignment = ambiguous`
- `constraint_status = ambiguous`
- `authority_status = ambiguous`
- `allowed_tool_misuse = ambiguous`
- `risk_level = warn`
- `violation_probability = 0.50`

The contract-aware judgments were also normalized from compact ALLOW/DENY outputs into the full HELIX semantic judgment schema.

Therefore this evidence should be described as a frozen normalized replay artifact, not a pure unmodified model-emission artifact.

## Remaining Work

Before making a stronger publication-style claim, HELIX should add:

1. Raw-output archival for generic and contract-aware model emissions.
2. Control-run scoring for:
   - no-violation controls,
   - swap controls,
   - irrelevant-rule controls.
3. Token-overlap/Jaccard diagnostics between generic-visible text and contract summaries.
4. Bootstrap analysis grouped by template family rather than naïve per-pair sampling.
5. A stricter model-output validator that rejects schema-invalid generations before normalization.
