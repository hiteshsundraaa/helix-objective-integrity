# HELIX v10 Case Generation Report

## Executive Summary

- status: `complete`
- total_cases: `300`
- seed: `42`
- generator_overlap_mean: `0.088863`
- high_overlap_case_count: `0`

No judgments were collected. No observed scores were produced. Target score bands are preregistered generation targets only, not model outputs. There is no reportability claim yet; the future v10 runner must pass the v10 reportability gate.

## Family Distribution

- `clean_compliance`: `30`
- `direct_violation`: `30`
- `near_boundary_authority_ambiguity`: `30`
- `locally_safe_globally_drifted`: `30`
- `stale_rule_conflict`: `30`
- `adjacent_rule_distractor`: `30`
- `benign_noise`: `30`
- `disguised_violation`: `30`
- `missing_evidence`: `30`
- `citation_failure_control`: `30`

## Label Distribution

- `safe`: `70`
- `unsafe`: `100`
- `ambiguous`: `100`
- `locally_safe_globally_drifted`: `30`

## Target Score-Band Distribution

- `clearly_safe`: `20`
- `low_risk_benign_noise`: `35`
- `uncertain_weak_concern`: `65`
- `moderate_risk_likely_drift`: `80`
- `high_risk`: `65`
- `severe_direct_violation`: `35`

## Mid-Risk / Near-Boundary Coverage

- mid_risk_fraction: `0.600000`
- near_boundary_fraction: `0.483333`

## Anti-Leakage / Overlap Audit

- generator_overlap_mean: `0.088863`
- generator_overlap_max: `0.206897`
- label_in_case_id_count: `0`
- generic_contract_leakage_count: `0`

## High-Overlap Cases

- None.

## Warnings

- `safe_label_fraction_below_v10_design_target`

## What This Supports

- This artifact supports deterministic v10 scaffold generation with family balance, target-band diversity, and pre-run leakage diagnostics.

## What This Does Not Yet Prove

- It does not prove v10 reportability.
- It does not contain live model judgments.
- It does not contain normalized judgments, benchmark scores, or receipts.
- Target score bands are design metadata, not observed calibration.
- Future v10 evidence must pass the generic integrity audit and the v10 reportability gate.

## Limitations

- These are deterministic synthetic cases, not human-audited enterprise data.
- Label balance follows the family protocol and is not itself a reportability claim.
- Overlap diagnostics use simple token Jaccard overlap, not semantic similarity.
