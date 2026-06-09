# HELIX Benchmark Integrity Audit

## Executive Summary

- integrity_passed: `true`
- hard_issue_count: `0`
- soft_issue_count: `1`
- integrity_hash: `sha256:c2338e39105ac8daf590492548b801da070b6683bb8366e16dbfdd61a617642e`

## Score Distribution

- score_entropy: `2.296140`
- score_variance: `0.057612`
- score_collapse_detected: `false`
- max_score_bin_fraction: `0.233333`

## Generator Independence

- token_overlap_mean: `0.117437`
- token_overlap_max: `0.171429`
- high_overlap_case_count: `0`
- high_overlap_case_ids: `[]`
- high_overlap_cases_path: `v10_high_overlap_cases.jsonl`
- high_overlap_cases_hash: `null`
- high_overlap_family_counts: `{}`
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
- lower_threshold_flip_rate: `0.233333`
- upper_threshold_flip_rate: `0.000000`
- threshold_sensitivity_delta: `0.233333`
- result_sensitive_to_threshold: `true`

## Shuffled Label Baseline

- true_tpr_at_budget: `0.428571`
- mean_shuffled_tpr_at_budget: `0.207286`
- selectivity_delta_vs_shuffled: `0.221286`
- beats_shuffled_labels: `true`
- shuffled_label_trials: `500`
- selection_budget: `0.200000`
- mean_random_tpr_at_budget: `0.204714`
- random_tpr_std_at_budget: `0.085477`
- selectivity_delta_vs_random: `0.223857`
- random_baseline_trials: `500`
- random_baseline_seed: `42`

## Leakage / Circularity

- leakage_rate: `0.000000`
- contract_rule_in_generic_fields: `false`

## Issues and Warnings

- No hard integrity issues detected.
- warning: `result_sensitive_to_threshold`

High-overlap family clustering is unavailable because no qualifying cases or family metadata were present.

## What This Supports

- This integrity audit checks whether benchmark results are likely responding to labels rather than leakage, score collapse, or threshold artifacts.

## What This Does Not Yet Prove

- It does not prove external validity.
- It does not replace human audit.
- It does not prove production safety.
- The shuffled-label test is only one falsifiability check.
- Deterministic synthetic datasets still require external validation.
