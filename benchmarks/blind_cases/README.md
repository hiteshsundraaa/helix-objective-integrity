# Blind Case Directory

Place externally authored blind Type B JSONL files here.

## Rule

Do not generate blind cases by reading HELIX scoring files.

The case author should see only:

- the mock workspace contract;
- allowed tools;
- forbidden tools;
- safe/unsafe definitions;
- the generation protocol.

They should not see:

- `helix/scoring/polarity.py`;
- `helix/scoring/forbidden_pressure.py`;
- `helix/scoring/authority_divergence.py`;
- existing v0.4.4/v0.4.5 cases;
- reason-code patterns.

## Format

Each line is one JSON object:

```json
{"case_id":"blind_unsafe_001","label":"unsafe","tool":"draft_report","rationale":"...","memory":"...","context":"...","label_reason":"...","family":"externalization"}
```

Run:

```bash
python examples/run_blind_type_b_budget_sweep.py --cases benchmarks/blind_cases/YOUR_FILE.jsonl
```
