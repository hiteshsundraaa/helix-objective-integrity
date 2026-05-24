from helix.benchmark.budget_sweep import run_budget_selectivity_sweep
from helix.benchmark.type_b_balanced_generator import (
    generate_balanced_type_b_mock_workspace_samples,
)
from helix.contracts.build_contract import load_contract_yaml


def test_balanced_type_b_generator_is_balanced() -> None:
    contract = load_contract_yaml("scenarios/mock_workspace/contract.yaml")
    samples = generate_balanced_type_b_mock_workspace_samples(contract=contract, repeats=3)

    unsafe_count = sum(sample.ground_truth.unsafe for sample in samples)
    safe_count = len(samples) - unsafe_count

    assert unsafe_count == safe_count
    assert unsafe_count > 0


def test_balanced_budget_sweep_runs() -> None:
    contract = load_contract_yaml("scenarios/mock_workspace/contract.yaml")
    samples = generate_balanced_type_b_mock_workspace_samples(contract=contract, repeats=2)
    report = run_budget_selectivity_sweep(
        contract=contract,
        samples=samples,
        budgets=[0.10, 0.20],
    )

    assert report.sample_count == len(samples)
    assert report.metric("helix_risk_rank", 0.10).selected_count >= 1
    assert report.metric("matched_random", 0.20).selected_count >= 1
