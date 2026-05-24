from helix.benchmark.budget_sweep import run_budget_selectivity_sweep
from helix.benchmark.subtle_balanced_generator import generate_subtle_balanced_type_b_samples
from helix.contracts.build_contract import load_contract_yaml


def test_subtle_balanced_budget_sweep_runs() -> None:
    contract = load_contract_yaml("scenarios/mock_workspace/contract.yaml")
    samples = generate_subtle_balanced_type_b_samples(contract=contract, repeats=2)

    report = run_budget_selectivity_sweep(
        contract=contract,
        samples=samples,
        budgets=[0.10, 0.20],
    )

    assert report.sample_count == len(samples)
    assert report.metric("helix_risk_rank", 0.10).selected_count >= 1
    assert report.metric("matched_random", 0.20).selected_count >= 1
