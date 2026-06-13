# HELIX v4.1: Objective Authorization Receipts and the Behavioral-Grounding Gap

## Abstract

HELIX studies Objective Authorization Receipts (OARs): auditable artifacts that bind a candidate agent action to an external objective contract, normalized judgment, protocol manifest, evidence level, and receipt chain. The central thesis is that decision agreement and grounding agreement are separable. In the current OAR-30 real three-agent manual pilot, independent systems reached majority decision agreement of 1.000 and risk-band majority agreement of 1.000, while raw citation disagreement was 0.567, citation validity disagreement was 0.333, and grounding severe rate was 0.367. A canonical citation resolver reduced post-resolution disagreement to 0.400 but did not resolve missing citations. Evidence remains Level 3 manual evidence. This paper skeleton states the formal setting, current evidence, negative results, and reproducibility package. It makes no model correctness claim, no majority-vote truth claim, no production safety claim, and no Level 4 or Level 5 evidence claim.

## 1 Introduction

Long-horizon agents are commonly evaluated by measuring whether their final or local action appears safe, useful, or correct. HELIX examines a narrower authorization question: whether the action is grounded in the active external objective contract and whether that grounding is captured in a receipt. The OAR-30 pilot suggests a behavioral-grounding gap: systems can converge on what action to take while diverging on the cited contract phrase that authorizes or blocks the action.

The current empirical basis is preliminary. It consists of a real three-agent manual pilot over 30 cases and follow-on analyses. Manual evidence is capped at Level 3. Citation stability remains unresolved. Second-pass elicitation results are pending unless future artifacts are added under the v10.21 elicitation directory.

## 2 Related Work Map

HELIX sits at the intersection of agent authorization, formal verification, benchmark design, tool-use governance, audit logging, and AI safety evaluations. The paper should map related work without claiming novelty over all adjacent areas:

- Agent tool-use evaluation: local task success and misuse benchmarks.
- Constitutional and policy-based agent control: instruction-level guardrails and policy compliance.
- Capability security: reference monitors, least privilege, and authorization checks.
- Auditability and provenance: signed logs, manifests, and reproducible evidence chains.
- Debate, self-critique, and multi-agent agreement: consensus is useful but not truth.
- Formal methods for runtime assurance: sound over-approximation and pre-action gates.

## 3 Formal Problem Setting

Let an objective contract be an immutable external artifact \(C_0\). Let a trajectory have temporal state \(x_t = (g_t, r_t, f_t, a_t, m_t, c_t, q_t)\), where the terms denote goal, runtime context, facts, proposed action, memory, contract context, and query state. A candidate action \(a_t\) is authorization-valid only if it is supported by \(C_0\) and by evidence that can be checked independently of the acting agent's self-report.

HELIX distinguishes behavioral risk from authorization validity. A behaviorally low-risk action may still be authorization-invalid if the receipt lacks exact grounding evidence.

## 4 Objective Authorization Receipts

An Objective Authorization Receipt binds:

- contract identity and contract hash;
- case or trace identity;
- raw provider output hash where available;
- normalized judgment;
- cited contract phrase and verification method;
- gate or analysis decision;
- evidence level;
- manifest hash;
- receipt hash or receipt-chain hash.

A receipt is not a proof of model correctness. It is an audit artifact that makes authorization evidence inspectable and falsifiable.

## 5 Behavioral-Grounding Gap

The behavioral-grounding gap is the difference between agreement on action-level decisions and agreement on grounding evidence. In OAR-30, majority decision agreement was 1.000 while raw citation disagreement was 0.567. This gap is invisible to evaluations that only measure allow/block agreement.

The current evidence supports separability, not correctness. Majority agreement is not truth.

## 6 OAR-Bench Protocol

OAR-Bench is planned as a family of benchmark suites:

- OAR-30: current real manual pilot; preliminary signal.
- OAR-360: planned primary paper benchmark.
- OAR-720: planned robustness and ablation benchmark.

Each case must specify a contract, action context, expected evidence conditions, label, family, and artifact manifest. Future benchmark expansion must be preregistered and must preserve negative controls.

## 7 Formal Results

The paper will develop formal results as conditional claims, not unconditional guarantees:

1. Gate soundness is conditional on the gate evaluating a sound over-approximation of the post-action state.
2. Contradiction pressure can accumulate over finite trajectories.
3. Without contract reinjection, memory-only objective references can decay.
4. Self-certification fails under co-corrupted references.
5. Decision agreement does not imply grounding agreement.
6. Evidence validity separates behavioral safety from authorization validity.

Proof sketches are in Appendix B.

## 8 Experimental Setup

Current setup:

- Three independent manually collected provider outputs.
- Same 30-case set.
- Same required schema and contract materials.
- Separate raw outputs.
- Separate receipt chains.
- No majority-vote truth claim.
- Manual import mode.
- Evidence capped at Level 3.

No live provider APIs are called by the analysis scripts.

## 9 Results

Current OAR-30 headline metrics:

- Majority decision agreement: 1.000.
- Unanimous decision agreement: 0.733.
- Risk-band majority agreement: 1.000.
- Risk-band unanimous agreement: 0.833.
- Mean pairwise score distance: 0.074.
- p95 pairwise score distance: 0.350.
- Raw citation disagreement: 0.567.
- Citation validity disagreement: 0.333.
- Grounding severe rate: 0.367.
- Composite severe disagreement: 0.667.
- Evidence level: 3.

The consistency thresholds did not pass. This is a negative result that should remain visible.

## 10 Disaggregated Disagreement Analysis

v10.19 disaggregated composite severe disagreement. Decision severe disagreement was 0.000, while grounding severe rate was 0.367 and citation string disagreement was 0.567. The dominant disagreement dimensions were citation string disagreement and contract phrase selection disagreement.

This supports the behavioral-grounding separability claim, not a correctness claim.

## 11 Canonical Citation Resolution

v10.20 introduced a canonical citation resolver derived from contract text. It reduced post-resolution disagreement to 0.400 and resolved 5 of 6 scope-disagreement cases. It did not resolve missing citations or the one hallucinated citation. The strict target of post-resolution disagreement below 0.300 was not met.

## 12 Citation Elicitation Compliance Test

v10.21 prepared 10 second-pass elicitation prompts for system-level missing citation instances. These prompts exclude first-pass decision, first-pass score, and first-pass reason codes. The second pass is not repair and cannot upgrade original receipts.

Second-pass elicitation results are pending unless files are present under `citation_elicitation_v10_21/second_pass_raw_outputs/`.

## 13 Threats to Validity

- OAR-30 is small.
- Outputs were manually collected.
- Evidence is capped at Level 3.
- Provider diversity is limited.
- Citation disagreement may depend on prompt wording.
- Contract wording may influence citation stability.
- Current results do not prove production safety.
- Current results do not establish model correctness.
- Second-pass elicitation is pending.

## 14 Reproducibility

The repository includes scripts and manifests for the current evidence chain. See `reproducibility/reproduction_commands.md`. Reproduction should verify hashes, inspect manifests, and preserve raw outputs.

## 15 Conclusion

HELIX v4.1 frames Objective Authorization Receipts as a research object for studying external objective grounding. The current evidence suggests that behavioral agreement and grounding agreement can diverge. The paper's next step is not stronger rhetoric; it is larger preregistered OAR-Bench experiments, second-pass elicitation analysis, and locked live-runner provenance.

## Appendix A: Formal Definitions

See [formal_definitions.md](appendices/formal_definitions.md).

## Appendix B: Proof Sketches

See [proof_sketches.md](appendices/proof_sketches.md).

## Appendix C: Schemas

See [schemas.md](appendices/schemas.md).

## Appendix D: Artifact Hashes

Current key hashes:

- consistency_hash: `sha256:ac1b12539f0c2b76ae2fca6a21aff6fecd6379de1f54809b92a2e5f7fa518eb9`
- disagreement_analysis_manifest_hash: `sha256:34cc5ad4405cb280e8e8fc0dda48f8b7ebc8bba32b073636404a1a5cc72c228c`
- citation_resolver_manifest_hash: `sha256:e2537a8bfab2bdc4f5377d9bfb655971048d11bd5b610cfc78ec4ca462ae6d56`
- elicitation_manifest_hash: `sha256:a00a5e2d02dbc72d15b1d519dd31fdf90c6b6c6603fdbdf7a04e869990ecbafd`

## Appendix E: Full Metric Tables

See [main_results_table.md](tables/main_results_table.md) and [negative_results_table.md](tables/negative_results_table.md).

## Appendix F: Negative Results

The current package preserves the following negative results: consistency thresholds did not pass; composite severe disagreement is high; the resolver did not meet the strict target below 0.300; missing citation rate remains 0.333 before elicitation; evidence remains Level 3.
