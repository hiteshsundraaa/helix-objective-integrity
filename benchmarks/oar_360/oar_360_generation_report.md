# OAR-360 Deterministic Case Generation Report

## Purpose
OAR-360 materializes the v4.1 Objective Authorization Receipts benchmark blueprint into deterministic cases for future empirical evaluation. This generation run makes no provider calls and contains no model outputs.

## Suite Composition
- Total cases: 360
- Evidence level: 0
- Generator version: oar_360_generator_v1
- Case file hash: `sha256:b5c4f199c8699ea2e882811414037245039bbdfe2acf744adcf6118850aea6fd`
- Manifest hash: `sha256:1455966f7fb3feb98ac3f843efd161cdf0d6214b508e075af0c7e23909626f90`

## Family Distribution
| Family | Count |
|---|---:|
| adjacent_rule_distractor | 30 |
| benign_noise | 30 |
| citation_failure_control | 30 |
| clean_compliance | 30 |
| cross_document_scope_conflict | 30 |
| direct_violation | 30 |
| disguised_violation | 30 |
| locally_safe_globally_drifted | 30 |
| missing_evidence | 30 |
| near_boundary_authority_ambiguity | 30 |
| stale_rule_conflict | 30 |
| tool_permission_mismatch | 30 |

## Domain Distribution
| Domain | Count |
|---|---:|
| HR_policy | 36 |
| customer_support | 36 |
| cybersecurity_triage | 36 |
| data_governance | 36 |
| finance_ops | 36 |
| healthcare_admin | 36 |
| insurance_claims | 36 |
| legal_contract_review | 36 |
| procurement | 36 |
| research_compliance | 36 |

## Label Distribution
| Label | Count |
|---|---:|
| ambiguous | 90 |
| locally_safe_globally_drifted | 60 |
| safe | 90 |
| unsafe | 120 |

## Risk Band Distribution
| Risk Band | Count |
|---|---:|
| clearly_safe | 30 |
| high_risk | 60 |
| low_risk_benign_noise | 30 |
| moderate_risk_likely_drift | 90 |
| severe_direct_violation | 90 |
| uncertain_weak_concern | 60 |

## Expected Decision Distribution
| Expected Decision | Count |
|---|---:|
| ALLOW | 60 |
| BLOCK | 90 |
| DEGRADE | 60 |
| ESCALATE_FOR_APPROVAL | 60 |
| QUARANTINE | 30 |
| WARN | 60 |

## Edge Case Tags
| Edge Tag | Count |
|---|---:|
| adjacent_rule | 59 |
| ambiguous_delegation | 58 |
| authority_chain_gap | 32 |
| benign_trace_noise | 58 |
| citation_required | 58 |
| citation_span_scope | 59 |
| conflicting_evidence | 31 |
| cross_document_override | 58 |
| delegated_authority | 32 |
| evidence_recency | 32 |
| global_objective_drift | 57 |
| missing_evidence | 59 |
| missing_marker | 31 |
| near_threshold_action | 30 |
| operational_noise | 58 |
| policy_addendum_override | 33 |
| same_domain_distractor | 31 |
| scope_boundary | 60 |
| stale_memory | 31 |
| stale_policy | 59 |
| tool_action_mismatch | 31 |
| tool_permission_split | 59 |
| trajectory_drift | 33 |
| wrong_rule_citation | 31 |

## What This Supports
This artifact supports deterministic benchmark construction, distribution auditing, case hashing, and future prompt/judgment collection against a fixed OAR-360 suite.

## What This Does Not Prove
This artifact does not prove provider performance, HELIX gate selectivity, receipt validity on model outputs, Level 4 evidence, or production readiness. It contains no empirical model judgments.

## Limitations
- Generated cases are deterministic benchmark design artifacts, not model outputs.
- Evidence level is 0 until independent provider judgments are collected and analyzed.
- Ground-truth fields are for analysis only and must not be rendered into model prompts.
- The suite does not modify or replace OAR-30 pilot evidence.

## Next Steps
- Render provider-neutral prompts from the generated cases.
- Collect independent raw provider outputs without modifying ground truth.
- Validate imported outputs through the existing HELIX receipt pipeline.
- Run integrity, consistency, and reportability audits on the resulting evidence.

## Validation Issues
None.
