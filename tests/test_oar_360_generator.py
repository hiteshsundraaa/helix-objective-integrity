from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from helix.benchmark.oar_360_generator import (
    FAMILY_TO_LABEL,
    generate_oar_360_cases,
    load_oar_360_blueprint,
    load_oar_360_config,
    validate_oar_360_cases,
    write_oar_360_outputs,
)


CONFIG_PATH = Path("configs/oar_360_generator.json")
BLUEPRINT_PATH = Path("paper/helix_v4_1/experiments/oar_360_case_blueprint.json")


def _generated_cases():
    config = load_oar_360_config(CONFIG_PATH)
    blueprint = load_oar_360_blueprint(BLUEPRINT_PATH)
    return config, blueprint, generate_oar_360_cases(config, blueprint)


def test_generates_exactly_360_cases_with_required_family_counts() -> None:
    config, blueprint, cases = _generated_cases()
    family_counts = _count(case.family for case in cases)

    assert len(cases) == 360
    assert set(family_counts) == set(blueprint["families"])
    assert all(count == 30 for count in family_counts.values())
    assert validate_oar_360_cases(cases, config, blueprint) == []


def test_domain_counts_stay_within_required_range() -> None:
    _config, _blueprint, cases = _generated_cases()
    domain_counts = _count(case.domain for case in cases)

    assert len(domain_counts) >= 10
    assert all(24 <= count <= 48 for count in domain_counts.values())
    assert set(domain_counts.values()) == {36}


def test_label_distribution_matches_oar_360_targets() -> None:
    _config, _blueprint, cases = _generated_cases()
    label_counts = _count(case.label for case in cases)

    assert label_counts == {
        "ambiguous": 90,
        "locally_safe_globally_drifted": 60,
        "safe": 90,
        "unsafe": 120,
    }
    assert all(case.label == FAMILY_TO_LABEL[case.family] for case in cases)


def test_risk_bands_and_decisions_are_balanced() -> None:
    _config, _blueprint, cases = _generated_cases()
    risk_counts = _count(case.risk_band for case in cases)
    decision_counts = _count(case.expected_decision for case in cases)

    assert risk_counts == {
        "clearly_safe": 30,
        "high_risk": 60,
        "low_risk_benign_noise": 30,
        "moderate_risk_likely_drift": 90,
        "severe_direct_violation": 90,
        "uncertain_weak_concern": 60,
    }
    assert set(decision_counts) == {
        "ALLOW",
        "BLOCK",
        "DEGRADE",
        "ESCALATE_FOR_APPROVAL",
        "QUARANTINE",
        "WARN",
    }
    assert all(count >= 30 for count in decision_counts.values())


def test_edge_tags_have_required_diversity_and_per_case_coverage() -> None:
    _config, _blueprint, cases = _generated_cases()
    edge_counts: dict[str, int] = {}
    for case in cases:
        assert len(case.edge_case_tags) >= 2
        for tag in case.edge_case_tags:
            edge_counts[tag] = edge_counts.get(tag, 0) + 1

    assert len(edge_counts) >= 20
    assert all(count >= 5 for count in edge_counts.values())


def test_case_schema_contains_required_sections_and_no_model_outputs() -> None:
    _config, _blueprint, cases = _generated_cases()
    required_top_level = {
        "schema_version",
        "case_id",
        "suite",
        "family",
        "domain",
        "label",
        "risk_band",
        "expected_decision",
        "contract",
        "case",
        "ground_truth",
        "edge_case_tags",
        "generation",
    }

    for case in cases:
        payload = case.to_dict()
        assert required_top_level <= set(payload)
        assert payload["generation"]["case_hash"].startswith("sha256:")
        assert "safe" not in payload["case_id"].lower()
        assert "unsafe" not in payload["case_id"].lower()
        assert not _contains_forbidden_keys(
            payload,
            {"provider", "model", "raw_output", "judgment", "receipt"},
        )
        assert "evidence_level" not in payload


def test_output_writer_emits_all_artifacts_and_manifest_hashes(tmp_path: Path) -> None:
    config, blueprint, cases = _generated_cases()
    config_payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    result = write_oar_360_outputs(
        cases,
        config=config,
        config_payload=config_payload,
        blueprint=blueprint,
        out_dir=tmp_path,
    )
    manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))

    assert Path(result["case_path"]).exists()
    assert (tmp_path / "oar_360_case_manifest.json").exists()
    assert (tmp_path / "oar_360_family_distribution.json").exists()
    assert (tmp_path / "oar_360_domain_distribution.json").exists()
    assert (tmp_path / "oar_360_label_distribution.json").exists()
    assert (tmp_path / "oar_360_risk_band_distribution.json").exists()
    assert (tmp_path / "oar_360_edge_case_distribution.json").exists()
    assert (tmp_path / "oar_360_generation_report.md").exists()
    assert manifest["evidence_level"] == 0
    assert manifest["no_provider_calls"] is True
    assert manifest["no_model_outputs"] is True
    assert manifest["case_file_hash"].startswith("sha256:")
    assert manifest["manifest_hash"].startswith("sha256:")
    assert manifest["validation_issues"] == []


def test_generation_is_deterministic_across_repeated_writes(tmp_path: Path) -> None:
    config, blueprint, cases = _generated_cases()
    config_payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    first = write_oar_360_outputs(
        cases,
        config=config,
        config_payload=config_payload,
        blueprint=blueprint,
        out_dir=tmp_path / "first",
    )
    second = write_oar_360_outputs(
        generate_oar_360_cases(config, blueprint),
        config=config,
        config_payload=config_payload,
        blueprint=blueprint,
        out_dir=tmp_path / "second",
    )

    assert first["case_file_hash"] == second["case_file_hash"]
    assert first["manifest_hash"] == second["manifest_hash"]


def test_report_language_does_not_overclaim(tmp_path: Path) -> None:
    config, blueprint, cases = _generated_cases()
    config_payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    result = write_oar_360_outputs(
        cases,
        config=config,
        config_payload=config_payload,
        blueprint=blueprint,
        out_dir=tmp_path,
    )
    report = Path(result["report_path"]).read_text(encoding="utf-8")

    assert "no provider calls" in report
    assert "no model outputs" in report
    assert "does not prove provider performance" in report
    assert "Level 4 evidence" in report


def _count(values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _contains_forbidden_keys(value: Any, forbidden_keys: set[str]) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in forbidden_keys:
                return True
            if _contains_forbidden_keys(child, forbidden_keys):
                return True
    if isinstance(value, list):
        return any(_contains_forbidden_keys(item, forbidden_keys) for item in value)
    return False
