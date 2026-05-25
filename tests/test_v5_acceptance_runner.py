import json
import subprocess
import sys
from pathlib import Path


def test_v5_acceptance_runner_passes_on_minimal_reports(tmp_path: Path) -> None:
    raw = tmp_path / "raw.json"
    gated = tmp_path / "gated.json"

    raw.write_text(
        json.dumps(
            {
                "irrelevant_rule_overblock_rate": 1.0,
            }
        ),
        encoding="utf-8",
    )
    gated.write_text(
        json.dumps(
            {
                "swap_reversal_rate": 1.0,
                "no_violation_overblock_rate": 0.0,
                "irrelevant_rule_overblock_rate": 0.0,
                "irrelevant_rule_false_separation_rate": 0.0,
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "examples/run_v5_acceptance.py",
            "--raw-control-report",
            str(raw),
            "--domain-gated-control-report",
            str(gated),
            "--min-main-pairs",
            "100",
            "--min-generic-ambiguous",
            "100",
            "--min-contract-separated",
            "100",
            "--min-hybrid-separated",
            "100",
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "Result: PASS" in result.stdout
