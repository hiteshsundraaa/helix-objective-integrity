# HELIX v0.6.4 Split-View Evidence Checkpoint

## Test State

- Full test suite: 105 passed.
- v3 split-view leakage receipt: clean.
- v4 paired split-view dataset validation: valid, no validation issues.

## v3 Split-View Leakage Receipt

Dataset:

- `benchmarks/blind_cases/mock_workspace_blind_v3_split_view.jsonl`

Result:

- Total cases: 100
- Generic contaminated cases: 0
- Generic contaminated fields: 0
- Generic prompt renderable: true
- Contract-aware prompt renderable: true
- Split-view receipt clean: true

Interpretation:

v3 now validates the split-view prompt-surface and leakage-receipt machinery. The generic prompt can be rendered without leaking contract rule IDs, contract summaries, labels, or label reasons.

## v3 Semantic Benchmark Result

Dataset:

- `mock_workspace_blind_v3_split_view`

Observed result:

- `contract-generic TPR = +0.000` at all reported budget levels.

Interpretation:

v3 does not demonstrate measurable contract-aware lift. Generic semantic ranking is already strong enough on v3, so contract-aware mode has no room to improve under the current ranked-budget metric.

v3 should be cited as a clean receipt/protocol validation fixture, not as the main contract-lift evidence fixture.

## v4 Paired Ambiguous Protocol

Dataset:

- `benchmarks/blind_cases/mock_workspace_blind_v4_paired_split_view.jsonl`

Validation result:

- Total cases: 200
- Unsafe: 100
- Safe: 100
- Valid: true
- Validation issues: none

Gap analysis result:

- Pairs: 100
- Generic ambiguity threshold: 0.15
- Contract separation threshold: 0.30
- Generic ambiguous pairs: 10
- Contract separated pairs: 100
- Hybrid separated pairs: 100
- Contract success on generic-ambiguous pairs: 10
- Hybrid success on generic-ambiguous pairs: 10

Interpretation:

v4 provides the stronger contract-dependence evidence. Contract-aware judgments separate all 100 safe/unsafe pairs. On the 10 pairs where generic mode is ambiguous under the configured threshold, contract-aware mode resolves all 10.

## Important Limitation

Most v4 pairs are still generically separable:

- Many pairs have generic gap = 1.000.
- Only 10 / 100 pairs are generic-ambiguous under the current threshold.

Therefore, v4 supports a narrower claim:

> HELIX can construct paired split-view cases where generic mode is ambiguous and contract-aware mode resolves the distinction.

It does not yet support the stronger claim that generic mode broadly fails across the full v4 dataset.

## Current Honest Claim

HELIX v0.6.4 now has:

1. A clean split-view leakage receipt protocol.
2. A v3 fixture proving generic/contract-aware prompt-surface hygiene.
3. A v4 paired ambiguous fixture showing contract-aware separation on all generic-ambiguous pairs.
4. A validator that recognizes directional A/B paired rule IDs without false warning floods.

## Next Research Step

Build v5 hard-paired split-view cases where the majority of pairs are generic-ambiguous by construction.

Target v5 acceptance criteria:

- At least 60 / 100 pairs generic-ambiguous under threshold 0.15.
- At least 90 / 100 pairs contract-separated under threshold 0.30.
- Contract success on generic-ambiguous pairs at least 85%.
- No generic prompt contamination.
- Dataset validation clean.
