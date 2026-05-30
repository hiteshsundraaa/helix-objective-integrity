from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.multi_provider_replay import (
    ProviderReplayInput,
    compare_provider_replays,
    write_multi_provider_replay_outputs,
)


DEFAULT_CASES = {
    "paraphrase": "benchmarks/blind_cases/mock_workspace_blind_v6_paraphrase_controls.jsonl",
    "adjacent_rule": "benchmarks/blind_cases/mock_workspace_blind_v5_adjacent_rule_controls.jsonl",
}


DEFAULT_JUDGMENTS = {
    "paraphrase": [
        "google_flash=benchmarks/semantic_judgments/blind_v6_paraphrase_contract_google_flash.jsonl",
        "degraded_control=benchmarks/semantic_judgments/blind_v6_paraphrase_contract_degraded_control.jsonl",
    ],
    "adjacent_rule": [
        "google_flash=benchmarks/semantic_judgments/blind_v5_adjacent_rule_contract_google_flash.jsonl",
    ],
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare frozen normalized judgment replays across provider metadata labels."
    )
    parser.add_argument("--protocol", choices=["paraphrase", "adjacent_rule"], required=True)
    parser.add_argument("--cases", default=None)
    parser.add_argument(
        "--judgment",
        action="append",
        default=[],
        help="Provider replay in label=path format. May be repeated.",
    )
    parser.add_argument("--out-dir", default="outputs/multi_provider_replay/v6")
    args = parser.parse_args()

    cases_path = Path(args.cases or DEFAULT_CASES[args.protocol])
    if not cases_path.exists():
        raise SystemExit(f"Cases file does not exist: {cases_path}")

    judgment_specs = args.judgment or [
        spec
        for spec in DEFAULT_JUDGMENTS[args.protocol]
        if Path(spec.split("=", 1)[1]).exists()
    ]
    if not judgment_specs:
        raise SystemExit(
            "No provider replay judgment files were supplied or found. "
            "Pass at least one --judgment label=path normalized JSONL file."
        )

    provider_inputs = [_parse_judgment_spec(spec) for spec in judgment_specs]
    summary = compare_provider_replays(
        cases_path=cases_path,
        protocol_name=f"{args.protocol}_replay",
        provider_inputs=provider_inputs,
        analysis_kind=args.protocol,
    )
    write_multi_provider_replay_outputs(summary, args.out_dir)

    print(f"Protocol: {summary.protocol}")
    print(f"Provider replays: {summary.provider_count}")
    print(f"Complete replays: {summary.complete_provider_count}")
    print(f"Providers meeting clean targets: {', '.join(summary.providers_meeting_clean_targets) or 'none'}")
    for record in summary.records:
        print(
            f"{record.label}: status={record.status}, "
            f"tpr={_fmt(record.true_positive_rate)}, fpr={_fmt(record.false_positive_rate)}, "
            f"exact_citation={_fmt(record.exact_citation_rate)}, "
            f"invalid_citation={_fmt(record.invalid_citation_rate)}, "
            f"wrong_rule_citation={_fmt(record.wrong_rule_citation_rate)}"
        )
    print(f"Wrote outputs to {args.out_dir}")


def _parse_judgment_spec(spec: str) -> ProviderReplayInput:
    if "=" not in spec:
        raise SystemExit(f"Invalid --judgment value {spec!r}; expected label=path")
    label, path = spec.split("=", 1)
    label = label.strip()
    path = path.strip()
    if not label or not path:
        raise SystemExit(f"Invalid --judgment value {spec!r}; expected non-empty label=path")
    return ProviderReplayInput(label=label, judgment_path=path)


def _fmt(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.3f}"


if __name__ == "__main__":
    main()
