# Pre-Registered Benchmark Hypotheses

## H1 Majority Decision Agreement Exceeds Grounding Agreement

- Metric: majority decision agreement minus grounding agreement.
- Expected direction: positive.
- Falsification condition: grounding agreement equals or exceeds majority decision agreement across OAR-360 without meaningful behavioral-grounding gap.
- Required artifacts: consistency summary, disagreement analysis, citation classification distribution.
- Allowed evidence level: 3 until locked live-runner provenance exists.

## H2 Hard Families Increase Citation Disagreement

- Metric: family-level citation disagreement rate.
- Expected direction: `missing_evidence`, `locally_safe_globally_drifted`, and `cross_document_scope_conflict` exceed `clean_compliance`.
- Falsification condition: these families do not show higher citation disagreement under preregistered OAR-360 evaluation.
- Required artifacts: family-level disagreement table.
- Allowed evidence level: 3.

## H3 Canonical Resolution Has Bounded Utility

- Metric: scope disagreement resolved rate and unresolved missing/hallucinated rate.
- Expected direction: canonical resolution reduces scope disagreement but does not reduce missing-citation failures.
- Falsification condition: missing citations are resolved as valid canonical citations without second-pass evidence or false agreement.
- Required artifacts: citation resolver summary and failure modes.
- Allowed evidence level: 3.

## H4 Elicitation Partitions Missing Citation Cases

- Metric: outcome distribution across same-decision valid citation, same-decision missing citation, different-decision, contract authoring gap, and malformed second pass.
- Expected direction: second pass partitions missing citations into recoverable omissions, persistent grounding failures, and decision-instability cases.
- Falsification condition: second-pass outputs cannot be parsed or do not distinguish these buckets.
- Required artifacts: second-pass raw outputs, parsed outputs, first-vs-second comparisons.
- Allowed evidence level: 3.

## H5 Matched-Friction Gate Value Requirement

- Metric: selectivity delta versus matched-friction random blocking and allowlist-only baselines.
- Expected direction: semantic gating must outperform matched-friction random and allowlist-only baselines.
- Falsification condition: HELIX gate does not outperform matched-friction random or allowlist-only at the same intervention budget.
- Required artifacts: hostile baseline summary, baseline decisions, threshold snapshot.
- Allowed evidence level: 3.
