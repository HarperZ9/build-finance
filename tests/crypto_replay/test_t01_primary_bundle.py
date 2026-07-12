"""T01 RED contract for the sealed primary bundle and resolving vectors."""

from __future__ import annotations

import importlib.resources
import json
from pathlib import Path

EXAMPLE_ROOT = Path(__file__).parent / "resources" / "primary-v1" / "examples"


def test_primary_bundle_hash_is_locked() -> None:
    from build_finance.crypto_replay.canonical import parse_canonical_record, sha256_hex

    package = importlib.resources.files("build_finance.crypto_replay")
    bundle_record = package.joinpath("resources/primary-schema-bundle.json").read_bytes()
    digest_record = package.joinpath("resources/primary-schema-bundle.sha256").read_bytes()

    assert digest_record.endswith(b"\n") and len(digest_record) == 65
    expected_digest = digest_record[:-1].decode("ascii")
    assert expected_digest == sha256_hex(bundle_record[:-1])
    bundle = parse_canonical_record(bundle_record)
    assert bundle["schema"] == "build-finance.primary-schema-bundle/v1"
    assert len(bundle["schemas"]) == 8


def test_primary_vectors_contain_two_events_and_resolve_retained_byte_digests() -> None:
    from build_finance.crypto_replay.canonical import sha256_hex
    from tests.crypto_replay.support.primary_vectors import build_primary_vector_set

    vectors = build_primary_vector_set()
    events = [document for document in vectors.documents if document["schema"] == "trading.raw-event/v1"]

    assert len(events) >= 2
    assert len({event["revision"]["availability_slot"] for event in events}) >= 2
    for event in events:
        raw_payload = vectors.resolver.resolve_bytes(event["raw_payload_sha256"])
        assert raw_payload is not None
        assert sha256_hex(raw_payload) == event["raw_payload_sha256"]


def test_primary_examples_cover_exactly_eight_schema_ids() -> None:
    from build_finance.crypto_replay.schema_definitions import PRIMARY_SCHEMA_IDS

    examples = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(EXAMPLE_ROOT.glob("*.json"))]
    assert len(examples) == 8
    assert {document["schema"] for document in examples} == set(PRIMARY_SCHEMA_IDS)
