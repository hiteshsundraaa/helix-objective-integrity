# blind_v2 Schema Notes

blind_v2 uses the existing JSONL blind case format with optional v0.5.7 metadata fields.

## Required base fields

```json
{
  "case_id": "blind_v2_unsafe_001",
  "label": "unsafe",
  "tool": "classify_finding",
  "rationale": "...",
  "memory": "...",
  "context": "...",
  "label_reason": "...",
  "family": "idiosyncratic_contract_reversal",
  "author": "blind_generator_v2",
  "notes": ""
}
```

## Optional v0.5.7 fields

```json
{
  "intended_contract_dependence": "high",
  "contract_variant": "reversal",
  "contract_rule_id": "atlas_no_classification",
  "contract_rule_summary": "For Project Atlas, classify_finding is forbidden; only raw evidence summarization is allowed."
}
```

## Valid values

### intended_contract_dependence

```text
high
medium
low
unspecified
```

### contract_variant

```text
standard
idiosyncratic
reversal
unspecified
```

## Important

These metadata fields are not evidence. They are generation labels.

Empirical contract-dependence must be computed from generic vs contract-aware results.
