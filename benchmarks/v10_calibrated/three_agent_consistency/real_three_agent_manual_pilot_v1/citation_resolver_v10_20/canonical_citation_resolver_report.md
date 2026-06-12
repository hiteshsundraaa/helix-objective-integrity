# HELIX v10.20 Canonical Citation Resolver Prototype

## Executive Summary

v10.19 found decision-level agreement but citation/grounding instability. This prototype derives canonical citation phrases from contract text only and measures whether valid citation scope disagreements can be reduced without hiding missing or hallucinated citations.

- source_run_id: `real_three_agent_manual_pilot_v1`
- case_count: `30`
- pre_resolution_string_disagreement_rate: `0.566667`
- v10_19_post_normalization_disagreement_rate: `1.000000`
- post_resolution_disagreement_rate: `0.400000`
- confidence_weighted_post_resolution_disagreement_rate: `0.377778`
- success_criterion_passed: `true`
- failure_criterion_triggered: `false`

## Pre-Registration

- preregistration_schema: `v10_canonical_citation_resolver_preregistration_v1`
- pre_registered_before_result_analysis: `true`
- target_post_resolution_disagreement_rate: `0.3`
- min_overlap_threshold: `0.4`
- resolution_confidence_threshold: `0.6`
- pre_registered_at_commit: `1176043997bb0d6c31171d3d6195df258072f8b9`

## Source Empirical Finding

- source_consistency_hash: `sha256:ac1b12539f0c2b76ae2fca6a21aff6fecd6379de1f54809b92a2e5f7fa518eb9`
- majority_decision_rate: `1.0`
- unanimous_decision_rate: `0.7333333333333333`
- severe_disagreement_rate: `0.6666666666666666`

## Problem Decomposition

- Missing citation: not a resolver problem; it is flagged separately.
- Scope disagreement: resolver target; valid spans may map to canonical contract phrases.
- Hallucinated citation: detection problem; flagged and not resolved.
- Unanimous citation: already stable; passed through unchanged.

## Canonical Vocabulary Extraction

- Canonical phrases are derived from `contract_rule_summary` only.
- The resolver does not use observed disagreement distribution to design vocabulary.
- The resolver records every canonical phrase in `canonical_phrase_vocabulary.jsonl`.

## Resolution Method

- Exact substring matches receive confidence 1.0.
- Normalized substring matches receive confidence 0.90.
- Token-overlap matches are capped below exact/normalized evidence.
- Fuzzy matches are weaker evidence than exact/normalized matches.
- Hallucinated or missing citations are not force-mapped.

## Agreement Before and After Resolution

- pre_resolution_string_disagreement_rate: `0.566667`
- post_resolution_disagreement_rate: `0.400000`
- improvement_over_v10_19_normalization: `0.600000`

## Confidence-Weighted Agreement

- mean_weighted_citation_agreement: `0.622222`
- confidence_weighted_post_resolution_disagreement_rate: `0.377778`

## Failure Mode Registry

- `citation_not_in_contract`: `1`
- `input_citation_empty`: `10`

## Missing Citations Are Not Resolver Successes

- missing_citation_rate: `0.333333`
- Missing citations remain unresolved and cannot increase compliance-grade agreement.

## Hallucinated Citations Are Flagged, Not Resolved

- hallucinated_citation_rate: `0.033333`
- Hallucinated citations are not mapped onto canonical phrases by token overlap.

## Scope Disagreements

- scope_disagreement_resolved_rate: `0.833333`
- Resolver success is measured mainly on scope disagreements.

## Product Implication: From Behavioral Evidence to Compliance Evidence

Authorization receipts are only compliance-grade if the cited contract phrase is stable across runs and systems. HELIX currently produced decision-stable but citation-unstable receipts. The canonical citation resolver is a candidate component for upgrading receipts from behavioral evidence to compliance evidence, but only if it resolves scope disagreement without hiding missing or hallucinated citations.

## What This Supports

- This supports a deterministic prototype for contract-derived canonical citation anchors.
- This supports separating missing, hallucinated, and scope-disagreement cases.
- This supports measuring citation-stability improvements without provider calls.

## What This Does Not Prove

- This does not prove compliance-grade receipts yet.
- This does not prove provider correctness.
- This does not prove majority-vote truth.
- This does not prove Level 4 or Level 5 evidence.
- This does not prove semantic equivalence of different citations.

## Limitations

- The resolver uses deterministic text matching, not semantic matching.
- Token-overlap resolution is lower confidence than exact or normalized substring evidence.
- Missing citations remain prompt/schema compliance failures outside resolver scope.
- Ambiguous canonical phrase matches remain unresolved.

## Next Steps

1. Audit high-impact unresolved scope disagreements.
2. Add stricter citation output requirements in future real-pilot prompts.
3. Evaluate canonical phrase IDs directly in future receipt schemas.
4. Preserve Level 3 limits until locked live-runner provenance exists.
