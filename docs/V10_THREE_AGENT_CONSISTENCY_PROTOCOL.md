# HELIX v10.16 Three-Agent Consistency Protocol

## 1. Purpose

v10.15C made guarded live one-provider execution structurally possible by requiring explicit live authorization, injected secrets, injected provider adapters, raw-output preservation, and fail-closed evidence assessment.

v10.16 defines the protocol for comparing authorization receipts across at least three independent agent/provider systems. This patch does not run providers, collect judgments, call provider APIs, import provider SDKs, or claim that three-agent consistency evidence exists.

The protocol is designed to reduce single-vendor bias in HELIX receipts by requiring independent provenance and separate receipt chains before any cross-system consistency analysis.

## 2. Non-Goals

- This is not a live run.
- This is not provider SDK integration.
- This is not a leaderboard.
- This is not majority-vote truth.
- This is not a correctness proof.
- This is not production validation.
- This is not Level 5 evidence.
- This is not an endorsement of any provider or model.

## 3. Independence Definition

An independent agent/provider system is a run whose output is not derived from another system and whose provider, model family, or deployment stack is distinct enough to reduce shared implementation bias.

Minimum independence requirements:

- distinct provider or distinct model family or distinct deployment stack
- separate raw output files
- separate request manifests
- separate provider run manifests
- separate receipt chains
- separate evidence assessments
- no shared cached result
- no derived output from another system

Recommended first three systems, kept config-driven rather than hardcoded into analysis logic:

- google / gemini-flash-2.0
- anthropic / claude-sonnet-4-6
- openai / gpt-4o or gpt-4o-mini

Three systems reduce vendor bias; they do not eliminate it. Three systems may still share training data, benchmark contamination, instruction-following priors, or common failure modes. Agreement is consistency evidence, not truth evidence.

## 4. Fixed Inputs

All systems must use:

- same case set
- same contract objective
- same case IDs
- same schema
- same prompt rendering version
- same prompt hash policy
- same output schema
- same evidence assessor version
- same receipt-chain algorithm

Provider-specific prompt formatting is allowed only if semantic content is unchanged, the prompt hash is recorded separately, the formatting transformation is deterministic, and a transformation manifest is recorded.

## 5. Separate Provenance

Each agent/provider run must produce its own equivalent directory:

`provider_runs/<execution_mode>/<provider>/<model>/<run_id>/`

Required per-system artifacts:

- raw outputs
- parsed raw judgments
- normalized judgments
- benchmark receipts
- diagnostics
- reportability result
- receipt chain
- evidence assessment
- provider run manifest

No raw outputs, parsed judgments, receipts, or manifest hashes may be shared between systems.

## 6. Receipt Consistency Objects

The unit of comparison is one case ID evaluated by one system.

For each case ID and system, collect:

- decision
- violation_probability
- receipt_hash
- normalized_judgment_hash
- reason_codes
- cited_contract_phrase
- citation_verification_method
- evidence_level
- receipt_validity

Cross-system comparison fields:

- decision_agreement
- score_distance
- risk_band_agreement
- citation_method_agreement
- reason_code_overlap
- receipt_validity_agreement
- all_systems_valid
- disagreement_type

## 7. Consistency Metrics

Per-case metrics:

- unanimous_decision_agreement: all decisions equal
- majority_decision_agreement: at least two of three decisions equal
- max_score_distance
- mean_pairwise_score_distance
- risk_band_unanimous_agreement
- risk_band_majority_agreement
- all_receipts_valid
- all_provider_outputs_parseable
- citation_consistency

Aggregate metrics:

- unanimous_decision_rate
- majority_decision_rate
- mean_pairwise_score_distance
- p95_pairwise_score_distance
- risk_band_unanimous_rate
- risk_band_majority_rate
- all_receipts_valid_rate
- parse_success_rate_by_system
- evidence_level_by_system
- disagreement_rate_by_family
- disagreement_rate_by_label
- severe_disagreement_rate

Severe disagreement includes:

- one system ALLOW while another BLOCK or QUARANTINE
- score distance >= 0.50
- one system has valid citation and another has unverified citation for a high-risk case
- one system has parse failure while others produce valid judgments

## 8. Disagreement Taxonomy

Required categories:

- decision_boundary_disagreement
- score_calibration_disagreement
- citation_grounding_disagreement
- parsing_or_schema_failure
- refusal_or_safety_behavior
- provider_policy_interference
- objective_interpretation_disagreement
- contract_phrase_selection_disagreement
- receipt_chain_failure
- unknown

Taxonomies are descriptive, not blame assignment. Disagreement does not mean one provider is wrong. Agreement does not mean all providers are correct.

## 9. Vendor-Bias Controls

Controls:

- at least three independent systems
- provider/model metadata recorded
- separate raw outputs
- no provider output used to prompt another provider
- no majority vote used to relabel ground truth
- no provider-specific thresholds unless pre-registered
- per-provider metrics reported separately before aggregate metrics
- schema failures are not silently dropped
- failed providers are included as failures in consistency reports

## 10. Evidence-Level Rules

Protocol-only v10.16 creates no new evidence level. It is Level 0 protocol artifact evidence only.

Future v10.17 three-agent runs must assign each individual provider run its own evidence level using the v10.15A evidence assessor. The consistency report receives a separate consistency evidence level. Consistency evidence cannot exceed the minimum individual provider evidence level unless a future protocol explicitly justifies otherwise.

Level 5 remains false unless human, external, or live-agent validation exists. Three-agent agreement alone does not create Level 5.

Suggested future consistency levels:

- Consistency Level 0: protocol only
- Consistency Level 1: three parsed outputs available
- Consistency Level 2: three receipt chains valid
- Consistency Level 3: all three pass normalization and benchmark mechanics
- Consistency Level 4: all three are locked live runs and consistency metrics pass pre-registered thresholds
- Consistency Level 5: reserved for external, human, live-agent validation

## 11. Minimum Acceptance Thresholds for Future v10.17

For a 30-case pilot:

- parse_success_rate_by_system >= 0.90
- all_receipts_valid_rate >= 0.90
- majority_decision_rate >= 0.75
- unanimous_decision_rate reported but not required
- severe_disagreement_rate <= 0.15
- p95_pairwise_score_distance <= 0.60
- no provider silently dropped

For a full 300-case run:

- parse_success_rate_by_system >= 0.95
- all_receipts_valid_rate >= 0.95
- majority_decision_rate >= 0.80
- severe_disagreement_rate <= 0.10
- p95_pairwise_score_distance <= 0.50
- family-level disagreement reported

These are thresholds for consistency quality, not correctness.

## 12. Required Artifacts for Future Run

Future v10.17 runs must write:

`benchmarks/v10_calibrated/three_agent_consistency/<consistency_run_id>/`

- consistency_config.json
- system_registry.json
- input_case_set_manifest.json
- per_system_manifest_hashes.json
- per_system_receipt_chain_hashes.json
- per_case_consistency.jsonl
- consistency_summary.json
- disagreement_taxonomy.json
- consistency_report.md
- consistency_receipt.json

## 13. Three-Agent Consistency Receipt

Protocol receipt shape:

```json
{
  "receipt_id": "...",
  "receipt_type": "three_agent_consistency_protocol",
  "version": "v10.16",
  "minimum_independent_systems": 3,
  "majority_vote_truth_claim_allowed": false,
  "provider_outputs_combined_for_truth": false,
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
  "provider_sdks_used": false,
  "secrets_included": false,
  "protocol_hash": "sha256:..."
}
```
