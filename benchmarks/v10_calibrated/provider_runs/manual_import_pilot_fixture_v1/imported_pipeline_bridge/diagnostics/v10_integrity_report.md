# HELIX Benchmark Integrity Audit

## Executive Summary

- integrity_passed: `false`
- hard_issue_count: `2`
- soft_issue_count: `0`
- integrity_hash: `sha256:958fa5c8764ed4108cab52436f03d7e3acbadc03437b9be221bb76183c4c1102`

## Score Distribution

- score_entropy: `-0.000000`
- score_variance: `0.000000`
- score_collapse_detected: `true`
- max_score_bin_fraction: `1.000000`

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
- lower_threshold_flip_rate: `0.000000`
- upper_threshold_flip_rate: `0.000000`
- threshold_sensitivity_delta: `0.000000`
- result_sensitive_to_threshold: `false`

## Shuffled Label Baseline

- true_tpr_at_budget: `0.214286`
- mean_shuffled_tpr_at_budget: `0.201429`
- selectivity_delta_vs_shuffled: `0.012857`
- beats_shuffled_labels: `false`
- shuffled_label_trials: `500`
- selection_budget: `0.200000`
- mean_random_tpr_at_budget: `0.204714`
- random_tpr_std_at_budget: `0.085477`
- selectivity_delta_vs_random: `0.009571`
- random_baseline_trials: `500`
- random_baseline_seed: `42`

## Leakage / Circularity

- leakage_rate: `0.000000`
- contract_rule_in_generic_fields: `false`

## Issues and Warnings

- issue: `score_collapse_detected`
- issue: `does_not_beat_shuffled_labels`
- No soft integrity warnings detected.

High-overlap family clustering is unavailable because no qualifying cases or family metadata were present.

## What This Supports

- This integrity audit checks whether benchmark results are likely responding to labels rather than leakage, score collapse, or threshold artifacts.

## What This Does Not Yet Prove

- It does not prove external validity.
- It does not replace human audit.
- It does not prove production safety.
- The shuffled-label test is only one falsifiability check.
- Deterministic synthetic datasets still require external validation.
