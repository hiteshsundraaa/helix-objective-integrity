import json
import subprocess
import sys
from pathlib import Path


CLI = Path("examples/prepare_v10_18_real_three_agent_manual_pilot.py")


def _config_json(tmp_path: Path) -> Path:
    payload = json.loads(
        Path("configs/v10_real_three_agent_manual_pilot.json").read_text(encoding="utf-8")
    )
    payload["output_root"] = str(tmp_path / "real_three_agent_manual_pilot_v1")
    payload["provider_import_root"] = str(tmp_path / "provider_imports")
    payload["provider_runs_root"] = str(tmp_path / "provider_runs")
    path = tmp_path / "v10_real_three_agent_manual_pilot.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def test_cli_prepares_prompt_pack_and_exits_zero_when_outputs_missing(tmp_path: Path) -> None:
    config_path = _config_json(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--config",
            str(config_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "ready_to_run_consistency: false" in result.stdout
    assert "status: awaiting_manual_outputs" in result.stdout
    assert "Manual provider outputs are not collected yet. Prompt pack is ready." in result.stdout
    output_root = tmp_path / "real_three_agent_manual_pilot_v1"
    assert (output_root / "prompt_pack").exists()
    assert (output_root / "raw_outputs").exists()
    assert (output_root / "systems.json").exists()
    assert not (output_root / "consistency_summary.json").exists()


def test_cli_run_if_ready_with_missing_outputs_does_not_error(tmp_path: Path) -> None:
    config_path = _config_json(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--config",
            str(config_path),
            "--run-if-ready",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "ready_to_run_consistency: false" in result.stdout
    assert "Manual provider outputs are not collected yet. Prompt pack is ready." in result.stdout
    wrapper = tmp_path / "real_three_agent_manual_pilot_v1" / "real_manual_pilot_summary.json"
    assert wrapper.exists()
    payload = json.loads(wrapper.read_text(encoding="utf-8"))
    assert payload["consistency_run_executed"] is False


def test_cli_source_has_no_provider_sdk_or_secret_reads() -> None:
    source = CLI.read_text(encoding="utf-8")

    assert "import openai" not in source
    assert "import anthropic" not in source
    assert "import google" not in source
    assert "os.environ" not in source
    assert "API_KEY" not in source
