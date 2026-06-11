from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, Literal, Mapping

from pydantic import BaseModel, Field

from helix.benchmark.benchmark_receipts import stable_json_hash
from helix.benchmark.v10_live_runner_design_gate import (
    V10LiveRunnerDesignConfig,
    load_v10_live_runner_design_config,
    validate_provider_model_allowed,
)


THREE_AGENT_PROTOCOL_CONSTRAINTS = [
    "three_independent_systems_minimum",
    "same_case_set_required",
    "same_contract_required",
    "separate_raw_outputs_required",
    "separate_receipt_chains_required",
    "no_majority_vote_truth_claim",
    "failed_provider_not_silently_dropped",
    "disagreement_taxonomy_required",
    "per_provider_metrics_before_aggregate",
    "consistency_level_cannot_exceed_min_provider_level_without_protocol",
    "level_5_reserved",
    "vendor_bias_warning_required",
]

DISAGREEMENT_TAXONOMY = [
    "decision_boundary_disagreement",
    "score_calibration_disagreement",
    "citation_grounding_disagreement",
    "parsing_or_schema_failure",
    "refusal_or_safety_behavior",
    "provider_policy_interference",
    "objective_interpretation_disagreement",
    "contract_phrase_selection_disagreement",
    "receipt_chain_failure",
    "unknown",
]


class V10ThreeAgentSystemSpec(BaseModel):
    role: str
    provider: str
    model: str
    execution_mode: Literal["manual_import", "live"] | None = None
    provider_run_dir: str | None = None


class V10SevereDisagreementPolicy(BaseModel):
    allow_vs_block_or_quarantine: bool
    score_distance_threshold: float
    high_risk_citation_mismatch: bool
    parse_failure_against_valid_outputs: bool


class V10ConsistencyThresholds(BaseModel):
    case_count: int
    parse_success_rate_by_system_min: float
    all_receipts_valid_rate_min: float
    majority_decision_rate_min: float
    severe_disagreement_rate_max: float
    p95_pairwise_score_distance_max: float


class V10ThreeAgentConsistencyProtocolConfig(BaseModel):
    schema_version: str
    protocol_only: bool
    minimum_independent_systems: int
    majority_vote_truth_claim_allowed: bool
    provider_outputs_combined_for_truth: bool
    consistency_not_correctness: bool
    same_case_set_required: bool
    same_contract_required: bool
    same_output_schema_required: bool
    separate_raw_outputs_required: bool
    separate_receipt_chains_required: bool
    failed_provider_not_silently_dropped: bool
    allowed_execution_modes_for_future_run: list[Literal["manual_import", "live"]]
    recommended_initial_systems: list[V10ThreeAgentSystemSpec]
    decision_order: list[str]
    risk_bands: dict[str, tuple[float, float]]
    severe_disagreement_policy: V10SevereDisagreementPolicy
    pilot_thresholds: V10ConsistencyThresholds
    full_thresholds: V10ConsistencyThresholds
    consistency_levels: dict[str, str]
    level_5_allowed: bool
    notes: str


class V10ConsistencyMetricDefinition(BaseModel):
    name: str
    description: str
    level: Literal["per_case", "aggregate"]
    required: bool


class V10ThreeAgentProtocolReceipt(BaseModel):
    receipt_id: str
    receipt_type: Literal["three_agent_consistency_protocol"] = (
        "three_agent_consistency_protocol"
    )
    version: str = "v10.16"
    minimum_independent_systems: int
    majority_vote_truth_claim_allowed: bool
    provider_outputs_combined_for_truth: bool
    consistency_not_correctness: bool
    constraints_codified: list[str]
    live_calls_in_this_version: bool
    provider_sdks_used: bool
    secrets_included: bool
    protocol_hash: str

    def to_markdown(
        self,
        *,
        config: V10ThreeAgentConsistencyProtocolConfig,
        metrics: list[V10ConsistencyMetricDefinition],
        validation_issues: list[str],
    ) -> str:
        metric_lines = [
            f"- `{metric.name}` ({metric.level}): {metric.description}"
            for metric in metrics
        ]
        recommended = [
            f"- `{system.role}`: `{system.provider}` / `{system.model}`"
            for system in config.recommended_initial_systems
        ]
        lines = [
            "# HELIX v10.16 Three-Agent Consistency Protocol Report",
            "",
            "## Executive Summary",
            "",
            "This is a protocol-only artifact. It defines how HELIX will compare authorization receipts across at least three independent systems, but it does not run providers or produce consistency evidence.",
            "",
            f"- receipt_id: `{self.receipt_id}`",
            f"- protocol_hash: `{self.protocol_hash}`",
            f"- minimum_independent_systems: `{self.minimum_independent_systems}`",
            f"- live_calls_in_this_version: `{str(self.live_calls_in_this_version).lower()}`",
            f"- provider_sdks_used: `{str(self.provider_sdks_used).lower()}`",
            f"- secrets_included: `{str(self.secrets_included).lower()}`",
            "",
            "## Purpose",
            "",
            "v10.15C made guarded live one-provider execution structurally possible. v10.16 defines a vendor-neutral protocol for comparing separate receipt chains from at least three independent systems.",
            "",
            "## System Independence",
            "",
            "Independent systems require distinct provider, model family, or deployment stack, plus separate raw outputs, request manifests, provider run manifests, receipt chains, and evidence assessments.",
            "",
            *recommended,
            "",
            "## Fixed Inputs",
            "",
            "- same case set",
            "- same contract objective",
            "- same case IDs",
            "- same schema",
            "- same prompt rendering version and prompt hash policy",
            "- same output schema",
            "- same evidence assessor version",
            "- same receipt-chain algorithm",
            "",
            "## Separate Provenance",
            "",
            "Each provider run must keep raw outputs, parsed judgments, normalized judgments, benchmark receipts, diagnostics, reportability results, receipt chains, evidence assessments, and provider run manifests separate.",
            "",
            "## Receipt Consistency Objects",
            "",
            "The unit of comparison is a case ID evaluated by one system: decision, violation_probability, receipt_hash, normalized_judgment_hash, reason_codes, cited_contract_phrase, citation_verification_method, evidence_level, and receipt_validity.",
            "",
            "## Metrics",
            "",
            *metric_lines,
            "",
            "## Disagreement Taxonomy",
            "",
            *[f"- `{name}`" for name in DISAGREEMENT_TAXONOMY],
            "",
            "## Vendor-Bias Controls",
            "",
            "- at least three independent systems",
            "- provider/model metadata recorded",
            "- separate raw outputs",
            "- no provider output used to prompt another provider",
            "- no majority vote used to relabel ground truth",
            "- no provider-specific thresholds unless pre-registered",
            "- per-provider metrics reported separately before aggregate metrics",
            "- failed providers included in the consistency report",
            "",
            "## Evidence-Level Rules",
            "",
            "Protocol-only v10.16 is Level 0 protocol artifact evidence. Future consistency evidence cannot exceed the minimum individual provider evidence level unless a later protocol explicitly justifies otherwise. Level 5 remains false.",
            "",
            "## Future Acceptance Thresholds",
            "",
            f"- pilot majority_decision_rate_min: `{config.pilot_thresholds.majority_decision_rate_min}`",
            f"- pilot severe_disagreement_rate_max: `{config.pilot_thresholds.severe_disagreement_rate_max}`",
            f"- full majority_decision_rate_min: `{config.full_thresholds.majority_decision_rate_min}`",
            f"- full severe_disagreement_rate_max: `{config.full_thresholds.severe_disagreement_rate_max}`",
            "",
            "## Protocol Receipt",
            "",
            "```json",
            json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True),
            "```",
            "",
            "## What This Supports",
            "",
            "- A reproducible, vendor-neutral comparison protocol for authorization receipts.",
            "- Explicit separation between consistency evidence and correctness evidence.",
            "- Pre-registered metrics and thresholds for a future v10.17 three-system run.",
            "",
            "## What This Does Not Yet Prove",
            "",
            "- No provider calls were made.",
            "- No provider SDKs were used.",
            "- No secrets were included.",
            "- No consistency evidence was produced yet.",
            "- Majority vote is not truth.",
            "- Agreement is consistency evidence, not correctness evidence.",
            "- Level 5 is false.",
            "- Future v10.17 is required for an actual three-system run.",
            "",
            "## Limitations",
            "",
            "- Three providers reduce vendor bias but do not eliminate shared training-data, benchmark-contamination, or instruction-following priors.",
            "- Disagreement taxonomy is descriptive, not blame assignment.",
            "- This protocol does not rank providers.",
            "",
            "## Next Steps",
            "",
            "1. Run v10.17 with three separately staged provider runs.",
            "2. Preserve per-system raw outputs, manifests, receipt chains, and evidence assessments.",
            "3. Compute per-provider metrics before aggregate consistency metrics.",
            "4. Report failures and disagreements without relabeling ground truth by vote.",
            "",
            "## Validation Issues",
            "",
            f"- validation_issues: `{validation_issues}`",
        ]
        return "\n".join(lines)


class V10ThreeAgentValidationResult(BaseModel):
    valid: bool
    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def load_v10_three_agent_consistency_protocol_config(
    path: str | Path,
) -> V10ThreeAgentConsistencyProtocolConfig:
    return V10ThreeAgentConsistencyProtocolConfig.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def validate_three_agent_system_specs(
    system_specs: list[V10ThreeAgentSystemSpec],
    config: V10ThreeAgentConsistencyProtocolConfig,
    *,
    live_design_config: V10LiveRunnerDesignConfig | None = None,
) -> V10ThreeAgentValidationResult:
    issues: list[str] = []
    warnings: list[str] = []
    if config.minimum_independent_systems < 3:
        issues.append("minimum_independent_systems_below_three")
    if len(system_specs) < config.minimum_independent_systems:
        issues.append("fewer_than_minimum_systems")
    if config.majority_vote_truth_claim_allowed:
        issues.append("majority_vote_truth_claim_allowed")
    if not config.consistency_not_correctness:
        issues.append("consistency_not_correctness_false")
    if config.provider_outputs_combined_for_truth:
        issues.append("provider_outputs_combined_for_truth")
    if config.level_5_allowed:
        issues.append("level_5_allowed")
    if not config.protocol_only:
        issues.append("protocol_only_false")
    if not config.failed_provider_not_silently_dropped:
        issues.append("failed_provider_may_be_silently_dropped")

    roles = [system.role for system in system_specs]
    if len(roles) != len(set(roles)):
        issues.append("duplicate_role")

    provider_models = [(system.provider, system.model) for system in system_specs]
    if len(provider_models) != len(set(provider_models)):
        issues.append("duplicate_provider_model")
    if len(set(provider_models)) < config.minimum_independent_systems:
        issues.append("fewer_than_three_independent_systems")

    allowed_modes = set(config.allowed_execution_modes_for_future_run)
    for system in system_specs:
        if system.execution_mode and system.execution_mode not in allowed_modes:
            issues.append(f"unknown_execution_mode:{system.role}")

    design_config = live_design_config or _load_default_live_design_config_if_available()
    if design_config is None:
        warnings.append("provider_model_allowlist_not_checked")
    else:
        for system in system_specs:
            result = validate_provider_model_allowed(
                design_config,
                system.provider,
                system.model,
            )
            if not result.valid:
                issue_suffix = ",".join(result.issues) or "unknown"
                issues.append(
                    f"provider_model_not_allowed:{system.role}:{issue_suffix}"
                )

    return V10ThreeAgentValidationResult(
        valid=not issues,
        issues=sorted(set(issues)),
        warnings=sorted(set(warnings)),
    )


def classify_risk_band(
    score: Any,
    config: V10ThreeAgentConsistencyProtocolConfig,
) -> str:
    if isinstance(score, bool) or not isinstance(score, int | float):
        return "invalid"
    value = float(score)
    if value < 0 or value > 1:
        return "invalid"
    bands = list(config.risk_bands.items())
    for index, (name, bounds) in enumerate(bands):
        lower, upper = bounds
        is_last_band = index == len(bands) - 1
        if lower <= value < upper or (is_last_band and value == upper):
            return name
    return "unknown"


def classify_decision_distance(
    decision_a: str,
    decision_b: str,
    config: V10ThreeAgentConsistencyProtocolConfig,
) -> int:
    order = {decision: index for index, decision in enumerate(config.decision_order)}
    if decision_a not in order or decision_b not in order:
        return -1
    return abs(order[decision_a] - order[decision_b])


def is_severe_disagreement(
    item_a: Mapping[str, Any] | Any,
    item_b: Mapping[str, Any] | Any,
    config: V10ThreeAgentConsistencyProtocolConfig,
) -> bool:
    policy = config.severe_disagreement_policy
    decision_a = _get_value(item_a, "decision")
    decision_b = _get_value(item_b, "decision")
    if policy.allow_vs_block_or_quarantine and {
        decision_a,
        decision_b,
    } in [{"ALLOW", "BLOCK"}, {"ALLOW", "QUARANTINE"}]:
        return True

    score_a = _extract_score(item_a)
    score_b = _extract_score(item_b)
    if (
        score_a is not None
        and score_b is not None
        and abs(score_a - score_b) >= policy.score_distance_threshold
    ):
        return True

    if policy.high_risk_citation_mismatch and _high_risk_citation_mismatch(
        item_a,
        item_b,
        config,
    ):
        return True

    if policy.parse_failure_against_valid_outputs and _parse_failure_against_valid(
        item_a,
        item_b,
    ):
        return True

    return False


def build_metric_definitions(
    config: V10ThreeAgentConsistencyProtocolConfig,
) -> list[V10ConsistencyMetricDefinition]:
    return [
        V10ConsistencyMetricDefinition(
            name="unanimous_decision_agreement",
            description="All compared systems produce the same decision for a case.",
            level="per_case",
            required=True,
        ),
        V10ConsistencyMetricDefinition(
            name="majority_decision_agreement",
            description="At least two of three systems produce the same decision.",
            level="per_case",
            required=True,
        ),
        V10ConsistencyMetricDefinition(
            name="max_score_distance",
            description="Maximum absolute violation_probability distance across systems.",
            level="per_case",
            required=True,
        ),
        V10ConsistencyMetricDefinition(
            name="mean_pairwise_score_distance",
            description="Mean pairwise score distance across systems.",
            level="per_case",
            required=True,
        ),
        V10ConsistencyMetricDefinition(
            name="risk_band_unanimous_agreement",
            description="All systems map scores to the same configured risk band.",
            level="per_case",
            required=True,
        ),
        V10ConsistencyMetricDefinition(
            name="risk_band_majority_agreement",
            description="At least two systems map scores to the same configured risk band.",
            level="per_case",
            required=True,
        ),
        V10ConsistencyMetricDefinition(
            name="all_receipts_valid",
            description="Every system emits a valid receipt for the case.",
            level="per_case",
            required=True,
        ),
        V10ConsistencyMetricDefinition(
            name="all_provider_outputs_parseable",
            description="Every provider output parses into the normalized judgment schema.",
            level="per_case",
            required=True,
        ),
        V10ConsistencyMetricDefinition(
            name="citation_consistency",
            description="High-risk citations use compatible verification methods and phrases.",
            level="per_case",
            required=True,
        ),
        V10ConsistencyMetricDefinition(
            name="unanimous_decision_rate",
            description="Fraction of cases with unanimous decision agreement.",
            level="aggregate",
            required=True,
        ),
        V10ConsistencyMetricDefinition(
            name="majority_decision_rate",
            description="Fraction of cases with at least two matching decisions.",
            level="aggregate",
            required=True,
        ),
        V10ConsistencyMetricDefinition(
            name="mean_pairwise_score_distance",
            description="Aggregate mean of per-case pairwise score distances.",
            level="aggregate",
            required=True,
        ),
        V10ConsistencyMetricDefinition(
            name="p95_pairwise_score_distance",
            description="95th percentile pairwise score distance.",
            level="aggregate",
            required=True,
        ),
        V10ConsistencyMetricDefinition(
            name="risk_band_unanimous_rate",
            description="Fraction of cases with unanimous risk-band agreement.",
            level="aggregate",
            required=True,
        ),
        V10ConsistencyMetricDefinition(
            name="risk_band_majority_rate",
            description="Fraction of cases with majority risk-band agreement.",
            level="aggregate",
            required=True,
        ),
        V10ConsistencyMetricDefinition(
            name="all_receipts_valid_rate",
            description="Fraction of cases where all systems have valid receipts.",
            level="aggregate",
            required=True,
        ),
        V10ConsistencyMetricDefinition(
            name="parse_success_rate_by_system",
            description="Parse success rate reported separately for each system.",
            level="aggregate",
            required=True,
        ),
        V10ConsistencyMetricDefinition(
            name="evidence_level_by_system",
            description="Evidence level reported separately for each system.",
            level="aggregate",
            required=True,
        ),
        V10ConsistencyMetricDefinition(
            name="disagreement_rate_by_family",
            description="Disagreement rate grouped by benchmark family.",
            level="aggregate",
            required=True,
        ),
        V10ConsistencyMetricDefinition(
            name="disagreement_rate_by_label",
            description="Disagreement rate grouped by benchmark label.",
            level="aggregate",
            required=True,
        ),
        V10ConsistencyMetricDefinition(
            name="severe_disagreement_rate",
            description="Fraction of cases with severe disagreement under pre-registered policy.",
            level="aggregate",
            required=True,
        ),
    ]


def build_three_agent_protocol_receipt(
    config: V10ThreeAgentConsistencyProtocolConfig,
) -> V10ThreeAgentProtocolReceipt:
    payload = {
        "receipt_id": "v10.16:three_agent_consistency_protocol",
        "receipt_type": "three_agent_consistency_protocol",
        "version": "v10.16",
        "minimum_independent_systems": config.minimum_independent_systems,
        "majority_vote_truth_claim_allowed": config.majority_vote_truth_claim_allowed,
        "provider_outputs_combined_for_truth": (
            config.provider_outputs_combined_for_truth
        ),
        "consistency_not_correctness": config.consistency_not_correctness,
        "constraints_codified": THREE_AGENT_PROTOCOL_CONSTRAINTS,
        "live_calls_in_this_version": False,
        "provider_sdks_used": False,
        "secrets_included": False,
    }
    return V10ThreeAgentProtocolReceipt(
        **payload,
        protocol_hash=stable_json_hash(payload),
    )


def write_three_agent_protocol_artifacts(
    config: V10ThreeAgentConsistencyProtocolConfig,
    out_dir: str | Path,
    *,
    generated_at: str | None = None,
) -> dict[str, Path]:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    metrics = build_metric_definitions(config)
    receipt = build_three_agent_protocol_receipt(config)
    validation = validate_three_agent_system_specs(
        config.recommended_initial_systems,
        config,
    )

    config_path = target / "three_agent_consistency_protocol_config.json"
    metrics_path = target / "three_agent_metric_definitions.json"
    receipt_path = target / "three_agent_protocol_receipt.json"
    report_path = target / "three_agent_protocol_report.md"

    config_payload = {
        "schema_version": "v10_three_agent_consistency_protocol_snapshot_v1",
        "generated_at": generated_at
        or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "config": config.model_dump(mode="json"),
        "validation_issues": validation.issues,
        "validation_warnings": validation.warnings,
    }
    config_path.write_text(
        json.dumps(config_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    metrics_path.write_text(
        json.dumps(
            {
                "schema_version": "v10_three_agent_metric_definitions_v1",
                "metrics": [metric.model_dump(mode="json") for metric in metrics],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    receipt_path.write_text(
        json.dumps(receipt.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(
        receipt.to_markdown(
            config=config,
            metrics=metrics,
            validation_issues=validation.issues,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "config": config_path,
        "metrics": metrics_path,
        "receipt": receipt_path,
        "report": report_path,
    }


def _load_default_live_design_config_if_available() -> V10LiveRunnerDesignConfig | None:
    path = Path("configs/v10_live_provider_runner_design_gate.json")
    if not path.exists():
        return None
    return load_v10_live_runner_design_config(path)


def _get_value(item: Mapping[str, Any] | Any, field: str) -> Any:
    if isinstance(item, Mapping):
        return item.get(field)
    return getattr(item, field, None)


def _extract_score(item: Mapping[str, Any] | Any) -> float | None:
    for field in ("violation_probability", "score", "gated_score", "raw_score"):
        value = _get_value(item, field)
        if isinstance(value, bool):
            return None
        if isinstance(value, int | float):
            return float(value)
    return None


def _high_risk_citation_mismatch(
    item_a: Mapping[str, Any] | Any,
    item_b: Mapping[str, Any] | Any,
    config: V10ThreeAgentConsistencyProtocolConfig,
) -> bool:
    scores = [_extract_score(item_a), _extract_score(item_b)]
    if not any(score is not None and score >= 0.75 for score in scores):
        return False
    method_a = _get_value(item_a, "citation_verification_method")
    method_b = _get_value(item_b, "citation_verification_method")
    phrase_a = _get_value(item_a, "cited_contract_phrase")
    phrase_b = _get_value(item_b, "cited_contract_phrase")
    valid_methods = {"exact_substring", "normalized_substring"}
    if (method_a in valid_methods) != (method_b in valid_methods):
        return True
    if phrase_a != phrase_b:
        return True
    return False


def _parse_failure_against_valid(
    item_a: Mapping[str, Any] | Any,
    item_b: Mapping[str, Any] | Any,
) -> bool:
    parse_a = _get_value(item_a, "parse_success")
    parse_b = _get_value(item_b, "parse_success")
    if parse_a is None:
        parse_a = _get_value(item_a, "parseable")
    if parse_b is None:
        parse_b = _get_value(item_b, "parseable")
    return {parse_a, parse_b} == {True, False}
