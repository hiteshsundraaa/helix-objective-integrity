# HELIX v10.17 Three-Agent Manual Consistency Pilot Report

## Executive Summary

- consistency_run_id: `three_agent_manual_fixture_v1`
- system_count: `3`
- case_count: `30`
- consistency_evidence_level: `3`
- majority_decision_rate: `1.000000`
- severe_disagreement_rate: `0.033333`

This is the first empirical cross-system HELIX receipt check if real outputs are provided. No live API calls were made by HELIX; outputs were manually collected.

## Execution Mode

- execution_mode: `manual_import`
- no live API calls were made by HELIX
- provider SDKs were not used
- outputs were manually collected

## Systems Compared

- `system_a`: `google` / `gemini-flash-2.0` status `needs_work` level `3`
- `system_b`: `anthropic` / `claude-sonnet-4-6` status `needs_work` level `3`
- `system_c`: `openai` / `gpt-4o` status `needs_work` level `3`

## Fixed Inputs

- same case set required
- same contract and schema required
- same provider run plan required

## Separate Provenance

- separate raw outputs required
- separate parsed judgments required
- separate receipt chains required
- one provider failure is not silently dropped

## Per-System Evidence

- `system_a` receipts `30` invalid `0` chain_complete `true` blocking `['diagnostics_status_blocks_level_4', 'execution_mode_not_live_blocks_level_4', 'integrity_failure_blocks_level_4', 'normalization_status_blocks_level_4', 'score_collapse_blocks_level_4']`
- `system_b` receipts `30` invalid `0` chain_complete `true` blocking `['diagnostics_status_blocks_level_4', 'execution_mode_not_live_blocks_level_4', 'integrity_failure_blocks_level_4', 'normalization_status_blocks_level_4', 'score_collapse_blocks_level_4']`
- `system_c` receipts `30` invalid `0` chain_complete `true` blocking `['diagnostics_status_blocks_level_4', 'execution_mode_not_live_blocks_level_4', 'normalization_status_blocks_level_4']`

## Per-Case Consistency

- per_case_record_count: `30`

## Aggregate Consistency Metrics

- unanimous_decision_rate: `0.966667`
- majority_decision_rate: `1.000000`
- mean_pairwise_score_distance: `0.014667`
- p95_pairwise_score_distance: `0.000000`
- risk_band_unanimous_rate: `0.966667`
- risk_band_majority_rate: `1.000000`
- all_receipts_valid_rate: `1.000000`

## Disagreement Taxonomy

- `citation_grounding_disagreement`: `1`
- `contract_phrase_selection_disagreement`: `1`
- `decision_boundary_disagreement`: `1`
- `score_calibration_disagreement`: `1`
- `unknown`: `29`

## Severe Disagreements

- `v10_case_0035`: `['citation_grounding_disagreement', 'contract_phrase_selection_disagreement', 'decision_boundary_disagreement', 'score_calibration_disagreement']`

## Vendor-Bias Controls

- at least three independent systems required
- per-provider metrics reported before aggregate metrics
- no majority vote used to relabel truth
- failed providers included in reports

## Consistency Evidence Level

- consistency_evidence_level: `3`
- manual consistency evidence capped at Level 3
- Level 4 requires locked live runs
- Level 5 false

## What This Supports

- HELIX can compare authorization receipts from independently collected provider outputs on the same case set.
- HELIX can preserve disagreements and emit a consistency receipt without treating agreement as truth.

## What This Does Not Prove

- Consistency is not correctness.
- Majority vote is not truth.
- This does not prove provider correctness.
- This does not prove Level 4 or Level 5 evidence.
- This does not prove production readiness.

## Limitations

- Manual collection is not locked live-runner provenance.
- Provider outputs are not repaired to improve consistency.
- Agreement can reflect shared priors or shared benchmark exposure.

## Next Steps

- v10.18 should run real three-system provider outputs under the registered protocol.
- Future Level 4 requires locked live runs.

## Consistency Receipt

```json
{
  "all_receipts_valid_rate": 1.0,
  "case_count": 30,
  "consistency_evidence_level": 3,
  "consistency_hash": "sha256:4989f41dda19d237d192690d1fa2ae46c88703b5f240f39acfb1976f2ff9ca20",
  "consistency_not_correctness": true,
  "consistency_run_id": "three_agent_manual_fixture_v1",
  "constraints_enforced": [
    "three_independent_systems_minimum",
    "same_case_set_required",
    "separate_raw_outputs_required",
    "separate_receipt_chains_required",
    "no_majority_vote_truth_claim",
    "failed_provider_not_silently_dropped",
    "disagreement_taxonomy_required",
    "per_provider_metrics_before_aggregate",
    "manual_consistency_level_cap_3",
    "level_5_reserved"
  ],
  "execution_mode": "manual_import",
  "individual_run_evidence_levels": {
    "system_a": 3,
    "system_b": 3,
    "system_c": 3
  },
  "level_4_allowed": false,
  "level_5_allowed": false,
  "majority_decision_rate": 1.0,
  "majority_vote_truth_claim_allowed": false,
  "provider_outputs_combined_for_truth": false,
  "receipt_id": "v10.17:three_agent_manual_fixture_v1:three_agent_manual_consistency",
  "receipt_type": "three_agent_manual_consistency_pilot",
  "severe_disagreement_rate": 0.03333333333333333,
  "system_count": 3,
  "unanimous_decision_rate": 0.9666666666666667,
  "version": "v10.17"
}
```
