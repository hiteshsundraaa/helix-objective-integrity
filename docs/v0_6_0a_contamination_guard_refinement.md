# v0.6.0a Contamination Guard Refinement

## Problem

The initial split-view generic prompt contamination guard was too aggressive. It extracted neutral tokens from `contract_rule_summary` and flagged them in generic-visible fields.

False positives included:

```text
Atlas
Reading
Summary
Executive
Access
Severity
/workspace
```

These terms can be legitimate subject matter. The generic judge may know the module, file, or vulnerability being discussed. It must not know the contract rule.

## Fix

The guard now blocks:

```text
exact contract_rule_id
signed contract / contract rule language
contract says/states/requires/forbids language
forbidden / prohibited / must not / must never
allowed only / may only
long rule-bearing phrases from contract_rule_summary
```

It no longer blocks neutral single-word entities by themselves.

## Examples

Allowed:

```text
The agent classifies the Atlas module finding.
```

Blocked:

```text
The agent classifies the Atlas module finding even though classify_finding is forbidden.
```
