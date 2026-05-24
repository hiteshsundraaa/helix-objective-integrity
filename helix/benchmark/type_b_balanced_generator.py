from __future__ import annotations

import json
from pathlib import Path

from helix.benchmark.labels import GroundTruthLabel, RuleBasedMockWorkspaceLabeler
from helix.benchmark.trajectory import BenchmarkSample
from helix.benchmark.type_b_cases import build_type_b_cases
from helix.benchmark.type_b_hard_controls import build_type_b_hard_safe_controls
from helix.contracts.schema import ObjectiveContract
from helix.field.dose_ladder import DoseLevel


def generate_balanced_type_b_mock_workspace_samples(
    contract: ObjectiveContract,
    repeats: int = 20,
) -> list[BenchmarkSample]:
    """Generate a balanced Type B suite.

    Composition with default repeats:
    - 6 unsafe Type B cases x 20 = 120 unsafe samples.
    - 6 hard-safe controls x 20 = 120 safe samples.
    - total = 240, unsafe base rate = 50%.

    This makes matched-random selectivity meaningful.
    """

    labeler = RuleBasedMockWorkspaceLabeler(contract)
    unsafe_cases = build_type_b_cases()
    hard_controls = build_type_b_hard_safe_controls()
    samples: list[BenchmarkSample] = []

    for repeat in range(repeats):
        for case in unsafe_cases:
            action = case.action.model_copy(update={"step": repeat + 1})
            samples.append(
                BenchmarkSample(
                    sample_id=f"{case.case_id}_balanced_repeat_{repeat:03d}",
                    run_id=f"balanced_unsafe_{case.kind.value}_{repeat:03d}",
                    step=repeat + 1,
                    perturbation_level=DoseLevel.OPERATIONAL_PRESSURE.name,
                    proposed_action=action,
                    ground_truth=GroundTruthLabel.unsafe_label(case.expected_label_reason),
                    metadata={
                        "suite": "balanced_type_b",
                        "case_type": "unsafe_type_b",
                        "case_id": case.case_id,
                        "case_kind": case.kind.value,
                    },
                )
            )

        for control in hard_controls:
            action = control.action.model_copy(update={"step": repeat + 1})
            # Force safe label because these are deliberate hard-safe controls.
            # If the generic labeler flags them, that is a scorer/labeler failure
            # to be caught by tests, not a ground-truth change.
            generic_label = labeler.label(action)
            samples.append(
                BenchmarkSample(
                    sample_id=f"{control.control_id}_balanced_repeat_{repeat:03d}",
                    run_id=f"balanced_safe_{control.kind.value}_{repeat:03d}",
                    step=repeat + 1,
                    perturbation_level=DoseLevel.CLEAN.name,
                    proposed_action=action,
                    ground_truth=GroundTruthLabel.safe(control.expected_label_reason),
                    metadata={
                        "suite": "balanced_type_b",
                        "case_type": "hard_safe_control",
                        "control_id": control.control_id,
                        "control_kind": control.kind.value,
                        "generic_label_unsafe": str(generic_label.unsafe),
                        "generic_label_reason": generic_label.reason,
                    },
                )
            )

    return samples


def export_balanced_type_b_manifest(path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    manifest = {
        "unsafe_type_b_cases": [
            case.model_dump(mode="json") for case in build_type_b_cases()
        ],
        "hard_safe_controls": [
            control.model_dump(mode="json") for control in build_type_b_hard_safe_controls()
        ],
    }
    target.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
