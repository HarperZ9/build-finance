"""T01 RED contract for the sealed primary bundle and resolving vectors."""

from __future__ import annotations

import hashlib
import importlib.resources
import json
from pathlib import Path
from typing import Any

EXAMPLE_ROOT = Path(__file__).parent / "resources" / "primary-v1" / "examples"
EXPECTED_PRIMARY_BUNDLE_SHA256 = "3996eb230f078f5a34d295208974afe8131439ccd7bbb87da8dfa94631148ff8"


def _utf16_sort_key(value: str) -> bytes:
    return value.encode("utf-16-be", errors="strict")


def _independent_jcs_bytes(value: Any) -> bytes:
    """Serialize the bundle without importing the runtime canonicalizer."""
    if value is None:
        return b"null"
    if value is True:
        return b"true"
    if value is False:
        return b"false"
    if isinstance(value, int):
        return str(value).encode("ascii")
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    if isinstance(value, list):
        return b"[" + b",".join(_independent_jcs_bytes(item) for item in value) + b"]"
    if isinstance(value, dict):
        fields = (
            _independent_jcs_bytes(key) + b":" + _independent_jcs_bytes(value[key])
            for key in sorted(value, key=_utf16_sort_key)
        )
        return b"{" + b",".join(fields) + b"}"
    raise TypeError(f"unsupported independent JCS value: {type(value)!r}")


def _parse_independent(payload: bytes) -> Any:
    def object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key!r}")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise ValueError(f"forbidden JSON constant: {value}")

    return json.loads(
        payload.decode("utf-8", errors="strict"),
        object_pairs_hook=object_without_duplicates,
        parse_constant=reject_constant,
    )


EXPECTED_ALIASES = [
    {
        "name": "CausalDigest",
        "json_type": "string",
        "pattern": "^[0-9a-f]{64}$",
        "minimum": None,
        "maximum": None,
        "scale": None,
    },
    {
        "name": "ContentID",
        "json_type": "string",
        "pattern": "^[0-9a-f]{64}$",
        "minimum": None,
        "maximum": None,
        "scale": None,
    },
    {
        "name": "i128s",
        "json_type": "string",
        "pattern": "^(0|-?[1-9][0-9]*)$",
        "minimum": "-170141183460469231731687303715884105728",
        "maximum": "170141183460469231731687303715884105727",
        "scale": None,
    },
    {
        "name": "sq18s",
        "json_type": "string",
        "pattern": "^(0|-?[1-9][0-9]*)$",
        "minimum": "-170141183460469231731687303715884105728",
        "maximum": "170141183460469231731687303715884105727",
        "scale": "1000000000000000000",
    },
    {
        "name": "u64s",
        "json_type": "string",
        "pattern": "^(0|[1-9][0-9]*)$",
        "minimum": "0",
        "maximum": "18446744073709551615",
        "scale": None,
    },
    {
        "name": "uints",
        "json_type": "string",
        "pattern": "^(0|[1-9][0-9]*)$",
        "minimum": "0",
        "maximum": None,
        "scale": None,
    },
    {
        "name": "uq18s",
        "json_type": "string",
        "pattern": "^(0|[1-9][0-9]*)$",
        "minimum": "0",
        "maximum": "1000000000000000000",
        "scale": "1000000000000000000",
    },
]


def test_primary_bundle_hash_is_locked() -> None:
    package = importlib.resources.files("build_finance.crypto_replay")
    bundle_record = package.joinpath("resources/primary-schema-bundle.json").read_bytes()
    digest_record = package.joinpath("resources/primary-schema-bundle.sha256").read_bytes()

    assert bundle_record.endswith(b"\n") and not bundle_record.endswith(b"\n\n")
    payload = bundle_record[:-1]
    bundle = _parse_independent(payload)
    independent_payload = _independent_jcs_bytes(bundle)
    assert independent_payload == payload
    assert hashlib.sha256(independent_payload).hexdigest() == EXPECTED_PRIMARY_BUNDLE_SHA256
    assert digest_record == EXPECTED_PRIMARY_BUNDLE_SHA256.encode("ascii") + b"\n"
    assert set(bundle) == {"schema", "jcs_profile", "protocol_constants", "aliases", "schemas"}
    assert bundle["schema"] == "build-finance.primary-schema-bundle/v1"
    assert bundle["jcs_profile"] == "RFC8785_INTEGER_AUTHORITY_V1"
    assert bundle["protocol_constants"] == {
        "MAX_RUN_CLOSURE_PROOF_ROWS_V0": "1000000",
        "MAX_U64_V0": "18446744073709551615",
    }
    assert bundle["aliases"] == EXPECTED_ALIASES
    assert len(bundle["schemas"]) == 8
    assert [row["contract_schema"] for row in bundle["schemas"]] == sorted(
        (row["contract_schema"] for row in bundle["schemas"]),
        key=lambda value: value.encode("utf-8"),
    )
    for row in bundle["schemas"]:
        assert set(row) == {"contract_schema", "json_schema_id", "family", "self_id_field", "schema_sha256"}
        assert row["family"] == "PRIMARY"
        assert isinstance(row["self_id_field"], str) and row["self_id_field"]
        contract_name, version = row["contract_schema"].removeprefix("trading.").split("/", maxsplit=1)
        assert row["json_schema_id"] == f"urn:build-finance:contract:{contract_name}:{version}"
        filename = f"{contract_name}-{version}.schema.json"
        schema_record = package.joinpath(f"resources/schemas/{filename}").read_bytes()
        assert schema_record.endswith(b"\n") and not schema_record.endswith(b"\n\n")
        schema_document = _parse_independent(schema_record[:-1])
        assert _independent_jcs_bytes(schema_document) + b"\n" == schema_record
        assert schema_document["$id"] == row["json_schema_id"]
        assert schema_document["x-contract-schema"] == row["contract_schema"]
        assert hashlib.sha256(schema_record[:-1]).hexdigest() == row["schema_sha256"]


def test_primary_vectors_contain_two_events_and_resolve_retained_byte_digests() -> None:
    from tests.crypto_replay.support.primary_vectors import build_primary_vector_set

    vectors = build_primary_vector_set()
    events = [document for document in vectors.documents if document["schema"] == "trading.raw-event/v1"]

    assert len(events) >= 2
    assert len({event["revision"]["availability_slot"] for event in events}) >= 2
    for event in events:
        raw_payload = vectors.resolver.resolve_bytes(event["raw_payload_sha256"])
        assert raw_payload is not None
        assert hashlib.sha256(raw_payload).hexdigest() == event["raw_payload_sha256"]


def test_primary_examples_cover_exactly_eight_schema_ids() -> None:
    from build_finance.crypto_replay.schema_definitions import PRIMARY_SCHEMA_IDS

    examples = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(EXAMPLE_ROOT.glob("*.json"))]
    assert len(examples) == 8
    assert {document["schema"] for document in examples} == set(PRIMARY_SCHEMA_IDS)
