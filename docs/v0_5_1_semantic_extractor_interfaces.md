# v0.5.1 Semantic Extractor Interfaces

v0.5.1 adds the semantic extractor interfaces needed for the v0.5 experiment.

## What this adds

```text
helix/extract/llm_semantic_extractor.py
helix/extract/fake_semantic_extractor.py
helix/benchmark/semantic_baselines.py
```

## Modes

Two extractor modes are defined:

```text
generic
contract_aware
```

The generic judge sees only the action/rationale/memory/context. The contract-aware judge sees the signed contract and allowed/forbidden boundaries.

## Why this matters

The central v0.5 question is not whether an LLM can classify suspicious text. The question is whether contract-aware semantic extraction adds value over generic semantic judgment.

## Evidence boundary

The deterministic fake extractor is only for CI and benchmark wiring. It must not be treated as empirical evidence.

Provider-backed LLM extractors come later.
