# HELIX v0.6.4 Exact Identity Patch

This ZIP contains a repo-local patch script that adds the hard blind_v5 validator gate:

```bash
--require-exact-generic-identity
```

## Apply

From your repository root:

```bash
unzip helix_v064_exact_identity_patch.zip -d .
python tools/apply_v064_exact_identity_patch.py
```

## Test

Run:

```bash
pytest -q tests/test_paired_split_view_exact_identity.py
```

Then run the validator against blind_v4:

```bash
python examples/validate_paired_split_view_dataset.py \
  --cases benchmarks/blind_cases/mock_workspace_blind_v4_paired_split_view.jsonl \
  --require-exact-generic-identity
```

Expected: blind_v4 should fail with `generic_identity_violation` errors. That is a successful failure.

## Caveat

This script is designed around the repo shape you showed. If the internal validator structure differs, it will stop and ask for the validator file so we can patch line-by-line.
