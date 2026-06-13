# Reproduction Commands

Run commands from the repository root.

## Full Tests

```bash
pytest -q
```

## v10.17 Three-Agent Manual Pilot

This command replays the manual-import pilot from existing manually collected raw outputs. It does not call provider APIs.

```bash
python examples/run_v10_17_three_agent_manual_pilot.py \
  --consistency-run-id real_three_agent_manual_pilot_v1 \
  --system-json benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/systems.json \
  --plan benchmarks/v10_calibrated/provider_run_plans/pilot_v1/provider_run_plan.json \
  --out-root benchmarks/v10_calibrated/three_agent_consistency
```

## v10.19 Disagreement Analysis

```bash
python examples/run_v10_19_disagreement_analysis.py \
  --real-pilot-root benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1 \
  --out-dir benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/disagreement_analysis_v10_19
```

## v10.20 Canonical Citation Resolver

```bash
python examples/run_v10_20_canonical_citation_resolver.py \
  --real-pilot-root benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1 \
  --v10-19-root benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/disagreement_analysis_v10_19 \
  --preregistration-config configs/v10_canonical_citation_resolver_preregistration.json \
  --out-dir benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/citation_resolver_v10_20
```

## v10.21 Citation Elicitation Preparation

```bash
python examples/run_v10_21_citation_elicitation_gate.py \
  --real-pilot-root benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1 \
  --v10-20-root benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/citation_resolver_v10_20 \
  --preregistration-config configs/v10_citation_elicitation_preregistration.json \
  --out-dir benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/citation_elicitation_v10_21
```

To analyze manually collected second-pass files after they are saved:

```bash
python examples/run_v10_21_citation_elicitation_gate.py \
  --real-pilot-root benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1 \
  --v10-20-root benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/citation_resolver_v10_20 \
  --preregistration-config configs/v10_citation_elicitation_preregistration.json \
  --out-dir benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/citation_elicitation_v10_21 \
  --analyze-second-pass
```

## Inspect Outputs

```bash
python -m json.tool benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/consistency_summary.json
python -m json.tool benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/disagreement_analysis_v10_19/disaggregated_severe_rates.json
python -m json.tool benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/citation_resolver_v10_20/citation_resolver_summary.json
python -m json.tool benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/citation_elicitation_v10_21/elicitation_preparation_summary.json
```

## Check Hashes

```bash
python -m json.tool benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/consistency_receipt.json
python -m json.tool benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/disagreement_analysis_v10_19/disagreement_analysis_manifest.json
python -m json.tool benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/citation_resolver_v10_20/citation_resolver_manifest.json
python -m json.tool benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/citation_elicitation_v10_21/elicitation_manifest.json
```
