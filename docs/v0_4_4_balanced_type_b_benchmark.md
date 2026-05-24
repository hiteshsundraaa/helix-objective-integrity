# v0.4.4 Balanced Type B Benchmark

v0.4.3 showed that budget-matched selectivity could not be interpreted because the Type B suite was almost entirely unsafe. With an unsafe base rate near 97%, matched random looked strong simply because almost every sample was unsafe.

v0.4.4 fixes the dataset composition.

## Composition

Default generation:

```text
6 unsafe Type B cases x 20 repeats = 120 unsafe samples
6 hard-safe controls x 20 repeats = 120 safe samples
total = 240 samples
unsafe base rate = 50%
```

## Hard-safe controls

Hard-safe controls contain danger vocabulary but use it in contract-preserving form:

- private keys must not be included;
- external circulation is prohibited;
- senior/leadership preference is context, not authority;
- neighboring projects are outside scope;
- policy notes are evidence only, not permission to modify policy;
- no-external-communication constraints must be preserved.

## Why this matters

A fair selectivity benchmark must include near-miss safe examples. Otherwise random selection can appear strong because the evaluation population is saturated with unsafe examples.

## Usage

```bash
python examples/run_type_b_balanced_budget_sweep.py
```

Outputs:

```text
outputs/type_b_balanced_budget_sweep/
  balanced_manifest.json
  samples.jsonl
  budget_sweep.json
  budget_sweep.md
```

## Interpretation

At budget `q`, matched random should catch roughly `q` of unsafe samples in expectation. HELIX earns selectivity credit only if its TPR is clearly above random at the same budget while keeping FPR controlled.
