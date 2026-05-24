from helix.benchmark.evaluator import evaluate_gate_value
from helix.benchmark.type_b_generator import generate_type_b_mock_workspace_samples
from helix.contracts.build_contract import load_contract_yaml


def test_type_b_benchmark_runs() -> None:
    contract = load_contract_yaml("scenarios/mock_workspace/contract.yaml")
    samples = generate_type_b_mock_workspace_samples(contract=contract, repeats=2)

    assert len(samples) > 0
    assert any(sample.ground_truth.unsafe for sample in samples)

    report = evaluate_gate_value(contract=contract, samples=samples)
    assert report.samples == len(samples)
    assert "helix" in report.metrics
