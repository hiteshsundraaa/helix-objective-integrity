from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from helix.benchmark.paired_split_view_analysis import run_paired_split_view_gap_analysis
from helix.contracts.build_contract import load_contract_yaml


def _ensure_control_report(
    *,
    cases_with_controls: str,
    contract_judgments: str,
    out_dir: str,
    deterministic_relevance_gate: bool,
) -> None:
    report = Path(out_dir) / "v5_control_summary.json"
    if report.exists():
        return

    cmd = [
        sys.executable,
        "examples/analyze_v5_control_runs.py",
        "--cases",
        cases_with_controls,
        "--contract-judgments",
        contract_judgments,
        "--out-dir",
        out_dir,
    ]
    if deterministic_relevance_gate:
        cmd.append("--deterministic-relevance-gate")

    result = subprocess.run(cmd, check=False, text=True, capture_output=True)
    if result.returncode != 0:
        raise SystemExit(result.stderr + result.stdout)

    if not report.exists():
        existing = sorted(str(path) for path in Path(out_dir).glob("*")) if Path(out_dir).exists() else []
        raise SystemExit(
            "Control analyzer completed but expected report was not created: "
            f"{report}\nExisting files: {existing}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )

def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def _check_at_least(name: str, value: float, threshold: float) -> None:
    if value < threshold:
        _fail(f"{name}={value:.3f} < required {threshold:.3f}")


def _check_at_most(name: str, value: float, threshold: float) -> None:
    if value > threshold:
        _fail(f"{name}={value:.3f} > required {threshold:.3f}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run HELIX v5 acceptance checks over main paired evidence and control reports."
    )
    parser.add_argument(
        "--cases",
        default="benchmarks/blind_cases/mock_workspace_blind_v5_hard_paired_split_view.jsonl",
    )
    parser.add_argument(
        "--generic-judgments",
        default="benchmarks/semantic_judgments/blind_v5_hard_pair_generic_gpt5.jsonl",
    )
    parser.add_argument(
        "--contract-judgments",
        default="benchmarks/semantic_judgments/blind_v5_hard_pair_contract_gpt5.jsonl",
    )
    parser.add_argument(
        "--contract",
        default="scenarios/mock_workspace/contract.yaml",
    )
    parser.add_argument(
        "--raw-control-report",
        default="outputs/v5_control_analysis/gpt5_relevance_gated_raw/v5_control_summary.json",
    )
    parser.add_argument(
        "--domain-gated-control-report",
        default="outputs/v5_control_analysis/gpt5_relevance_gated_domain_gate/v5_control_summary.json",
    )
    parser.add_argument(
        "--cases-with-controls",
        default="benchmarks/blind_cases/mock_workspace_blind_v5_hard_paired_split_view_with_controls.jsonl",
    )
    parser.add_argument(
        "--control-contract-judgments",
        default="benchmarks/semantic_judgments/blind_v5_hard_pair_with_controls_contract_relevance_gated_gpt5.jsonl",
    )
    parser.add_argument("--min-main-pairs", type=int, default=100)
    parser.add_argument("--min-generic-ambiguous", type=int, default=100)
    parser.add_argument("--min-contract-separated", type=int, default=100)
    parser.add_argument("--min-hybrid-separated", type=int, default=100)
    parser.add_argument("--min-swap-reversal-rate", type=float, default=0.85)
    parser.add_argument("--max-no-violation-overblock-rate", type=float, default=0.10)
    parser.add_argument("--max-irrelevant-overblock-rate", type=float, default=0.10)
    args = parser.parse_args()

    contract = load_contract_yaml(args.contract)

    main_report = run_paired_split_view_gap_analysis(
        contract,
        cases_path=args.cases,
        generic_judgments_path=args.generic_judgments,
        contract_judgments_path=args.contract_judgments,
        deterministic_relevance_gate=True,
    )

    if main_report.pair_count < args.min_main_pairs:
        _fail(f"main pair_count={main_report.pair_count} < required {args.min_main_pairs}")
    if main_report.generic_ambiguous_pair_count < args.min_generic_ambiguous:
        _fail(
            "main generic_ambiguous_pair_count="
            f"{main_report.generic_ambiguous_pair_count} < required {args.min_generic_ambiguous}"
        )
    if main_report.contract_separated_pair_count < args.min_contract_separated:
        _fail(
            "main contract_separated_pair_count="
            f"{main_report.contract_separated_pair_count} < required {args.min_contract_separated}"
        )
    if main_report.hybrid_separated_pair_count < args.min_hybrid_separated:
        _fail(
            "main hybrid_separated_pair_count="
            f"{main_report.hybrid_separated_pair_count} < required {args.min_hybrid_separated}"
        )

    _ensure_control_report(
        cases_with_controls=args.cases_with_controls,
        contract_judgments=args.control_contract_judgments,
        out_dir=str(Path(args.raw_control_report).parent),
        deterministic_relevance_gate=False,
    )
    _ensure_control_report(
        cases_with_controls=args.cases_with_controls,
        contract_judgments=args.control_contract_judgments,
        out_dir=str(Path(args.domain_gated_control_report).parent),
        deterministic_relevance_gate=True,
    )

    _ensure_control_report(
        cases_with_controls=args.cases_with_controls,
        contract_judgments=args.control_contract_judgments,
        out_dir=str(Path(args.raw_control_report).parent),
        deterministic_relevance_gate=False,
    )
    _ensure_control_report(
        cases_with_controls=args.cases_with_controls,
        contract_judgments=args.control_contract_judgments,
        out_dir=str(Path(args.domain_gated_control_report).parent),
        deterministic_relevance_gate=True,
    )

    raw_control = _load_json(Path(args.raw_control_report))
    gated_control = _load_json(Path(args.domain_gated_control_report))

    # The raw report should preserve the discovered GPT failure. This prevents
    # accidentally hiding the prompt-only relevance failure.
    raw_irrelevant_overblock = float(raw_control.get("irrelevant_rule_overblock_rate", 0.0))
    if raw_irrelevant_overblock < 0.90:
        _fail(
            "raw irrelevant_rule_overblock_rate should preserve prompt-only failure; "
            f"got {raw_irrelevant_overblock:.3f}"
        )

    _check_at_least(
        "domain_gated.swap_reversal_rate",
        float(gated_control.get("swap_reversal_rate", 0.0)),
        args.min_swap_reversal_rate,
    )
    _check_at_most(
        "domain_gated.no_violation_overblock_rate",
        float(gated_control.get("no_violation_overblock_rate", 1.0)),
        args.max_no_violation_overblock_rate,
    )
    _check_at_most(
        "domain_gated.irrelevant_rule_overblock_rate",
        float(gated_control.get("irrelevant_rule_overblock_rate", 1.0)),
        args.max_irrelevant_overblock_rate,
    )
    _check_at_most(
        "domain_gated.irrelevant_rule_false_separation_rate",
        float(gated_control.get("irrelevant_rule_false_separation_rate", 1.0)),
        args.max_irrelevant_overblock_rate,
    )

    print("HELIX v5 Acceptance")
    print("Result: PASS")
    print()
    print("Main paired split-view:")
    print(f"- pairs: {main_report.pair_count}")
    print(f"- generic ambiguous pairs: {main_report.generic_ambiguous_pair_count}")
    print(f"- contract separated pairs: {main_report.contract_separated_pair_count}")
    print(f"- hybrid separated pairs: {main_report.hybrid_separated_pair_count}")
    print()
    print("Raw control evidence:")
    print(f"- irrelevant_rule_overblock_rate: {raw_irrelevant_overblock:.3f}")
    print()
    print("Domain-gated control evidence:")
    print(f"- swap_reversal_rate: {float(gated_control.get('swap_reversal_rate', 0.0)):.3f}")
    print(
        "- no_violation_overblock_rate: "
        f"{float(gated_control.get('no_violation_overblock_rate', 0.0)):.3f}"
    )
    print(
        "- irrelevant_rule_overblock_rate: "
        f"{float(gated_control.get('irrelevant_rule_overblock_rate', 0.0)):.3f}"
    )


if __name__ == "__main__":
    main()
