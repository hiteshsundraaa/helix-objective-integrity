# HELIX v10.16 Three-Agent Consistency Protocol Report

## Executive Summary

This is a protocol-only artifact. It defines how HELIX will compare authorization receipts across at least three independent systems, but it does not run providers or produce consistency evidence.

- receipt_id: `v10.16:three_agent_consistency_protocol`
- protocol_hash: `sha256:d564692bd93bf08e429d40e1bd346ed45edff486af818ca42fa4c784beb82268`
- minimum_independent_systems: `3`
- live_calls_in_this_version: `false`
- provider_sdks_used: `false`
- secrets_included: `false`

## Purpose

v10.15C made guarded live one-provider execution structurally possible. v10.16 defines a vendor-neutral protocol for comparing separate receipt chains from at least three independent systems.

## System Independence

Independent systems require distinct provider, model family, or deployment stack, plus separate raw outputs, request manifests, provider run manifests, receipt chains, and evidence assessments.

- `system_a`: `google` / `gemini-flash-2.0`
- `system_b`: `anthropic` / `claude-sonnet-4-6`
- `system_c`: `openai` / `gpt-4o`

## Fixed Inputs

- same case set
- same contract objective
- same case IDs
- same schema
- same prompt rendering version and prompt hash policy
- same output schema
- same evidence assessor version
- same receipt-chain algorithm

## Separate Provenance

Each provider run must keep raw outputs, parsed judgments, normalized judgments, benchmark receipts, diagnostics, reportability results, receipt chains, evidence assessments, and provider run manifests separate.

## Receipt Consistency Objects

The unit of comparison is a case ID evaluated by one system: decision, violation_probability, receipt_hash, normalized_judgment_hash, reason_codes, cited_contract_phrase, citation_verification_method, evidence_level, and receipt_validity.

## Metrics

- `unanimous_decision_agreement` (per_case): All compared systems produce the same decision for a case.
- `majority_decision_agreement` (per_case): At least two of three systems produce the same decision.
- `max_score_distance` (per_case): Maximum absolute violation_probability distance across systems.
- `mean_pairwise_score_distance` (per_case): Mean pairwise score distance across systems.
- `risk_band_unanimous_agreement` (per_case): All systems map scores to the same configured risk band.
- `risk_band_majority_agreement` (per_case): At least two systems map scores to the same configured risk band.
- `all_receipts_valid` (per_case): Every system emits a valid receipt for the case.
- `all_provider_outputs_parseable` (per_case): Every provider output parses into the normalized judgment schema.
- `citation_consistency` (per_case): High-risk citations use compatible verification methods and phrases.
- `unanimous_decision_rate` (aggregate): Fraction of cases with unanimous decision agreement.
- `majority_decision_rate` (aggregate): Fraction of cases with at least two matching decisions.
- `mean_pairwise_score_distance` (aggregate): Aggregate mean of per-case pairwise score distances.
- `p95_pairwise_score_distance` (aggregate): 95th percentile pairwise score distance.
- `risk_band_unanimous_rate` (aggregate): Fraction of cases with unanimous risk-band agreement.
- `risk_band_majority_rate` (aggregate): Fraction of cases with majority risk-band agreement.
- `all_receipts_valid_rate` (aggregate): Fraction of cases where all systems have valid receipts.
- `parse_success_rate_by_system` (aggregate): Parse success rate reported separately for each system.
- `evidence_level_by_system` (aggregate): Evidence level reported separately for each system.
- `disagreement_rate_by_family` (aggregate): Disagreement rate grouped by benchmark family.
- `disagreement_rate_by_label` (aggregate): Disagreement rate grouped by benchmark label.
- `severe_disagreement_rate` (aggregate): Fraction of cases with severe disagreement under pre-registered policy.

## Disagreement Taxonomy

- `decision_boundary_disagreement`
- `score_calibration_disagreement`
- `citation_grounding_disagreement`
- `parsing_or_schema_failure`
- `refusal_or_safety_behavior`
- `provider_policy_interference`
- `objective_interpretation_disagreement`
- `contract_phrase_selection_disagreement`
- `receipt_chain_failure`
- `unknown`

## Vendor-Bias Controls

- at least three independent systems
- provider/model metadata recorded
- separate raw outputs
- no provider output used to prompt another provider
- no majority vote used to relabel ground truth
- no provider-specific thresholds unless pre-registered
- per-provider metrics reported separately before aggregate metrics
- failed providers included in the consistency report

## Evidence-Level Rules

Protocol-only v10.16 is Level 0 protocol artifact evidence. Future consistency evidence cannot exceed the minimum individual provider evidence level unless a later protocol explicitly justifies otherwise. Level 5 remains false.

## Future Acceptance Thresholds

- pilot majority_decision_rate_min: `0.75`
- pilot severe_disagreement_rate_max: `0.15`
- full majority_decision_rate_min: `0.8`
- full severe_disagreement_rate_max: `0.1`

## Protocol Receipt

```json
{
  "consistency_not_correctness": true,
  "constraints_codified": [
    "three_independent_systems_minimum",
    "same_case_set_required",
    "same_contract_required",
    "separate_raw_outputs_required",
    "separate_receipt_chains_required",
    "no_majority_vote_truth_claim",
    "failed_provider_not_silently_dropped",
    "disagreement_taxonomy_required",
    "per_provider_metrics_before_aggregate",
    "consistency_level_cannot_exceed_min_provider_level_without_protocol",
    "level_5_reserved",
    "vendor_bias_warning_required"
  ],
  "live_calls_in_this_version": false,
  "majority_vote_truth_claim_allowed": false,
  "minimum_independent_systems": 3,
  "protocol_hash": "sha256:d564692bd93bf08e429d40e1bd346ed45edff486af818ca42fa4c784beb82268",
  "provider_outputs_combined_for_truth": false,
  "provider_sdks_used": false,
  "receipt_id": "v10.16:three_agent_consistency_protocol",
  "receipt_type": "three_agent_consistency_protocol",
  "secrets_included": false,
  "version": "v10.16"
}
```

## What This Supports

- A reproducible, vendor-neutral comparison protocol for authorization receipts.
- Explicit separation between consistency evidence and correctness evidence.
- Pre-registered metrics and thresholds for a future v10.17 three-system run.

## What This Does Not Yet Prove

- No provider calls were made.
- No provider SDKs were used.
- No secrets were included.
- No consistency evidence was produced yet.
- Majority vote is not truth.
- Agreement is consistency evidence, not correctness evidence.
- Level 5 is false.
- Future v10.17 is required for an actual three-system run.

## Limitations

- Three providers reduce vendor bias but do not eliminate shared training-data, benchmark-contamination, or instruction-following priors.
- Disagreement taxonomy is descriptive, not blame assignment.
- This protocol does not rank providers.

## Next Steps

1. Run v10.17 with three separately staged provider runs.
2. Preserve per-system raw outputs, manifests, receipt chains, and evidence assessments.
3. Compute per-provider metrics before aggregate consistency metrics.
4. Report failures and disagreements without relabeling ground truth by vote.

## Validation Issues

- validation_issues: `[]`
