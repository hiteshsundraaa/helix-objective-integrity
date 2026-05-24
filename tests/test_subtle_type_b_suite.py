from helix.benchmark.subtle_balanced_generator import generate_subtle_balanced_type_b_samples
from helix.benchmark.subtle_hard_controls import SubtleHardSafeKind, build_subtle_hard_safe_controls
from helix.benchmark.subtle_type_b_cases import SubtleTypeBKind, build_subtle_type_b_cases
from helix.contracts.build_contract import load_contract_yaml


def test_subtle_unsafe_cases_cover_expected_kinds() -> None:
    kinds = {case.kind for case in build_subtle_type_b_cases()}

    assert SubtleTypeBKind.AUTH_MATERIAL_REPRODUCIBILITY in kinds
    assert SubtleTypeBKind.PARTNER_FACING_PACKET in kinds
    assert SubtleTypeBKind.LEADERSHIP_POSTURE_ALIGNMENT in kinds
    assert SubtleTypeBKind.NEIGHBORING_PROJECT_COMPLETENESS in kinds
    assert SubtleTypeBKind.PROCEDURAL_CAVEAT_COMPRESSION in kinds
    assert SubtleTypeBKind.ENFORCEMENT_WORDING_NORMALIZATION in kinds


def test_subtle_safe_controls_cover_expected_kinds() -> None:
    kinds = {control.kind for control in build_subtle_hard_safe_controls()}

    assert SubtleHardSafeKind.AUTH_MATERIAL_EXCLUSION in kinds
    assert SubtleHardSafeKind.PARTNER_PACKET_REJECTION in kinds
    assert SubtleHardSafeKind.LEADERSHIP_POSTURE_CONTEXT_ONLY in kinds
    assert SubtleHardSafeKind.NEIGHBORING_PROJECT_EXCLUSION in kinds
    assert SubtleHardSafeKind.PROCEDURAL_CAVEAT_PRESERVATION in kinds
    assert SubtleHardSafeKind.ENFORCEMENT_WORDING_PRESERVATION in kinds


def test_subtle_balanced_suite_is_balanced() -> None:
    contract = load_contract_yaml("scenarios/mock_workspace/contract.yaml")
    samples = generate_subtle_balanced_type_b_samples(contract=contract, repeats=3)

    unsafe_count = sum(sample.ground_truth.unsafe for sample in samples)
    safe_count = len(samples) - unsafe_count

    assert unsafe_count == safe_count
    assert unsafe_count > 0
