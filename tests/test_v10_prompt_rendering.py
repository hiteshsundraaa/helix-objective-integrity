import json
from pathlib import Path

from helix.benchmark.v10_generator import (
    audit_v10_generated_cases,
    generate_v10_cases,
    load_v10_generator_config,
    write_v10_generation_outputs,
)
from helix.benchmark.v10_prompt_rendering import (
    audit_v10_prompt_leakage,
    load_v10_cases,
    load_v10_prompt_config,
    render_v10_contract_prompt,
    render_v10_generic_prompt,
    write_v10_prompt_outputs,
)


GENERATOR_CONFIG_PATH = Path("configs/v10_case_generator.json")
PROMPT_CONFIG_PATH = Path("configs/v10_prompt_rendering.json")


def _cases():
    return generate_v10_cases(load_v10_generator_config(GENERATOR_CONFIG_PATH))[:12]


def _config():
    return load_v10_prompt_config(PROMPT_CONFIG_PATH)


def test_v10_prompt_config_loads() -> None:
    config = _config()

    assert config.schema_version == "v10_prompt_rendering_v1"
    assert config.registered_before_judgment_collection
    assert "label" in config.generic_prompt_must_suppress
    assert "violation_probability" in config.required_judgment_fields


def test_generic_prompt_suppresses_contract_labels_and_target_scores() -> None:
    cases = _cases()
    prompt = render_v10_generic_prompt(cases, _config())

    for case in cases:
        assert case.active_contract_rule_summary not in prompt
        assert case.governing_rule_id not in prompt
        assert case.label_reason not in prompt
        assert case.target_score_band not in prompt
        assert "target_score_band" not in prompt
        assert "target_score_range" not in prompt
    assert "violation_probability" in prompt
    assert "Binary 0/1-only scoring is not acceptable" in prompt


def test_contract_prompt_includes_contract_but_suppresses_labels_and_scores() -> None:
    cases = _cases()
    prompt = render_v10_contract_prompt(cases, _config())

    assert cases[0].active_contract_rule_summary in prompt
    assert cases[0].active_contract_rule_id in prompt
    assert "candidate_contract_rules" in prompt
    for case in cases:
        assert case.label_reason not in prompt
        assert case.target_score_band not in prompt
        assert "target_score_band" not in prompt
        assert "target_score_range" not in prompt
    assert "exact or normalized substring" in prompt


def test_leakage_audit_detects_injected_generic_contract_leak() -> None:
    cases = _cases()
    config = _config()
    generic = render_v10_generic_prompt(cases, config) + cases[0].active_contract_rule_summary
    contract = render_v10_contract_prompt(cases, config)

    summary = audit_v10_prompt_leakage(generic, contract, cases, config)

    assert summary.status == "fail"
    assert "generic_active_contract_rule_summary" in summary.issue_types
    assert summary.generic_contract_phrase_hit_count >= 1


def test_leakage_audit_detects_injected_target_score_leak() -> None:
    cases = _cases()
    config = _config()
    generic = render_v10_generic_prompt(cases, config) + "\ntarget_score_band: high_risk\n"
    contract = render_v10_contract_prompt(cases, config)

    summary = audit_v10_prompt_leakage(generic, contract, cases, config)

    assert summary.status == "fail"
    assert "generic_target_score_band" in summary.issue_types
    assert summary.generic_target_score_hit_count >= 1


def test_prompt_outputs_are_written_with_manifest_and_report(tmp_path: Path) -> None:
    generator_config = load_v10_generator_config(GENERATOR_CONFIG_PATH)
    cases = _cases()
    generated_summary = audit_v10_generated_cases(cases, generator_config)
    cases_path = tmp_path / "v10_cases.jsonl"
    write_v10_generation_outputs(
        cases,
        generated_summary,
        tmp_path / "generated",
        GENERATOR_CONFIG_PATH,
        generated_at="2026-06-05T00:00:00Z",
    )
    cases_path.write_text(
        "\n".join(json.dumps(case.model_dump(mode="json"), sort_keys=True) for case in cases)
        + "\n",
        encoding="utf-8",
    )

    loaded_cases = load_v10_cases(cases_path)
    config = _config()
    generic = render_v10_generic_prompt(loaded_cases, config)
    contract = render_v10_contract_prompt(loaded_cases, config)
    leakage = audit_v10_prompt_leakage(generic, contract, loaded_cases, config)
    paths = write_v10_prompt_outputs(
        generic_prompt=generic,
        contract_prompt=contract,
        leakage_summary=leakage,
        cases=loaded_cases,
        config_path=PROMPT_CONFIG_PATH,
        input_cases_path=cases_path,
        out_dir=tmp_path / "prompts",
        generated_at="2026-06-05T00:00:00Z",
    )

    for path in paths:
        assert path.exists()
    manifest = json.loads(paths[3].read_text(encoding="utf-8"))
    assert manifest["manifest_hash"].startswith("sha256:")
    report = paths[4].read_text(encoding="utf-8")
    assert "What This Does Not Yet Prove" in report
    assert "No model calls" in report
    assert leakage.status == "pass"


def test_v10_prompt_rendering_is_deterministic() -> None:
    cases = _cases()
    config = _config()

    assert render_v10_generic_prompt(cases, config) == render_v10_generic_prompt(cases, config)
    assert render_v10_contract_prompt(cases, config) == render_v10_contract_prompt(cases, config)
