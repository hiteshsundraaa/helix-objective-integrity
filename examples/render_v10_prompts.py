from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.v10_prompt_rendering import (
    audit_v10_prompt_leakage,
    load_v10_cases,
    load_v10_prompt_config,
    render_v10_contract_prompt,
    render_v10_generic_prompt,
    write_v10_prompt_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render v10 generic and contract-aware prompts and audit leakage."
    )
    parser.add_argument("--cases", default="benchmarks/v10_calibrated/v10_cases.jsonl")
    parser.add_argument("--config", default="configs/v10_prompt_rendering.json")
    parser.add_argument("--out-dir", default="benchmarks/v10_calibrated/prompts")
    args = parser.parse_args()

    try:
        config = load_v10_prompt_config(args.config)
        cases = load_v10_cases(args.cases)
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc

    generic_prompt = render_v10_generic_prompt(cases, config)
    contract_prompt = render_v10_contract_prompt(cases, config)
    leakage = audit_v10_prompt_leakage(
        generic_prompt,
        contract_prompt,
        cases,
        config,
    )
    paths = write_v10_prompt_outputs(
        generic_prompt=generic_prompt,
        contract_prompt=contract_prompt,
        leakage_summary=leakage,
        cases=cases,
        config_path=args.config,
        input_cases_path=args.cases,
        out_dir=args.out_dir,
    )
    summary_path = paths[2]
    summary = summary_path.read_text(encoding="utf-8")
    import json

    payload = json.loads(summary)

    print(f"case_count: {payload['case_count']}")
    print(f"generic_prompt_hash: {payload['generic_prompt_hash']}")
    print(f"contract_prompt_hash: {payload['contract_prompt_hash']}")
    print(f"leakage_status: {payload['leakage_status']}")
    print(f"issue_count: {payload['issue_count']}")
    print(f"output_path: {Path(args.out_dir)}")


if __name__ == "__main__":
    main()
