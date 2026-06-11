import subprocess
import sys
from pathlib import Path


def test_v10_15_live_pilot_cli_unavailable_adapter_fails_without_api_call() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "examples/run_v10_15_live_pilot.py",
            "--config",
            "configs/v10_guarded_live_one_provider_pilot.json",
            "--live-design-config",
            "configs/v10_live_provider_runner_design_gate.json",
            "--provider",
            "google",
            "--model",
            "gemini-flash-2.0",
            "--run-id",
            "live_pilot_guard_check_v1",
            "--plan",
            "benchmarks/v10_calibrated/provider_run_plans/pilot_v1/provider_run_plan.json",
            "--out-root",
            "benchmarks/v10_calibrated/provider_runs/live",
            "--case-limit",
            "30",
            "--live",
            "--adapter-kind",
            "unavailable",
        ],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 2
    assert "live_pilot_validation_status: passed" in result.stdout
    assert "adapter_status: unavailable" in result.stdout
    assert "No live provider adapter configured in this patch" in result.stdout
    assert not Path(
        "benchmarks/v10_calibrated/provider_runs/live/google/gemini-flash-2.0/live_pilot_guard_check_v1/raw"
    ).exists()


def test_v10_15_live_pilot_cli_validates_live_flag_before_adapter() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "examples/run_v10_15_live_pilot.py",
            "--provider",
            "google",
            "--model",
            "gemini-flash-2.0",
            "--run-id",
            "missing_live_flag",
            "--adapter-kind",
            "unavailable",
        ],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 2
    assert "live_pilot_validation_status: failed" in result.stdout
    assert "missing_live_flag" in result.stdout


def test_v10_15_live_pilot_cli_unknown_provider_fails_before_adapter() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "examples/run_v10_15_live_pilot.py",
            "--provider",
            "unknown",
            "--model",
            "model",
            "--run-id",
            "unknown_provider",
            "--live",
            "--adapter-kind",
            "unavailable",
        ],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 2
    assert "provider_model_not_allowed" in result.stdout


def test_v10_15_live_pilot_cli_source_has_no_sdk_or_secret_reads() -> None:
    source = Path("examples/run_v10_15_live_pilot.py").read_text(encoding="utf-8")

    assert "import openai" not in source
    assert "import anthropic" not in source
    assert "import google" not in source
    assert "os.environ" not in source
    assert "API_KEY" not in source
