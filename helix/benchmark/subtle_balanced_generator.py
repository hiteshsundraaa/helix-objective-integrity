from __future__ import annotations

import json
from pathlib import Path

from helix.benchmark.labels import GroundTruthLabel, RuleBasedMockWorkspaceLabeler
from helix.benchmark.subtle_hard_controls import build_subtle_hard_safe_controls
from helix.benchmark.subtle_type_b_cases import build_subtle_type_b_cases
from helix.benchmark.trajectory import BenchmarkSample
from helix.contracts.schema import ObjectiveContract
from helix.field.dose_ladder import DoseLevel


def generate_subtle_balanced_type_b_samples(
    contract: ObjectiveContract,
    repeats: int = 20,
) -> list[BenchmarkSample]:
    """Generate a balanced subtle Type B suite.

    Default composition:
    - 6 subtle unsafe Type B cases x 20 = 120 unsafe.
    - 6 subtle hard-safe controls x 20 = 120 safe.
    - total = 240 with 50% unsafe base rate.

    These cases are still synthetic, but are intentionally less keyword-obvious
    than the v0.4.4 suite.
    """

    labeler = RuleBasedMockWorkspaceLabeler(contract)
    unsafe_cases = build_subtle_type_b_cases()
    safe_controls = build_subtle_hard_safe_controls()
    samples: list[BenchmarkSample] = []

    for repeat in range(repeats):
        for case in unsafe_cases:
            action = case.action.model_copy(update={"step": repeat + 1})
            generic_label = labeler.label(action)
            samples.append(
                BenchmarkSample(
                    sample_id=f"{case.case_id}_repeat_{repeat:03d}",
                    run_id=f"subtle_unsafe_{case.kind.value}_{repeat:03d}",
                    step=repeat + 1,
                    perturbation_level=DoseLevel.OPERATIONAL_PRESSURE.name,
                    proposed_action=action,
                    ground_truth=GroundTruthLabel.unsafe_label(case.expected_label_reason),
                    metadata={
                        "suite": "subtle_balanced_type_b",
                        "case_type": "subtle_unsafe_type_b",
                        "case_id": case.case_id,
                        "case_kind": case.kind.value,
                        "generic_label_unsafe": str(generic_label.unsafe),
                        "generic_label_reason": generic_label.reason,
                    },
                )
            )

        for control in safe_controls:
            action = control.action.model_copy(update={"step": repeat + 1})
            generic_label = labeler.label(action)
            samples.append(
                BenchmarkSample(
                    sample_id=f"{control.control_id}_repeat_{repeat:03d}",
                    run_id=f"subtle_safe_{control.kind.value}_{repeat:03d}",
                    step=repeat + 1,
                    perturbation_level=DoseLevel.CLEAN.name,
                    proposed_action=action,
                    ground_truth=GroundTruthLabel.safe(control.expected_label_reason),
                    metadata={
                        "suite": "subtle_balanced_type_b",
                        "case_type": "subtle_hard_safe_control",
                        "control_id": control.control_id,
                        "control_kind": control.kind.value,
                        "generic_label_unsafe": str(generic_label.unsafe),
                        "generic_label_reason": generic_label.reason,
                    },
                )
            )

    return samples


def export_subtle_balanced_manifest(path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    manifest = {
        "subtle_unsafe_type_b_cases": [
            case.model_dump(mode="json") for case in build_subtle_type_b_cases()
        ],
        "subtle_hard_safe_controls": [
            control.model_dump(mode="json") for control in build_subtle_hard_safe_controls()
        ],
        "claim_boundary": (
            "This suite is synthetic and cannot prove deployment validity. It tests "
            "whether polarity/source-aware scoring transfers from obvious Type B "
            "phrasing to subtler paired unsafe/safe near-misses."
        ),
    }
    target.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
