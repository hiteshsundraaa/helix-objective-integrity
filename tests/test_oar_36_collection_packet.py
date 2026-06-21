from __future__ import annotations

import json
from pathlib import Path

from helix.benchmark.oar_36_collection_packet import (
    load_jsonl,
    load_oar_36_collection_packet_config,
    write_oar_36_collection_packet_outputs,
)


CONFIG_PATH = Path("configs/oar_36_collection_packet.json")
PROMPTS_PATH = Path("benchmarks/oar_360/oar_36_dry_run/oar_36_prompt_pack.jsonl")
PROMPT_MANIFEST_PATH = Path("benchmarks/oar_360/oar_36_dry_run/oar_36_prompt_manifest.json")
EXPECTED_FILES_PATH = Path("benchmarks/oar_360/oar_36_dry_run/oar_36_expected_raw_output_filenames.json")


def _fixture():
    config = load_oar_36_collection_packet_config(CONFIG_PATH)
    prompts = load_jsonl(PROMPTS_PATH)
    prompt_manifest = json.loads(PROMPT_MANIFEST_PATH.read_text(encoding="utf-8"))
    expected_payload = json.loads(EXPECTED_FILES_PATH.read_text(encoding="utf-8"))
    return config, prompts, prompt_manifest, expected_payload["files"]


def _write(out_dir: Path):
    config, prompts, prompt_manifest, expected_files = _fixture()
    summary = write_oar_36_collection_packet_outputs(
        config,
        prompts,
        prompt_manifest,
        expected_files,
        out_dir,
    )
    return summary


def test_config_loads() -> None:
    config = load_oar_36_collection_packet_config(CONFIG_PATH)

    assert config.suite_name == "OAR-36"
    assert config.no_provider_calls is True
    assert config.no_model_outputs is True
    assert config.no_empirical_results is True
    assert len(config.default_systems) == 3


def test_provider_packets_generated_for_default_systems(tmp_path: Path) -> None:
    _write(tmp_path)

    provider_dir = tmp_path / "provider_packets"
    assert (provider_dir / "google_oar36_collection_packet.md").exists()
    assert (provider_dir / "anthropic_oar36_collection_packet.md").exists()
    assert (provider_dir / "openai_oar36_collection_packet.md").exists()


def test_each_provider_packet_contains_36_case_blocks(tmp_path: Path) -> None:
    _write(tmp_path)

    for path in (tmp_path / "provider_packets").glob("*_oar36_collection_packet.md"):
        if path.name == "generic_oar36_collection_packet.md":
            continue
        text = path.read_text(encoding="utf-8")
        assert text.count("BEGIN COPY PROMPT") == 36
        assert text.count("END COPY PROMPT") == 36


def test_provider_packets_exclude_answer_key_fields(tmp_path: Path) -> None:
    _write(tmp_path)

    forbidden_tokens = [
        "expected_decision",
        "expected_risk_interval",
        "ground_truth",
        "label",
        "risk_band",
        "required_citation_phrases",
        "forbidden_citation_phrases",
    ]
    for path in (tmp_path / "provider_packets").glob("*_oar36_collection_packet.md"):
        text = path.read_text(encoding="utf-8").lower()
        for token in forbidden_tokens:
            assert token not in text


def test_collector_log_template_contains_required_attestations(tmp_path: Path) -> None:
    _write(tmp_path)
    payload = json.loads((tmp_path / "oar_36_collector_log_template.json").read_text(encoding="utf-8"))

    attestation = payload["attestation"]
    assert "no_ground_truth_exposed" in attestation
    assert "no_cross_provider_output_sharing" in attestation
    assert "raw_outputs_not_edited" in attestation
    assert "malformed_rows_not_repaired" in attestation
    assert "missing_citations_not_filled" in attestation
    assert "majority_vote_not_treated_as_truth" in attestation
    assert attestation["manual_evidence_cap_level_3"] is True


def test_checklist_warns_against_repairs(tmp_path: Path) -> None:
    _write(tmp_path)
    text = (tmp_path / "OAR36_COLLECTION_CHECKLIST.md").read_text(encoding="utf-8")

    assert "Do not edit malformed rows" in text
    assert "Do not fill missing citations" in text


def test_post_collection_commands_include_receipt_prep_and_analysis(tmp_path: Path) -> None:
    _write(tmp_path)
    text = (tmp_path / "OAR36_POST_COLLECTION_COMMANDS.md").read_text(encoding="utf-8")

    assert "python examples/prepare_oar_36_raw_receipts.py" in text
    assert "python examples/analyze_oar_36_results.py" in text
    assert "--receipt-prep-manifest benchmarks/oar_360/oar_36_dry_run/receipt_prep/oar_36_receipt_prep_manifest.json" in text


def test_manifest_boundary_flags(tmp_path: Path) -> None:
    summary = _write(tmp_path)
    manifest = json.loads((tmp_path / "oar_36_collection_manifest.json").read_text(encoding="utf-8"))

    assert manifest["no_provider_calls"] is True
    assert manifest["no_model_outputs"] is True
    assert manifest["no_empirical_results"] is True
    assert manifest["ground_truth_exposed"] is False
    assert summary.no_provider_calls is True


def test_readme_states_no_correctness_claim(tmp_path: Path) -> None:
    _write(tmp_path)
    text = (tmp_path / "OAR36_COLLECTION_README.md").read_text(encoding="utf-8")

    assert "this does not prove model correctness" in text
    assert "no provider calls were made by this package" in text
    assert "ground truth is not included" in text
    assert "Level 4/5 not claimed" in text


def test_deterministic_rerun_gives_same_manifest_hash(tmp_path: Path) -> None:
    first = _write(tmp_path / "first")
    second = _write(tmp_path / "second")

    assert first.manifest_hash == second.manifest_hash
    assert first.provider_packet_hashes == second.provider_packet_hashes
    assert first.generic_packet_hash == second.generic_packet_hash
