# Appendix A: Formal Definitions

## Objective Contract

An objective contract \(C_0\) is an immutable external artifact specifying authorized objectives, constraints, evidence requirements, and scope. It is external to the acting agent's self-report.

## Temporal Objective State

The temporal objective state is \(x_t = (g_t, r_t, f_t, a_t, m_t, c_t, q_t)\), representing goal, runtime context, facts, proposed action, memory, contract context, and query state.

## Authorization Basin

An authorization basin is a subset of temporal states for which the active contract, context, and evidence support continued execution without objective-integrity violation.

## Evidence Validity

Evidence validity is a predicate over a judgment or receipt requiring that cited evidence is present, exact or verifiably normalized, and linked to the active contract.

## Receipt-Aware Risk

Receipt-aware risk decomposes action risk into behavioral risk and evidence-validity risk.

## Evaluator Judgment

An evaluator judgment is a normalized structured assessment of a case or tool call, including decision, score, reason codes, citation fields, and verification metadata.

## Receipt

A receipt is a hash-linked artifact binding contract, case, raw output or trace, normalized judgment, decision, evidence level, and manifest.

## Receipt-Chain Completeness

Receipt-chain completeness holds when every expected case or system output has a corresponding receipt and every receipt hash links to the declared preimage.

## Decision Agreement

Decision agreement holds when evaluators assign the same action-level decision label, such as ALLOW, BLOCK, or ESCALATE_FOR_APPROVAL.

## Score Distance

Score distance is the absolute difference between normalized violation probability or risk scores across evaluators.

## Risk-Band Agreement

Risk-band agreement holds when evaluators assign the same risk band after mapping scores to preregistered bands.

## Citation Agreement

Citation agreement holds when evaluators cite the same non-empty contract phrase, or the same canonical contract phrase after a preregistered resolver.

## Grounding Agreement

Grounding agreement holds when evaluators cite valid, contract-supported evidence with compatible scope and verification method.

## Behavioral-Grounding Gap

The behavioral-grounding gap is the difference between action-level agreement and grounding agreement.

## Evidence Levels

Evidence levels classify provenance strength. Manual imports are capped at Level 3. Level 4 or Level 5 requires stronger locked provenance and is not claimed here.
