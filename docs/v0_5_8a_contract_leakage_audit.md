# v0.5.8a Contract Leakage Audit

## Purpose

blind_v2 was designed to test contract-aware judgment against generic semantic judgment. However, early inspection showed that several blind_v2 cases may include signed-contract rules inside `memory` or `context`.

If the generic judge sees signed-contract rules, then the generic condition is contaminated.

## What this patch adds

```text
helix/benchmark/contract_leakage_audit.py
examples/audit_contract_leakage.py
tests/test_contract_leakage_audit.py
```

## Generic-visible fields scanned

```text
rationale
memory
context
```

## Leak patterns

The audit flags phrases such as:

```text
Signed contract
contract says/states/requires/permits/allows/forbids
allowed only
forbidden / prohibited / must never
contract rule IDs
Partner A / Partner B
Project Atlas / Project Borealis
red_team_fixtures / training_fixture
```

## Usage

```bash
python examples/audit_contract_leakage.py \
  --cases benchmarks/blind_cases/mock_workspace_blind_v2.jsonl \
  --out-dir outputs/contract_leakage_audit/blind_v2
```

## Interpretation

High leakage means generic-vs-contract-aware decision comparisons are not clean evidence.

The correct fix is not to tune prompts or weights. The correct fix is to separate:

```text
ordinary agent memory/context
signed contract rules
case metadata
```

so generic sees only ordinary action text, while contract-aware sees signed contract rules.
