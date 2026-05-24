import subprocess
import sys


def test_real_agent_benchmark_cli_fake_runs() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "examples/run_real_agent_trajectory_benchmark.py",
            "--provider",
            "fake",
            "--trajectories-per-level",
            "1",
            "--steps-per-trajectory",
            "2",
            "--levels",
            "L0,L4",
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    assert "HELIX Real-Agent Trajectory Gate Value Benchmark" in result.stdout
    assert "Samples: 4" in result.stdout
