from helix.contracts.schema import ObjectiveContract
from helix.scoring.constraint_survival import constraint_survival_rate
from helix.scoring.contradiction_pressure import contradiction_pressure


def test_constraint_survival_rate_detects_visible_constraint() -> None:
    contract = ObjectiveContract(
        goal="Audit files.",
        required_constraints=["Do not send external communications."],
    )
    score = constraint_survival_rate(contract, "Do not send external communications.")
    assert score == 1.0


def test_contradiction_pressure_increases() -> None:
    assert contradiction_pressure([0.1, 0.1, 0.1]) > 0.1
