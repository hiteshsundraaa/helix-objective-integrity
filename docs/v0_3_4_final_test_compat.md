# v0.3.4 Final Test Compatibility Patch

Fixes the remaining old-test expectations:

- `MatchedFrictionRandomGate.evaluate_index(i)`
- `BenchmarkReport.samples`
- `GroundTruthLabel.SAFE`
- `GroundTruthLabel.UNSAFE`
- `label_mock_workspace_action(contract, action)` returns `(LabelKind, reason)`

Apply:

```bash
unzip ~/Downloads/helix-objective-integrity-v0.3.4-final-test-compat.zip
rsync -a helix-objective-integrity-v0.3.4-final-test-compat/ .
rm -rf helix-objective-integrity-v0.3.4-final-test-compat
pytest -q
python examples/run_real_agent_trajectory_benchmark.py --provider fake
```
