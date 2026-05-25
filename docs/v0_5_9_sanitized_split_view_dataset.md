# v0.5.9 Split-View Sanitization

## Purpose

v0.5.8a found contract leakage in 80/80 blind_v2 cases. The generic judge was seeing signed-contract content through `memory`, `rationale`, and `context`.

This patch creates a sanitized candidate dataset and review report.

## Important limitation

Sanitization is not certification.

There are three contamination classes:

1. Explicit contract references: can often be auto-sanitized.
2. Implicit structural contamination: requires human review.
3. Label-leaking context: requires human review and possibly relabeling.

## Adds

```text
helix/benchmark/blind_case_sanitizer.py
examples/sanitize_blind_cases.py
tests/test_blind_case_sanitizer.py
```

## Usage

```bash
python examples/sanitize_blind_cases.py \
  --input benchmarks/blind_cases/mock_workspace_blind_v2.jsonl \
  --output benchmarks/blind_cases/mock_workspace_blind_v2_sanitized.jsonl \
  --review-out outputs/sanitization_review/blind_v2/review_findings.jsonl \
  --report-out outputs/sanitization_review/blind_v2/report.md \
  --json-report-out outputs/sanitization_review/blind_v2/report.json
```

Then audit leakage:

```bash
python examples/audit_contract_leakage.py \
  --cases benchmarks/blind_cases/mock_workspace_blind_v2_sanitized.jsonl \
  --out-dir outputs/contract_leakage_audit/blind_v2_sanitized
```

## Scientific rule

Do not treat sanitized blind_v2 as clean until human review confirms labels still hold after removing contract leakage.

If sanitization removes the reason a case is unsafe/safe, the case must be relabeled as ambiguous or rewritten.
