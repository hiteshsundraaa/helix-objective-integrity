from helix.benchmark.evaluator import evaluate_gate_value
from helix.benchmark.synthetic import generate_mock_workspace_samples
from helix.contracts.build_contract import load_contract_yaml


def test_gate_value_evaluator_runs() -> None:
    contract = load_contract_yaml("scenarios/mock_workspace/contract.yaml")
    samples = generate_mock_workspace_samples(contract, trajectories_per_level=2)
    report, enriched = evaluate_gate_value(contract, samples)

    assert report.samples == len(samples)
    assert "helix" in report.metrics
    assert "matched_friction_random" in report.metrics
    assert len(enriched) == len(samples)
    assert all(sample.helix_decision is not None for sample in enriched)
