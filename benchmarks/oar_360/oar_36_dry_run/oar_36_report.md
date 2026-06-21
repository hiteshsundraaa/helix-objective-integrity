# OAR-36 Dry-Run Pilot Extraction Report

## Executive Summary
OAR-36 is a locked dry-run subset extracted from OAR-360 to validate manual collection, import validation, parser behavior, and reviewer-visible evidence discipline. No provider calls were made, no model outputs were created, and no empirical results were created.

## Source Artifacts
- `benchmarks/oar_360/oar_360_cases.jsonl`
- `benchmarks/oar_360/prompts/oar_360_prompt_pack.jsonl`
- `benchmarks/oar_360/prompts/ground_truth_holdout/oar_360_ground_truth_holdout.jsonl`

## Selection Method
Selection is deterministic and family-first: exactly three cases are chosen from each OAR-360 family, greedily preferring coverage of domains, labels, expected decisions, risk bands, and edge tags.

## Selection Distributions
- total_cases: `36`
- family_distribution: `{'adjacent_rule_distractor': 3, 'benign_noise': 3, 'citation_failure_control': 3, 'clean_compliance': 3, 'cross_document_scope_conflict': 3, 'direct_violation': 3, 'disguised_violation': 3, 'locally_safe_globally_drifted': 3, 'missing_evidence': 3, 'near_boundary_authority_ambiguity': 3, 'stale_rule_conflict': 3, 'tool_permission_mismatch': 3}`
- domain_distribution: `{'HR_policy': 3, 'customer_support': 3, 'cybersecurity_triage': 4, 'data_governance': 3, 'finance_ops': 4, 'healthcare_admin': 4, 'insurance_claims': 4, 'legal_contract_review': 4, 'procurement': 4, 'research_compliance': 3}`
- label_distribution: `{'ambiguous': 9, 'locally_safe_globally_drifted': 6, 'safe': 9, 'unsafe': 12}`
- expected_decision_distribution: `{'ALLOW': 6, 'BLOCK': 9, 'DEGRADE': 6, 'ESCALATE_FOR_APPROVAL': 6, 'QUARANTINE': 3, 'WARN': 6}`
- risk_band_distribution: `{'clearly_safe': 3, 'high_risk': 6, 'low_risk_benign_noise': 3, 'moderate_risk_likely_drift': 9, 'severe_direct_violation': 9, 'uncertain_weak_concern': 6}`
- distinct_edge_tags: `24`

## Prompt/Holdout Separation
- OAR-36 prompts are derived from OAR-360 prompt records.
- Ground truth is not exposed in the prompt pack.
- OAR-36 holdout records are separated from prompts and are not for model prompting.

## Raw Output Plan
- expected_raw_output_file_count: `3`
- Raw outputs must be saved exactly under provider-specific directories.
- Do not edit malformed rows or fill missing citations.

## What This Supports
- Provider prompt usability checks.
- Manual raw-output collection workflow checks.
- JSON schema, citation-field, import-validation, and parser dry-run checks.

## What This Does Not Prove
- This dry-run does not prove model correctness.
- This dry-run does not estimate full OAR-360 performance.
- This dry-run does not produce scored benchmark results.

## Limitations
- OAR-36 is a protocol validation subset, not a replacement for OAR-360.
- No provider calls are made and no model outputs are created.
- No empirical results or performance claims are produced by this extraction.
- Manual dry-run evidence remains capped at Level 3.
- Manual evidence is capped at Level 3.
- Level 4/5 are not claimed.

## Next Steps
- Use OAR-36 prompt pack only for dry-run collection.
- Validate raw outputs with the raw import validator.
- Review schema and parser behavior before scaling to OAR-360.
