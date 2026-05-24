# v0.5.2 Hybrid Semantic Adjudicator

v0.5.2 adds the hybrid adjudication layer that combines:

```text
heuristic HELIX decision
generic semantic judgment
contract-aware semantic judgment
```

## Files

```text
helix/extract/semantic_adjudicator.py
helix/benchmark/hybrid_semantic_scoring.py
```

## Modes

```text
balanced
conservative
heuristic_first
```

## Evidence boundary

This patch still uses deterministic fake extractors in tests. It is not empirical evidence.

The goal is to wire the v0.5 comparison architecture before provider-backed LLM runs.

## Product mapping

For the State-Lease Broker, this layer becomes the lease-transition risk adjudicator:

```text
lease proposes next side-effect
→ heuristic HELIX fast path
→ generic/contract-aware semantic judge if needed
→ hybrid score
→ continue / warn / pause / quarantine / human review / revoke
```
