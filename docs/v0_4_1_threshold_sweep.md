# v0.4.1 Threshold Sweep

The v0.4 Type B benchmark showed that HELIX beat allowlist-only but tied matched-friction random blocking under hard `BLOCK` evaluation.

That result is useful but incomplete because HELIX has multiple intervention states:

```text
ALLOW / WARN / DEGRADE / QUARANTINE / BLOCK
```

A Type B unsafe action may be detected as `WARN` or `DEGRADE` without crossing the hard-block threshold. v0.4.1 adds a threshold sweep to test this.

## Thresholds

- `block_only`
- `quarantine_or_higher`
- `degrade_or_higher`
- `warn_or_higher`

For each HELIX threshold, random blocking is matched to the same intervention rate.

## Usage

```bash
python examples/run_type_b_threshold_sweep.py
```

Outputs:

```text
outputs/type_b_threshold_sweep/
  samples.jsonl
  threshold_sweep.json
  threshold_sweep.md
```

## Interpretation

If HELIX beats random at `degrade_or_higher` or `warn_or_higher`, the gate is detecting Type B risk but the hard-block threshold is too strict.

If HELIX still does not beat random even at `warn_or_higher`, the extractor/scoring is not selecting the right unsafe states.
