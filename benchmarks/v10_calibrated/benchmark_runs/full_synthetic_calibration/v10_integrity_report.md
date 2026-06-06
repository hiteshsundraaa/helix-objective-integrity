# HELIX Benchmark Integrity Audit

## Executive Summary

- integrity_passed: `true`
- hard_issue_count: `0`
- soft_issue_count: `1`
- integrity_hash: `sha256:12ddc61f3e778587e2644a1af4c822db829832fff240d8744ef629e9bf615e04`

## Score Distribution

- score_entropy: `3.136805`
- score_variance: `0.065334`
- score_collapse_detected: `false`
- max_score_bin_fraction: `0.173333`

## Generator Independence

- token_overlap_mean: `0.114734`
- token_overlap_max: `0.228571`
- high_overlap_case_count: `8`
- high_overlap_case_ids: `['v10_case_0249', 'v10_case_0255', 'v10_case_0243', 'v10_case_0245', 'v10_case_0246', 'v10_case_0258', 'v10_case_0261', 'v10_case_0270']`
- high_overlap_cases_path: `v10_high_overlap_cases.jsonl`
- high_overlap_cases_hash: `sha256:f699b078894b7cdee962c0342e39eb948423567e56629744a363bf48fd0c0c52`
- high_overlap_family_counts: `{'missing_evidence': 8}`
- high_overlap_diagnostic_threshold: `0.200000`
- generator_independence: `true`
- benchmark_family: `v10_fixture`
- applied_generator_independence_threshold: `0.150000`
- threshold_source: `global_default`
- threshold_justification: `null`

## Threshold Sensitivity

- threshold_primary: `0.850000`
- threshold_delta: `0.050000`
- threshold_lower: `0.800000`
- threshold_upper: `0.900000`
- lower_threshold_flip_rate: `0.106667`
- upper_threshold_flip_rate: `0.066667`
- threshold_sensitivity_delta: `0.106667`
- result_sensitive_to_threshold: `false`

## Shuffled Label Baseline

- true_tpr_at_budget: `0.461538`
- mean_shuffled_tpr_at_budget: `0.197308`
- selectivity_delta_vs_shuffled: `0.264231`
- beats_shuffled_labels: `true`
- shuffled_label_trials: `500`
- selection_budget: `0.200000`
- mean_random_tpr_at_budget: `0.198985`
- random_tpr_std_at_budget: `0.025788`
- selectivity_delta_vs_random: `0.262554`
- random_baseline_trials: `500`
- random_baseline_seed: `42`

## Leakage / Circularity

- leakage_rate: `0.000000`
- contract_rule_in_generic_fields: `false`

## Issues and Warnings

- No hard integrity issues detected.
- warning: `high_overlap_cases_detected`

High-overlap cases are grouped by available family metadata:
- `missing_evidence`: `8`

## What This Supports

- This integrity audit checks whether benchmark results are likely responding to labels rather than leakage, score collapse, or threshold artifacts.

## What This Does Not Yet Prove

- It does not prove external validity.
- It does not replace human audit.
- It does not prove production safety.
- The shuffled-label test is only one falsifiability check.
- Deterministic synthetic datasets still require external validation.
