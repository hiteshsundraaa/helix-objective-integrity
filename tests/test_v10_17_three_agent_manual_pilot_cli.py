import json
import subprocess
import sys
from pathlib import Path

from helix.benchmark.v10_generator import V10Case
from helix.benchmark.v10_provider_raw_import import load_provider_run_plan


PLAN_PATH = Path("benchmarks/v10_calibrated/provider_run_plans/pilot_v1/provider_run_plan.json")
CASES_PATH = Path("benchmarks/v10_calibrated/v10_cases.jsonl")
CLI = Path("examples/run_v10_17_three_agent_manual_pilot.py")


def _cases_by_id() -> dict[str, V10Case]:
    return {
        case.case_id: case
        for case in [
            V10Case.model_validate_json(line)
            for line in CASES_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    }


def _write_raw(path: Path, *, provider: str, model: str, disagree: bool = False) -> Path:
    plan = load_provider_run_plan(PLAN_PATH)
    cases = _cases_by_id()
    rows = []
    disagreement_used = False
    for index, case_id in enumerate(plan.sampled_case_ids):
        case = cases[case_id]
        unsafe = case.label in {"unsafe", "locally_safe_globally_drifted"}
        if disagree and unsafe and not disagreement_used:
            disagreement_used = True
            decision = "ALLOW"
            score = 0.2
            phrase = ""
            method = "unverified"
        elif unsafe:
            decision = "BLOCK"
            score = 0.86
            phrase = case.expected_cited_contract_phrase or case.active_contract_rule_summary
            method = "exact_substring"
        else:
            decision = "ALLOW"
            score = 0.14
            phrase = ""
            method = "unverified"
        rows.append(
            {
                "case_id": case.case_id,
                "decision": decision,
                "violation_probability": score,
                "cited_contract_phrase": phrase,
                "citation_verification_method": method,
                "reason_codes": ["fixture_cli.not_real_provider_evidence"],
                "provider": provider,
                "model": model,
            }
        )
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    return path


def _system_json(tmp_path: Path) -> Path:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    systems = {
        "systems": [
            {
                "role": "system_a",
                "provider": "google",
                "model": "gemini-flash-2.0",
                "raw_output_file": str(
                    _write_raw(raw_dir / "google.jsonl", provider="google", model="gemini-flash-2.0")
                ),
                "collection_method": "manual_copy_paste",
            },
            {
                "role": "system_b",
                "provider": "anthropic",
                "model": "claude-sonnet-4-6",
                "raw_output_file": str(
                    _write_raw(raw_dir / "anthropic.jsonl", provider="anthropic", model="claude-sonnet-4-6")
                ),
                "collection_method": "manual_export",
            },
            {
                "role": "system_c",
                "provider": "openai",
                "model": "gpt-4o",
                "raw_output_file": str(
                    _write_raw(raw_dir / "openai.jsonl", provider="openai", model="gpt-4o", disagree=True)
                ),
                "collection_method": "external_saved_response",
            },
        ]
    }
    path = tmp_path / "systems.json"
    path.write_text(json.dumps(systems, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _config_json(tmp_path: Path) -> Path:
    payload = json.loads(
        Path("configs/v10_three_agent_manual_pilot.json").read_text(encoding="utf-8")
    )
    payload["provider_runs_root"] = str(tmp_path / "provider_runs")
    payload["consistency_output_root"] = str(tmp_path / "consistency")
    path = tmp_path / "v10_three_agent_manual_pilot_config.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def test_cli_runs_fixture_three_agent_manual_pilot(tmp_path: Path) -> None:
    out_root = tmp_path / "consistency"
    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--config",
            str(_config_json(tmp_path)),
            "--consistency-run-id",
            "cli_fixture",
            "--system-json",
            str(_system_json(tmp_path)),
            "--plan",
            str(PLAN_PATH),
            "--out-root",
            str(out_root),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "consistency_run_id: cli_fixture" in result.stdout
    assert "system_count: 3" in result.stdout
    assert "case_count: 30" in result.stdout
    assert "consistency_report_path:" in result.stdout
    assert (out_root / "cli_fixture" / "consistency_report.md").exists()
    assert (out_root / "cli_fixture" / "consistency_receipt.json").exists()


def test_cli_validation_failure_reports_issue(tmp_path: Path) -> None:
    system_json = _system_json(tmp_path)
    payload = json.loads(system_json.read_text(encoding="utf-8"))
    payload["systems"] = payload["systems"][:2]
    system_json.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--config",
            str(_config_json(tmp_path)),
            "--consistency-run-id",
            "cli_invalid",
            "--system-json",
            str(system_json),
            "--plan",
            str(PLAN_PATH),
            "--out-root",
            str(tmp_path / "consistency"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "three_agent_manual_pilot_validation_status: failed" in result.stdout
    assert "fewer_than_three_systems" in result.stdout


def test_cli_source_does_not_import_provider_sdks_or_api_keys() -> None:
    source = CLI.read_text(encoding="utf-8")

    assert "import openai" not in source
    assert "import anthropic" not in source
    assert "import google" not in source
    assert "os.environ" not in source
    assert "API_KEY" not in source
