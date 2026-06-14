from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any


@dataclass(frozen=True)
class OAR360SystemSpec:
    role: str
    provider: str
    model: str
    prompt_pack: str
    collection_method: str


@dataclass(frozen=True)
class OAR360ManualEvalIntakeConfig:
    schema_version: str
    suite_name: str
    protocol_version: str
    case_count: int
    manual_evaluation: bool
    ground_truth_holdout_required: bool
    ground_truth_must_not_be_exposed: bool
    no_provider_calls: bool
    no_model_outputs: bool
    evidence_level: int
    manual_result_evidence_cap: int
    level_4_allowed: bool
    level_5_allowed: bool
    default_systems: list[OAR360SystemSpec]
    batch_plan: dict[str, Any]
    raw_output_filename_template: str
    notes: str


@dataclass(frozen=True)
class OAR360BatchSpec:
    batch_id: str
    batch_type: str
    case_count: int
    case_ids: list[str]
    family_distribution: dict[str, int]
    domain_distribution: dict[str, int]
    label_distribution: dict[str, int] | None
    risk_band_distribution: dict[str, int] | None
    intended_use: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return {key: value for key, value in payload.items() if value is not None}


@dataclass(frozen=True)
class OAR360ExpectedRawOutputFile:
    system_role: str
    provider: str
    model: str
    batch_id: str
    batch_type: str
    relative_path: str
    expected_filename: str
    required: bool
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OAR360ManualEvalReadiness:
    case_file_exists: bool
    case_manifest_exists: bool
    prompt_manifest_exists: bool
    prompt_pack_exists: bool
    provider_prompt_packs_exist: bool
    holdout_exists: bool
    ground_truth_not_exposed: bool
    batch_plan_complete: bool
    raw_output_dirs_created: bool
    no_provider_calls: bool
    no_model_outputs: bool
    evidence_level: int
    validation_issues: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OAR360ManualEvalIntakeSummary:
    schema_version: str
    suite_name: str
    case_count: int
    system_count: int
    batch_count: int
    family_batch_count: int
    mixed_batch_count: int
    balanced_batch_count: int
    full_batch_count: int
    expected_raw_output_file_count: int
    source_case_file_hash: str
    source_case_manifest_hash: str
    source_prompt_pack_hash: str
    source_prompt_manifest_hash: str
    source_holdout_hash: str
    intake_manifest_hash: str
    no_provider_calls: bool
    no_model_outputs: bool
    ground_truth_not_exposed: bool
    evidence_level: int
    limitations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_oar_360_manual_eval_intake_config(
    path: Path | str,
) -> OAR360ManualEvalIntakeConfig:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    systems = [OAR360SystemSpec(**system) for system in payload.pop("default_systems")]
    return OAR360ManualEvalIntakeConfig(default_systems=systems, **payload)


def load_jsonl(path: Path | str) -> list[dict[str, Any]]:
    target = Path(path)
    return [
        json.loads(line)
        for line in target.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_cases(path: Path | str) -> list[dict[str, Any]]:
    return load_jsonl(path)


def load_case_manifest(path: Path | str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_prompt_manifest(path: Path | str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def stable_json_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def sanitize_filename_component(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    sanitized = re.sub(r"_+", "_", sanitized)
    return sanitized.strip("_")


def build_system_registry_template(
    config: OAR360ManualEvalIntakeConfig,
) -> dict[str, Any]:
    return {
        "schema_version": "oar_360_system_registry_template_v1",
        "suite_name": config.suite_name,
        "systems": [asdict(system) for system in config.default_systems],
        "minimum_independent_systems": 3,
        "independence_requirements": [
            "separate provider/model or deployment stack",
            "separate raw outputs",
            "separate request manifests",
            "no shared cached outputs",
            "no output from one system used as input to another",
        ],
        "evidence_level_cap_for_manual_results": config.manual_result_evidence_cap,
        "level_4_allowed": config.level_4_allowed,
        "level_5_allowed": config.level_5_allowed,
    }


def build_oar_360_batch_plan(
    cases: list[dict[str, Any]],
    config: OAR360ManualEvalIntakeConfig,
) -> list[OAR360BatchSpec]:
    del config
    sorted_cases = sorted(cases, key=lambda row: row["case_id"])
    batches: list[OAR360BatchSpec] = []

    for family in sorted({case["family"] for case in sorted_cases}):
        family_cases = [case for case in sorted_cases if case["family"] == family]
        batches.append(
            _batch_spec(
                batch_id=f"family_{family}",
                batch_type="family",
                cases=family_cases,
                intended_use="Collect one family-specific raw output file.",
            )
        )

    interleaved = _interleave_cases_by_family(sorted_cases)
    for index, chunk in enumerate(_chunks(interleaved, 60), start=1):
        batches.append(
            _batch_spec(
                batch_id=f"mixed_{index:02d}",
                batch_type="mixed",
                cases=chunk,
                intended_use="Collect a mixed-family 60-case output slice.",
            )
        )

    for index, chunk in enumerate(_chunks(interleaved, 120), start=1):
        batches.append(
            _batch_spec(
                batch_id=f"balanced_{index:02d}",
                batch_type="balanced",
                cases=chunk,
                intended_use="Collect a larger balanced 120-case output slice.",
            )
        )

    batches.append(
        _batch_spec(
            batch_id="full_oar_360",
            batch_type="full",
            cases=sorted_cases,
            intended_use="Collect the full OAR-360 output in one file if feasible.",
        )
    )
    return batches


def build_expected_raw_output_filenames(
    system_registry: dict[str, Any],
    batch_plan: list[OAR360BatchSpec],
    config: OAR360ManualEvalIntakeConfig,
) -> list[OAR360ExpectedRawOutputFile]:
    expected: list[OAR360ExpectedRawOutputFile] = []
    for system in system_registry["systems"]:
        provider = sanitize_filename_component(system["provider"])
        model = sanitize_filename_component(system["model"])
        role = sanitize_filename_component(system["role"])
        for batch in batch_plan:
            filename = config.raw_output_filename_template.format(
                system_role=role,
                provider=provider,
                model=model,
                batch_id=sanitize_filename_component(batch.batch_id),
            )
            expected.append(
                OAR360ExpectedRawOutputFile(
                    system_role=system["role"],
                    provider=system["provider"],
                    model=system["model"],
                    batch_id=batch.batch_id,
                    batch_type=batch.batch_type,
                    relative_path=f"raw_outputs/{provider}/{filename}",
                    expected_filename=filename,
                    required=True,
                    notes="Save raw provider output exactly as collected; do not edit malformed rows.",
                )
            )
    return expected


def validate_ground_truth_not_exposed(
    prompt_root: Path,
    prompt_manifest: dict[str, Any],
) -> tuple[bool, list[str]]:
    issues: list[str] = []
    prompt_pack = prompt_root / "oar_360_prompt_pack.jsonl"
    if not prompt_manifest.get("ground_truth_excluded"):
        issues.append("prompt_manifest_ground_truth_excluded_not_true")
    if not prompt_pack.exists():
        issues.append("prompt_pack_missing")
        return False, issues
    forbidden_tokens = [
        "ground_truth",
        "label",
        "risk_band",
        "expected_decision",
        "expected_risk_interval",
        "required_citation_phrases",
        "forbidden_citation_phrases",
        "reason_codes",
        "case_hash",
    ]
    for index, line in enumerate(prompt_pack.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        record = json.loads(line)
        prompt_text = record.get("prompt_text", "")
        for token in forbidden_tokens:
            if token in prompt_text:
                issues.append(f"prompt_text_leaks_{token}:line_{index}")
    return not issues, issues


def validate_manual_eval_readiness(
    cases_path: Path,
    case_manifest_path: Path,
    prompt_manifest_path: Path,
    prompt_root: Path,
    out_dir: Path,
    cases: list[dict[str, Any]],
    batch_plan: list[OAR360BatchSpec],
    system_registry: dict[str, Any],
    expected_files: list[OAR360ExpectedRawOutputFile],
    config: OAR360ManualEvalIntakeConfig,
) -> OAR360ManualEvalReadiness:
    validation_issues: list[str] = []
    prompt_manifest = load_prompt_manifest(prompt_manifest_path) if prompt_manifest_path.exists() else {}
    ground_truth_not_exposed, ground_truth_issues = validate_ground_truth_not_exposed(
        prompt_root,
        prompt_manifest,
    )
    validation_issues.extend(ground_truth_issues)

    providers = [system["provider"] for system in system_registry["systems"]]
    raw_output_dirs_created = _ensure_raw_output_dirs(out_dir, providers)
    provider_pack_dir = prompt_root / "provider_prompt_packs"
    provider_prompt_packs_exist = all(
        (provider_pack_dir / system["prompt_pack"]).exists()
        for system in system_registry["systems"]
    )
    batch_plan_complete = _batch_plan_complete(cases, batch_plan)

    checks = {
        "case_file_exists": cases_path.exists(),
        "case_manifest_exists": case_manifest_path.exists(),
        "prompt_manifest_exists": prompt_manifest_path.exists(),
        "prompt_pack_exists": (prompt_root / "oar_360_prompt_pack.jsonl").exists(),
        "provider_prompt_packs_exist": provider_prompt_packs_exist,
        "holdout_exists": (
            prompt_root
            / "ground_truth_holdout"
            / "oar_360_ground_truth_holdout.jsonl"
        ).exists(),
        "ground_truth_not_exposed": ground_truth_not_exposed,
        "batch_plan_complete": batch_plan_complete,
        "raw_output_dirs_created": raw_output_dirs_created,
        "no_provider_calls": config.no_provider_calls,
        "no_model_outputs": config.no_model_outputs,
    }
    for check_name, value in checks.items():
        if not value:
            validation_issues.append(f"readiness_failed:{check_name}")
    if len(expected_files) != len(system_registry["systems"]) * len(batch_plan):
        validation_issues.append("expected_raw_output_file_count_mismatch")

    return OAR360ManualEvalReadiness(
        case_file_exists=checks["case_file_exists"],
        case_manifest_exists=checks["case_manifest_exists"],
        prompt_manifest_exists=checks["prompt_manifest_exists"],
        prompt_pack_exists=checks["prompt_pack_exists"],
        provider_prompt_packs_exist=checks["provider_prompt_packs_exist"],
        holdout_exists=checks["holdout_exists"],
        ground_truth_not_exposed=checks["ground_truth_not_exposed"],
        batch_plan_complete=checks["batch_plan_complete"],
        raw_output_dirs_created=checks["raw_output_dirs_created"],
        no_provider_calls=checks["no_provider_calls"],
        no_model_outputs=checks["no_model_outputs"],
        evidence_level=config.evidence_level,
        validation_issues=sorted(set(validation_issues)),
    )


def write_oar_360_manual_eval_intake_outputs(
    config: OAR360ManualEvalIntakeConfig,
    cases: list[dict[str, Any]],
    case_manifest: dict[str, Any],
    prompt_manifest: dict[str, Any],
    batch_plan: list[OAR360BatchSpec],
    system_registry: dict[str, Any],
    expected_files: list[OAR360ExpectedRawOutputFile],
    readiness: OAR360ManualEvalReadiness,
    out_dir: Path | str,
) -> OAR360ManualEvalIntakeSummary:
    del cases
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_output_root = output_dir / "raw_outputs"
    raw_output_root.mkdir(parents=True, exist_ok=True)
    for system in system_registry["systems"]:
        provider_dir = raw_output_root / sanitize_filename_component(system["provider"])
        provider_dir.mkdir(parents=True, exist_ok=True)
        (provider_dir / ".gitkeep").write_text("", encoding="utf-8")
    (raw_output_root / "README.md").write_text(_raw_output_readme(config), encoding="utf-8")

    plan_path = output_dir / "oar_360_manual_eval_plan.json"
    registry_path = output_dir / "oar_360_system_registry_template.json"
    batch_plan_path = output_dir / "oar_360_batch_plan.json"
    instructions_path = output_dir / "oar_360_collection_instructions.md"
    expected_files_path = output_dir / "oar_360_expected_raw_output_filenames.json"
    manifest_path = output_dir / "oar_360_intake_manifest.json"
    report_path = output_dir / "oar_360_intake_report.md"

    _write_json(registry_path, system_registry)
    _write_json(
        batch_plan_path,
        {
            "schema_version": "oar_360_batch_plan_v1",
            "suite_name": config.suite_name,
            "batch_count": len(batch_plan),
            "batches": [batch.to_dict() for batch in batch_plan],
        },
    )
    _write_json(
        expected_files_path,
        {
            "schema_version": "oar_360_expected_raw_output_filenames_v1",
            "suite_name": config.suite_name,
            "expected_raw_output_file_count": len(expected_files),
            "files": [record.to_dict() for record in expected_files],
        },
    )
    instructions_path.write_text(
        _collection_instructions(config, system_registry, batch_plan),
        encoding="utf-8",
    )
    _write_json(
        plan_path,
        {
            "schema_version": "oar_360_manual_eval_plan_v1",
            "suite_name": config.suite_name,
            "purpose": "Prepare OAR-360 for manual collection from independent systems without exposing ground truth.",
            "source_artifacts": {
                "cases": config.case_count,
                "case_file_hash": case_manifest.get("case_file_hash"),
                "case_manifest_hash": case_manifest.get("manifest_hash"),
                "prompt_pack_hash": prompt_manifest.get("prompt_pack_hash"),
                "prompt_manifest_hash": prompt_manifest.get("manifest_hash"),
                "holdout_file_hash": prompt_manifest.get("holdout_file_hash"),
            },
            "system_registry_template_path": str(registry_path),
            "batch_plan_path": str(batch_plan_path),
            "expected_raw_output_filenames_path": str(expected_files_path),
            "collection_instructions_path": str(instructions_path),
            "raw_output_root": str(raw_output_root),
            "evidence_level": config.evidence_level,
            "manual_result_evidence_cap": config.manual_result_evidence_cap,
            "no_provider_calls": config.no_provider_calls,
            "no_model_outputs": config.no_model_outputs,
            "ground_truth_not_exposed": readiness.ground_truth_not_exposed,
        },
    )

    batch_counts = Counter(batch.batch_type for batch in batch_plan)
    manifest = {
        "schema_version": "oar_360_intake_manifest_v1",
        "suite_name": config.suite_name,
        "case_count": config.case_count,
        "system_count": len(system_registry["systems"]),
        "batch_count": len(batch_plan),
        "family_batch_count": batch_counts.get("family", 0),
        "mixed_batch_count": batch_counts.get("mixed", 0),
        "balanced_batch_count": batch_counts.get("balanced", 0),
        "full_batch_count": batch_counts.get("full", 0),
        "expected_raw_output_file_count": len(expected_files),
        "source_case_file_hash": case_manifest.get("case_file_hash"),
        "source_case_manifest_hash": case_manifest.get("manifest_hash"),
        "source_prompt_pack_hash": prompt_manifest.get("prompt_pack_hash"),
        "source_prompt_manifest_hash": prompt_manifest.get("manifest_hash"),
        "source_holdout_hash": prompt_manifest.get("holdout_file_hash"),
        "system_registry_hash": sha256_file(registry_path),
        "batch_plan_hash": sha256_file(batch_plan_path),
        "expected_raw_output_filenames_hash": sha256_file(expected_files_path),
        "collection_instructions_hash": sha256_file(instructions_path),
        "intake_manifest_hash": "",
        "no_provider_calls": config.no_provider_calls,
        "no_model_outputs": config.no_model_outputs,
        "ground_truth_not_exposed": readiness.ground_truth_not_exposed,
        "evidence_level": config.evidence_level,
        "manual_result_evidence_cap": config.manual_result_evidence_cap,
        "level_4_allowed": config.level_4_allowed,
        "level_5_allowed": config.level_5_allowed,
        "readiness": readiness.to_dict(),
        "limitations": _limitations(config),
    }
    manifest_preimage = dict(manifest)
    manifest_preimage.pop("intake_manifest_hash")
    manifest["intake_manifest_hash"] = sha256_text(stable_json_dumps(manifest_preimage))
    _write_json(manifest_path, manifest)

    summary = OAR360ManualEvalIntakeSummary(
        schema_version="oar_360_manual_eval_intake_summary_v1",
        suite_name=config.suite_name,
        case_count=config.case_count,
        system_count=len(system_registry["systems"]),
        batch_count=len(batch_plan),
        family_batch_count=batch_counts.get("family", 0),
        mixed_batch_count=batch_counts.get("mixed", 0),
        balanced_batch_count=batch_counts.get("balanced", 0),
        full_batch_count=batch_counts.get("full", 0),
        expected_raw_output_file_count=len(expected_files),
        source_case_file_hash=manifest["source_case_file_hash"],
        source_case_manifest_hash=manifest["source_case_manifest_hash"],
        source_prompt_pack_hash=manifest["source_prompt_pack_hash"],
        source_prompt_manifest_hash=manifest["source_prompt_manifest_hash"],
        source_holdout_hash=manifest["source_holdout_hash"],
        intake_manifest_hash=manifest["intake_manifest_hash"],
        no_provider_calls=config.no_provider_calls,
        no_model_outputs=config.no_model_outputs,
        ground_truth_not_exposed=readiness.ground_truth_not_exposed,
        evidence_level=config.evidence_level,
        limitations=manifest["limitations"],
    )
    report_path.write_text(
        generate_oar_360_intake_report(
            summary,
            readiness,
            batch_plan,
            system_registry,
            expected_files,
            output_dir,
        ),
        encoding="utf-8",
    )
    return summary


def generate_oar_360_intake_report(
    summary: OAR360ManualEvalIntakeSummary,
    readiness: OAR360ManualEvalReadiness,
    batch_plan: list[OAR360BatchSpec],
    system_registry: dict[str, Any],
    expected_files: list[OAR360ExpectedRawOutputFile],
    out_dir: Path | str,
) -> str:
    del out_dir
    batch_counts = Counter(batch.batch_type for batch in batch_plan)
    lines = [
        "# OAR-360 Manual Evaluation Intake Report",
        "",
        "## Executive Summary",
        (
            "This intake prepares OAR-360 for manual collection from independent "
            "systems. No provider calls were made, no model outputs were created, "
            "and OAR-360 intake itself remains evidence Level 0."
        ),
        "",
        "## Source Artifacts",
        f"- source_case_file_hash: `{summary.source_case_file_hash}`",
        f"- source_case_manifest_hash: `{summary.source_case_manifest_hash}`",
        f"- source_prompt_pack_hash: `{summary.source_prompt_pack_hash}`",
        f"- source_prompt_manifest_hash: `{summary.source_prompt_manifest_hash}`",
        f"- source_holdout_hash: `{summary.source_holdout_hash}`",
        "",
        "## Systems",
        *[
            f"- `{system['role']}`: provider `{system['provider']}`, model `{system['model']}`, prompt pack `{system['prompt_pack']}`"
            for system in system_registry["systems"]
        ],
        "",
        "## Batch Plan Summary",
        f"- batch_count: `{len(batch_plan)}`",
        f"- family_batch_count: `{batch_counts.get('family', 0)}`",
        f"- mixed_batch_count: `{batch_counts.get('mixed', 0)}`",
        f"- balanced_batch_count: `{batch_counts.get('balanced', 0)}`",
        f"- full_batch_count: `{batch_counts.get('full', 0)}`",
        "",
        "## Raw Output Naming",
        f"- expected_raw_output_file_count: `{len(expected_files)}`",
        "- Use the exact filenames listed in `oar_360_expected_raw_output_filenames.json`.",
        "- Do not edit malformed rows.",
        "- Do not fill missing citations.",
        "",
        "## Readiness Checks",
        *[
            f"- {key}: `{value}`"
            for key, value in readiness.to_dict().items()
            if key != "validation_issues"
        ],
        f"- validation_issues: `{readiness.validation_issues}`",
        "",
        "## Ground-Truth Holdout Protection",
        "- Do not expose the ground truth holdout to any model prompt.",
        "- Use provider-specific prompt pack only.",
        "- Ground truth was not exposed to prompts according to the readiness checks.",
        "",
        "## Evidence-Level Boundary",
        "- Manual collection results will be capped at Level 3.",
        "- Level 4 requires locked live runner provenance.",
        "- Level 5 is not claimed.",
        "- Majority vote is not truth.",
        "",
        "## What This Supports",
        "- A reproducible manual intake plan for OAR-360 output collection.",
        "- Stable batch, system registry, expected filename, and intake manifest artifacts.",
        "- Ground-truth-held-out preparation before provider output collection.",
        "",
        "## What This Does Not Prove",
        "- This does not prove model correctness.",
        "- This does not produce OAR-360 empirical results.",
        "- This does not validate provider outputs or HELIX receipt performance.",
        "",
        "## Limitations",
        *[f"- {limitation}" for limitation in summary.limitations],
        "",
        "## Next Steps",
        "- Collect raw outputs manually into the expected provider directories.",
        "- Record retry notes only for UI or network failures.",
        "- Import raw outputs through a validator without repairing provider responses.",
        "- Analyze results against the holdout after collection is complete.",
        "",
    ]
    return "\n".join(lines)


def _batch_spec(
    *,
    batch_id: str,
    batch_type: str,
    cases: list[dict[str, Any]],
    intended_use: str,
) -> OAR360BatchSpec:
    return OAR360BatchSpec(
        batch_id=batch_id,
        batch_type=batch_type,
        case_count=len(cases),
        case_ids=[case["case_id"] for case in cases],
        family_distribution=_distribution(cases, "family"),
        domain_distribution=_distribution(cases, "domain"),
        label_distribution=None,
        risk_band_distribution=None,
        intended_use=intended_use,
    )


def _distribution(cases: list[dict[str, Any]], key: str) -> dict[str, int]:
    counter = Counter(case[key] for case in cases)
    return {name: counter[name] for name in sorted(counter)}


def _interleave_cases_by_family(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        by_family[case["family"]].append(case)
    for family_cases in by_family.values():
        family_cases.sort(key=lambda row: row["case_id"])
    interleaved: list[dict[str, Any]] = []
    max_len = max(len(family_cases) for family_cases in by_family.values())
    for index in range(max_len):
        for family in sorted(by_family):
            family_cases = by_family[family]
            if index < len(family_cases):
                interleaved.append(family_cases[index])
    return interleaved


def _chunks(values: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def _batch_plan_complete(
    cases: list[dict[str, Any]],
    batch_plan: list[OAR360BatchSpec],
) -> bool:
    case_ids = {case["case_id"] for case in cases}
    family_ids = [case_id for batch in batch_plan if batch.batch_type == "family" for case_id in batch.case_ids]
    mixed_ids = [case_id for batch in batch_plan if batch.batch_type == "mixed" for case_id in batch.case_ids]
    balanced_ids = [case_id for batch in batch_plan if batch.batch_type == "balanced" for case_id in batch.case_ids]
    full_batches = [batch for batch in batch_plan if batch.batch_type == "full"]
    return (
        len(batch_plan) == 22
        and len([batch for batch in batch_plan if batch.batch_type == "family"]) == 12
        and len([batch for batch in batch_plan if batch.batch_type == "mixed"]) == 6
        and len([batch for batch in batch_plan if batch.batch_type == "balanced"]) == 3
        and len(full_batches) == 1
        and set(family_ids) == case_ids
        and len(family_ids) == len(case_ids)
        and set(mixed_ids) == case_ids
        and len(mixed_ids) == len(case_ids)
        and set(balanced_ids) == case_ids
        and len(balanced_ids) == len(case_ids)
        and set(full_batches[0].case_ids) == case_ids
    )


def _ensure_raw_output_dirs(out_dir: Path, providers: list[str]) -> bool:
    root = out_dir / "raw_outputs"
    root.mkdir(parents=True, exist_ok=True)
    for provider in providers:
        provider_dir = root / sanitize_filename_component(provider)
        provider_dir.mkdir(parents=True, exist_ok=True)
        (provider_dir / ".gitkeep").write_text("", encoding="utf-8")
    return root.exists() and all((root / sanitize_filename_component(provider)).exists() for provider in providers)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def _raw_output_readme(config: OAR360ManualEvalIntakeConfig) -> str:
    return "\n".join(
        [
            "# OAR-360 Raw Output Intake",
            "",
            "Save provider raw outputs exactly here using the expected filenames.",
            "Do not edit malformed rows.",
            "Do not repair JSON.",
            "Do not fill missing citations.",
            "Do not paste one provider output into another provider directory.",
            "Manual evidence cap is Level 3.",
            "Level 4 requires locked live provenance.",
            f"OAR-360 intake evidence level is {config.evidence_level}.",
            "",
        ]
    )


def _collection_instructions(
    config: OAR360ManualEvalIntakeConfig,
    system_registry: dict[str, Any],
    batch_plan: list[OAR360BatchSpec],
) -> str:
    lines = [
        "# OAR-360 Manual Evaluation Collection Instructions",
        "",
        "## 1. Purpose",
        "Collect real OAR-360 outputs manually from independent systems without calling providers from this repository.",
        "",
        "## 2. Evidence Boundary",
        "This intake creates no empirical results. No provider calls were made and no model outputs were created.",
        "",
        "## 3. Systems",
        *[
            f"- `{system['role']}` uses provider `{system['provider']}` with model `{system['model']}`."
            for system in system_registry["systems"]
        ],
        "",
        "## 4. Prompt Packs",
        "Use provider-specific prompt pack only. Do not expose the ground truth holdout.",
        "",
        "## 5. Batch Plan",
        f"Use the {len(batch_plan)} batches defined in `oar_360_batch_plan.json`.",
        "",
        "## 6. Raw Output Naming",
        "Save raw output exactly using `oar_360_expected_raw_output_filenames.json`.",
        "",
        "## 7. Collection Rules",
        "Save raw output exactly. Do not edit malformed rows. Do not fill missing citations. Do not normalize provider output manually.",
        "",
        "## 8. Retry Rules",
        "Do not retry because the output looks bad. Retry only on UI/network failure and record retry note.",
        "",
        "## 9. What Not To Do",
        "Never paste one provider's output into another provider. Majority vote is not truth. Model correctness is not claimed.",
        "",
        "## 10. Evidence-Level Limits",
        f"Manual evidence is capped at Level {config.manual_result_evidence_cap}. Level 4 requires locked live runner provenance. Level 5 is not claimed. OAR-360 intake itself is evidence Level 0.",
        "",
        "## 11. After Collection",
        "Run raw-output validation and preserve malformed or incomplete outputs honestly.",
        "",
    ]
    return "\n".join(lines)


def _limitations(config: OAR360ManualEvalIntakeConfig) -> list[str]:
    return [
        config.notes,
        "This intake protocol does not parse, normalize, or score provider outputs.",
        "Manual collection cannot establish Level 4 or Level 5 evidence.",
        "Majority agreement across systems must not be treated as truth.",
        "Ground truth is held out from prompts but remains necessary for later analysis.",
    ]
