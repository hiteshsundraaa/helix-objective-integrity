import json
import subprocess
import sys
from pathlib import Path

from helix.benchmark.v10_provider_raw_import import load_provider_run_plan


CONFIG_PATH = Path("configs/v10_manual_one_provider_pilot.json")
PLAN_PATH = Path("benchmarks/v10_calibrated/provider_run_plans/pilot_v1/provider_run_plan.json")


def test_v10_15_manual_pilot_cli_runs_valid_fixture(tmp_path: Path) -> None:
    config_path = _write_tmp_config(tmp_path)
    raw = _write_raw_file(tmp_path / "raw_output.jsonl")
    out_root = tmp_path / "runs"

    result = subprocess.run(
        [
            sys.executable,
            "examples/run_v10_15_manual_pilot.py",
            "--config",
            str(config_path),
            "--raw-output-file",
            str(raw),
            "--provider",
            "google",
            "--model",
            "gemini-flash-2.0",
            "--run-id",
            "cli_manual_valid",
            "--collection-method",
            "manual_copy_paste",
            "--plan",
            str(PLAN_PATH),
            "--out-root",
            str(out_root),
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    run_dir = out_root / "cli_manual_valid"
    summary = json.loads((run_dir / "manual_pilot_summary.json").read_text(encoding="utf-8"))
    report = (run_dir / "manual_pilot_report.md").read_text(encoding="utf-8")

    assert "run_id: cli_manual_valid" in result.stdout
    assert "final_evidence_level:" in result.stdout
    assert summary["import_validation_status"] == "complete"
    assert summary["evidence_assessment_status"] == "complete"
    assert summary["final_evidence_level"] <= 3
    assert summary["level_4_allowed"] is False
    assert summary["level_5_allowed"] is False
    assert summary["receipt_count"] == load_provider_run_plan(PLAN_PATH).case_count
    assert summary["invalid_receipt_count"] == 0
    assert "What This Does Not Prove" in report
    assert "One provider does not prove cross-provider consistency" in report


def test_v10_15_manual_pilot_cli_fails_before_staging_for_unknown_provider(tmp_path: Path) -> None:
    config_path = _write_tmp_config(tmp_path)
    raw = _write_raw_file(tmp_path / "raw_output.jsonl")

    result = subprocess.run(
        [
            sys.executable,
            "examples/run_v10_15_manual_pilot.py",
            "--config",
            str(config_path),
            "--raw-output-file",
            str(raw),
            "--provider",
            "unknown",
            "--model",
            "model",
            "--run-id",
            "cli_unknown_provider",
            "--collection-method",
            "manual_copy_paste",
            "--plan",
            str(PLAN_PATH),
            "--out-root",
            str(tmp_path / "runs"),
        ],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 2
    assert "manual_pilot_validation_status: failed" in result.stdout
    assert "provider_model_not_allowed" in result.stdout
    assert not (tmp_path / "imports" / "cli_unknown_provider").exists()


def test_v10_15_manual_pilot_cli_uses_no_provider_sdks_or_secret_sources() -> None:
    source = Path("examples/run_v10_15_manual_pilot.py").read_text(encoding="utf-8")

    assert "import openai" not in source
    assert "import anthropic" not in source
    assert "import google" not in source
    assert "os.environ" not in source


def _write_tmp_config(tmp_path: Path) -> Path:
    payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    payload["provider_imports_root"] = str(tmp_path / "imports")
    payload["provider_runs_root"] = str(tmp_path / "runs")
    path = tmp_path / "manual_pilot_config.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _write_raw_file(path: Path) -> Path:
    plan = load_provider_run_plan(PLAN_PATH)
    rows = []
    for index, case_id in enumerate(plan.sampled_case_ids):
        rows.append(
            {
                "case_id": case_id,
                "decision": "WARN",
                "violation_probability": round(0.08 + (index % 10) * 0.073, 3),
                "cited_contract_phrase": "",
                "citation_verification_method": "unverified",
                "reason_codes": ["test.manual_cli_fixture"],
                "uncertainty_reason": None,
            }
        )
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    return path
