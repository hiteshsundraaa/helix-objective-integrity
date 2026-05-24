# v0.3.3 Test Compatibility Fix

This patch aligns the new v0.3 benchmark internals with the old v0.2 tests.

## Fixed

- `AllowlistOnlyGate.evaluate()` returns `GateVerdict`, as old tests expect.
- `PromptFilterOnlyGate.evaluate()` returns `GateVerdict`.
- `MatchedFrictionRandomGate.from_block_count(...)` is restored.
- `evaluate_gate_value(...)` can still be unpacked as `(report, enriched)`.
- `label_mock_workspace_action(contract, action)` returns `(unsafe_bool, reason)`.

## Apply

```bash
unzip ~/Downloads/helix-objective-integrity-v0.3.3-test-compat-fix.zip
rsync -a helix-objective-integrity-v0.3.3-test-compat-fix/ .
rm -rf helix-objective-integrity-v0.3.3-test-compat-fix
pytest -q
python examples/run_real_agent_trajectory_benchmark.py --provider fake
```
