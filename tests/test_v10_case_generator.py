import json
from pathlib import Path

from helix.benchmark.v10_generator import (
    V10Case,
    audit_v10_generated_cases,
    generate_v10_cases,
    load_v10_generator_config,
    write_v10_generation_outputs,
)


CONFIG_PATH = Path("configs/v10_case_generator.json")


def _cases() -> list[V10Case]:
    return generate_v10_cases(load_v10_generator_config(CONFIG_PATH))


def test_v10_case_generator_config_loads() -> None:
    config = load_v10_generator_config(CONFIG_PATH)

    assert config.schema_version == "v10_case_generator_v1"
    assert config.registered_before_generation
    assert config.seed == 42
    assert config.total_cases == 300
    assert config.cases_per_family == 30


def test_v10_generation_produces_exact_family_counts() -> None:
    config = load_v10_generator_config(CONFIG_PATH)
    cases = generate_v10_cases(config)
    summary = audit_v10_generated_cases(cases, config)

    assert len(cases) == 300
    assert len(summary.family_counts) == 10
    assert set(summary.family_counts.values()) == {30}
    assert summary.total_cases == 300


def test_v10_case_ids_do_not_encode_labels() -> None:
    config = load_v10_generator_config(CONFIG_PATH)
    summary = audit_v10_generated_cases(generate_v10_cases(config), config)

    assert summary.label_in_case_id_count == 0
    assert all(
        case.case_id.startswith("v10_case_")
        for case in generate_v10_cases(config)
    )


def test_v10_required_schema_fields_are_present() -> None:
    first = _cases()[0]
    payload = first.model_dump(mode="json")

    for field in (
        "case_id",
        "family",
        "domain",
        "generic_context",
        "proposed_tool",
        "proposed_action",
        "proposed_arguments",
        "active_contract_rule_id",
        "active_contract_rule_summary",
        "candidate_contract_rules",
        "governing_rule_id",
        "label",
        "label_reason",
        "target_score_band",
        "target_score_range",
        "requires_trajectory_context",
        "expected_cited_contract_phrase",
        "generation_metadata",
    ):
        assert field in payload
    assert "violation_probability" not in payload
    assert first.candidate_contract_rules


def test_v10_target_score_band_distribution_and_boundary_targets() -> None:
    config = load_v10_generator_config(CONFIG_PATH)
    summary = audit_v10_generated_cases(generate_v10_cases(config), config)

    assert set(summary.target_score_band_counts) == {
        band.band_id for band in config.score_bands
    }
    assert all(count > 0 for count in summary.target_score_band_counts.values())
    assert summary.mid_risk_fraction >= config.mid_risk_min_fraction
    assert summary.near_boundary_fraction >= config.near_boundary_min_fraction
    assert summary.status == "complete"
    assert summary.failed_targets == []


def test_v10_generic_contract_leakage_and_overlap_are_audited() -> None:
    config = load_v10_generator_config(CONFIG_PATH)
    cases = generate_v10_cases(config)
    summary = audit_v10_generated_cases(cases, config)

    assert summary.generic_contract_leakage_count == 0
    assert summary.generator_overlap_mean < config.overlap_mean_target_max
    assert summary.generator_overlap_max < config.high_overlap_threshold
    assert summary.high_overlap_case_count == 0


def test_v10_high_overlap_diagnostics_are_emitted_for_bad_case() -> None:
    config = load_v10_generator_config(CONFIG_PATH)
    cases = generate_v10_cases(config)
    bad_case = cases[0].model_copy(
        update={"generic_context": cases[0].active_contract_rule_summary}
    )
    summary = audit_v10_generated_cases([bad_case, *cases[1:]], config)

    assert summary.high_overlap_case_count >= 1
    assert summary.generic_contract_leakage_count >= 1
    assert summary.high_overlap_cases[0]["case_id"] == bad_case.case_id


def test_v10_generation_outputs_include_manifest_and_report(tmp_path: Path) -> None:
    config = load_v10_generator_config(CONFIG_PATH)
    cases = generate_v10_cases(config)
    summary = audit_v10_generated_cases(cases, config)
    cases_path, summary_path, manifest_path, high_overlap_path, report_path = (
        write_v10_generation_outputs(
            cases,
            summary,
            tmp_path,
            CONFIG_PATH,
            generated_at="2026-06-05T00:00:00Z",
        )
    )

    assert cases_path.exists()
    assert summary_path.exists()
    assert high_overlap_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["manifest_hash"].startswith("sha256:")
    report = report_path.read_text(encoding="utf-8")
    assert "What This Does Not Yet Prove" in report
    assert "No judgments were collected" in report


def test_v10_generation_is_deterministic_with_fixed_seed() -> None:
    first = [case.model_dump(mode="json") for case in _cases()]
    second = [case.model_dump(mode="json") for case in _cases()]

    assert first == second
