"""T03 SYNTHETIC local fixture admission tests."""

from __future__ import annotations

import dataclasses
import shutil
from pathlib import Path

import pytest

from build_finance.crypto_replay.canonical import parse_canonical_record, sha256_hex
from tests.crypto_replay.support.synthetic_local_fixture import (
    SYNTHETIC_BASE_MINT,
    SYNTHETIC_EVENT_TIME,
    SYNTHETIC_INGESTED_AT,
    SYNTHETIC_OBSERVED_AT,
    SYNTHETIC_PAYLOAD_BASE_SENTINEL,
    SYNTHETIC_PAYLOAD_SOURCE_SENTINEL,
    SYNTHETIC_QUOTE_MINT,
    SYNTHETIC_SOURCE_ID,
    SYNTHETIC_TERMS_PREFIX,
    SYNTHETICEventSpec,
    reseal_SYNTHETIC_manifest,
    rewrite_SYNTHETIC_rights,
    rewrite_SYNTHETIC_witness,
    witness_for_SYNTHETIC_fixture,
    write_SYNTHETIC_local_fixture,
)


def _capture_and_admit(root: Path):
    from build_finance.crypto_replay.admission import admit_local_fixture
    from build_finance.crypto_replay.local_fixture import capture_local_fixture

    captured = capture_local_fixture(root)
    return captured, admit_local_fixture(captured)


def _receipts(batch) -> tuple[dict[str, object], ...]:
    return tuple(parse_canonical_record(record) for record in batch.source_receipt_records)


def _reason_codes(batch) -> tuple[str, ...]:
    return tuple(batch.reason_codes)


def test_fixture_hash_mismatch_quarantines_set(tmp_path: Path) -> None:
    fixture = write_SYNTHETIC_local_fixture(tmp_path)
    fixture.payload_paths[0].write_bytes(fixture.payloads[0] + b"\nSYNTHETIC_DIGEST_MISMATCH\n")

    _captured, batch = _capture_and_admit(fixture.root)

    receipt = _receipts(batch)[0]
    assert batch.status == "QUARANTINED"
    assert _reason_codes(batch) == ("ADMISSION_HASH_MISMATCH", "ADMISSION_SET_NOT_CLOSED")
    assert receipt["status"] == "QUARANTINED"
    assert receipt["reason_codes"] == ["ADMISSION_HASH_MISMATCH", "ADMISSION_SET_NOT_CLOSED"]
    assert receipt["raw_payload_sha256"] == sha256_hex(fixture.payloads[0] + b"\nSYNTHETIC_DIGEST_MISMATCH\n")


def test_point_in_time_fields_required(tmp_path: Path) -> None:
    spec = SYNTHETICEventSpec(observed_at=None)
    fixture = write_SYNTHETIC_local_fixture(tmp_path, event_specs=(spec,))

    _captured, batch = _capture_and_admit(fixture.root)

    receipt = _receipts(batch)[0]
    assert batch.status == "REJECTED"
    assert _reason_codes(batch) == ("ADMISSION_POINT_IN_TIME_MISSING",)
    assert receipt["observed_at"] is None
    assert receipt["ingested_at"] == SYNTHETIC_INGESTED_AT


def test_duplicate_base_mint_quarantines_set(tmp_path: Path) -> None:
    first = SYNTHETICEventSpec()
    second = dataclasses.replace(
        first,
        admission_sequence="2",
        availability_slot="2",
        relative_path="payloads/quote-0002.json",
        source_native_event_id="synthetic-event-0002",
        market_id=f"{SYNTHETIC_BASE_MINT}/SYNTHETIC_ALT_QUOTE_INVALID:jupiter",
        quote_mint="SYNTHETIC_ALT_QUOTE_INVALID",
    )
    fixture = write_SYNTHETIC_local_fixture(tmp_path, event_specs=(first, second))

    _captured, batch = _capture_and_admit(fixture.root)

    assert batch.status == "QUARANTINED"
    assert _reason_codes(batch) == ("ADMISSION_UNIVERSE_BIASED", "ADMISSION_SET_NOT_CLOSED")


def test_base_mint_cannot_equal_quote_mint(tmp_path: Path) -> None:
    spec = SYNTHETICEventSpec(quote_mint=SYNTHETIC_BASE_MINT, market_id=f"{SYNTHETIC_BASE_MINT}/{SYNTHETIC_BASE_MINT}:jupiter")
    fixture = write_SYNTHETIC_local_fixture(tmp_path, event_specs=(spec,))

    _captured, batch = _capture_and_admit(fixture.root)

    receipt = _receipts(batch)[0]
    assert batch.status == "REJECTED"
    assert _reason_codes(batch) == ("ADMISSION_PROFILE_MISMATCH",)
    assert receipt["market_id"] == spec.market_id


def test_partial_rights_evidence_is_preserved(tmp_path: Path) -> None:
    fixture = write_SYNTHETIC_local_fixture(tmp_path)
    rights = dict(fixture.rights_manifest)
    rights["rights_review_date"] = None
    rewrite_SYNTHETIC_rights(fixture, rights)
    manifest = dict(fixture.manifest)
    manifest["rights_manifest_sha256"] = sha256_hex(fixture.rights_manifest_path.read_bytes())
    reseal_SYNTHETIC_manifest(fixture, manifest)

    _captured, batch = _capture_and_admit(fixture.root)

    receipt = _receipts(batch)[0]
    assert batch.status == "REJECTED"
    assert _reason_codes(batch) == ("ADMISSION_RIGHTS_MISSING",)
    assert receipt["rights_role"] == "offline_research_replay"
    assert receipt["rights_effective_date"] == "2026-01-01"
    assert receipt["rights_review_date"] is None
    assert receipt["terms_sha256"] == sha256_hex(fixture.terms_payload)


def test_conflicting_source_position_rejected(tmp_path: Path) -> None:
    first = SYNTHETICEventSpec()
    second = dataclasses.replace(
        first,
        admission_sequence="2",
        relative_path="payloads/quote-0002.json",
        route_capacity_base_atoms="999999",
    )
    fixture = write_SYNTHETIC_local_fixture(tmp_path, event_specs=(first, second))

    _captured, batch = _capture_and_admit(fixture.root)

    assert batch.status == "QUARANTINED"
    assert _reason_codes(batch) == ("ADMISSION_POSITION_CONFLICT",)


def test_same_slot_different_market_is_not_conflict(tmp_path: Path) -> None:
    first = SYNTHETICEventSpec()
    second = dataclasses.replace(
        first,
        admission_sequence="2",
        relative_path="payloads/quote-0002.json",
        source_native_event_id="synthetic-event-0002",
        market_id="SYNTHETIC_OTHER_BASE_INVALID/SYNTHETIC_OTHER_QUOTE_INVALID:jupiter",
        base_mint="SYNTHETIC_OTHER_BASE_INVALID",
        quote_mint="SYNTHETIC_OTHER_QUOTE_INVALID",
    )
    fixture = write_SYNTHETIC_local_fixture(tmp_path, event_specs=(first, second))

    _captured, batch = _capture_and_admit(fixture.root)

    assert batch.status == "ADMITTED"
    assert _reason_codes(batch) == ()
    assert len(batch.candidates) == 2


def test_terms_digest_mismatch_preserves_actual_terms_digest(tmp_path: Path) -> None:
    fixture = write_SYNTHETIC_local_fixture(tmp_path)
    actual_terms = fixture.terms_payload + b"SYNTHETIC TERMS DIGEST MISMATCH\n"
    fixture.terms_path.write_bytes(actual_terms)

    _captured, batch = _capture_and_admit(fixture.root)

    receipt = _receipts(batch)[0]
    assert batch.status == "REJECTED"
    assert _reason_codes(batch) == ("ADMISSION_RIGHTS_MISSING",)
    assert receipt["terms_sha256"] == sha256_hex(actual_terms)
    assert receipt["rights_role"] == "offline_research_replay"


def test_witness_identity_mismatch_maps_manifest_mismatch(tmp_path: Path) -> None:
    spec = SYNTHETICEventSpec()
    fixture = write_SYNTHETIC_local_fixture(tmp_path, event_specs=(spec,))
    witness = witness_for_SYNTHETIC_fixture(fixture, 0, spec)
    witness["raw_payload_sha256"] = "0" * 64
    rewrite_SYNTHETIC_witness(fixture, 0, witness)

    _captured, batch = _capture_and_admit(fixture.root)

    receipt = _receipts(batch)[0]
    assert batch.status == "REJECTED"
    assert _reason_codes(batch) == ("ADMISSION_MANIFEST_MISMATCH",)
    assert receipt["raw_payload_sha256"] == sha256_hex(fixture.payloads[0])


def test_path_confinement_rejects_traversal_absolute_drive_and_backslash(tmp_path: Path) -> None:
    unsafe_paths = ("../outside.json", "/absolute.json", "C:/absolute.json", "payloads\\quote.json")
    for unsafe_path in unsafe_paths:
        case_root = tmp_path / unsafe_path.replace("/", "_").replace("\\", "_").replace(":", "_")
        fixture = write_SYNTHETIC_local_fixture(case_root)
        manifest = dict(fixture.manifest)
        files = list(manifest["files"])  # type: ignore[arg-type]
        files[0] = {**files[0], "relative_path": unsafe_path}
        manifest["files"] = files
        reseal_SYNTHETIC_manifest(fixture, manifest)

        captured, batch = _capture_and_admit(fixture.root)

        assert captured.capture_issues
        assert batch.status == "REJECTED"
        assert "ADMISSION_MANIFEST_MISMATCH" in _reason_codes(batch)


def test_symlink_root_and_payload_entries_are_rejected(tmp_path: Path) -> None:
    fixture = write_SYNTHETIC_local_fixture(tmp_path / "entry")
    fixture.payload_paths[0].unlink()
    try:
        fixture.payload_paths[0].symlink_to(tmp_path / "outside-payload.json")
    except OSError as error:
        pytest.skip(f"symlink creation unavailable in this environment: {error}")
    (tmp_path / "outside-payload.json").write_bytes(fixture.payloads[0])

    captured, batch = _capture_and_admit(fixture.root)

    assert captured.capture_issues
    assert batch.status == "REJECTED"
    assert "ADMISSION_NOT_LOCAL" in _reason_codes(batch) or "ADMISSION_MANIFEST_MISMATCH" in _reason_codes(batch)

    link_root = tmp_path / "root-link"
    try:
        link_root.symlink_to(fixture.root, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"root symlink creation unavailable in this environment: {error}")
    from build_finance.crypto_replay.local_fixture import capture_local_fixture

    linked_capture = capture_local_fixture(link_root)
    assert linked_capture.capture_issues


def test_missing_extra_and_non_regular_payloads_close_set(tmp_path: Path) -> None:
    missing = write_SYNTHETIC_local_fixture(tmp_path / "missing")
    missing.payload_paths[0].unlink()
    _captured_missing, missing_batch = _capture_and_admit(missing.root)
    assert missing_batch.status == "QUARANTINED"
    assert "ADMISSION_SET_NOT_CLOSED" in _reason_codes(missing_batch)

    extra = write_SYNTHETIC_local_fixture(tmp_path / "extra")
    (extra.root / "payloads" / "unexpected.json").write_bytes(extra.payloads[0])
    _captured_extra, extra_batch = _capture_and_admit(extra.root)
    assert extra_batch.status == "QUARANTINED"
    assert "ADMISSION_SET_NOT_CLOSED" in _reason_codes(extra_batch)

    non_regular = write_SYNTHETIC_local_fixture(tmp_path / "non-regular")
    non_regular.payload_paths[0].unlink()
    non_regular.payload_paths[0].mkdir()
    _captured_non_regular, non_regular_batch = _capture_and_admit(non_regular.root)
    assert non_regular_batch.status == "QUARANTINED"
    assert "ADMISSION_SET_NOT_CLOSED" in _reason_codes(non_regular_batch)


def test_stable_receipts_across_roots(tmp_path: Path) -> None:
    left = write_SYNTHETIC_local_fixture(tmp_path / "left")
    right = write_SYNTHETIC_local_fixture(tmp_path / "right")

    _left_capture, left_batch = _capture_and_admit(left.root)
    _right_capture, right_batch = _capture_and_admit(right.root)

    assert left_batch.status == "ADMITTED"
    assert left_batch.source_receipt_records == right_batch.source_receipt_records
    assert left_batch.candidates == right_batch.candidates


def test_duplicate_version_idempotence_is_not_a_conflict(tmp_path: Path) -> None:
    spec = SYNTHETICEventSpec()
    duplicate = dataclasses.replace(spec, admission_sequence="2", relative_path="payloads/quote-0002.json")
    fixture = write_SYNTHETIC_local_fixture(tmp_path, event_specs=(spec, duplicate))

    _captured, batch = _capture_and_admit(fixture.root)

    assert batch.status == "ADMITTED"
    assert _reason_codes(batch) == ()


def test_parser_identity_matches_independent_runtime_closure(tmp_path: Path) -> None:
    fixture = write_SYNTHETIC_local_fixture(tmp_path)
    from build_finance.crypto_replay.canonical import canonical_json_bytes
    from build_finance.crypto_replay.jupiter_fixture import PARSER_VERSION, current_parser_identity

    import ast
    import hashlib
    import importlib.util

    roots = (
        "build_finance.crypto_replay.local_fixture",
        "build_finance.crypto_replay.jupiter_fixture",
        "build_finance.crypto_replay.admission",
    )
    seen: set[str] = set()
    pending = list(roots)
    rows: list[dict[str, str]] = []
    while pending:
        module = pending.pop()
        if module in seen:
            continue
        seen.add(module)
        spec = importlib.util.find_spec(module)
        assert spec is not None
        assert spec.origin is not None
        path = Path(spec.origin)
        payload = path.read_bytes()
        rows.append({"module": module, "sha256": hashlib.sha256(payload).hexdigest(), "byte_length": str(len(payload))})
        tree = ast.parse(payload, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("build_finance.crypto_replay."):
                        pending.append(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("build_finance.crypto_replay"):
                pending.append(node.module)

    expected_bundle = {
        "parser_version": PARSER_VERSION,
        "runtime_modules": sorted(rows, key=lambda row: row["module"].encode("utf-8")),
        "resources": [],
    }
    expected_digest = hashlib.sha256(canonical_json_bytes(expected_bundle)).hexdigest()
    identity = current_parser_identity()

    assert identity.version == "solana-jupiter-fixture-parser/v1"
    assert identity.code_sha256 == expected_digest
    assert fixture.root.is_relative_to(tmp_path)


def test_universe_declaration_does_not_write_or_promote_real_p2_artifacts(tmp_path: Path) -> None:
    fixture = write_SYNTHETIC_local_fixture(tmp_path)

    _captured, batch = _capture_and_admit(fixture.root)

    assert fixture.manifest["universe_policy"] == "FULL_DECLARED_SOURCE_UNIVERSE"
    assert batch.status == "ADMITTED"
    assert not hasattr(batch, "promotion_status")
    assert not hasattr(batch, "real_fixture_identity")
    assert not (Path("docs") / "crypto-replay" / "T03-green.json").exists()
    for path in (*fixture.payload_paths, fixture.terms_path, *fixture.witness_paths):
        assert path.is_relative_to(tmp_path)
    assert SYNTHETIC_PAYLOAD_SOURCE_SENTINEL in fixture.payloads[0]
    assert SYNTHETIC_PAYLOAD_BASE_SENTINEL in fixture.payloads[0]
    assert fixture.terms_payload.decode("utf-8").startswith(SYNTHETIC_TERMS_PREFIX)
    assert SYNTHETIC_SOURCE_ID in fixture.payloads[0].decode("utf-8")
    assert SYNTHETIC_BASE_MINT in fixture.payloads[0].decode("utf-8")
    assert SYNTHETIC_EVENT_TIME in fixture.payloads[0].decode("utf-8")
    assert SYNTHETIC_OBSERVED_AT in fixture.witness_paths[0].read_text(encoding="utf-8")
    assert SYNTHETIC_INGESTED_AT in fixture.witness_paths[0].read_text(encoding="utf-8")


def test_rights_manifest_digest_mismatch_maps_manifest_mismatch(tmp_path: Path) -> None:
    fixture = write_SYNTHETIC_local_fixture(tmp_path)
    rights = dict(fixture.rights_manifest)
    rights["retention_posture"] = "LOCAL_RESEARCH_RETENTION_CHANGED"
    rewrite_SYNTHETIC_rights(fixture, rights)

    _captured, batch = _capture_and_admit(fixture.root)

    assert batch.status == "REJECTED"
    assert _reason_codes(batch) == ("ADMISSION_MANIFEST_MISMATCH",)


def test_noncanonical_witness_maps_point_in_time_missing(tmp_path: Path) -> None:
    spec = SYNTHETICEventSpec()
    fixture = write_SYNTHETIC_local_fixture(tmp_path, event_specs=(spec,))
    rewrite_SYNTHETIC_witness(fixture, 0, witness_for_SYNTHETIC_fixture(fixture, 0, spec), canonical=False)

    _captured, batch = _capture_and_admit(fixture.root)

    assert batch.status == "REJECTED"
    assert _reason_codes(batch) == ("ADMISSION_POINT_IN_TIME_MISSING",)


def test_fixtures_never_escape_tmp_path_when_copied(tmp_path: Path) -> None:
    fixture = write_SYNTHETIC_local_fixture(tmp_path / "original")
    copied_root = tmp_path / "copy"
    shutil.copytree(fixture.root, copied_root)

    _captured, batch = _capture_and_admit(copied_root)

    assert batch.status == "ADMITTED"
    assert copied_root.is_relative_to(tmp_path)
