from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime
import json
import random
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from helix.benchmark.benchmark_receipts import hash_file, stable_json_hash
from helix.benchmark.v10_generator import V10Case


Stage = Literal["pilot", "full"]


class V10ProviderProtocolConfig(BaseModel):
    schema_version: str
    registered_before_provider_calls: bool
    default_run_stage: Stage
    pilot_case_count: int
    pilot_cases_per_family: int
    pilot_sampling_seed: int
    full_case_count: int
    prompt_mode: Literal["contract", "generic", "split_view"]
    generic_prompt_path: str
    contract_prompt_path: str
    prompt_rendering_manifest_path: str
    cases_path: str
    normalization_config_path: str
    benchmark_config_path: str
    diagnostics_config_path: str
    reportability_config_path: str
    provider: str | None = None
    model: str | None = None
    model_version: str | None = None
    temperature: float
    top_p: float
    max_output_tokens: int
    timeout_seconds: int
    max_retries: int
    retry_allowed_reasons: list[str]
    retry_disallowed_reasons: list[str]
    max_pilot_cost_usd: float
    max_full_cost_usd: float
    evidence_level_cap_without_human_or_live_validation: int
    level_5_allowed: bool
    notes: str = ""


class V10ProviderSamplingSummary(BaseModel):
    stage: Stage
    case_count: int
    family_counts: dict[str, int]
    label_counts: dict[str, int]
    sampled_case_ids: list[str]
    deterministic_seed: int | None
    status: Literal["complete", "needs_work", "failed"]


class V10ProviderRunPlan(BaseModel):
    schema_version: str = "v10_provider_run_plan_v1"
    stage: Stage
    provider: str | None = None
    model: str | None = None
    model_version: str | None = None
    prompt_mode: str
    case_count: int
    family_counts: dict[str, int]
    label_counts: dict[str, int]
    prompt_hashes: dict[str, str | None]
    config_hashes: dict[str, str]
    sampled_case_ids: list[str]
    evidence_level_cap_without_human_or_live_validation: int
    level_5_allowed: bool
    no_api_calls_made: bool = True
    runtime_settings: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    plan_hash: str

    def to_markdown(self) -> str:
        provider = self.provider if self.provider is not None else "null"
        model = self.model if self.model is not None else "null"
        lines = [
            "# HELIX v10 Provider Run Plan",
            "",
            "## Executive Summary",
            "",
            f"- stage: `{self.stage}`",
            f"- case_count: `{self.case_count}`",
            f"- provider: `{provider}`",
            f"- model: `{model}`",
            f"- no_api_calls_made: `{str(self.no_api_calls_made).lower()}`",
            f"- level_5_allowed: `{str(self.level_5_allowed).lower()}`",
            f"- plan_hash: `{self.plan_hash}`",
            "",
            "This is a planning artifact only. Live provider calls are not executed.",
            "",
            "## Stage",
            "",
            f"- `{self.stage}`",
            "",
            "## Provider / Model",
            "",
            f"- provider: `{provider}`",
            f"- model: `{model}`",
            f"- model_version: `{self.model_version or 'null'}`",
            "- Provider/model names are metadata only.",
            "- Live execution requires filling provider/model and an explicit future run command.",
            "",
            "## Prompt Hashes",
            "",
        ]
        lines.extend(
            f"- `{key}`: `{value}`" for key, value in sorted(self.prompt_hashes.items())
        )
        lines.extend(
            [
                "",
                "## Case Sampling",
                "",
                f"- case_count: `{self.case_count}`",
                f"- sampled_case_ids_path: `sampled_case_ids.json`",
                "",
                "## Label and Family Distribution",
                "",
                "### Family Counts",
                "",
            ]
        )
        lines.extend(f"- `{key}`: `{value}`" for key, value in sorted(self.family_counts.items()))
        lines.extend(["", "### Label Counts", ""])
        lines.extend(f"- `{key}`: `{value}`" for key, value in sorted(self.label_counts.items()))
        lines.extend(
            [
                "",
                "## Evidence-Level Rules",
                "",
                f"- evidence_level_cap_without_human_or_live_validation: `{self.evidence_level_cap_without_human_or_live_validation}`",
                "- Level 5 is not allowed.",
                "- Pilot runs are schema/compliance evidence only.",
                "- A single-provider full run may reach Level 4 only if all preregistered gates pass.",
                "",
                "## What This Supports",
                "",
                "- This supports locked provider-run planning before live calls.",
                "- This supports deterministic sampling, prompt hashing, and config hashing.",
                "",
                "## What This Does Not Yet Prove",
                "",
                "- No API calls were made.",
                "- No provider judgments were collected.",
                "- No provider output was parsed or normalized.",
                "- No final v10 evidence is claimed.",
                "",
                "## Limitations",
                "",
                "- Provider/model may be null in planning config.",
                "- This is not a live provider run.",
                "- The plan cannot validate schema compliance until real raw outputs exist.",
                "- Level 5 remains false.",
            ]
        )
        if self.warnings:
            lines.extend(["", "## Warnings", ""])
            lines.extend(f"- `{warning}`" for warning in self.warnings)
        return "\n".join(lines)


def load_v10_provider_protocol_config(path: str | Path) -> V10ProviderProtocolConfig:
    return V10ProviderProtocolConfig.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def load_v10_cases(path: str | Path) -> list[V10Case]:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(
            f"V10 cases file does not exist: {target}. "
            "Run examples/generate_v10_calibrated_cases.py first."
        )
    return [
        V10Case.model_validate_json(line)
        for line in target.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def build_v10_pilot_case_sample(
    cases: list[V10Case],
    config: V10ProviderProtocolConfig,
) -> V10ProviderSamplingSummary:
    by_family: dict[str, list[V10Case]] = defaultdict(list)
    for case in cases:
        by_family[case.family].append(case)

    selected: list[V10Case] = []
    for family in sorted(by_family):
        pool = sorted(by_family[family], key=lambda item: item.case_id)
        if len(pool) < config.pilot_cases_per_family:
            raise ValueError(
                f"Family {family} has fewer than {config.pilot_cases_per_family} cases"
            )
        rng = random.Random(f"{config.pilot_sampling_seed}:{family}")
        shuffled = list(pool)
        rng.shuffle(shuffled)
        chosen: list[V10Case] = []
        seen_labels: set[str] = set()
        for case in shuffled:
            if case.label not in seen_labels:
                chosen.append(case)
                seen_labels.add(case.label)
            if len(chosen) == config.pilot_cases_per_family:
                break
        chosen_ids = {case.case_id for case in chosen}
        for case in shuffled:
            if len(chosen) == config.pilot_cases_per_family:
                break
            if case.case_id not in chosen_ids:
                chosen.append(case)
                chosen_ids.add(case.case_id)
        selected.extend(chosen)

    selected = sorted(selected, key=lambda item: item.case_id)
    if len(selected) != config.pilot_case_count:
        raise ValueError(
            f"Pilot sample expected {config.pilot_case_count} cases but selected {len(selected)}"
        )
    return _sampling_summary(
        stage="pilot",
        cases=selected,
        deterministic_seed=config.pilot_sampling_seed,
        expected_count=config.pilot_case_count,
    )


def build_v10_full_case_list(
    cases: list[V10Case],
    config: V10ProviderProtocolConfig,
) -> V10ProviderSamplingSummary:
    selected = sorted(cases, key=lambda item: item.case_id)
    if len(selected) != config.full_case_count:
        raise ValueError(
            f"Full run expected {config.full_case_count} cases but found {len(selected)}"
        )
    return _sampling_summary(
        stage="full",
        cases=selected,
        deterministic_seed=None,
        expected_count=config.full_case_count,
    )


def build_v10_provider_run_plan(
    *,
    cases: list[V10Case],
    config: V10ProviderProtocolConfig,
    config_path: str | Path,
    stage: Stage | None = None,
) -> V10ProviderRunPlan:
    selected_stage = stage or config.default_run_stage
    sampling = (
        build_v10_pilot_case_sample(cases, config)
        if selected_stage == "pilot"
        else build_v10_full_case_list(cases, config)
    )
    prompt_hashes = _prompt_hashes(config)
    config_hashes = _config_hashes(config, config_path)
    warnings = []
    if config.provider is None or config.model is None:
        warnings.append("provider_or_model_not_filled_for_planning")
    if selected_stage == "pilot":
        warnings.append("pilot_run_not_final_evidence")
    payload = {
        "schema_version": "v10_provider_run_plan_v1",
        "stage": selected_stage,
        "provider": config.provider,
        "model": config.model,
        "model_version": config.model_version,
        "prompt_mode": config.prompt_mode,
        "case_count": sampling.case_count,
        "family_counts": sampling.family_counts,
        "label_counts": sampling.label_counts,
        "prompt_hashes": prompt_hashes,
        "config_hashes": config_hashes,
        "sampled_case_ids": sampling.sampled_case_ids,
        "evidence_level_cap_without_human_or_live_validation": config.evidence_level_cap_without_human_or_live_validation,
        "level_5_allowed": config.level_5_allowed,
        "no_api_calls_made": True,
        "runtime_settings": {
            "temperature": config.temperature,
            "top_p": config.top_p,
            "max_output_tokens": config.max_output_tokens,
            "timeout_seconds": config.timeout_seconds,
            "max_retries": config.max_retries,
            "retry_allowed_reasons": config.retry_allowed_reasons,
            "retry_disallowed_reasons": config.retry_disallowed_reasons,
            "max_pilot_cost_usd": config.max_pilot_cost_usd,
            "max_full_cost_usd": config.max_full_cost_usd,
        },
        "warnings": sorted(set(warnings)),
    }
    return V10ProviderRunPlan(**payload, plan_hash=stable_json_hash(payload))


def write_v10_provider_run_plan(
    *,
    plan: V10ProviderRunPlan,
    config_path: str | Path,
    out_dir: str | Path,
    generated_at: str | None = None,
) -> dict[str, Path]:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    plan_path = target / "provider_run_plan.json"
    sampled_path = target / "sampled_case_ids.json"
    manifest_path = target / "provider_run_planning_manifest.json"
    report_path = target / "provider_run_planning_report.md"

    plan_path.write_text(
        json.dumps(plan.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    sampled_payload = {
        "schema_version": "v10_provider_sampled_case_ids_v1",
        "stage": plan.stage,
        "case_count": plan.case_count,
        "sampled_case_ids": plan.sampled_case_ids,
    }
    sampled_path.write_text(
        json.dumps(sampled_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(plan.to_markdown() + "\n", encoding="utf-8")
    manifest = _planning_manifest(
        plan=plan,
        config_path=Path(config_path),
        plan_path=plan_path,
        sampled_path=sampled_path,
        report_path=report_path,
        generated_at=generated_at,
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "plan": plan_path,
        "sampled_case_ids": sampled_path,
        "manifest": manifest_path,
        "report": report_path,
    }


def _sampling_summary(
    *,
    stage: Stage,
    cases: list[V10Case],
    deterministic_seed: int | None,
    expected_count: int,
) -> V10ProviderSamplingSummary:
    family_counts = Counter(case.family for case in cases)
    label_counts = Counter(case.label for case in cases)
    status: Literal["complete", "needs_work", "failed"] = (
        "complete" if len(cases) == expected_count else "failed"
    )
    return V10ProviderSamplingSummary(
        stage=stage,
        case_count=len(cases),
        family_counts=dict(sorted(family_counts.items())),
        label_counts=dict(sorted(label_counts.items())),
        sampled_case_ids=[case.case_id for case in cases],
        deterministic_seed=deterministic_seed,
        status=status,
    )


def _prompt_hashes(config: V10ProviderProtocolConfig) -> dict[str, str | None]:
    generic_path = Path(config.generic_prompt_path)
    contract_path = Path(config.contract_prompt_path)
    manifest_path = Path(config.prompt_rendering_manifest_path)
    if config.prompt_mode in {"generic", "split_view"} and not generic_path.exists():
        raise FileNotFoundError(
            f"Render v10 prompts before planning provider run. Missing: {generic_path}"
        )
    if config.prompt_mode in {"contract", "split_view"} and not contract_path.exists():
        raise FileNotFoundError(
            f"Render v10 prompts before planning provider run. Missing: {contract_path}"
        )
    return {
        "generic_prompt": hash_file(generic_path) if generic_path.exists() else None,
        "contract_prompt": hash_file(contract_path) if contract_path.exists() else None,
        "prompt_rendering_manifest": hash_file(manifest_path) if manifest_path.exists() else None,
    }


def _config_hashes(
    config: V10ProviderProtocolConfig,
    config_path: str | Path,
) -> dict[str, str]:
    return {
        "provider_protocol_config": hash_file(config_path),
        "cases": hash_file(config.cases_path),
        "normalization_config": hash_file(config.normalization_config_path),
        "benchmark_config": hash_file(config.benchmark_config_path),
        "diagnostics_config": hash_file(config.diagnostics_config_path),
        "reportability_config": hash_file(config.reportability_config_path),
    }


def _planning_manifest(
    *,
    plan: V10ProviderRunPlan,
    config_path: Path,
    plan_path: Path,
    sampled_path: Path,
    report_path: Path,
    generated_at: str | None,
) -> dict[str, Any]:
    payload = {
        "schema_version": "v10_provider_run_planning_manifest_v1",
        "provider_protocol_config_path": str(config_path),
        "provider_protocol_config_hash": hash_file(config_path),
        "provider_run_plan_path": str(plan_path),
        "provider_run_plan_hash": hash_file(plan_path),
        "sampled_case_ids_path": str(sampled_path),
        "sampled_case_ids_hash": hash_file(sampled_path),
        "provider_run_planning_report_path": str(report_path),
        "provider_run_planning_report_hash": hash_file(report_path),
        "plan_hash": plan.plan_hash,
        "prompt_hashes": plan.prompt_hashes,
        "config_hashes": plan.config_hashes,
        "no_api_calls_made": True,
        "generated_at": generated_at
        or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "limitations": [
            "Planning artifact only.",
            "No provider API calls were made.",
            "No provider judgments were collected.",
            "Level 5 is not allowed.",
        ],
    }
    return {**payload, "manifest_hash": stable_json_hash(payload)}
