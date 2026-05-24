# v0.3.6 Enriched Object Compatibility Fix

Fixes the final old-test expectation:

- `enriched` rows now support attribute access, including `.helix_decision`.

Apply:

```bash
unzip ~/Downloads/helix-objective-integrity-v0.3.6-enriched-object-fix.zip
rsync -a helix-objective-integrity-v0.3.6-enriched-object-fix/ .
rm -rf helix-objective-integrity-v0.3.6-enriched-object-fix
pytest -q
python examples/run_real_agent_trajectory_benchmark.py --provider fake
```
