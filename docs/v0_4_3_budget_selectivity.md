# v0.4.3 Budget-Matched Selectivity Sweep

v0.4.2a fixed false positives from polarity/source confusion, but threshold sweep still showed weak selectivity versus matched random. HELIX caught many unsafe states, but at a high intervention rate, so random caught nearly as many.

This patch evaluates HELIX as a risk-ranking governor.

## Question

At a fixed intervention budget, does HELIX select more unsafe Type B samples than matched random?

## Method

For each sample, compute:

```text
HELIX risk_score
```

Then for budgets:

```text
q = 0.05, 0.10, 0.20, 0.30, 0.50
```

select the top `q` fraction by HELIX risk and compare against:

- matched random at the same budget;
- prompt-filter rank at the same budget.

## Usage

```bash
python examples/run_type_b_budget_sweep.py
```

Outputs:

```text
outputs/type_b_budget_sweep/
  samples.jsonl
  budget_sweep.json
  budget_sweep.md
```

## Interpretation

A positive HELIX-minus-random TPR gap means HELIX's risk ranking is selecting unsafe states better than an equal-cost null.

A zero gap means HELIX is not more selective than suppression at the same budget, even if its thresholded TPR looks high.
