from helix.benchmark.threshold_sweep import run_threshold_sweep
from helix.benchmark.type_b_generator import generate_type_b_mock_workspace_samples
from helix.contracts.build_contract import load_contract_yaml


def test_threshold_sweep_runs() -> None:
    contract = load_contract_yaml("scenarios/mock_workspace/contract.yaml")
    samples = generate_type_b_mock_workspace_samples(contract=contract, repeats=2)

    report = run_threshold_sweep(contract=contract, samples=samples)

    assert report.sample_count == len(samples)
    assert report.metric("helix", "block_only")
    assert report.metric("matched_friction_random", "degrade_or_higher")
    assert report.metric("prompt_filter_only", "warn_or_higher")
