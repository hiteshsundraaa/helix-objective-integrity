# v0.5.8 Blind v2 Validation Harness

## Purpose

blind_v2 is more complex than blind_v1 because it includes contract-dependence metadata and idiosyncratic reversal cases.

Before rendering prompts or generating semantic judgments, validate that the case file is structurally sound.

## Adds

```text
helix/benchmark/blind_v2_validator.py
examples/validate_blind_v2.py
tests/test_blind_v2_validator.py
```

## Checks

The validator checks:

```text
expected total cases
safe/unsafe balance
valid tools
duplicate case ids
presence of rationale
minimum reversal cases
minimum idiosyncratic/reversal cases
minimum intended high-dependence cases
contract_rule_id and contract_rule_summary for idiosyncratic/reversal cases
safe/unsafe pairing per contract_rule_id
```

## Usage

```bash
python examples/validate_blind_v2.py \
  --cases benchmarks/blind_cases/mock_workspace_blind_v2.jsonl
```

Outputs:

```text
outputs/blind_v2_validation/report.md
outputs/blind_v2_validation/report.json
```

## Interpretation

Warnings do not fail validation. Errors do.

Warnings are still important. For example, an unpaired contract rule does not break parsing, but it weakens the experimental design.
