from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class OAR36CollectionSystemSpec:
    role: str
    provider: str
    model: str
    packet_filename: str
    expected_raw_output_path: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OAR36CollectionPacketConfig:
    schema_version: str
    suite_name: str
    source_suite: str
    protocol_version: str
    expected_case_count: int
    expected_system_count: int
    manual_result_evidence_cap: int
    ground_truth_exposure_allowed: bool
    no_provider_calls: bool
    no_model_outputs: bool
    no_empirical_results: bool
    default_systems: list[OAR36CollectionSystemSpec]
    notes: str


@dataclass(frozen=True)
class OAR36CollectionPacketSummary:
    schema_version: str
    suite_name: str
    source_suite: str
    expected_case_count: int
    prompt_count: int
    system_count: int
    provider_packet_hashes: dict[str, str]
    generic_packet_hash: str
    collection_readme_hash: str
    checklist_hash: str
    post_collection_commands_hash: str
    collector_log_template_hash: str
    provider_file_targets_hash: str
    manifest_hash: str
    no_provider_calls: bool
    no_model_outputs: bool
    no_empirical_results: bool
    ground_truth_exposed: bool
    manual_result_evidence_cap: int
    level_4_allowed: bool
    level_5_allowed: bool
    limitations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_oar_36_collection_packet_config(path: str | Path) -> OAR36CollectionPacketConfig:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    systems = [OAR36CollectionSystemSpec(**system) for system in payload.pop("default_systems")]
    return OAR36CollectionPacketConfig(default_systems=systems, **payload)


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def stable_json_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def build_provider_packet(
    system: OAR36CollectionSystemSpec,
    prompts: list[dict[str, Any]],
    config: OAR36CollectionPacketConfig,
    receipt_prep_expected_path: str | None = None,
) -> str:
    target_path = receipt_prep_expected_path or system.expected_raw_output_path
    lines = [
        f"# {config.suite_name} Collection Packet: {system.provider} / {system.model}",
        "",
        "## Collection Boundary",
        "- Use this packet only for the OAR-36 dry-run collection.",
        "- Copy each model response as exactly one JSONL row.",
        "- JSON only.",
        "- Do not include markdown fences in output.",
        "- Do not repair or rewrite outputs after generation.",
        "- Do not expose ground truth.",
        "- Do not paste one provider's answers into another provider.",
        "- Do not retry because an answer looks bad.",
        "- Retry only for UI or network failure and record the retry note.",
        "",
        "## Raw Output Target",
        f"- system_role: `{system.role}`",
        f"- provider: `{system.provider}`",
        f"- model: `{system.model}`",
        f"- save raw JSONL to: `{target_path}`",
        f"- configured packet target: `{system.expected_raw_output_path}`",
        "",
        "## Prompt Blocks",
    ]
    for index, prompt in enumerate(prompts, start=1):
        lines.extend(
            [
                "",
                f"### Prompt {index:02d}: {prompt['case_id']}",
                f"- prompt_id: `{prompt.get('prompt_id', '')}`",
                f"- prompt_hash: `{prompt.get('prompt_hash', '')}`",
                f"- source_oar360_prompt_id: `{prompt.get('source_oar360_prompt_id', '')}`",
                f"- source_oar360_prompt_hash: `{prompt.get('source_oar360_prompt_hash', '')}`",
                "",
                "BEGIN COPY PROMPT",
                prompt["prompt_text"].rstrip(),
                "END COPY PROMPT",
                "",
                "Record the model response as one raw JSON object line in the target JSONL file.",
            ]
        )
    return "\n".join(lines) + "\n"


def build_generic_packet(prompts: list[dict[str, Any]], config: OAR36CollectionPacketConfig) -> str:
    lines = [
        f"# {config.suite_name} Generic Collection Packet",
        "",
        "Use this packet when a provider-specific packet is not appropriate.",
        "JSON only. Do not include markdown fences in output.",
        "Do not expose ground truth. Do not repair or rewrite model outputs.",
        "Do not paste one provider's answers into another provider.",
        "",
        "## Prompt Blocks",
    ]
    for index, prompt in enumerate(prompts, start=1):
        lines.extend(
            [
                "",
                f"### Prompt {index:02d}: {prompt['case_id']}",
                f"- prompt_id: `{prompt.get('prompt_id', '')}`",
                f"- prompt_hash: `{prompt.get('prompt_hash', '')}`",
                "",
                "BEGIN COPY PROMPT",
                prompt["prompt_text"].rstrip(),
                "END COPY PROMPT",
            ]
        )
    return "\n".join(lines) + "\n"


def build_provider_file_targets(
    config: OAR36CollectionPacketConfig,
    expected_files: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    expected_by_system = {
        (record.get("system_role"), record.get("provider"), record.get("model")): record
        for record in expected_files or []
    }
    targets: list[dict[str, Any]] = []
    for system in config.default_systems:
        expected = expected_by_system.get((system.role, system.provider, system.model), {})
        receipt_prep_path = expected.get("relative_path") or system.expected_raw_output_path
        targets.append(
            {
                "system_role": system.role,
                "provider": system.provider,
                "model": system.model,
                "packet_filename": system.packet_filename,
                "configured_expected_raw_output_path": system.expected_raw_output_path,
                "receipt_prep_expected_raw_output_path": receipt_prep_path,
                "expected_filename": expected.get("expected_filename") or Path(receipt_prep_path).name,
                "required": bool(expected.get("required", True)),
                "notes": "Save raw provider output exactly as collected; do not edit malformed rows.",
            }
        )
    return {
        "schema_version": "oar_36_provider_file_targets_v1",
        "suite_name": config.suite_name,
        "targets": targets,
    }


def build_collector_log_template(config: OAR36CollectionPacketConfig) -> dict[str, Any]:
    return {
        "schema_version": "oar_36_collector_log_template_v1",
        "suite_name": config.suite_name,
        "collection_started_utc": "",
        "collection_completed_utc": "",
        "collector_id_optional": "",
        "systems": [system.to_dict() for system in config.default_systems],
        "per_system_collection_log": [
            {
                "system_role": system.role,
                "provider": system.provider,
                "model": system.model,
                "started_utc": "",
                "completed_utc": "",
                "raw_output_file": system.expected_raw_output_path,
                "prompt_packet_used": system.packet_filename,
                "notes": "",
            }
            for system in config.default_systems
        ],
        "retry_events": [],
        "ui_or_network_failures": [],
        "deviations_from_protocol": [],
        "raw_output_files_written": [],
        "notes": "",
        "attestation": {
            "no_ground_truth_exposed": False,
            "no_cross_provider_output_sharing": False,
            "raw_outputs_not_edited": False,
            "malformed_rows_not_repaired": False,
            "missing_citations_not_filled": False,
            "majority_vote_not_treated_as_truth": False,
            "manual_evidence_cap_level_3": True,
        },
    }


def validate_collection_packet_outputs(
    prompts: list[dict[str, Any]],
    config: OAR36CollectionPacketConfig,
    provider_packets: dict[str, str],
    generic_packet: str,
    manifest: dict[str, Any],
) -> list[str]:
    issues: list[str] = []
    if len(prompts) != config.expected_case_count:
        issues.append("prompt_count_mismatch")
    for provider, packet in provider_packets.items():
        if packet.count("BEGIN COPY PROMPT") != config.expected_case_count:
            issues.append(f"{provider}:prompt_block_count_mismatch")
        lowered = packet.lower()
        for forbidden in (
            "expected_decision",
            "expected_risk_interval",
            "ground_truth",
            "risk_band",
        ):
            if forbidden in lowered:
                issues.append(f"{provider}:forbidden_token:{forbidden}")
    if generic_packet.count("BEGIN COPY PROMPT") != config.expected_case_count:
        issues.append("generic_prompt_block_count_mismatch")
    if manifest.get("ground_truth_exposed") is not False:
        issues.append("ground_truth_exposed")
    if manifest.get("no_provider_calls") is not True:
        issues.append("provider_calls_claimed")
    if manifest.get("no_model_outputs") is not True:
        issues.append("model_outputs_claimed")
    if manifest.get("no_empirical_results") is not True:
        issues.append("empirical_results_claimed")
    return issues


def write_oar_36_collection_packet_outputs(
    config: OAR36CollectionPacketConfig,
    prompts: list[dict[str, Any]],
    prompt_manifest: dict[str, Any],
    expected_files: list[dict[str, Any]],
    out_dir: str | Path,
) -> OAR36CollectionPacketSummary:
    output_dir = Path(out_dir)
    provider_dir = output_dir / "provider_packets"
    provider_dir.mkdir(parents=True, exist_ok=True)

    targets = build_provider_file_targets(config, expected_files)
    targets_by_system = {
        (target["system_role"], target["provider"], target["model"]): target
        for target in targets["targets"]
    }
    provider_packets: dict[str, str] = {}
    for system in config.default_systems:
        target = targets_by_system[(system.role, system.provider, system.model)]
        packet = build_provider_packet(
            system,
            prompts,
            config,
            receipt_prep_expected_path=target["receipt_prep_expected_raw_output_path"],
        )
        provider_packets[system.provider] = packet
        (provider_dir / system.packet_filename).write_text(packet, encoding="utf-8")
    generic_packet = build_generic_packet(prompts, config)
    (provider_dir / "generic_oar36_collection_packet.md").write_text(generic_packet, encoding="utf-8")

    _write_json(output_dir / "oar_36_provider_file_targets.json", targets)
    _write_json(output_dir / "oar_36_collector_log_template.json", build_collector_log_template(config))

    summary = OAR36CollectionPacketSummary(
        schema_version="oar_36_collection_manifest_v1",
        suite_name=config.suite_name,
        source_suite=config.source_suite,
        expected_case_count=config.expected_case_count,
        prompt_count=len(prompts),
        system_count=len(config.default_systems),
        provider_packet_hashes={
            system.provider: sha256_file(provider_dir / system.packet_filename)
            for system in config.default_systems
        },
        generic_packet_hash=sha256_file(provider_dir / "generic_oar36_collection_packet.md"),
        collection_readme_hash="",
        checklist_hash="",
        post_collection_commands_hash="",
        collector_log_template_hash=sha256_file(output_dir / "oar_36_collector_log_template.json"),
        provider_file_targets_hash=sha256_file(output_dir / "oar_36_provider_file_targets.json"),
        manifest_hash="",
        no_provider_calls=config.no_provider_calls,
        no_model_outputs=config.no_model_outputs,
        no_empirical_results=config.no_empirical_results,
        ground_truth_exposed=False,
        manual_result_evidence_cap=config.manual_result_evidence_cap,
        level_4_allowed=False,
        level_5_allowed=False,
        limitations=[
            config.notes,
            "This package does not include OAR-36 or OAR-360 holdout records.",
            "Manual collection evidence remains capped at Level 3.",
            "Provider output quality is not known until raw outputs are collected and validated.",
            f"Source prompt manifest hash: {prompt_manifest.get('manifest_hash', 'unknown')}",
        ],
    )
    (output_dir / "OAR36_COLLECTION_README.md").write_text(
        generate_collection_readme(summary, config, output_dir),
        encoding="utf-8",
    )
    (output_dir / "OAR36_COLLECTION_CHECKLIST.md").write_text(
        generate_collection_checklist(summary, config, output_dir),
        encoding="utf-8",
    )
    (output_dir / "OAR36_POST_COLLECTION_COMMANDS.md").write_text(
        generate_post_collection_commands(summary, config, output_dir),
        encoding="utf-8",
    )
    summary_payload = {
        **summary.to_dict(),
        "collection_readme_hash": sha256_file(output_dir / "OAR36_COLLECTION_README.md"),
        "checklist_hash": sha256_file(output_dir / "OAR36_COLLECTION_CHECKLIST.md"),
        "post_collection_commands_hash": sha256_file(output_dir / "OAR36_POST_COLLECTION_COMMANDS.md"),
        "manifest_hash": "",
    }
    summary_payload["manifest_hash"] = sha256_text(stable_json_dumps(summary_payload))
    issues = validate_collection_packet_outputs(
        prompts,
        config,
        provider_packets,
        generic_packet,
        summary_payload,
    )
    if issues:
        raise ValueError(f"OAR-36 collection packet validation failed: {issues}")
    _write_json(output_dir / "oar_36_collection_manifest.json", summary_payload)
    return OAR36CollectionPacketSummary(**summary_payload)


def generate_collection_readme(
    summary: OAR36CollectionPacketSummary,
    config: OAR36CollectionPacketConfig,
    out_dir: str | Path,
) -> str:
    del out_dir
    targets = "\n".join(
        f"- `{system.role}` / `{system.provider}` / `{system.model}`: `{system.expected_raw_output_path}`"
        for system in config.default_systems
    )
    return "\n".join(
        [
            "# OAR-36 Human Collection Packet",
            "",
            "## Purpose",
            "This packet prepares human collection of OAR-36 provider outputs.",
            "",
            "## Packet Contents",
            "- Provider-specific prompt packets for google, anthropic, and openai.",
            "- A generic prompt packet for other manual systems.",
            "- A collector log template.",
            "- A checklist and post-collection validation commands.",
            "",
            "## Source Prompt Manifest",
            "Prompts are derived from the locked OAR-36 prompt pack and prompt manifest.",
            "",
            "## Collection Boundary",
            "- no provider calls were made by this package.",
            "- no model outputs were created.",
            "- ground truth is not included.",
            "- do not expose holdout.",
            "- Do not use one provider output as input to another provider.",
            "",
            "## Evidence Boundary",
            f"- manual evidence capped at Level {summary.manual_result_evidence_cap}.",
            "- Level 4/5 not claimed.",
            "- this does not prove model correctness.",
            "- no empirical results are created by this packet.",
            "",
            "## Raw-Output Target Paths",
            targets,
            "",
            "## What This Supports",
            "- Clean manual copy/paste collection.",
            "- Raw JSONL file target discipline.",
            "- Post-collection receipt-prep and analysis workflow.",
            "",
            "## What This Does Not Prove",
            "- This does not prove model correctness.",
            "- This does not estimate OAR-360 performance.",
            "- This does not create empirical OAR-36 results.",
            "",
            "## Limitations",
            *[f"- {limitation}" for limitation in summary.limitations],
            "",
        ]
    )


def generate_collection_checklist(
    summary: OAR36CollectionPacketSummary,
    config: OAR36CollectionPacketConfig,
    out_dir: str | Path,
) -> str:
    del summary, out_dir
    filenames = "\n".join(
        f"- `{system.role}`: `{system.expected_raw_output_path}`"
        for system in config.default_systems
    )
    return "\n".join(
        [
            "# OAR-36 Collection Checklist",
            "",
            "## Before Collection",
            "- Confirm the OAR-36 prompt packet is the only prompt source.",
            "- Confirm the OAR-36 and OAR-360 holdout files are closed.",
            "- Confirm each provider has its own target raw JSONL file.",
            "- Confirm the collector log template is ready.",
            "",
            "## During Collection",
            "- Paste one prompt block at a time.",
            "- Save each model response exactly as one JSONL row.",
            "- Do not edit malformed rows.",
            "- Do not fill missing citations.",
            "- Do not normalize provider output manually.",
            "- Retry only for UI or network failure and record the event.",
            "",
            "## After Collection",
            "- Write all raw output files to their expected paths.",
            "- Complete the collector log attestation.",
            "- Run the receipt-prep command.",
            "- Run the OAR-36 analysis command only after receipt prep.",
            "",
            "## Prohibited Actions",
            "- Do not expose ground truth.",
            "- Do not expose holdout.",
            "- Do not paste one provider's answers into another provider.",
            "- Do not treat majority vote as truth.",
            "- Do not claim empirical results before validation.",
            "",
            "## Expected Raw Filenames",
            filenames,
            "",
            "## Validation Commands",
            "- `python examples/prepare_oar_36_raw_receipts.py --config configs/oar_36_raw_receipt_prep.json --cases benchmarks/oar_360/oar_36_dry_run/oar_36_cases.jsonl --prompts benchmarks/oar_360/oar_36_dry_run/oar_36_prompt_pack.jsonl --expected-files benchmarks/oar_360/oar_36_dry_run/oar_36_expected_raw_output_filenames.json --raw-output-root benchmarks/oar_360/oar_36_dry_run/raw_outputs --out-dir benchmarks/oar_360/oar_36_dry_run/receipt_prep`",
            "- `python examples/analyze_oar_36_results.py --config configs/oar_36_scoring_analysis.json --cases benchmarks/oar_360/oar_36_dry_run/oar_36_cases.jsonl --holdout benchmarks/oar_360/oar_36_dry_run/oar_36_ground_truth_holdout.jsonl --receipt-prep-manifest benchmarks/oar_360/oar_36_dry_run/receipt_prep/oar_36_receipt_prep_manifest.json --receipt-prep benchmarks/oar_360/oar_36_dry_run/receipt_prep/oar_36_receipt_preparation.jsonl --normalized-judgments benchmarks/oar_360/oar_36_dry_run/receipt_prep/oar_36_normalized_judgments.jsonl --out-dir benchmarks/oar_360/oar_36_dry_run/analysis`",
            "",
        ]
    )


def generate_post_collection_commands(
    summary: OAR36CollectionPacketSummary,
    config: OAR36CollectionPacketConfig,
    out_dir: str | Path,
) -> str:
    del summary, config, out_dir
    return "\n".join(
        [
            "# OAR-36 Post-Collection Commands",
            "",
            "## Run Receipt Prep",
            "```bash",
            "python examples/prepare_oar_36_raw_receipts.py \\",
            "  --config configs/oar_36_raw_receipt_prep.json \\",
            "  --cases benchmarks/oar_360/oar_36_dry_run/oar_36_cases.jsonl \\",
            "  --prompts benchmarks/oar_360/oar_36_dry_run/oar_36_prompt_pack.jsonl \\",
            "  --expected-files benchmarks/oar_360/oar_36_dry_run/oar_36_expected_raw_output_filenames.json \\",
            "  --raw-output-root benchmarks/oar_360/oar_36_dry_run/raw_outputs \\",
            "  --out-dir benchmarks/oar_360/oar_36_dry_run/receipt_prep",
            "```",
            "",
            "## Inspect Receipt Prep Manifest",
            "```bash",
            "cat benchmarks/oar_360/oar_36_dry_run/receipt_prep/oar_36_receipt_prep_manifest.json | python -m json.tool",
            "```",
            "",
            "## Run OAR-36 Analysis",
            "```bash",
            "python examples/analyze_oar_36_results.py \\",
            "  --config configs/oar_36_scoring_analysis.json \\",
            "  --cases benchmarks/oar_360/oar_36_dry_run/oar_36_cases.jsonl \\",
            "  --holdout benchmarks/oar_360/oar_36_dry_run/oar_36_ground_truth_holdout.jsonl \\",
            "  --receipt-prep-manifest benchmarks/oar_360/oar_36_dry_run/receipt_prep/oar_36_receipt_prep_manifest.json \\",
            "  --receipt-prep benchmarks/oar_360/oar_36_dry_run/receipt_prep/oar_36_receipt_preparation.jsonl \\",
            "  --normalized-judgments benchmarks/oar_360/oar_36_dry_run/receipt_prep/oar_36_normalized_judgments.jsonl \\",
            "  --out-dir benchmarks/oar_360/oar_36_dry_run/analysis",
            "```",
            "",
            "## Inspect Analysis Manifest and Report",
            "```bash",
            "cat benchmarks/oar_360/oar_36_dry_run/analysis/oar_36_analysis_manifest.json | python -m json.tool",
            "cat benchmarks/oar_360/oar_36_dry_run/analysis/oar_36_analysis_report.md",
            "```",
            "",
            "## Expected State Transitions",
            "- Before raw files: receipt prep is `awaiting_raw_outputs`; analysis is `awaiting_receipt_preparation`.",
            "- After raw files with parseable rows: receipt prep should create normalized judgments and receipt-prep rows.",
            "- Analysis may score only receipt-ready rows.",
            "",
            "## Malformed Rows",
            "- Malformed rows are evidence.",
            "- Do not repair malformed rows.",
            "- Do not fill missing citations.",
            "- Do not rewrite output to make validation pass.",
            "",
        ]
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
