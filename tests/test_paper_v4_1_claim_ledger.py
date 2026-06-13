import json
from pathlib import Path


ROOT = Path("paper/helix_v4_1")
REQUIRED_CLAIM_FIELDS = {
    "claim_id",
    "claim_text",
    "claim_type",
    "status",
    "evidence_level_allowed",
    "required_artifacts",
    "current_artifacts",
    "falsification_condition",
    "paper_section",
    "limitations",
}


def test_claim_ledger_exists_and_claims_have_required_fields() -> None:
    path = ROOT / "claims" / "claim_ledger.json"
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert path.exists()
    assert payload["claims"]
    for claim in payload["claims"]:
        assert REQUIRED_CLAIM_FIELDS.issubset(claim)


def test_no_claim_exceeds_level_three_or_claims_level_four_five() -> None:
    payload = json.loads((ROOT / "claims" / "claim_ledger.json").read_text(encoding="utf-8"))

    for claim in payload["claims"]:
        assert claim["evidence_level_allowed"] <= 3
        assert claim["status"] in {
            "supported",
            "partially_supported",
            "proposed",
            "falsified",
            "pending",
        }


def test_supported_empirical_claims_have_artifact_paths() -> None:
    payload = json.loads((ROOT / "claims" / "claim_ledger.json").read_text(encoding="utf-8"))

    for claim in payload["claims"]:
        if claim["claim_type"] == "empirical" and claim["status"] == "supported":
            assert claim["current_artifacts"]


def test_required_tables_and_blueprint_exist() -> None:
    assert (ROOT / "tables" / "negative_results_table.md").exists()
    blueprint = json.loads((ROOT / "experiments" / "oar_360_case_blueprint.json").read_text(encoding="utf-8"))

    assert blueprint["total_cases"] == 360
    assert len(blueprint["families"]) == 12
    assert len(blueprint["domains"]) >= 10


def test_hypotheses_include_falsification_conditions() -> None:
    text = (ROOT / "experiments" / "benchmark_hypotheses.md").read_text(encoding="utf-8")

    assert text.count("Falsification condition") >= 5


def test_proof_sketches_contains_post_action_over_approximation() -> None:
    text = (ROOT / "appendices" / "proof_sketches.md").read_text(encoding="utf-8")

    assert "post-action over-approximation" in text


def test_readme_says_no_model_correctness_claim() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "No model correctness claim" in text


def test_claim_counts_and_evidence_level_summary() -> None:
    payload = json.loads((ROOT / "claims" / "claim_ledger.json").read_text(encoding="utf-8"))
    statuses = [claim["status"] for claim in payload["claims"]]

    assert len(payload["claims"]) >= 7
    assert statuses.count("supported") >= 2
    assert "proposed" in statuses or "pending" in statuses
    assert max(claim["evidence_level_allowed"] for claim in payload["claims"]) == 3
