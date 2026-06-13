# Appendix C: Schema Descriptions

## Objective Contract

Fields: `contract_id`, `contract_hash`, `active_rule_id`, `active_rule_summary`, `allowed_actions`, `forbidden_actions`, `evidence_requirements`, `scope`.

## Model Judgment

Fields: `case_id`, `provider`, `model`, `decision`, `violation_probability`, `risk_band`, `reason_codes`, `cited_contract_phrase`, `citation_verification_method`, `normalization_status`.

## Raw Output Manifest

Fields: `provider`, `model`, `raw_output_file`, `raw_output_hash`, `collection_method`, `collection_timestamp`, `manual_import`.

## Receipt

Fields: `receipt_type`, `case_id`, `contract_hash`, `raw_output_hash`, `normalized_judgment_hash`, `decision`, `evidence_level`, `receipt_hash`.

## Receipt Chain

Fields: `system_role`, `receipt_count`, `receipt_hashes`, `receipt_chain_hash`, `chain_complete`, `invalid_receipt_count`.

## Consistency Summary

Fields: `consistency_run_id`, `system_count`, `case_count`, `majority_decision_rate`, `risk_band_majority_rate`, `mean_pairwise_score_distance`, `severe_disagreement_rate`, `consistency_hash`, `evidence_level`.

## Disagreement Analysis

Fields: `decision_disagreement_rate`, `score_disagreement_rate`, `risk_band_disagreement_rate`, `citation_string_disagreement_rate`, `citation_validity_disagreement_rate`, `grounding_severe_rate`, `dominant_disagreement_dimensions`.

## Citation Resolver Output

Fields: `case_id`, `canonical_phrases`, `resolved_by_system`, `raw_citation_agreement`, `resolved_citation_agreement`, `weighted_resolved_agreement`, `resolver_category`, `failure_mode`.

## Citation Elicitation Output

Fields: `case_id`, `decision`, `violation_probability`, `cited_contract_phrase`, `citation_verification_method`, `reason_codes`, `uncertainty_reason`.
