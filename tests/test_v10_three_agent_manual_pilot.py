import json
from pathlib import Path

from helix.benchmark.v10_generator import V10Case
from helix.benchmark.v10_live_runner_design_gate import load_v10_live_runner_design_config
from helix.benchmark.v10_provider_raw_import import load_provider_run_plan
from helix.benchmark.v10_three_agent_consistency_protocol import (
    load_v10_three_agent_consistency_protocol_config,
)
from helix.benchmark.v10_three_agent_manual_pilot import (
    V10ManualAgentSystemInput,
    V10ThreeAgentManualPilotInput,
    compute_per_case_consistency,
    load_per_system_receipts_and_judgments,
    load_v10_three_agent_manual_pilot_config,
    run_three_agent_manual_pilot,
    run_per_system_manual_pilots,
    validate_three_agent_manual_pilot_input,
)


CONFIG_PATH = Path("configs/v10_three_agent_manual_pilot.json")
PLAN_PATH = Path("benchmarks/v10_calibrated/provider_run_plans/pilot_v1/provider_run_plan.json")
CASES_PATH = Path("benchmarks/v10_calibrated/v10_cases.jsonl")


def _config(tmp_path: Path):
    return load_v10_three_agent_manual_pilot_config(CONFIG_PATH).model_copy(
        update={
            "provider_runs_root": str(tmp_path / "provider_runs"),
            "consistency_output_root": str(tmp_path / "consistency"),
        }
    )


def _cases_by_id() -> dict[str, V10Case]:
    return {
        case.case_id: case
        for case in [
            V10Case.model_validate_json(line)
            for line in CASES_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    }


def _pilot_cases() -> list[V10Case]:
    plan = load_provider_run_plan(PLAN_PATH)
    cases = _cases_by_id()
    return [cases[case_id] for case_id in plan.sampled_case_ids]


def _write_fixture_raw_output(
    path: Path,
    *,
    provider: str,
    model: str,
    variant: str = "clean",
) -> Path:
    judgments = []
    disagreement_used = False
    for index, case in enumerate(_pilot_cases()):
        unsafe = case.label in {"unsafe", "locally_safe_globally_drifted"}
        if variant == "disagree" and unsafe and not disagreement_used:
            disagreement_used = True
            decision = "ALLOW"
            score = 0.18
            phrase = ""
            method = "unverified"
            reason_codes = ["fixture_negative_control.allow_disagreement"]
        elif unsafe:
            decision = "BLOCK"
            score = 0.88 - ((index % 3) * 0.03)
            phrase = case.expected_cited_contract_phrase or case.active_contract_rule_summary
            method = "exact_substring"
            reason_codes = ["fixture_manual_provider.block"]
        else:
            decision = "ALLOW"
            score = 0.12 + ((index % 3) * 0.03)
            phrase = ""
            method = "unverified"
            reason_codes = ["fixture_manual_provider.allow"]
        judgments.append(
            {
                "case_id": case.case_id,
                "decision": decision,
                "violation_probability": score,
                "cited_contract_phrase": phrase,
                "citation_verification_method": method,
                "reason_codes": reason_codes,
                "provider": provider,
                "model": model,
                "fixture_note": "test_fixture_not_real_provider_evidence",
            }
        )
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in judgments) + "\n",
        encoding="utf-8",
    )
    return path


def _systems(tmp_path: Path, *, missing: bool = False) -> list[V10ManualAgentSystemInput]:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    google = _write_fixture_raw_output(
        raw_dir / "google_fixture.jsonl",
        provider="google",
        model="gemini-flash-2.0",
    )
    anthropic = _write_fixture_raw_output(
        raw_dir / "anthropic_fixture.jsonl",
        provider="anthropic",
        model="claude-sonnet-4-6",
    )
    openai = _write_fixture_raw_output(
        raw_dir / "openai_fixture.jsonl",
        provider="openai",
        model="gpt-4o",
        variant="disagree",
    )
    if missing:
        openai = raw_dir / "missing.jsonl"
    return [
        V10ManualAgentSystemInput(
            role="system_a",
            provider="google",
            model="gemini-flash-2.0",
            raw_output_file=str(google),
            collection_method="manual_copy_paste",
        ),
        V10ManualAgentSystemInput(
            role="system_b",
            provider="anthropic",
            model="claude-sonnet-4-6",
            raw_output_file=str(anthropic),
            collection_method="manual_export",
        ),
        V10ManualAgentSystemInput(
            role="system_c",
            provider="openai",
            model="gpt-4o",
            raw_output_file=str(openai),
            collection_method="external_saved_response",
        ),
    ]


def _input(tmp_path: Path, systems=None) -> V10ThreeAgentManualPilotInput:
    return V10ThreeAgentManualPilotInput(
        consistency_run_id="three_agent_fixture",
        systems=systems or _systems(tmp_path),
        plan_path=str(PLAN_PATH),
        output_root=str(tmp_path / "consistency"),
        notes="fixture only",
    )


def _validation_context(tmp_path: Path):
    config = _config(tmp_path)
    protocol = load_v10_three_agent_consistency_protocol_config(
        config.three_agent_protocol_config_path
    )
    live_design = load_v10_live_runner_design_config(config.live_design_config_path)
    return config, protocol, live_design


def test_config_loads(tmp_path: Path) -> None:
    config = _config(tmp_path)

    assert config.schema_version == "v10_three_agent_manual_pilot_v1"
    assert config.manual_three_agent_pilot
    assert config.execution_mode == "manual_import"
    assert config.minimum_independent_systems == 3
    assert config.individual_run_evidence_cap == 3
    assert config.consistency_evidence_cap == 3
    assert not config.level_4_allowed
    assert not config.level_5_allowed


def test_fewer_than_three_systems_fails(tmp_path: Path) -> None:
    config, protocol, live_design = _validation_context(tmp_path)
    pilot_input = _input(tmp_path, _systems(tmp_path)[:2])

    issues = validate_three_agent_manual_pilot_input(
        pilot_input,
        config,
        protocol,
        live_design,
    )

    assert "fewer_than_three_systems" in issues


def test_duplicate_role_fails(tmp_path: Path) -> None:
    config, protocol, live_design = _validation_context(tmp_path)
    systems = _systems(tmp_path)
    systems[1] = systems[1].model_copy(update={"role": "system_a"})

    issues = validate_three_agent_manual_pilot_input(
        _input(tmp_path, systems),
        config,
        protocol,
        live_design,
    )

    assert "duplicate_role" in issues


def test_duplicate_provider_model_fails(tmp_path: Path) -> None:
    config, protocol, live_design = _validation_context(tmp_path)
    systems = _systems(tmp_path)
    systems[2] = systems[2].model_copy(
        update={"provider": "google", "model": "gemini-flash-2.0"}
    )

    issues = validate_three_agent_manual_pilot_input(
        _input(tmp_path, systems),
        config,
        protocol,
        live_design,
    )

    assert "duplicate_provider_model" in issues


def test_unknown_provider_and_model_fail(tmp_path: Path) -> None:
    config, protocol, live_design = _validation_context(tmp_path)
    systems = _systems(tmp_path)
    systems[0] = systems[0].model_copy(update={"provider": "unknown", "model": "model"})

    issues = validate_three_agent_manual_pilot_input(
        _input(tmp_path, systems),
        config,
        protocol,
        live_design,
    )

    assert "provider_model_not_allowed:system_a" in issues


def test_missing_raw_output_file_fails(tmp_path: Path) -> None:
    config, protocol, live_design = _validation_context(tmp_path)

    issues = validate_three_agent_manual_pilot_input(
        _input(tmp_path, _systems(tmp_path, missing=True)),
        config,
        protocol,
        live_design,
    )

    assert "missing_raw_output_file:system_c" in issues


def test_duplicate_raw_output_path_fails(tmp_path: Path) -> None:
    config, protocol, live_design = _validation_context(tmp_path)
    systems = _systems(tmp_path)
    systems[2] = systems[2].model_copy(update={"raw_output_file": systems[0].raw_output_file})

    issues = validate_three_agent_manual_pilot_input(
        _input(tmp_path, systems),
        config,
        protocol,
        live_design,
    )

    assert "duplicate_raw_output_file" in issues


def test_secret_looking_field_fails(tmp_path: Path) -> None:
    config, protocol, live_design = _validation_context(tmp_path)
    systems = _systems(tmp_path)
    systems[0] = systems[0].model_copy(update={"notes": "contains api_key material"})

    issues = validate_three_agent_manual_pilot_input(
        _input(tmp_path, systems),
        config,
        protocol,
        live_design,
    )

    assert "secret_like_system_field:system_a:notes" in issues


def test_three_valid_fixture_systems_run_separately(tmp_path: Path) -> None:
    config = _config(tmp_path)
    pilot_input = _input(tmp_path)

    results = run_per_system_manual_pilots(
        pilot_input,
        config,
        generated_at="2026-06-11T00:00:00Z",
    )

    assert len(results) == 3
    assert len({result.provider_run_dir for result in results}) == 3
    assert all(Path(result.provider_run_dir).exists() for result in results)
    assert all("three_agent_fixture__" in result.provider_run_dir for result in results)
    assert all(result.final_evidence_level <= 3 for result in results)
    assert all(result.receipt_count == 30 for result in results)


def test_per_system_receipt_chains_loaded(tmp_path: Path) -> None:
    config = _config(tmp_path)
    results = run_per_system_manual_pilots(
        _input(tmp_path),
        config,
        generated_at="2026-06-11T00:00:00Z",
    )

    artifacts = load_per_system_receipts_and_judgments(results)

    assert set(artifacts) == {"system_a", "system_b", "system_c"}
    assert all(len(item.receipts_by_case_id) == 30 for item in artifacts.values())
    assert all(item.receipt_chain_hash for item in artifacts.values())


def test_consistency_records_compute_expected_disagreement(tmp_path: Path) -> None:
    config = _config(tmp_path)
    protocol = load_v10_three_agent_consistency_protocol_config(
        config.three_agent_protocol_config_path
    )
    results = run_per_system_manual_pilots(
        _input(tmp_path),
        config,
        generated_at="2026-06-11T00:00:00Z",
    )
    artifacts = load_per_system_receipts_and_judgments(results)

    records = compute_per_case_consistency(artifacts, _pilot_cases(), protocol)

    assert len(records) == 30
    assert any(not record.unanimous_decision_agreement for record in records)
    assert all(record.majority_decision_agreement for record in records)
    assert any(record.severe_disagreement for record in records)
    assert any("decision_boundary_disagreement" in record.disagreement_types for record in records)


def test_run_writes_consistency_outputs_and_metrics(tmp_path: Path) -> None:
    config = _config(tmp_path)

    summary, paths = run_three_agent_manual_pilot(
        _input(tmp_path),
        config,
        generated_at="2026-06-11T00:00:00Z",
    )

    assert paths["per_case_consistency"].exists()
    assert paths["consistency_summary"].exists()
    assert paths["consistency_receipt"].exists()
    assert paths["consistency_report"].exists()
    assert summary.system_count == 3
    assert summary.case_count == 30
    assert summary.consistency_evidence_level <= 3
    assert summary.level_4_allowed is False
    assert summary.level_5_allowed is False
    assert summary.majority_decision_rate == 1.0
    assert summary.severe_disagreement_rate > 0
    assert summary.all_receipts_valid_rate == 1.0
    assert summary.consistency_hash.startswith("sha256:")


def test_consistency_receipt_has_required_non_claims(tmp_path: Path) -> None:
    config = _config(tmp_path)

    _, paths = run_three_agent_manual_pilot(
        _input(tmp_path),
        config,
        generated_at="2026-06-11T00:00:00Z",
    )
    receipt = json.loads(paths["consistency_receipt"].read_text(encoding="utf-8"))

    assert receipt["receipt_type"] == "three_agent_manual_consistency_pilot"
    assert receipt["majority_vote_truth_claim_allowed"] is False
    assert receipt["provider_outputs_combined_for_truth"] is False
    assert receipt["consistency_not_correctness"] is True
    assert receipt["level_4_allowed"] is False
    assert receipt["level_5_allowed"] is False
    assert "manual_consistency_level_cap_3" in receipt["constraints_enforced"]


def test_report_contains_required_limitations(tmp_path: Path) -> None:
    config = _config(tmp_path)

    _, paths = run_three_agent_manual_pilot(
        _input(tmp_path),
        config,
        generated_at="2026-06-11T00:00:00Z",
    )
    report = paths["consistency_report"].read_text(encoding="utf-8")

    assert "What This Does Not Prove" in report
    assert "Majority vote is not truth" in report
    assert "Consistency is not correctness" in report
    assert "manual consistency evidence capped at Level 3" in report
    assert "Level 4 requires locked live runs" in report
    assert "No live API calls were made by HELIX" in report


def test_failed_provider_not_silently_dropped(tmp_path: Path) -> None:
    config = _config(tmp_path)
    systems = _systems(tmp_path)
    systems[2] = systems[2].model_copy(update={"raw_output_file": str(tmp_path / "missing.jsonl")})

    results = run_per_system_manual_pilots(
        _input(tmp_path, systems),
        config,
        generated_at="2026-06-11T00:00:00Z",
    )

    assert len(results) == 3
    failed = [result for result in results if result.role == "system_c"][0]
    assert failed.status == "failed"
    assert failed.final_evidence_level == 0
    assert failed.blocking_issues
