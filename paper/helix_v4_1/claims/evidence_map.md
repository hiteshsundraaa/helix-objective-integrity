# HELIX v4.1 Evidence Map

## C1 Receipt Reproducibility

- Claim: Objective Authorization Receipts can deterministically bind contract, case, raw output, normalized judgment, protocol manifest, and evidence level.
- Mathematical object: Hash-linked receipt tuple `(contract, case, raw_output, normalized_judgment, manifest, evidence_level)`.
- Empirical metric: Receipt-chain completeness and recomputable hashes.
- Current evidence: `all_receipts_valid_rate = 1.0` in OAR-30.
- Artifact paths: `consistency_receipt.json`, `per_system_receipt_chain_hashes.json`, `system_registry.json`.
- Falsification: Receipt hashes or chain hashes cannot be recomputed.
- Not yet shown: Locked live-runner provenance.

## C2 Behavioral-Grounding Separability

- Claim: Decision agreement and grounding agreement are separable.
- Mathematical object: Pair of agreement relations, `A_decision` and `A_grounding`.
- Empirical metric: Majority decision agreement versus citation disagreement.
- Current evidence: decision majority 1.000, raw citation disagreement 0.567.
- Artifact paths: `consistency_summary.json`, `disaggregated_severe_rates.json`.
- Falsification: Larger preregistered studies show no measurable separability.
- Not yet shown: OAR-360 replication.

## C3 Evidence Validity Axis

- Claim: Behavioral low risk does not imply authorization-valid evidence.
- Mathematical object: Receipt-aware risk decomposed into behavior and evidence validity.
- Empirical metric: Missing citation cases among low-risk or allowed judgments.
- Current evidence: v10.21 found 10 missing-citation instances.
- Artifact paths: `missing_citation_cases.jsonl`, `elicitation_preparation_summary.json`.
- Falsification: Receipt schema can ignore missing evidence without changing authorization validity.
- Not yet shown: Completed second-pass elicitation partition.

## C4 Canonical Resolution Bounded Utility

- Claim: Canonical resolution reduces scope disagreement but not missing or hallucinated citations.
- Mathematical object: Partial function from valid citation spans to canonical contract phrases.
- Empirical metric: Scope disagreement resolved rate and unresolved failure modes.
- Current evidence: scope disagreement resolved rate 0.833; missing citation rate 0.333 remains.
- Artifact paths: `citation_resolver_summary.json`, `resolver_failure_modes.json`.
- Falsification: A resolver validly resolves missing/hallucinated citations without false agreement.
- Not yet shown: OAR-360 resolver behavior.

## C5 Missing Citation Compliance Gap

- Claim: Missing citations are first-pass compliance failures.
- Mathematical object: Receipt validity predicate requiring grounding evidence.
- Empirical metric: Missing-citation rate and elicitation outcomes.
- Current evidence: v10.21 prompt package prepared; second pass pending.
- Artifact paths: `elicitation_manifest.json`, `prompt_lint_report.json`.
- Falsification: Retroactive citation repair is shown to preserve original receipt semantics.
- Not yet shown: Recoverability versus persistent failure rates.

## C6 Temporal Objective Integrity

- Claim: Long-horizon objective integrity is trajectory-level.
- Mathematical object: Temporal objective state `x_t` and trajectory predicate over state transitions.
- Empirical metric: Future trajectory-level violation detection.
- Current evidence: Formal definitions and proof sketches only.
- Artifact paths: `formal_definitions.md`, `proof_sketches.md`.
- Falsification: A formal reduction to independent local action labels.
- Not yet shown: Large trajectory benchmark.

## C7 Gate Value Requires Matched Friction

- Claim: Runtime gate value requires matched-friction baselines.
- Mathematical object: Selectivity delta under fixed intervention budget.
- Empirical metric: TPR/FPR versus matched-friction random and allowlist-only baselines.
- Current evidence: Hostile baseline infrastructure exists for earlier evidence surfaces.
- Artifact paths: `outputs/hostile_baselines/v5/hostile_baseline_summary.json`, `benchmark_hypotheses.md`.
- Falsification: Gate-value claims are accepted without matched-friction controls.
- Not yet shown: OAR-360 gate-value results.
