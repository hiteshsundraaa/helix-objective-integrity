import json
from pathlib import Path

from helix.benchmark.v10_generator import V10Case
from helix.benchmark.v10_provider_raw_import import load_provider_run_plan
from helix.benchmark.v10_real_three_agent_manual_pilot import (
    load_v10_real_three_agent_manual_pilot_config,
    prepare_real_three_agent_manual_pilot,
    run_real_three_agent_manual_pilot_if_ready,
)


CONFIG_PATH = Path("configs/v10_real_three_agent_manual_pilot.json")
PLAN_PATH = Path("benchmarks/v10_calibrated/provider_run_plans/pilot_v1/provider_run_plan.json")
CASES_PATH = Path("benchmarks/v10_calibrated/v10_cases.jsonl")


def _config(tmp_path: Path):
    return load_v10_real_three_agent_manual_pilot_config(CONFIG_PATH).model_copy(
        update={
            "output_root": str(tmp_path / "real_three_agent_manual_pilot_v1"),
            "provider_import_root": str(tmp_path / "provider_imports"),
            "provider_runs_root": str(tmp_path / "provider_runs"),
        }
    )


def _pilot_cases() -> list[V10Case]:
    plan = load_provider_run_plan(PLAN_PATH)
    cases = {
        case.case_id: case
        for case in [
            V10Case.model_validate_json(line)
            for line in CASES_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    }
    return [cases[case_id] for case_id in plan.sampled_case_ids]


def _write_fixture_outputs(config) -> None:
    raw_dir = Path(config.output_root) / "raw_outputs"
    raw_dir.mkdir(parents=True, exist_ok=True)
    cases = _pilot_cases()
    for system, filename in zip(config.systems, config.required_manual_output_files):
        rows = []
        for case in cases:
            unsafe = case.label in {"unsafe", "locally_safe_globally_drifted"}
            rows.append(
                {
                    "case_id": case.case_id,
                    "decision": "BLOCK" if unsafe else "ALLOW",
                    "violation_probability": 0.86 if unsafe else 0.14,
                    "cited_contract_phrase": (
                        case.expected_cited_contract_phrase
                        or case.active_contract_rule_summary
                        if unsafe
                        else ""
                    ),
                    "citation_verification_method": "exact_substring" if unsafe else "unverified",
                    "reason_codes": [
                        "fixture_v10_18.not_real_provider_evidence"
                    ],
                    "uncertainty_reason": None,
                    "provider": system.provider,
                    "model": system.model,
                    "fixture_note": "fixture file only; not real provider evidence",
                }
            )
        (raw_dir / filename).write_text(
            "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
            encoding="utf-8",
        )


def test_config_loads(tmp_path: Path) -> None:
    config = _config(tmp_path)

    assert config.schema_version == "v10_real_three_agent_manual_pilot_v1"
    assert config.real_manual_pilot_artifact_flow
    assert config.execution_mode == "manual_import"
    assert config.case_count == 30
    assert not config.level_4_allowed
    assert not config.level_5_allowed


def test_prepare_creates_artifacts_and_awaits_outputs(tmp_path: Path) -> None:
    config = _config(tmp_path)

    summary = prepare_real_three_agent_manual_pilot(
        config,
        generated_at="2026-06-11T00:00:00Z",
    )
    root = Path(config.output_root)

    assert root.exists()
    assert (root / "raw_outputs").exists()
    assert (root / "prompt_pack").exists()
    assert len(list((root / "prompt_pack").glob("*_prompt.md"))) == 3
    assert (root / "prompt_pack" / "required_output_schema.json").exists()
    assert (root / "MANUAL_COLLECTION_INSTRUCTIONS.md").exists()
    assert (root / "systems.json").exists()
    assert (root / "preparation_summary.json").exists()
    assert summary.ready_to_run_consistency is False
    assert summary.status == "awaiting_manual_outputs"
    assert summary.preparation_hash.startswith("sha256:")
    assert not (root / "consistency_summary.json").exists()


def test_prompt_pack_contains_required_content_and_case_ids(tmp_path: Path) -> None:
    config = _config(tmp_path)

    summary = prepare_real_three_agent_manual_pilot(config)
    prompt_dir = Path(summary.prompt_pack_dir)
    case_ids = [case.case_id for case in _pilot_cases()]

    prompt_files = sorted(prompt_dir.glob("*_prompt.md"))
    assert len(prompt_files) == 3
    for prompt_file in prompt_files:
        text = prompt_file.read_text(encoding="utf-8")
        assert "HELIX v10.18 Manual Collection Prompt" in text
        assert "Output JSONL only" in text
        assert "case_id, decision, violation_probability" in text
        assert "Do not include markdown fences" in text
        assert "Majority vote is not truth" in text
        assert "fake provider output" not in text.lower()
        for case_id in case_ids:
            assert case_id in text
    assert "google" in (prompt_dir / "system_a_google_gemini-flash-2.0_prompt.md").read_text(encoding="utf-8")
    assert "claude-sonnet-4-6" in (prompt_dir / "system_b_anthropic_claude-sonnet-4-6_prompt.md").read_text(encoding="utf-8")


def test_collection_instructions_contain_safety_rules(tmp_path: Path) -> None:
    config = _config(tmp_path)

    summary = prepare_real_three_agent_manual_pilot(config)
    instructions = Path(summary.collection_instructions_path).read_text(encoding="utf-8")

    assert "Do not edit malformed rows" in instructions
    assert "Do not fill missing fields manually" in instructions
    assert "Do not convert binary scores into continuous scores" in instructions
    assert "Consistency is not correctness" in instructions
    assert "Majority vote is not truth" in instructions
    assert "Manual evidence is capped at Level 3" in instructions
    assert "Level 4 requires locked live-runner provenance" in instructions


def test_existing_raw_outputs_are_hashed_and_systems_json_points_to_them(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _write_fixture_outputs(config)

    summary = prepare_real_three_agent_manual_pilot(config)
    systems_json = json.loads(Path(summary.system_json_path).read_text(encoding="utf-8"))

    assert summary.ready_to_run_consistency is True
    assert summary.outputs_collected_count == 3
    assert all(system.collected for system in summary.systems)
    assert all(system.output_hash and system.output_hash.startswith("sha256:") for system in summary.systems)
    assert [
        Path(system["raw_output_file"]).name for system in systems_json["systems"]
    ] == config.required_manual_output_files


def test_run_if_ready_does_not_run_when_outputs_missing(tmp_path: Path) -> None:
    config = _config(tmp_path)

    summary, paths = run_real_three_agent_manual_pilot_if_ready(
        config,
        generated_at="2026-06-11T00:00:00Z",
    )
    wrapper = json.loads(paths["wrapper_summary"].read_text(encoding="utf-8"))

    assert summary.ready_to_run_consistency is False
    assert wrapper["status"] == "awaiting_manual_outputs"
    assert wrapper["consistency_run_executed"] is False
    assert not (Path(config.output_root) / "consistency_summary.json").exists()


def test_run_if_ready_calls_v10_17_runner_with_fixture_outputs(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _write_fixture_outputs(config)

    summary, paths = run_real_three_agent_manual_pilot_if_ready(
        config,
        generated_at="2026-06-11T00:00:00Z",
    )

    assert summary.ready_to_run_consistency is True
    assert paths["consistency_summary"].exists()
    assert paths["consistency_report"].exists()
    assert paths["consistency_receipt"].exists()
    consistency = json.loads(paths["consistency_summary"].read_text(encoding="utf-8"))
    assert consistency["system_count"] == 3
    assert consistency["case_count"] == 30
    assert consistency["consistency_evidence_level"] <= 3
    assert consistency["level_4_allowed"] is False
    assert consistency["level_5_allowed"] is False


def test_preparation_report_contains_limitations(tmp_path: Path) -> None:
    config = _config(tmp_path)

    summary = prepare_real_three_agent_manual_pilot(config)
    report = (Path(config.output_root) / "preparation_report.md").read_text(encoding="utf-8")

    assert "manual outputs are not collected yet" in report.lower()
    assert "Consistency is not correctness" in report
    assert "Majority vote is not truth" in report
    assert "Level 4 or Level 5" in report
    assert summary.level_4_allowed is False
    assert summary.level_5_allowed is False


def test_source_has_no_api_or_sdk_usage() -> None:
    source = Path("helix/benchmark/v10_real_three_agent_manual_pilot.py").read_text(
        encoding="utf-8"
    )

    assert "import openai" not in source
    assert "import anthropic" not in source
    assert "import google" not in source
    assert "os.environ" not in source
    assert "API_KEY" not in source
    assert "requests" not in source
    assert "httpx" not in source
