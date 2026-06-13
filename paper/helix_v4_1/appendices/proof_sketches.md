# Appendix B: Proof Sketches

## Conditional Gate Soundness Under Sound Post-Action Over-Approximation

Let \(G\) be a gate that blocks when a sound over-approximation of the post-action state leaves the authorization basin. The important condition is post-action over-approximation: the gate must evaluate a set containing all possible states after executing the proposed action, not merely the current state. If the over-approximation is sound and the authorization predicate is conservative, then an allowed action is not known to leave the basin under the model. This is conditional soundness, not absolute safety.

## Finite-Time Accumulation of Contradiction Pressure

Suppose each step can introduce contradiction pressure relative to \(C_0\). If pressure is non-negative and some sequence has positive lower-bounded contradiction increments, then finite-time threshold crossing occurs. This motivates trajectory-level checks.

## Recursive Memory Information Decay Under No Contract Reinjection

If contract information is only carried through agent memory and each memory transformation can drop or distort contract tokens, then repeated transformations can reduce recoverable objective information. Contract reinjection or external receipt checks are needed to avoid relying solely on self-maintained memory.

## Self-Certification Failure Under Co-Corrupted References

If an agent and its reference memory are co-corrupted, self-certification can verify the corrupted state against corrupted references. External objective contracts are required for independent authorization checks.

## Decision Agreement Does Not Imply Grounding Agreement

Let evaluators \(E_i\) produce pairs \((d_i, g_i)\), where \(d_i\) is a decision and \(g_i\) is grounding evidence. It is possible that all \(d_i\) are equal while \(g_i\) differ or are missing. Therefore decision agreement does not imply grounding agreement.

## Evidence Validity Separates Behavioral Safety From Authorization Validity

An action may have low behavioral risk under local semantics while lacking required evidence under the contract. Thus behavioral safety and authorization validity are separate predicates.
