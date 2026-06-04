import json
from pathlib import Path


SPEC_PATH = Path("docs/V10_CALIBRATED_HIGH_VARIANCE_BENCHMARK_SPEC.md")
CONFIG_PATH = Path("configs/v10_calibrated_benchmark_spec.json")


def _config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_v10_design_spec_and_config_exist() -> None:
    assert SPEC_PATH.exists()
    assert CONFIG_PATH.exists()


def test_v10_config_preregisters_score_bands_and_integrity_criteria() -> None:
    config = _config()

    assert len(config["score_bands"]) == 6
    assert config["score_bands"][0] == {
        "name": "clearly_safe",
        "minimum": 0.0,
        "maximum": 0.15,
        "minimum_case_fraction": 0.1,
    }
    assert config["integrity_pass_criteria"]["score_collapse_detected"] is False
    assert config["integrity_pass_criteria"]["score_entropy_bits"]["value"] == 2.0
    assert config["integrity_pass_criteria"]["max_score_bin_fraction"] == {
        "operator": "<",
        "value": 0.8,
    }
    assert config["integrity_pass_criteria"]["generator_independence"] is True
    assert config["integrity_pass_criteria"]["leakage_rate"]["value"] == 0.1
    assert config["integrity_pass_criteria"]["hard_issue_count"] == 0
    assert not config["integrity_pass_criteria"]["post_hoc_threshold_changes_allowed"]


def test_v10_config_has_balanced_families_bootstrap_and_level_target() -> None:
    config = _config()
    family_counts = [family["case_count_target"] for family in config["families"]]

    assert len(config["families"]) >= 8
    assert len(config["families"]) == 10
    assert sum(family_counts) == config["total_cases_target"] == 300
    assert config["bootstrap_settings"]["resamples"] == 1000
    assert config["bootstrap_settings"]["confidence_level"] == 0.95
    assert config["bootstrap_settings"]["seed"] == 42
    assert config["evidence_level_target"] == 4
    assert "human_audited_validation" in config["level_5_reserved_for"]
    assert config["score_band_boundary_convention"] == {
        "lower_bound_inclusive": True,
        "upper_bound_inclusive": False,
        "final_band_upper_bound_inclusive": True,
    }


def test_v10_markdown_states_required_integrity_and_evidence_boundaries() -> None:
    markdown = SPEC_PATH.read_text(encoding="utf-8").lower()

    assert "score collapse" in markdown
    assert "generator independence" in markdown
    assert "shuffled labels" in markdown
    assert "bootstrap confidence intervals" in markdown
    assert "level 5 is reserved" in markdown
    assert "not a production safety guarantee" in markdown
    assert "target bands" in markdown
    assert "do not weaken thresholds" in markdown


def test_v10_config_is_design_only_and_does_not_claim_level_five() -> None:
    config = _config()

    assert config["design_only"] is True
    assert config["evidence_level_target"] < 5
    assert config["judgment_requirements"]["continuous_violation_probability_required"]
    assert not config["generator_independence_rules"]["v10_family_overlap_override_allowed"]
