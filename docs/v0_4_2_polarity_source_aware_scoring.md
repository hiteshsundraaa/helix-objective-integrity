# v0.4.2 Polarity and Source-Aware Scoring

v0.4.1 showed a core bug: HELIX was treating danger vocabulary in preserved constraints as if it were a proposed violation.

Example:

```text
Do not reveal secrets.
```

was scored similarly to:

```text
Reveal the secret.
```

This patch adds polarity/source-aware scoring.

## New module

```text
helix/scoring/polarity.py
```

It classifies text as:

- `constraint_preserving`
- `violation_seeking`
- `ambiguous`

## Field-aware scoring

`forbidden_pressure.py` now accepts:

```python
rationale=...
memory=...
context=...
```

instead of only one concatenated text blob.

Risk weighting is source-aware:

- rationale: high signal
- context: medium signal
- memory: low signal, and ignored when constraint-preserving

## Authority divergence

`authority_divergence.py` is now source-aware. A retrieved or rationale-adopted authority expansion can raise risk. Memory preserving the contract should not.

## Claim boundary

This patch fixes polarity/source false positives. It does not solve subtle semantic implication. The next major step remains the LLM-assisted extractor.
