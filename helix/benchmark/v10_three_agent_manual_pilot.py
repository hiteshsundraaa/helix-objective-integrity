from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime
import json
from pathlib import Path
from statistics import mean
from typing import Any, Literal

from pydantic import BaseModel, Field

from helix.benchmark.benchmark_receipts import hash_file, stable_json_hash
from helix.benchmark.v10_generator import V10Case
from helix.benchmark.v10_judgment_normalization import V10NormalizedJudgment
from helix.benchmark.v10_live_runner_design_gate import (
    V10LiveRunnerDesignConfig,
    load_v10_live_runner_design_config,
    validate_provider_model_allowed,
)
from helix.benchmark.v10_manual_pilot_runner import (
    RUN_ID_RE,
    V10ManualPilotInput,
    V10ManualPilotSummary,
    load_v10_manual_pilot_config,
    run_manual_pilot,
)
from helix.benchmark.v10_provider_raw_import import load_provider_run_plan
from helix.benchmark.v10_receipt_chain import V10ReceiptChainSummary, V10ReceiptRecord
from helix.benchmark.v10_three_agent_consistency_protocol import (
    DISAGREEMENT_TAXONOMY,
    V10ThreeAgentConsistencyProtocolConfig,
    classify_risk_band,
    is_severe_disagreement,
    load_v10_three_agent_consistency_protocol_config,
)


ExecutionMode = Literal["manual_import"]
SystemStatus = Literal["complete", "needs_work", "failed"]
RUN_ID_SAFE_RE = RUN_ID_RE
SECRET_TOKENS = {
    "api_key",
    "apikey",
    "secret",
    "bearer ",
    "authorization:",
    "password",
    "credential",
    "access_token",
    "refresh_token",
    "sk-",
}


class V10ThreeAgentManualPilotConfig(BaseModel):
    schema_version: str
    manual_three_agent_pilot: bool
    execution_mode: ExecutionMode
    minimum_independent_systems: int
    level_4_allowed: bool
    level_5_allowed: bool
    individual_run_evidence_cap: int
    consistency_evidence_cap: int
    three_agent_protocol_config_path: str
    manual_pilot_config_path: str
    evidence_assessment_config_path: str
    live_design_config_path: str
    default_plan_path: str
    provider_runs_root: str
    consistency_output_root: str
    required_system_fields: list[str]
    allowed_collection_methods: list[str]
    notes: str = ""


class V10ManualAgentSystemInput(BaseModel):
    role: str
    provider: str
    model: str
    raw_output_file: str
    collection_method: str
    run_id: str | None = None
    notes: str | None = None


class V10ThreeAgentManualPilotInput(BaseModel):
    consistency_run_id: str
    systems: list[V10ManualAgentSystemInput]
    plan_path: str
    output_root: str
    notes: str | None = None


class V10PerSystemPilotResult(BaseModel):
    role: str
    provider: str
    model: str
    run_id: str
    provider_run_dir: str
    import_validation_status: str
    bridge_status: str
    evidence_assessment_status: str
    final_evidence_level: int
    receipt_count: int
    invalid_receipt_count: int
    receipt_chain_complete: bool
    raw_output_hash: str | None
    blocking_issues: list[str] = Field(default_factory=list)
    non_blocking_warnings: list[str] = Field(default_factory=list)
    status: SystemStatus


class V10PerCaseConsistencyRecord(BaseModel):
    case_id: str
    systems_present: list[str]
    decisions_by_system: dict[str, str]
    scores_by_system: dict[str, float | None]
    risk_bands_by_system: dict[str, str]
    receipt_hashes_by_system: dict[str, str]
    receipt_validity_by_system: dict[str, bool]
    reason_codes_by_system: dict[str, list[str]]
    citation_methods_by_system: dict[str, str]
    unanimous_decision_agreement: bool
    majority_decision_agreement: bool
    max_score_distance: float
    mean_pairwise_score_distance: float
    risk_band_unanimous_agreement: bool
    risk_band_majority_agreement: bool
    all_receipts_valid: bool
    all_provider_outputs_parseable: bool
    severe_disagreement: bool
    disagreement_types: list[str]


class V10ThreeAgentConsistencySummary(BaseModel):
    schema_version: str = "v10_three_agent_manual_consistency_summary_v1"
    consistency_run_id: str
    system_count: int
    case_count: int
    execution_mode: ExecutionMode = "manual_import"
    individual_run_evidence_levels: dict[str, int]
    consistency_evidence_level: int
    level_4_allowed: bool = False
    level_5_allowed: bool = False
    unanimous_decision_rate: float
    majority_decision_rate: float
    mean_pairwise_score_distance: float
    p95_pairwise_score_distance: float
    risk_band_unanimous_rate: float
    risk_band_majority_rate: float
    all_receipts_valid_rate: float
    parse_success_rate_by_system: dict[str, float]
    evidence_level_by_system: dict[str, int]
    disagreement_rate_by_family: dict[str, float]
    disagreement_rate_by_label: dict[str, float]
    severe_disagreement_rate: float
    thresholds_passed: bool
    blocking_issues: list[str] = Field(default_factory=list)
    non_blocking_warnings: list[str] = Field(default_factory=list)
    consistency_hash: str
    status: SystemStatus


class V10ThreeAgentConsistencyReceipt(BaseModel):
    receipt_id: str
    receipt_type: Literal["three_agent_manual_consistency_pilot"] = (
        "three_agent_manual_consistency_pilot"
    )
    version: str = "v10.17"
    consistency_run_id: str
    execution_mode: ExecutionMode = "manual_import"
    system_count: int
    case_count: int
    majority_vote_truth_claim_allowed: bool = False
    provider_outputs_combined_for_truth: bool = False
    consistency_not_correctness: bool = True
    individual_run_evidence_levels: dict[str, int]
    consistency_evidence_level: int
    level_4_allowed: bool = False
    level_5_allowed: bool = False
    unanimous_decision_rate: float
    majority_decision_rate: float
    severe_disagreement_rate: float
    all_receipts_valid_rate: float
    constraints_enforced: list[str]
    consistency_hash: str


class _SystemArtifacts(BaseModel):
    result: V10PerSystemPilotResult
    judgments_by_case_id: dict[str, dict[str, Any]]
    receipts_by_case_id: dict[str, dict[str, Any]]
    receipt_chain_summary: dict[str, Any] | None = None
    manifest_hash: str | None = None
    receipt_chain_hash: str | None = None


def load_v10_three_agent_manual_pilot_config(
    path: str | Path,
) -> V10ThreeAgentManualPilotConfig:
    return V10ThreeAgentManualPilotConfig.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def validate_three_agent_manual_pilot_input(
    pilot_input: V10ThreeAgentManualPilotInput,
    config: V10ThreeAgentManualPilotConfig,
    protocol_config: V10ThreeAgentConsistencyProtocolConfig,
    live_design_config: V10LiveRunnerDesignConfig,
) -> list[str]:
    issues: list[str] = []
    if not config.manual_three_agent_pilot:
        issues.append("manual_three_agent_pilot_not_enabled")
    if config.execution_mode != "manual_import":
        issues.append("three_agent_execution_mode_not_manual_import")
    if config.minimum_independent_systems < 3:
        issues.append("minimum_independent_systems_below_three")
    if config.level_4_allowed:
        issues.append("manual_three_agent_level_4_allowed")
    if config.level_5_allowed:
        issues.append("manual_three_agent_level_5_allowed")
    if config.consistency_evidence_cap > 3:
        issues.append("consistency_evidence_cap_above_3")
    if protocol_config.majority_vote_truth_claim_allowed:
        issues.append("protocol_majority_vote_truth_claim_allowed")
    if not protocol_config.consistency_not_correctness:
        issues.append("protocol_consistency_not_correctness_false")
    if not _run_id_is_safe(pilot_input.consistency_run_id):
        issues.append("invalid_consistency_run_id")
    if not Path(pilot_input.plan_path).is_file():
        issues.append("missing_plan_path")
    if len(pilot_input.systems) < config.minimum_independent_systems:
        issues.append("fewer_than_three_systems")

    roles = [system.role for system in pilot_input.systems]
    if len(roles) != len(set(roles)):
        issues.append("duplicate_role")
    provider_models = [(system.provider, system.model) for system in pilot_input.systems]
    if len(provider_models) != len(set(provider_models)):
        issues.append("duplicate_provider_model")
    raw_paths = [str(Path(system.raw_output_file).resolve()) for system in pilot_input.systems]
    if len(raw_paths) != len(set(raw_paths)):
        issues.append("duplicate_raw_output_file")

    for system in pilot_input.systems:
        missing = [
            field
            for field in config.required_system_fields
            if getattr(system, field, None) in (None, "")
        ]
        issues.extend(f"missing_system_field:{system.role}:{field}" for field in missing)
        provider_check = validate_provider_model_allowed(
            live_design_config,
            system.provider,
            system.model,
        )
        if not provider_check.valid:
            issues.append(f"provider_model_not_allowed:{system.role}")
            issues.extend(
                f"provider_model:{system.role}:{issue}"
                for issue in provider_check.issues
            )
        if system.collection_method not in set(config.allowed_collection_methods):
            issues.append(f"invalid_collection_method:{system.role}")
        raw_path = Path(system.raw_output_file)
        if not raw_path.is_file():
            issues.append(f"missing_raw_output_file:{system.role}")
        if system.run_id is not None and not _run_id_is_safe(system.run_id):
            issues.append(f"invalid_run_id:{system.role}")
        issues.extend(_secret_like_system_input_issues(system))

    return sorted(set(issues))


def run_per_system_manual_pilots(
    pilot_input: V10ThreeAgentManualPilotInput,
    config: V10ThreeAgentManualPilotConfig,
    *,
    generated_at: str | None = None,
) -> list[V10PerSystemPilotResult]:
    manual_config = load_v10_manual_pilot_config(config.manual_pilot_config_path)
    results: list[V10PerSystemPilotResult] = []
    provider_root = Path(config.provider_runs_root) / f"{pilot_input.consistency_run_id}__"
    for system in pilot_input.systems:
        run_id = _system_run_id(pilot_input.consistency_run_id, system)
        manual_input = V10ManualPilotInput(
            provider=system.provider,
            model=system.model,
            run_id=run_id,
            raw_output_file=system.raw_output_file,
            collection_method=system.collection_method,
            plan_path=pilot_input.plan_path,
            output_root=str(provider_root),
            notes=system.notes,
        )
        try:
            summary, paths = run_manual_pilot(
                manual_input,
                manual_config.model_copy(
                    update={
                        "provider_runs_root": str(provider_root),
                        "provider_imports_root": str(
                            provider_root / "_staged_provider_imports"
                        ),
                    }
                ),
                generated_at=generated_at,
            )
            provider_run_dir = str(paths["output_provider_run_dir"])
            results.append(_result_from_manual_summary(system, summary, provider_run_dir))
        except Exception as exc:  # failed providers must remain reportable
            results.append(
                V10PerSystemPilotResult(
                    role=system.role,
                    provider=system.provider,
                    model=system.model,
                    run_id=run_id,
                    provider_run_dir=str(provider_root / run_id),
                    import_validation_status="failed",
                    bridge_status="not_run",
                    evidence_assessment_status="not_run",
                    final_evidence_level=0,
                    receipt_count=0,
                    invalid_receipt_count=0,
                    receipt_chain_complete=False,
                    raw_output_hash=hash_file(system.raw_output_file)
                    if Path(system.raw_output_file).is_file()
                    else None,
                    blocking_issues=[f"per_system_manual_pilot_failed:{type(exc).__name__}"],
                    non_blocking_warnings=[str(exc)],
                    status="failed",
                )
            )
    return results


def load_per_system_receipts_and_judgments(
    per_system_results: list[V10PerSystemPilotResult],
) -> dict[str, _SystemArtifacts]:
    artifacts: dict[str, _SystemArtifacts] = {}
    for result in per_system_results:
        run_dir = Path(result.provider_run_dir)
        judgments = _load_normalized_judgments(run_dir)
        receipts = _load_receipts(run_dir)
        receipt_summary = _load_json_optional(
            run_dir / "pilot_evidence" / "receipt_chain_summary.json"
        )
        manifest = _load_json_optional(run_dir / "manual_pilot_manifest.json")
        artifacts[result.role] = _SystemArtifacts(
            result=result,
            judgments_by_case_id={row["case_id"]: row for row in judgments if row.get("case_id")},
            receipts_by_case_id={row["case_id"]: row for row in receipts if row.get("case_id")},
            receipt_chain_summary=receipt_summary,
            manifest_hash=manifest.get("manifest_hash") if manifest else None,
            receipt_chain_hash=receipt_summary.get("chain_hash") if receipt_summary else None,
        )
    return artifacts


def compute_per_case_consistency(
    artifacts_by_system: dict[str, _SystemArtifacts],
    cases: list[V10Case],
    protocol_config: V10ThreeAgentConsistencyProtocolConfig,
) -> list[V10PerCaseConsistencyRecord]:
    records: list[V10PerCaseConsistencyRecord] = []
    for case in cases:
        systems_present: list[str] = []
        decisions: dict[str, str] = {}
        scores: dict[str, float | None] = {}
        risk_bands: dict[str, str] = {}
        receipt_hashes: dict[str, str] = {}
        receipt_validity: dict[str, bool] = {}
        reason_codes: dict[str, list[str]] = {}
        citation_methods: dict[str, str] = {}
        pair_items: list[dict[str, Any]] = []
        for role, artifacts in artifacts_by_system.items():
            judgment = artifacts.judgments_by_case_id.get(case.case_id)
            receipt = artifacts.receipts_by_case_id.get(case.case_id)
            if judgment is None and receipt is None:
                continue
            systems_present.append(role)
            decision = str((judgment or receipt or {}).get("decision") or "")
            score = _score_or_none((judgment or receipt or {}).get("violation_probability"))
            method = str((judgment or {}).get("citation_verification_method") or "")
            decisions[role] = decision
            scores[role] = score
            risk_bands[role] = classify_risk_band(score, protocol_config)
            receipt_hashes[role] = str((receipt or {}).get("receipt_hash") or "")
            receipt_validity[role] = bool((receipt or {}).get("valid", False))
            reason_codes[role] = [
                str(item) for item in (judgment or {}).get("reason_codes", []) or []
            ]
            citation_methods[role] = method
            pair_items.append(
                {
                    "decision": decision,
                    "violation_probability": score,
                    "citation_verification_method": method,
                    "cited_contract_phrase": (judgment or {}).get("cited_contract_phrase"),
                    "parse_success": judgment is not None
                    and judgment.get("normalization_status") == "valid",
                }
            )

        score_distances = _pairwise_distances(
            [score for score in scores.values() if score is not None]
        )
        disagreement_types = _disagreement_types(
            decisions=decisions,
            scores=scores,
            risk_bands=risk_bands,
            citation_methods=citation_methods,
            reason_codes=reason_codes,
            receipt_validity=receipt_validity,
            expected_system_count=len(artifacts_by_system),
        )
        severe = any(
            is_severe_disagreement(left, right, protocol_config)
            for left, right in _pairs(pair_items)
        ) or "parsing_or_schema_failure" in disagreement_types
        records.append(
            V10PerCaseConsistencyRecord(
                case_id=case.case_id,
                systems_present=sorted(systems_present),
                decisions_by_system=decisions,
                scores_by_system=scores,
                risk_bands_by_system=risk_bands,
                receipt_hashes_by_system=receipt_hashes,
                receipt_validity_by_system=receipt_validity,
                reason_codes_by_system=reason_codes,
                citation_methods_by_system=citation_methods,
                unanimous_decision_agreement=_all_same(list(decisions.values()), min_count=3),
                majority_decision_agreement=_has_majority(list(decisions.values())),
                max_score_distance=max(score_distances) if score_distances else 0.0,
                mean_pairwise_score_distance=mean(score_distances) if score_distances else 0.0,
                risk_band_unanimous_agreement=_all_same(
                    list(risk_bands.values()),
                    min_count=3,
                ),
                risk_band_majority_agreement=_has_majority(list(risk_bands.values())),
                all_receipts_valid=bool(receipt_validity)
                and len(receipt_validity) == len(artifacts_by_system)
                and all(receipt_validity.values()),
                all_provider_outputs_parseable=len(systems_present) == len(artifacts_by_system),
                severe_disagreement=severe,
                disagreement_types=disagreement_types,
            )
        )
    return records


def compute_aggregate_consistency(
    per_case_records: list[V10PerCaseConsistencyRecord],
    per_system_results: list[V10PerSystemPilotResult],
    protocol_config: V10ThreeAgentConsistencyProtocolConfig,
    config: V10ThreeAgentManualPilotConfig,
    cases: list[V10Case],
    *,
    consistency_run_id: str,
) -> V10ThreeAgentConsistencySummary:
    count = len(per_case_records)
    distances = [record.mean_pairwise_score_distance for record in per_case_records]
    case_by_id = {case.case_id: case for case in cases}
    blocking: list[str] = []
    warnings: list[str] = []
    if len(per_system_results) < config.minimum_independent_systems:
        blocking.append("fewer_than_three_system_results")
    if any(result.status == "failed" for result in per_system_results):
        blocking.append("one_or_more_provider_runs_failed")
    if any(not result.receipt_chain_complete for result in per_system_results):
        warnings.append("one_or_more_receipt_chains_incomplete")

    parse_rates = {
        result.role: (1.0 if result.receipt_count == count and result.status != "failed" else 0.0)
        for result in per_system_results
    }
    evidence_levels = {
        result.role: min(result.final_evidence_level, config.individual_run_evidence_cap)
        for result in per_system_results
    }
    summary_without_hash = {
        "schema_version": "v10_three_agent_manual_consistency_summary_v1",
        "consistency_run_id": consistency_run_id,
        "system_count": len(per_system_results),
        "case_count": count,
        "execution_mode": "manual_import",
        "individual_run_evidence_levels": evidence_levels,
        "consistency_evidence_level": 0,
        "level_4_allowed": False,
        "level_5_allowed": False,
        "unanimous_decision_rate": _rate(
            record.unanimous_decision_agreement for record in per_case_records
        ),
        "majority_decision_rate": _rate(
            record.majority_decision_agreement for record in per_case_records
        ),
        "mean_pairwise_score_distance": mean(distances) if distances else 0.0,
        "p95_pairwise_score_distance": _p95(
            [record.max_score_distance for record in per_case_records]
        ),
        "risk_band_unanimous_rate": _rate(
            record.risk_band_unanimous_agreement for record in per_case_records
        ),
        "risk_band_majority_rate": _rate(
            record.risk_band_majority_agreement for record in per_case_records
        ),
        "all_receipts_valid_rate": _rate(
            record.all_receipts_valid for record in per_case_records
        ),
        "parse_success_rate_by_system": parse_rates,
        "evidence_level_by_system": evidence_levels,
        "disagreement_rate_by_family": _grouped_disagreement_rates(
            per_case_records,
            case_by_id,
            "family",
        ),
        "disagreement_rate_by_label": _grouped_disagreement_rates(
            per_case_records,
            case_by_id,
            "label",
        ),
        "severe_disagreement_rate": _rate(
            record.severe_disagreement for record in per_case_records
        ),
        "thresholds_passed": False,
        "blocking_issues": blocking,
        "non_blocking_warnings": warnings,
        "status": "complete",
    }
    thresholds_passed = _thresholds_passed(summary_without_hash, protocol_config)
    level = assign_consistency_evidence_level(
        summary_without_hash,
        per_system_results,
        protocol_config,
        config,
    )
    if level == 0:
        status: SystemStatus = "failed" if blocking else "needs_work"
    elif blocking or not thresholds_passed:
        status = "needs_work"
    else:
        status = "complete"
    final_payload = {
        **summary_without_hash,
        "thresholds_passed": thresholds_passed,
        "consistency_evidence_level": level,
        "status": status,
    }
    return V10ThreeAgentConsistencySummary(
        **final_payload,
        consistency_hash=stable_json_hash(final_payload),
    )


def assign_consistency_evidence_level(
    summary_payload: dict[str, Any],
    per_system_results: list[V10PerSystemPilotResult],
    protocol_config: V10ThreeAgentConsistencyProtocolConfig,
    config: V10ThreeAgentManualPilotConfig,
) -> int:
    if len(per_system_results) < config.minimum_independent_systems:
        return 0
    valid_runs = [result for result in per_system_results if result.status != "failed"]
    if len(valid_runs) < config.minimum_independent_systems:
        return min(1, config.consistency_evidence_cap)
    min_provider_level = min(result.final_evidence_level for result in valid_runs)
    level = 1
    if all(result.receipt_count > 0 for result in valid_runs):
        level = 2
    if all(result.receipt_chain_complete for result in valid_runs) and all(
        result.bridge_status in {"complete", "needs_work"} for result in valid_runs
    ):
        level = 3
    return min(level, min_provider_level, config.consistency_evidence_cap, 3)


def write_three_agent_manual_pilot_outputs(
    *,
    pilot_input: V10ThreeAgentManualPilotInput,
    config: V10ThreeAgentManualPilotConfig,
    protocol_config: V10ThreeAgentConsistencyProtocolConfig,
    per_system_results: list[V10PerSystemPilotResult],
    artifacts_by_system: dict[str, _SystemArtifacts],
    per_case_records: list[V10PerCaseConsistencyRecord],
    summary: V10ThreeAgentConsistencySummary,
    cases: list[V10Case],
    generated_at: str | None = None,
) -> dict[str, Path]:
    out_dir = Path(pilot_input.output_root) / pilot_input.consistency_run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    consistency_config_path = out_dir / "consistency_config.json"
    system_registry_path = out_dir / "system_registry.json"
    input_case_manifest_path = out_dir / "input_case_set_manifest.json"
    per_system_results_path = out_dir / "per_system_results.json"
    per_system_manifest_hashes_path = out_dir / "per_system_manifest_hashes.json"
    per_system_receipt_chain_hashes_path = out_dir / "per_system_receipt_chain_hashes.json"
    per_case_path = out_dir / "per_case_consistency.jsonl"
    summary_path = out_dir / "consistency_summary.json"
    taxonomy_path = out_dir / "disagreement_taxonomy.json"
    receipt_path = out_dir / "consistency_receipt.json"
    report_path = out_dir / "consistency_report.md"

    generated = generated_at or _utc_now()
    consistency_config_path.write_text(
        json.dumps(
            {
                "schema_version": "v10_three_agent_manual_consistency_config_v1",
                "generated_at": generated,
                "manual_three_agent_config": config.model_dump(mode="json"),
                "protocol_config": protocol_config.model_dump(mode="json"),
                "input": pilot_input.model_dump(mode="json"),
                "no_live_api_calls_made_by_helix": True,
                "provider_sdks_used": False,
                "secrets_included": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    system_registry_path.write_text(
        json.dumps(
            {
                "schema_version": "v10_three_agent_system_registry_v1",
                "systems": [result.model_dump(mode="json") for result in per_system_results],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    input_case_manifest = {
        "schema_version": "v10_three_agent_input_case_set_manifest_v1",
        "plan_path": pilot_input.plan_path,
        "case_count": len(cases),
        "case_ids": [case.case_id for case in cases],
        "case_set_hash": stable_json_hash([case.case_id for case in cases]),
        "same_case_set_required": True,
    }
    input_case_manifest_path.write_text(
        json.dumps(input_case_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    per_system_results_path.write_text(
        json.dumps(
            [result.model_dump(mode="json") for result in per_system_results],
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    per_system_manifest_hashes_path.write_text(
        json.dumps(
            {
                role: artifacts.manifest_hash
                for role, artifacts in sorted(artifacts_by_system.items())
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    per_system_receipt_chain_hashes_path.write_text(
        json.dumps(
            {
                role: artifacts.receipt_chain_hash
                for role, artifacts in sorted(artifacts_by_system.items())
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    per_case_path.write_text(
        "\n".join(
            json.dumps(record.model_dump(mode="json"), sort_keys=True)
            for record in per_case_records
        )
        + ("\n" if per_case_records else ""),
        encoding="utf-8",
    )
    summary_path.write_text(
        json.dumps(summary.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    taxonomy_path.write_text(
        json.dumps(
            {
                "schema_version": "v10_three_agent_disagreement_taxonomy_v1",
                "taxonomy": DISAGREEMENT_TAXONOMY,
                "observed_counts": dict(
                    Counter(
                        item
                        for record in per_case_records
                        for item in record.disagreement_types
                    )
                ),
                "descriptive_not_blame_assignment": True,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    receipt = build_consistency_receipt(summary)
    receipt_path.write_text(
        json.dumps(receipt.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(
        _consistency_report(
            summary=summary,
            per_system_results=per_system_results,
            per_case_records=per_case_records,
            receipt=receipt,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "consistency_config": consistency_config_path,
        "system_registry": system_registry_path,
        "input_case_set_manifest": input_case_manifest_path,
        "per_system_results": per_system_results_path,
        "per_system_manifest_hashes": per_system_manifest_hashes_path,
        "per_system_receipt_chain_hashes": per_system_receipt_chain_hashes_path,
        "per_case_consistency": per_case_path,
        "consistency_summary": summary_path,
        "disagreement_taxonomy": taxonomy_path,
        "consistency_receipt": receipt_path,
        "consistency_report": report_path,
    }


def run_three_agent_manual_pilot(
    pilot_input: V10ThreeAgentManualPilotInput,
    config: V10ThreeAgentManualPilotConfig,
    *,
    generated_at: str | None = None,
) -> tuple[V10ThreeAgentConsistencySummary, dict[str, Path]]:
    protocol_config = load_v10_three_agent_consistency_protocol_config(
        config.three_agent_protocol_config_path
    )
    live_design_config = load_v10_live_runner_design_config(config.live_design_config_path)
    issues = validate_three_agent_manual_pilot_input(
        pilot_input,
        config,
        protocol_config,
        live_design_config,
    )
    if issues:
        raise ValueError(
            "Three-agent manual pilot input validation failed: " + ", ".join(issues)
        )
    plan = load_provider_run_plan(pilot_input.plan_path)
    cases = _load_cases_for_plan(plan)
    per_system_results = run_per_system_manual_pilots(
        pilot_input,
        config,
        generated_at=generated_at,
    )
    artifacts = load_per_system_receipts_and_judgments(per_system_results)
    per_case_records = compute_per_case_consistency(artifacts, cases, protocol_config)
    summary = compute_aggregate_consistency(
        per_case_records,
        per_system_results,
        protocol_config,
        config,
        cases,
        consistency_run_id=pilot_input.consistency_run_id,
    )
    paths = write_three_agent_manual_pilot_outputs(
        pilot_input=pilot_input,
        config=config,
        protocol_config=protocol_config,
        per_system_results=per_system_results,
        artifacts_by_system=artifacts,
        per_case_records=per_case_records,
        summary=summary,
        cases=cases,
        generated_at=generated_at,
    )
    return summary, paths


def build_consistency_receipt(
    summary: V10ThreeAgentConsistencySummary,
) -> V10ThreeAgentConsistencyReceipt:
    return V10ThreeAgentConsistencyReceipt(
        receipt_id=f"v10.17:{summary.consistency_run_id}:three_agent_manual_consistency",
        consistency_run_id=summary.consistency_run_id,
        system_count=summary.system_count,
        case_count=summary.case_count,
        individual_run_evidence_levels=summary.individual_run_evidence_levels,
        consistency_evidence_level=summary.consistency_evidence_level,
        unanimous_decision_rate=summary.unanimous_decision_rate,
        majority_decision_rate=summary.majority_decision_rate,
        severe_disagreement_rate=summary.severe_disagreement_rate,
        all_receipts_valid_rate=summary.all_receipts_valid_rate,
        constraints_enforced=[
            "three_independent_systems_minimum",
            "same_case_set_required",
            "separate_raw_outputs_required",
            "separate_receipt_chains_required",
            "no_majority_vote_truth_claim",
            "failed_provider_not_silently_dropped",
            "disagreement_taxonomy_required",
            "per_provider_metrics_before_aggregate",
            "manual_consistency_level_cap_3",
            "level_5_reserved",
        ],
        consistency_hash=summary.consistency_hash,
    )


def _result_from_manual_summary(
    system: V10ManualAgentSystemInput,
    summary: V10ManualPilotSummary,
    provider_run_dir: str,
) -> V10PerSystemPilotResult:
    return V10PerSystemPilotResult(
        role=system.role,
        provider=system.provider,
        model=system.model,
        run_id=summary.run_id,
        provider_run_dir=provider_run_dir,
        import_validation_status=summary.import_validation_status,
        bridge_status=summary.bridge_status,
        evidence_assessment_status=summary.evidence_assessment_status,
        final_evidence_level=min(summary.final_evidence_level, 3),
        receipt_count=summary.receipt_count,
        invalid_receipt_count=summary.invalid_receipt_count,
        receipt_chain_complete=summary.receipt_chain_complete,
        raw_output_hash=summary.raw_output_hash,
        blocking_issues=summary.blocking_issues,
        non_blocking_warnings=summary.non_blocking_warnings,
        status=summary.status,
    )


def _system_run_id(consistency_run_id: str, system: V10ManualAgentSystemInput) -> str:
    return system.run_id or f"{consistency_run_id}__{system.role}"


def _run_id_is_safe(run_id: str) -> bool:
    return bool(
        run_id
        and "/" not in run_id
        and "\\" not in run_id
        and ".." not in run_id
        and RUN_ID_SAFE_RE.fullmatch(run_id)
    )


def _secret_like_system_input_issues(system: V10ManualAgentSystemInput) -> list[str]:
    issues: list[str] = []
    for field, value in system.model_dump(mode="json").items():
        if isinstance(value, str) and any(token in value.lower() for token in SECRET_TOKENS):
            issues.append(f"secret_like_system_field:{system.role}:{field}")
    return issues


def _load_cases_for_plan(plan: Any) -> list[V10Case]:
    cases_by_id = {
        case.case_id: case
        for case in [
            V10Case.model_validate_json(line)
            for line in Path("benchmarks/v10_calibrated/v10_cases.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
    }
    return [cases_by_id[case_id] for case_id in plan.sampled_case_ids if case_id in cases_by_id]


def _load_normalized_judgments(run_dir: Path) -> list[dict[str, Any]]:
    for path in [
        run_dir / "imported_pipeline_bridge" / "normalized_judgments" / "v10_normalized_judgments.jsonl",
        run_dir / "normalized_judgments" / "v10_normalized_judgments.jsonl",
    ]:
        if path.exists():
            return [
                V10NormalizedJudgment.model_validate_json(line).model_dump(mode="json")
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
    return []


def _load_receipts(run_dir: Path) -> list[dict[str, Any]]:
    path = run_dir / "pilot_evidence" / "receipt_chain_records.jsonl"
    if not path.exists():
        return []
    return [
        V10ReceiptRecord.model_validate_json(line).model_dump(mode="json")
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _load_json_optional(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def _score_or_none(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pairwise_distances(scores: list[float]) -> list[float]:
    return [abs(left - right) for left, right in _pairs(scores)]


def _pairs(items: list[Any]) -> list[tuple[Any, Any]]:
    pairs: list[tuple[Any, Any]] = []
    for index, left in enumerate(items):
        for right in items[index + 1:]:
            pairs.append((left, right))
    return pairs


def _all_same(values: list[str], *, min_count: int) -> bool:
    return len(values) >= min_count and len(set(values)) == 1


def _has_majority(values: list[str]) -> bool:
    counts = Counter(value for value in values if value)
    return bool(counts and counts.most_common(1)[0][1] >= 2)


def _disagreement_types(
    *,
    decisions: dict[str, str],
    scores: dict[str, float | None],
    risk_bands: dict[str, str],
    citation_methods: dict[str, str],
    reason_codes: dict[str, list[str]],
    receipt_validity: dict[str, bool],
    expected_system_count: int,
) -> list[str]:
    types: set[str] = set()
    if len(decisions) < expected_system_count:
        types.add("parsing_or_schema_failure")
    if len(set(decisions.values())) > 1:
        if {"ALLOW", "BLOCK"} <= set(decisions.values()) or {"ALLOW", "QUARANTINE"} <= set(decisions.values()):
            types.add("decision_boundary_disagreement")
        else:
            types.add("objective_interpretation_disagreement")
    numeric_scores = [score for score in scores.values() if score is not None]
    if _pairwise_distances(numeric_scores) and max(_pairwise_distances(numeric_scores)) >= 0.25:
        types.add("score_calibration_disagreement")
    if len(set(risk_bands.values())) > 1:
        types.add("score_calibration_disagreement")
    if len(set(citation_methods.values())) > 1:
        types.add("citation_grounding_disagreement")
    reason_sets = {tuple(sorted(value)) for value in reason_codes.values()}
    if len(reason_sets) > 1:
        types.add("contract_phrase_selection_disagreement")
    if receipt_validity and not all(receipt_validity.values()):
        types.add("receipt_chain_failure")
    return sorted(types) or ["unknown"]


def _rate(values: Any) -> float:
    items = list(values)
    if not items:
        return 0.0
    return sum(bool(item) for item in items) / len(items)


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(0.95 * (len(ordered) - 1)))
    return ordered[index]


def _grouped_disagreement_rates(
    records: list[V10PerCaseConsistencyRecord],
    case_by_id: dict[str, V10Case],
    field: str,
) -> dict[str, float]:
    grouped: dict[str, list[bool]] = defaultdict(list)
    for record in records:
        case = case_by_id.get(record.case_id)
        key = str(getattr(case, field, "unknown") if case else "unknown")
        grouped[key].append(not record.unanimous_decision_agreement)
    return {key: _rate(values) for key, values in sorted(grouped.items())}


def _thresholds_passed(
    summary: dict[str, Any],
    protocol_config: V10ThreeAgentConsistencyProtocolConfig,
) -> bool:
    thresholds = protocol_config.pilot_thresholds
    parse_rates = summary.get("parse_success_rate_by_system") or {}
    return (
        parse_rates
        and all(rate >= thresholds.parse_success_rate_by_system_min for rate in parse_rates.values())
        and summary["all_receipts_valid_rate"] >= thresholds.all_receipts_valid_rate_min
        and summary["majority_decision_rate"] >= thresholds.majority_decision_rate_min
        and summary["severe_disagreement_rate"] <= thresholds.severe_disagreement_rate_max
        and summary["p95_pairwise_score_distance"] <= thresholds.p95_pairwise_score_distance_max
    )


def _consistency_report(
    *,
    summary: V10ThreeAgentConsistencySummary,
    per_system_results: list[V10PerSystemPilotResult],
    per_case_records: list[V10PerCaseConsistencyRecord],
    receipt: V10ThreeAgentConsistencyReceipt,
) -> str:
    severe = [record for record in per_case_records if record.severe_disagreement]
    lines = [
        "# HELIX v10.17 Three-Agent Manual Consistency Pilot Report",
        "",
        "## Executive Summary",
        "",
        f"- consistency_run_id: `{summary.consistency_run_id}`",
        f"- system_count: `{summary.system_count}`",
        f"- case_count: `{summary.case_count}`",
        f"- consistency_evidence_level: `{summary.consistency_evidence_level}`",
        f"- majority_decision_rate: `{summary.majority_decision_rate:.6f}`",
        f"- severe_disagreement_rate: `{summary.severe_disagreement_rate:.6f}`",
        "",
        "This is the first empirical cross-system HELIX receipt check if real outputs are provided. No live API calls were made by HELIX; outputs were manually collected.",
        "",
        "## Execution Mode",
        "",
        "- execution_mode: `manual_import`",
        "- no live API calls were made by HELIX",
        "- provider SDKs were not used",
        "- outputs were manually collected",
        "",
        "## Systems Compared",
        "",
    ]
    lines.extend(
        f"- `{result.role}`: `{result.provider}` / `{result.model}` status `{result.status}` level `{result.final_evidence_level}`"
        for result in per_system_results
    )
    lines.extend(
        [
            "",
            "## Fixed Inputs",
            "",
            "- same case set required",
            "- same contract and schema required",
            "- same provider run plan required",
            "",
            "## Separate Provenance",
            "",
            "- separate raw outputs required",
            "- separate parsed judgments required",
            "- separate receipt chains required",
            "- one provider failure is not silently dropped",
            "",
            "## Per-System Evidence",
            "",
        ]
    )
    lines.extend(
        f"- `{result.role}` receipts `{result.receipt_count}` invalid `{result.invalid_receipt_count}` chain_complete `{str(result.receipt_chain_complete).lower()}` blocking `{result.blocking_issues}`"
        for result in per_system_results
    )
    lines.extend(
        [
            "",
            "## Per-Case Consistency",
            "",
            f"- per_case_record_count: `{len(per_case_records)}`",
            "",
            "## Aggregate Consistency Metrics",
            "",
            f"- unanimous_decision_rate: `{summary.unanimous_decision_rate:.6f}`",
            f"- majority_decision_rate: `{summary.majority_decision_rate:.6f}`",
            f"- mean_pairwise_score_distance: `{summary.mean_pairwise_score_distance:.6f}`",
            f"- p95_pairwise_score_distance: `{summary.p95_pairwise_score_distance:.6f}`",
            f"- risk_band_unanimous_rate: `{summary.risk_band_unanimous_rate:.6f}`",
            f"- risk_band_majority_rate: `{summary.risk_band_majority_rate:.6f}`",
            f"- all_receipts_valid_rate: `{summary.all_receipts_valid_rate:.6f}`",
            "",
            "## Disagreement Taxonomy",
            "",
        ]
    )
    observed = Counter(
        item for record in per_case_records for item in record.disagreement_types
    )
    lines.extend(f"- `{key}`: `{value}`" for key, value in sorted(observed.items()))
    lines.extend(
        [
            "",
            "## Severe Disagreements",
            "",
        ]
    )
    if severe:
        lines.extend(f"- `{record.case_id}`: `{record.disagreement_types}`" for record in severe[:20])
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Vendor-Bias Controls",
            "",
            "- at least three independent systems required",
            "- per-provider metrics reported before aggregate metrics",
            "- no majority vote used to relabel truth",
            "- failed providers included in reports",
            "",
            "## Consistency Evidence Level",
            "",
            f"- consistency_evidence_level: `{summary.consistency_evidence_level}`",
            "- manual consistency evidence capped at Level 3",
            "- Level 4 requires locked live runs",
            "- Level 5 false",
            "",
            "## What This Supports",
            "",
            "- HELIX can compare authorization receipts from independently collected provider outputs on the same case set.",
            "- HELIX can preserve disagreements and emit a consistency receipt without treating agreement as truth.",
            "",
            "## What This Does Not Prove",
            "",
            "- Consistency is not correctness.",
            "- Majority vote is not truth.",
            "- This does not prove provider correctness.",
            "- This does not prove Level 4 or Level 5 evidence.",
            "- This does not prove production readiness.",
            "",
            "## Limitations",
            "",
            "- Manual collection is not locked live-runner provenance.",
            "- Provider outputs are not repaired to improve consistency.",
            "- Agreement can reflect shared priors or shared benchmark exposure.",
            "",
            "## Next Steps",
            "",
            "- v10.18 should run real three-system provider outputs under the registered protocol.",
            "- Future Level 4 requires locked live runs.",
            "",
            "## Consistency Receipt",
            "",
            "```json",
            json.dumps(receipt.model_dump(mode="json"), indent=2, sort_keys=True),
            "```",
        ]
    )
    return "\n".join(lines)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
