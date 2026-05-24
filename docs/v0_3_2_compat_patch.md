# v0.3.2 Compatibility Patch

This patch restores v0.2 public names expected by existing tests while preserving the v0.3 real-agent runner.

## Restored names

- `helix.benchmark.labels.label_mock_workspace_action`
- `helix.benchmark.synthetic.generate_mock_workspace_samples`

Both are thin wrappers around the newer v0.3 names.

## Apply

```bash
unzip ~/Downloads/helix-objective-integrity-v0.3.2-compat-patch.zip
rsync -a helix-objective-integrity-v0.3.2-compat-patch/ .
rm -rf helix-objective-integrity-v0.3.2-compat-patch
pytest -q
python examples/run_real_agent_trajectory_benchmark.py --provider fake
```
