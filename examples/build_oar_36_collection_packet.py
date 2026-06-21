from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.oar_36_collection_packet import (
    load_jsonl,
    load_oar_36_collection_packet_config,
    write_oar_36_collection_packet_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the OAR-36 human collection packet.")
    parser.add_argument("--config", default="configs/oar_36_collection_packet.json")
    parser.add_argument(
        "--prompts",
        default="benchmarks/oar_360/oar_36_dry_run/oar_36_prompt_pack.jsonl",
    )
    parser.add_argument(
        "--prompt-manifest",
        default="benchmarks/oar_360/oar_36_dry_run/oar_36_prompt_manifest.json",
    )
    parser.add_argument(
        "--expected-files",
        default="benchmarks/oar_360/oar_36_dry_run/oar_36_expected_raw_output_filenames.json",
    )
    parser.add_argument(
        "--out-dir",
        default="benchmarks/oar_360/oar_36_dry_run/collection_packet",
    )
    args = parser.parse_args()

    config = load_oar_36_collection_packet_config(args.config)
    prompts = load_jsonl(args.prompts)
    prompt_manifest = json.loads(Path(args.prompt_manifest).read_text(encoding="utf-8"))
    expected_payload = json.loads(Path(args.expected_files).read_text(encoding="utf-8"))
    expected_files = expected_payload.get("files", expected_payload if isinstance(expected_payload, list) else [])
    summary = write_oar_36_collection_packet_outputs(
        config,
        prompts,
        prompt_manifest,
        expected_files,
        args.out_dir,
    )

    print(f"suite_name: {summary.suite_name}")
    print(f"prompt_count: {summary.prompt_count}")
    print(f"system_count: {summary.system_count}")
    print(f"provider_packet_count: {len(summary.provider_packet_hashes)}")
    print(f"generic_packet_hash: {summary.generic_packet_hash}")
    print(f"provider_packet_hashes: {json.dumps(summary.provider_packet_hashes, sort_keys=True)}")
    print(f"manifest_hash: {summary.manifest_hash}")
    print(f"ground_truth_exposed: {summary.ground_truth_exposed}")
    print(f"no_provider_calls: {summary.no_provider_calls}")
    print(f"no_model_outputs: {summary.no_model_outputs}")
    print(f"no_empirical_results: {summary.no_empirical_results}")
    print(f"output_dir: {Path(args.out_dir)}")


if __name__ == "__main__":
    main()
