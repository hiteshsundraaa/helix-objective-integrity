# v0.6.2 Split-View Dataset Balance Validator

## Purpose

v0.6.1 proved the split-view runner works, but the first blind_v3 dataset contained:

```text
Unsafe: 50
Safe: 0
```

That makes FPR, precision, and selectivity deltas meaningless. Every ranked selector appears perfect because every case is unsafe.

## Adds

```text
helix/benchmark/split_view_validator.py
examples/validate_split_view_dataset.py
tests/test_split_view_validator.py
docs/prompts/blind_v3_safe_case_append_prompt.md
```

## Validator checks

The validator fails on:

```text
too few safe cases
too few unsafe cases
severe safe/unsafe imbalance
families with only safe or only unsafe cases
strata with only safe or only unsafe cases
invalid tools
duplicate case IDs
missing generic rationale
missing contract rule ID/summary
```

It warns on:

```text
unpaired contract rules
uncertified authoring order
generic fields not leakage checked
too few cases per family
```

## Usage

```bash
python examples/validate_split_view_dataset.py \
  --cases benchmarks/blind_cases/mock_workspace_blind_v3_split_view.jsonl
```

## Next step

Use `docs/prompts/blind_v3_safe_case_append_prompt.md` to generate 50 safe split-view cases, append them to the current blind_v3 file, then rerun validation.
