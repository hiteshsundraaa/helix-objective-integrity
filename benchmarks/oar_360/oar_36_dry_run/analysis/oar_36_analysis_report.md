# OAR-36 Scoring and Disagreement Analysis Report

## Executive Summary
Analysis state is `awaiting_receipt_preparation` with 0 scored rows across 0 cases. no provider calls were made, no fake outputs were generated, and no synthetic judgments were created.

## Analysis State
- analysis_state: `awaiting_receipt_preparation`
- empirical_results_created: `false`
- ground_truth_used_for_scoring: `false`

## Inputs
- receipt_preparation_count: `0`
- receipt_ready_count: `0`

## Scored Coverage
- scored_row_count: `0`
- scored_case_count: `0`

## Decision and Risk Scoring
- majority_decision_agreement_rate: `None`
- risk_band_majority_agreement_rate: `None`

## Citation and Grounding Scoring
- strict_grounding_valid_rate: `None`
- missing_citation_rate: `None`

## Disagreement Analysis
- case_count_with_any_score: `0`
- complete_case_count_all_systems: `0`
- mean_pairwise_score_distance: `None`

## Behavioral-Grounding Gap
- mean_delta_bg: `None`
- cases_with_positive_gap: `0`

## Family Breakdown
- family_count: `0`

## Evidence Boundary
- no provider calls were made.
- no fake outputs were generated.
- no synthetic judgments were created.
- majority vote is not truth.
- model correctness is not claimed.
- OAR-36 is a dry-run subset and does not estimate full OAR-360 performance.
- manual evidence is capped at Level 3.
- Level 4/5 are not claimed.

## What This Supports
- Holdout scoring for real parsed receipt-prep rows only.
- System-level and family-level dry-run diagnostics.
- Disagreement and behavioral-grounding-gap measurement without treating agreement as truth.

## What This Does Not Prove
- This does not prove model correctness.
- This does not create OAR-360 performance claims.
- This does not turn manual dry-run evidence into Level 4 or Level 5 evidence.

## Limitations
- Scores real receipt-prep rows against OAR-36 holdout. If no receipt rows exist, emits awaiting state.
- OAR-36 is a dry-run subset and does not estimate full OAR-360 performance.
- Majority vote is preserved as disagreement evidence, not truth.
- Model correctness is not claimed.
- Manual evidence remains capped at Level 3.
- Receipt-prep import state: awaiting_raw_outputs

## Next Steps
- Collect raw OAR-36 provider outputs.
- Run receipt preparation without repairing provider rows.
- Re-run this analysis only over receipt-ready rows.
