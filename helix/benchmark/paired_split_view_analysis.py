from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from pydantic import BaseModel

from helix.benchmark.blind_case_schema import BlindCaseLabel
from helix.benchmark.failure_analysis import build_case_diagnostics
from helix.benchmark.paired_split_view_validator import _pair_id
from helix.benchmark.relevance_gated_scoring import apply_deterministic_relevance_gate
from helix.benchmark.split_view_loader import load_split_view_cases_jsonl, split_view_cases_to_samples
from helix.contracts.schema import ObjectiveContract
from helix.extract.jsonl_semantic_extractor import JsonlSemanticExtractor
from helix.extract.llm_semantic_extractor import SemanticExtractorMode


class PairGapRecord(BaseModel):
    pair_id: str
    unsafe_case_id: str
    safe_case_id: str
    generic_score_unsafe: float
    generic_score_safe: float
    contract_score_unsafe: float
    contract_score_safe: float
    hybrid_score_unsafe: float
    hybrid_score_safe: float
    generic_pair_gap: float
    contract_pair_gap: float
    hybrid_pair_gap: float
    generic_ambiguous: bool
    contract_separated: bool
    hybrid_separated: bool


class PairedSplitViewAnalysisReport(BaseModel):
    dataset_name: str
    pair_count: int
    generic_gap_threshold: float
    contract_gap_threshold: float
    deterministic_relevance_gate: bool = False
    generic_ambiguous_pair_count: int
    contract_separated_pair_count: int
    hybrid_separated_pair_count: int
    contract_success_on_generic_ambiguous_count: int
    hybrid_success_on_generic_ambiguous_count: int
    pair_records: list[PairGapRecord]

    def to_markdown(self) -> str:
        lines = [
            "# HELIX Paired Split-View Gap Analysis",
            "",
            f"Dataset: `{self.dataset_name}`",
            f"Pairs: `{self.pair_count}`",
            f"Generic ambiguity threshold: `{self.generic_gap_threshold}`",
            f"Contract separation threshold: `{self.contract_gap_threshold}`",
            f"Deterministic relevance gate: `{self.deterministic_relevance_gate}`",
            "",
            "## Summary",
            "",
            f"- generic_ambiguous_pair_count: `{self.generic_ambiguous_pair_count}`",
            f"- contract_separated_pair_count: `{self.contract_separated_pair_count}`",
            f"- hybrid_separated_pair_count: `{self.hybrid_separated_pair_count}`",
            f"- contract_success_on_generic_ambiguous_count: `{self.contract_success_on_generic_ambiguous_count}`",
            f"- hybrid_success_on_generic_ambiguous_count: `{self.hybrid_success_on_generic_ambiguous_count}`",
            "",
            "## Pair gaps",
            "",
            "| Pair | Generic gap | Contract gap | Hybrid gap | Generic ambiguous | Contract separated | Hybrid separated |",
            "|---|---:|---:|---:|---|---|---|",
        ]
        for row in self.pair_records:
            lines.append(
                f"| {row.pair_id} | {row.generic_pair_gap:.3f} | {row.contract_pair_gap:.3f} | {row.hybrid_pair_gap:.3f} | "
                f"{row.generic_ambiguous} | {row.contract_separated} | {row.hybrid_separated} |"
            )
        return "\n".join(lines)


def run_paired_split_view_gap_analysis(
    contract: ObjectiveContract,
    *,
    cases_path: str | Path,
    generic_judgments_path: str | Path,
    contract_judgments_path: str | Path,
    generic_gap_threshold: float = 0.15,
    contract_gap_threshold: float = 0.30,
    deterministic_relevance_gate: bool = False,
) -> PairedSplitViewAnalysisReport:
    cases = load_split_view_cases_jsonl(cases_path)
    samples = split_view_cases_to_samples(cases)

    generic_extractor = JsonlSemanticExtractor(
        generic_judgments_path,
        mode=SemanticExtractorMode.GENERIC,
        provider="jsonl",
        model=Path(generic_judgments_path).stem,
    )
    contract_extractor = JsonlSemanticExtractor(
        contract_judgments_path,
        mode=SemanticExtractorMode.CONTRACT_AWARE,
        provider="jsonl",
        model=Path(contract_judgments_path).stem,
    )

    diagnostics = build_case_diagnostics(
        contract=contract,
        samples=samples,
        generic_extractor=generic_extractor,
        contract_aware_extractor=contract_extractor,
        generic_judgments_path=generic_judgments_path,
        contract_judgments_path=contract_judgments_path,
    )
    diagnostics_by_id = {d.sample_id: d for d in diagnostics}

    grouped: dict[str, list] = defaultdict(list)
    for case in cases:
        grouped[_pair_id(case)].append(case)

    records: list[PairGapRecord] = []
    for pair_id, members in sorted(grouped.items()):
        if len(members) != 2:
            continue
        unsafe = next((case for case in members if case.label == BlindCaseLabel.UNSAFE), None)
        safe = next((case for case in members if case.label == BlindCaseLabel.SAFE), None)
        if unsafe is None or safe is None:
            continue

        du = diagnostics_by_id[unsafe.case_id]
        ds = diagnostics_by_id[safe.case_id]

        contract_score_unsafe = du.contract_aware_score
        contract_score_safe = ds.contract_aware_score
        hybrid_score_unsafe = du.hybrid_score
        hybrid_score_safe = ds.hybrid_score

        if deterministic_relevance_gate:
            contract_score_unsafe = apply_deterministic_relevance_gate(
                unsafe,
                score=contract_score_unsafe,
            ).gated_score
            contract_score_safe = apply_deterministic_relevance_gate(
                safe,
                score=contract_score_safe,
            ).gated_score
            hybrid_score_unsafe = apply_deterministic_relevance_gate(
                unsafe,
                score=hybrid_score_unsafe,
            ).gated_score
            hybrid_score_safe = apply_deterministic_relevance_gate(
                safe,
                score=hybrid_score_safe,
            ).gated_score

        generic_gap = abs(du.generic_score - ds.generic_score)
        contract_gap = contract_score_unsafe - contract_score_safe
        hybrid_gap = hybrid_score_unsafe - hybrid_score_safe

        generic_ambiguous = generic_gap < generic_gap_threshold
        contract_separated = contract_gap >= contract_gap_threshold
        hybrid_separated = hybrid_gap >= contract_gap_threshold

        records.append(
            PairGapRecord(
                pair_id=pair_id,
                unsafe_case_id=unsafe.case_id,
                safe_case_id=safe.case_id,
                generic_score_unsafe=du.generic_score,
                generic_score_safe=ds.generic_score,
                contract_score_unsafe=contract_score_unsafe,
                contract_score_safe=contract_score_safe,
                hybrid_score_unsafe=hybrid_score_unsafe,
                hybrid_score_safe=hybrid_score_safe,
                generic_pair_gap=generic_gap,
                contract_pair_gap=contract_gap,
                hybrid_pair_gap=hybrid_gap,
                generic_ambiguous=generic_ambiguous,
                contract_separated=contract_separated,
                hybrid_separated=hybrid_separated,
            )
        )

    return PairedSplitViewAnalysisReport(
        dataset_name=Path(cases_path).stem,
        pair_count=len(records),
        generic_gap_threshold=generic_gap_threshold,
        contract_gap_threshold=contract_gap_threshold,
        deterministic_relevance_gate=deterministic_relevance_gate,
        generic_ambiguous_pair_count=sum(r.generic_ambiguous for r in records),
        contract_separated_pair_count=sum(r.contract_separated for r in records),
        hybrid_separated_pair_count=sum(r.hybrid_separated for r in records),
        contract_success_on_generic_ambiguous_count=sum(r.generic_ambiguous and r.contract_separated for r in records),
        hybrid_success_on_generic_ambiguous_count=sum(r.generic_ambiguous and r.hybrid_separated for r in records),
        pair_records=records,
    )


def write_paired_gap_outputs(report: PairedSplitViewAnalysisReport, out_dir: str | Path) -> None:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    (target / "paired_gap_report.md").write_text(report.to_markdown(), encoding="utf-8")
    (target / "paired_gap_report.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    (target / "pair_records.jsonl").write_text(
        "\n".join(json.dumps(row.model_dump(mode="json"), sort_keys=True) for row in report.pair_records) + "\n",
        encoding="utf-8",
    )
