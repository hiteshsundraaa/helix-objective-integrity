# v0.3 Real-Agent Trajectory Runner

v0.3 adds an optional LLM-backed trajectory runner for the HELIX Gate Value Benchmark.

## Why this matters

The v0.2 benchmark scaffold can test the evaluator and baselines, but synthetic samples are not paper evidence. HELIX needs trajectories where an agent actually generates rationales, memory updates, and proposed tool calls from the signed contract plus perturbation context.

## Design

```text
signed contract
→ perturbation context
→ recursive memory
→ LLM-generated JSON {tool, rationale, memory_update}
→ ProposedAction
→ rule-based ground-truth label
→ HELIX gate + baselines
→ report export
```

## Providers

The runner supports:

- `fake`: deterministic local client for CI and smoke tests.
- `openai`: optional adapter requiring `pip install openai` and `OPENAI_API_KEY`.

## Usage

Fake deterministic run:

```bash
python examples/run_real_agent_trajectory_benchmark.py \
  --provider fake \
  --trajectories-per-level 5 \
  --steps-per-trajectory 6 \
  --levels L0,L1,L2,L3,L4
```

OpenAI run:

```bash
pip install openai
export OPENAI_API_KEY=...
python examples/run_real_agent_trajectory_benchmark.py \
  --provider openai \
  --model gpt-4.1-mini \
  --trajectories-per-level 20 \
  --steps-per-trajectory 6 \
  --levels L0,L1,L2,L3,L4
```

## Output

```text
outputs/real_agent_gate_value/
  samples.jsonl
  agent_records.jsonl
  results.json
  report.md
```

## Claim boundary

Fake-provider results are only engineering smoke tests. Paper claims require real model-generated trajectories and audited labels.
