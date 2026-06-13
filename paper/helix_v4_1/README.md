# HELIX v4.1 Research Paper Package

This directory is a research-paper package for HELIX v4.1. It is intended to make the current Objective Authorization Receipts work reproducible, falsifiable, and reviewable as a research artifact.

This is not product documentation and not a go-to-market package. It does not add new empirical results. It organizes existing v10 real-pilot evidence and the next benchmark plan around the paper claim:

Independent agent systems can agree on what action to take while disagreeing on which contract phrase grounds that action.

## Current Evidence

- OAR-30 real three-agent manual pilot over 30 cases.
- Majority decision agreement: 1.000.
- Risk-band majority agreement: 1.000.
- Mean pairwise score distance: 0.074.
- Raw citation disagreement: 0.567.
- Citation validity disagreement: 0.333.
- Grounding severe rate: 0.367.
- Composite severe disagreement: 0.667.
- Canonical citation resolver reduced disagreement to 0.400.
- Missing citation rate remains 0.333.
- Evidence remains Level 3 manual evidence.

## Pending Evidence

- Second-pass citation elicitation outputs for the 10 missing-citation cases.
- OAR-360 primary paper benchmark.
- OAR-720 robustness and ablation benchmark.
- Locked live-runner provenance for any future Level 4 evidence claim.

## Reproduction

Start with [reproduction_commands.md](reproducibility/reproduction_commands.md). The commands reference existing repository scripts and current artifact paths.

## Extending to OAR-360

Use [oar_bench_suite_design.md](experiments/oar_bench_suite_design.md) and [oar_360_case_blueprint.json](experiments/oar_360_case_blueprint.json) as the preregistered suite design. Do not generate or label OAR-360 cases by inspecting future provider outputs.

## Claims Not Allowed

- No model correctness claim.
- No majority-vote truth claim.
- No production safety claim.
- No Level 4 or Level 5 evidence claim.
- No claim that second-pass elicitation repairs first-pass receipts.
- No claim that citation stability is solved.
