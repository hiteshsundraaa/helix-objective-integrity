from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any


@dataclass(frozen=True)
class OAR36DryRunConfig:
    schema_version: str
    suite_name: str
    source_suite: str
    protocol_version: str
    dry_run_id: str
    case_count: int
    cases_per_family: int
    minimum_domain_count: int
    minimum_edge_tag_count: int
    no_provider_calls: bool
    no_model_outputs: bool
    no_empirical_results: bool
    evidence_level: int
    manual_result_evidence_cap: int
    level_4_allowed: bool
    level_5_allowed: bool
    families: list[str]
    default_systems: list[dict[str, str]]
    raw_output_filename_template: str
    limitations: list[str]


@dataclass(frozen=True)
class OAR36SelectionSummary:
    total_cases: int
    family_distribution: dict[str, int]
    domain_distribution: dict[str, int]
    label_distribution: dict[str, int]
    expected_decision_distribution: dict[str, int]
    risk_band_distribution: dict[str, int]
    edge_tag_distribution: dict[str, int]
    distinct_edge_tags: int
    selected_case_ids: list[str]
    validation_issues: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OAR36ExpectedRawOutputFile:
    system_role: str
    provider: str
    model: str
    relative_path: str
    expected_filename: str
    required: bool
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OAR36DryRunSummary:
    suite_name: str
    source_suite: str
    total_cases: int
    prompt_count: int
    holdout_count: int
    expected_raw_output_file_count: int
    family_distribution: dict[str, int]
    domain_distribution: dict[str, int]
    label_distribution: dict[str, int]
    expected_decision_distribution: dict[str, int]
    risk_band_distribution: dict[str, int]
    distinct_edge_tags: int
    case_manifest_hash: str
    prompt_manifest_hash: str
    holdout_manifest_hash: str
    no_provider_calls: bool
    no_model_outputs: bool
    no_empirical_results: bool
    evidence_level: int
    limitations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_oar_36_dry_run_config(path: str | Path) -> OAR36DryRunConfig:
    return OAR36DryRunConfig(**json.loads(Path(path).read_text(encoding="utf-8")))


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_oar_360_cases(path: str | Path) -> list[dict[str, Any]]:
    return load_jsonl(path)


def load_oar_360_prompts(path: str | Path) -> list[dict[str, Any]]:
    return load_jsonl(path)


def load_oar_360_holdout(path: str | Path) -> list[dict[str, Any]]:
    return load_jsonl(path)


def select_oar_36_cases(
    cases: list[dict[str, Any]],
    config: OAR36DryRunConfig,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    domain_counts: Counter[str] = Counter()
    seen_labels: set[str] = set()
    seen_decisions: set[str] = set()
    seen_risk_bands: set[str] = set()
    seen_edge_tags: set[str] = set()

    for family in config.families:
        family_cases = sorted(
            [case for case in cases if case["family"] == family],
            key=lambda case: case["case_id"],
        )
        if len(family_cases) < config.cases_per_family:
            raise ValueError(f"Not enough OAR-360 cases for family {family}")
        chosen: list[dict[str, Any]] = []
        while len(chosen) < config.cases_per_family:
            remaining = [case for case in family_cases if case not in chosen]
            best = max(
                remaining,
                key=lambda case: (
                    _selection_score(
                        case,
                        domain_counts,
                        seen_labels,
                        seen_decisions,
                        seen_risk_bands,
                        seen_edge_tags,
                    ),
                    _case_number(case["case_id"]) * -1,
                ),
            )
            chosen.append(best)
            domain_counts[best["domain"]] += 1
            seen_labels.add(best["label"])
            seen_decisions.add(best["expected_decision"])
            seen_risk_bands.add(best["risk_band"])
            seen_edge_tags.update(best["edge_case_tags"])
        selected.extend(chosen)

    issues = validate_oar_36_selection(selected, [], [], config)
    if issues:
        raise ValueError(f"OAR-36 selection failed validation: {issues}")
    return selected


def build_oar_36_prompt_pack(
    selected_case_ids: list[str],
    oar_360_prompts: list[dict[str, Any]],
    config: OAR36DryRunConfig | None = None,
) -> list[dict[str, Any]]:
    cfg = config or _default_config()
    prompts_by_case_id = {prompt["case_id"]: prompt for prompt in oar_360_prompts}
    prompt_pack: list[dict[str, Any]] = []
    for index, case_id in enumerate(selected_case_ids, start=1):
        source = prompts_by_case_id[case_id]
        record = {
            "schema_version": "oar_36_prompt_v1",
            "suite": cfg.suite_name,
            "source_suite": cfg.source_suite,
            "dry_run_id": cfg.dry_run_id,
            "case_id": case_id,
            "prompt_id": f"oar36_prompt_{index:03d}",
            "prompt_mode": source.get("prompt_mode", "generic"),
            "prompt_text": source["prompt_text"],
            "visible_fields": source.get("visible_fields", []),
            "withheld_fields": source.get("withheld_fields", []),
            "source_case_hash": source["source_case_hash"],
            "source_oar360_prompt_id": source["prompt_id"],
            "source_oar360_prompt_hash": source["prompt_hash"],
            "prompt_hash": "",
        }
        record["prompt_hash"] = sha256_text(stable_json_dumps({**record, "prompt_hash": ""}))
        prompt_pack.append(record)
    return prompt_pack


def build_oar_36_holdout(
    selected_case_ids: list[str],
    oar_360_holdout: list[dict[str, Any]],
    config: OAR36DryRunConfig | None = None,
) -> list[dict[str, Any]]:
    cfg = config or _default_config()
    holdout_by_case_id = {record["case_id"]: record for record in oar_360_holdout}
    holdout: list[dict[str, Any]] = []
    for index, case_id in enumerate(selected_case_ids, start=1):
        source = holdout_by_case_id[case_id]
        holdout.append(
            {
                "schema_version": "oar_36_ground_truth_holdout_v1",
                "suite": cfg.suite_name,
                "source_suite": cfg.source_suite,
                "dry_run_id": cfg.dry_run_id,
                "case_id": case_id,
                "dry_run_case_index": index,
                "family": source["family"],
                "domain": source["domain"],
                "label": source["label"],
                "risk_band": source["risk_band"],
                "expected_decision": source["expected_decision"],
                "expected_risk_interval": source["expected_risk_interval"],
                "required_citation_phrases": source["required_citation_phrases"],
                "forbidden_citation_phrases": source["forbidden_citation_phrases"],
                "reason_codes": source["reason_codes"],
                "minimum_evidence_required": source["minimum_evidence_required"],
                "edge_case_tags": source["edge_case_tags"],
                "source_case_hash": source["case_hash"],
            }
        )
    return holdout


def build_oar_36_expected_raw_output_filenames(
    config: OAR36DryRunConfig,
) -> list[OAR36ExpectedRawOutputFile]:
    records: list[OAR36ExpectedRawOutputFile] = []
    for system in config.default_systems:
        role = sanitize_filename_component(system["role"])
        provider = sanitize_filename_component(system["provider"])
        model = sanitize_filename_component(system["model"])
        filename = config.raw_output_filename_template.format(
            system_role=role,
            provider=provider,
            model=model,
        )
        records.append(
            OAR36ExpectedRawOutputFile(
                system_role=system["role"],
                provider=system["provider"],
                model=system["model"],
                relative_path=f"raw_outputs/{provider}/{filename}",
                expected_filename=filename,
                required=True,
                notes="Save raw provider output exactly as collected; do not edit malformed rows.",
            )
        )
    return records


def validate_oar_36_selection(
    selected_cases: list[dict[str, Any]],
    prompts: list[dict[str, Any]],
    holdout: list[dict[str, Any]],
    config: OAR36DryRunConfig,
) -> list[str]:
    issues: list[str] = []
    family_distribution = _distribution(selected_cases, "family")
    domain_distribution = _distribution(selected_cases, "domain")
    label_distribution = _distribution(selected_cases, "label")
    decision_distribution = _distribution(selected_cases, "expected_decision")
    risk_distribution = _distribution(selected_cases, "risk_band")
    edge_distribution = _edge_distribution(selected_cases)
    selected_ids = [case["case_id"] for case in selected_cases]

    if len(selected_cases) != config.case_count:
        issues.append(f"case_count_expected_{config.case_count}_got_{len(selected_cases)}")
    if len(set(selected_ids)) != len(selected_ids):
        issues.append("duplicate_selected_case_id")
    for family in config.families:
        if family_distribution.get(family) != config.cases_per_family:
            issues.append(f"family_count_mismatch:{family}")
    if len(domain_distribution) < config.minimum_domain_count:
        issues.append("domain_coverage_too_low")
    if len(label_distribution) < 4:
        issues.append("label_coverage_too_low")
    if len(decision_distribution) < 6:
        issues.append("decision_coverage_too_low")
    if len(risk_distribution) < 6:
        issues.append("risk_band_coverage_too_low")
    if len(edge_distribution) < config.minimum_edge_tag_count:
        issues.append("edge_tag_coverage_too_low")

    if prompts:
        prompt_ids = {prompt["case_id"] for prompt in prompts}
        if prompt_ids != set(selected_ids):
            issues.append("prompt_case_id_mismatch")
        forbidden_prompt_tokens = [
            "label",
            "risk_band",
            "expected_decision",
            "expected_risk_interval",
            "ground_truth",
        ]
        for prompt in prompts:
            text = prompt.get("prompt_text", "")
            for token in forbidden_prompt_tokens:
                if token in text:
                    issues.append(f"prompt_leaks_{token}:{prompt['case_id']}")
    if holdout:
        holdout_ids = {record["case_id"] for record in holdout}
        if holdout_ids != set(selected_ids):
            issues.append("holdout_case_id_mismatch")
        for record in holdout:
            if "expected_decision" not in record:
                issues.append(f"holdout_missing_expected_decision:{record['case_id']}")
            if "required_citation_phrases" not in record:
                issues.append(f"holdout_missing_required_citation_phrases:{record['case_id']}")
    return sorted(set(issues))


def write_oar_36_outputs(
    *,
    config: OAR36DryRunConfig,
    selected_cases: list[dict[str, Any]],
    prompts: list[dict[str, Any]],
    holdout: list[dict[str, Any]],
    expected_raw_outputs: list[OAR36ExpectedRawOutputFile],
    source_case_file: str | Path,
    source_case_manifest: dict[str, Any],
    source_prompt_pack: str | Path,
    source_prompt_manifest: dict[str, Any],
    source_holdout_file: str | Path,
    source_holdout_manifest: dict[str, Any],
    out_dir: str | Path,
) -> OAR36DryRunSummary:
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_root = output_dir / "raw_outputs"
    raw_root.mkdir(parents=True, exist_ok=True)
    for provider in sorted({record.provider for record in expected_raw_outputs}):
        provider_dir = raw_root / sanitize_filename_component(provider)
        provider_dir.mkdir(parents=True, exist_ok=True)
        (provider_dir / ".gitkeep").write_text("", encoding="utf-8")
    (raw_root / "README.md").write_text(_raw_output_readme(config), encoding="utf-8")

    selected_case_ids = [case["case_id"] for case in selected_cases]
    wrapped_cases = [
        {
            "schema_version": "oar_36_case_wrapper_v1",
            "suite": config.suite_name,
            "source_suite": config.source_suite,
            "dry_run_id": config.dry_run_id,
            "case_id": case["case_id"],
            "source_case_hash": case["generation"]["case_hash"],
            "source_case": case,
        }
        for case in selected_cases
    ]
    cases_path = output_dir / "oar_36_cases.jsonl"
    prompt_path = output_dir / "oar_36_prompt_pack.jsonl"
    holdout_path = output_dir / "oar_36_ground_truth_holdout.jsonl"
    expected_path = output_dir / "oar_36_expected_raw_output_filenames.json"
    instructions_path = output_dir / "oar_36_collection_instructions.md"
    manual_plan_path = output_dir / "oar_36_manual_eval_plan.json"
    case_manifest_path = output_dir / "oar_36_case_manifest.json"
    prompt_manifest_path = output_dir / "oar_36_prompt_manifest.json"
    holdout_manifest_path = output_dir / "oar_36_ground_truth_holdout_manifest.json"
    report_path = output_dir / "oar_36_report.md"

    _write_jsonl(cases_path, wrapped_cases)
    _write_jsonl(prompt_path, prompts)
    _write_jsonl(holdout_path, holdout)
    _write_json(
        expected_path,
        {
            "schema_version": "oar_36_expected_raw_output_filenames_v1",
            "suite_name": config.suite_name,
            "expected_raw_output_file_count": len(expected_raw_outputs),
            "files": [record.to_dict() for record in expected_raw_outputs],
        },
    )
    instructions_path.write_text(_collection_instructions(config), encoding="utf-8")

    selection_summary = summarize_selection(selected_cases, [])
    case_manifest = {
        "schema_version": "oar_36_case_manifest_v1",
        "suite_name": config.suite_name,
        "source_suite": config.source_suite,
        "total_cases": len(selected_cases),
        "source_case_file_hash": sha256_file(source_case_file),
        "source_case_manifest_hash": source_case_manifest.get("manifest_hash"),
        "selected_case_ids": selected_case_ids,
        "family_distribution": selection_summary.family_distribution,
        "domain_distribution": selection_summary.domain_distribution,
        "label_distribution": selection_summary.label_distribution,
        "expected_decision_distribution": selection_summary.expected_decision_distribution,
        "risk_band_distribution": selection_summary.risk_band_distribution,
        "edge_tag_distribution": selection_summary.edge_tag_distribution,
        "case_file_hash": sha256_file(cases_path),
        "manifest_hash": "",
        "no_provider_calls": True,
        "no_model_outputs": True,
        "evidence_level": config.evidence_level,
        "limitations": config.limitations,
    }
    case_manifest["manifest_hash"] = _manifest_hash(case_manifest)
    _write_json(case_manifest_path, case_manifest)

    prompt_manifest = {
        "schema_version": "oar_36_prompt_manifest_v1",
        "suite_name": config.suite_name,
        "source_suite": config.source_suite,
        "prompt_count": len(prompts),
        "source_prompt_pack_hash": source_prompt_manifest.get("prompt_pack_hash") or sha256_file(source_prompt_pack),
        "selected_prompt_ids": [prompt["prompt_id"] for prompt in prompts],
        "source_oar360_prompt_ids": [prompt["source_oar360_prompt_id"] for prompt in prompts],
        "prompt_file_hash": sha256_file(prompt_path),
        "manifest_hash": "",
        "ground_truth_excluded": True,
        "no_provider_calls": True,
        "no_model_outputs": True,
    }
    prompt_manifest["manifest_hash"] = _manifest_hash(prompt_manifest)
    _write_json(prompt_manifest_path, prompt_manifest)

    holdout_manifest = {
        "schema_version": "oar_36_ground_truth_holdout_manifest_v1",
        "suite_name": config.suite_name,
        "source_suite": config.source_suite,
        "holdout_count": len(holdout),
        "source_holdout_file_hash": source_holdout_manifest.get("holdout_file_hash") or sha256_file(source_holdout_file),
        "holdout_file_hash": sha256_file(holdout_path),
        "manifest_hash": "",
        "separated_from_prompts": True,
        "not_for_model_prompting": True,
    }
    holdout_manifest["manifest_hash"] = _manifest_hash(holdout_manifest)
    _write_json(holdout_manifest_path, holdout_manifest)

    manual_plan = {
        "schema_version": "oar_36_manual_eval_plan_v1",
        "suite_name": config.suite_name,
        "purpose": "Validate OAR-360 provider prompt usability and manual collection workflow on a locked 36-case subset.",
        "system_count": len(config.default_systems),
        "expected_raw_output_file_count": len(expected_raw_outputs),
        "raw_output_root": str(raw_root),
        "collection_instructions_path": str(instructions_path),
        "no_provider_calls": True,
        "no_model_outputs": True,
        "evidence_level": config.evidence_level,
        "manual_result_evidence_cap": config.manual_result_evidence_cap,
        "level_4_allowed": config.level_4_allowed,
        "level_5_allowed": config.level_5_allowed,
    }
    _write_json(manual_plan_path, manual_plan)

    summary = OAR36DryRunSummary(
        suite_name=config.suite_name,
        source_suite=config.source_suite,
        total_cases=len(selected_cases),
        prompt_count=len(prompts),
        holdout_count=len(holdout),
        expected_raw_output_file_count=len(expected_raw_outputs),
        family_distribution=selection_summary.family_distribution,
        domain_distribution=selection_summary.domain_distribution,
        label_distribution=selection_summary.label_distribution,
        expected_decision_distribution=selection_summary.expected_decision_distribution,
        risk_band_distribution=selection_summary.risk_band_distribution,
        distinct_edge_tags=selection_summary.distinct_edge_tags,
        case_manifest_hash=case_manifest["manifest_hash"],
        prompt_manifest_hash=prompt_manifest["manifest_hash"],
        holdout_manifest_hash=holdout_manifest["manifest_hash"],
        no_provider_calls=True,
        no_model_outputs=True,
        no_empirical_results=True,
        evidence_level=config.evidence_level,
        limitations=config.limitations,
    )
    report_path.write_text(
        generate_oar_36_report(summary, config, selection_summary),
        encoding="utf-8",
    )
    return summary


def generate_oar_36_report(
    summary: OAR36DryRunSummary,
    config: OAR36DryRunConfig,
    selection_summary: OAR36SelectionSummary,
) -> str:
    lines = [
        "# OAR-36 Dry-Run Pilot Extraction Report",
        "",
        "## Executive Summary",
        (
            "OAR-36 is a locked dry-run subset extracted from OAR-360 to validate "
            "manual collection, import validation, parser behavior, and reviewer-visible "
            "evidence discipline. No provider calls were made, no model outputs were "
            "created, and no empirical results were created."
        ),
        "",
        "## Source Artifacts",
        "- `benchmarks/oar_360/oar_360_cases.jsonl`",
        "- `benchmarks/oar_360/prompts/oar_360_prompt_pack.jsonl`",
        "- `benchmarks/oar_360/prompts/ground_truth_holdout/oar_360_ground_truth_holdout.jsonl`",
        "",
        "## Selection Method",
        (
            "Selection is deterministic and family-first: exactly three cases are "
            "chosen from each OAR-360 family, greedily preferring coverage of domains, "
            "labels, expected decisions, risk bands, and edge tags."
        ),
        "",
        "## Selection Distributions",
        f"- total_cases: `{summary.total_cases}`",
        f"- family_distribution: `{summary.family_distribution}`",
        f"- domain_distribution: `{summary.domain_distribution}`",
        f"- label_distribution: `{summary.label_distribution}`",
        f"- expected_decision_distribution: `{summary.expected_decision_distribution}`",
        f"- risk_band_distribution: `{summary.risk_band_distribution}`",
        f"- distinct_edge_tags: `{selection_summary.distinct_edge_tags}`",
        "",
        "## Prompt/Holdout Separation",
        "- OAR-36 prompts are derived from OAR-360 prompt records.",
        "- Ground truth is not exposed in the prompt pack.",
        "- OAR-36 holdout records are separated from prompts and are not for model prompting.",
        "",
        "## Raw Output Plan",
        f"- expected_raw_output_file_count: `{summary.expected_raw_output_file_count}`",
        "- Raw outputs must be saved exactly under provider-specific directories.",
        "- Do not edit malformed rows or fill missing citations.",
        "",
        "## What This Supports",
        "- Provider prompt usability checks.",
        "- Manual raw-output collection workflow checks.",
        "- JSON schema, citation-field, import-validation, and parser dry-run checks.",
        "",
        "## What This Does Not Prove",
        "- This dry-run does not prove model correctness.",
        "- This dry-run does not estimate full OAR-360 performance.",
        "- This dry-run does not produce scored benchmark results.",
        "",
        "## Limitations",
        *[f"- {limitation}" for limitation in config.limitations],
        "- Manual evidence is capped at Level 3.",
        "- Level 4/5 are not claimed.",
        "",
        "## Next Steps",
        "- Use OAR-36 prompt pack only for dry-run collection.",
        "- Validate raw outputs with the raw import validator.",
        "- Review schema and parser behavior before scaling to OAR-360.",
        "",
    ]
    return "\n".join(lines)


def summarize_selection(
    selected_cases: list[dict[str, Any]],
    validation_issues: list[str],
) -> OAR36SelectionSummary:
    edge_distribution = _edge_distribution(selected_cases)
    return OAR36SelectionSummary(
        total_cases=len(selected_cases),
        family_distribution=_distribution(selected_cases, "family"),
        domain_distribution=_distribution(selected_cases, "domain"),
        label_distribution=_distribution(selected_cases, "label"),
        expected_decision_distribution=_distribution(selected_cases, "expected_decision"),
        risk_band_distribution=_distribution(selected_cases, "risk_band"),
        edge_tag_distribution=edge_distribution,
        distinct_edge_tags=len(edge_distribution),
        selected_case_ids=[case["case_id"] for case in selected_cases],
        validation_issues=validation_issues,
    )


def _selection_score(
    case: dict[str, Any],
    domain_counts: Counter[str],
    seen_labels: set[str],
    seen_decisions: set[str],
    seen_risk_bands: set[str],
    seen_edge_tags: set[str],
) -> int:
    domain_count = domain_counts[case["domain"]]
    return (
        (5000 if domain_count == 0 else 0)
        + (2500 if domain_count == 1 else 0)
        + max(0, 8 - domain_count) * 100
        + (300 if case["label"] not in seen_labels else 0)
        + (300 if case["expected_decision"] not in seen_decisions else 0)
        + (300 if case["risk_band"] not in seen_risk_bands else 0)
        + sum(50 for tag in case["edge_case_tags"] if tag not in seen_edge_tags)
    )


def _distribution(cases: list[dict[str, Any]], key: str) -> dict[str, int]:
    counter = Counter(case[key] for case in cases)
    return {name: counter[name] for name in sorted(counter)}


def _edge_distribution(cases: list[dict[str, Any]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for case in cases:
        counter.update(case["edge_case_tags"])
    return {name: counter[name] for name in sorted(counter)}


def _case_number(case_id: str) -> int:
    return int(case_id.rsplit("_", 1)[1])


def sanitize_filename_component(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    sanitized = re.sub(r"_+", "_", sanitized)
    return sanitized.strip("_")


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


def _manifest_hash(manifest: dict[str, Any]) -> str:
    preimage = dict(manifest)
    preimage["manifest_hash"] = ""
    return sha256_text(stable_json_dumps(preimage))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(record, sort_keys=True, ensure_ascii=True) + "\n" for record in records),
        encoding="utf-8",
    )


def _raw_output_readme(config: OAR36DryRunConfig) -> str:
    return "\n".join(
        [
            "# OAR-36 Dry-Run Raw Outputs",
            "",
            "Save provider raw outputs exactly here using the expected filenames.",
            "Do not edit malformed rows.",
            "Do not fill missing citations.",
            "Do not normalize provider output manually.",
            f"Manual evidence is capped at Level {config.manual_result_evidence_cap}.",
            "Level 4/5 are not claimed.",
            "",
        ]
    )


def _collection_instructions(config: OAR36DryRunConfig) -> str:
    return "\n".join(
        [
            "# OAR-36 Dry-Run Collection Instructions",
            "",
            "- Use OAR-36 prompt pack only for dry run.",
            "- Do not expose OAR-36 holdout.",
            "- Do not expose OAR-360 holdout.",
            "- Save raw output exactly.",
            "- Do not edit malformed rows.",
            "- Do not fill missing citations.",
            "- Do not normalize provider output manually.",
            "- Do not retry because the output looks bad.",
            "- Retry only on UI/network failure and record retry note.",
            "- Do not use one provider output as input to another.",
            "- Majority vote is not truth.",
            "- Model correctness is not claimed.",
            "- Dry-run results are only protocol validation unless separately scored later.",
            f"- Manual evidence is capped at Level {config.manual_result_evidence_cap}.",
            "- Level 4/5 are not claimed.",
            "",
        ]
    )


def _default_config() -> OAR36DryRunConfig:
    return OAR36DryRunConfig(
        schema_version="oar_36_dry_run_config_v1",
        suite_name="OAR-36",
        source_suite="OAR-360",
        protocol_version="oar_36_dry_run_v1",
        dry_run_id="oar36_dry_run_001",
        case_count=36,
        cases_per_family=3,
        minimum_domain_count=10,
        minimum_edge_tag_count=18,
        no_provider_calls=True,
        no_model_outputs=True,
        no_empirical_results=True,
        evidence_level=0,
        manual_result_evidence_cap=3,
        level_4_allowed=False,
        level_5_allowed=False,
        families=[],
        default_systems=[],
        raw_output_filename_template="{system_role}{provider}{model}_oar36_dry_run_raw.jsonl",
        limitations=[],
    )
