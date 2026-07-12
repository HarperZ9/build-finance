"""Strict in-memory builders for synthetic crypto-replay contract vectors."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from build_finance.crypto_replay.canonical import (
    JsonObject,
    JsonValue,
    canonical_record_bytes,
    parse_canonical_record,
    sha256_hex,
)
from build_finance.crypto_replay.content_ids import compute_content_id, seal_content_id, verify_content_id
from build_finance.crypto_replay.schema_definitions import CONTRACT_SPECS_BY_SCHEMA
from build_finance.crypto_replay.schema_model import Assurance, ContractFamily, ResolvedContent
from build_finance.crypto_replay.schema_registry import require_valid_contract


@dataclass(frozen=True, slots=True)
class _RetainedRecord:
    record: bytes
    assurance: Assurance


class InMemoryResolver:
    """Resolve self-addressed records and exact retained bytes in separate maps."""

    __slots__ = ("_bytes_by_sha256", "_objects_by_content_id")

    def __init__(self) -> None:
        self._objects_by_content_id: dict[str, _RetainedRecord] = {}
        self._bytes_by_sha256: dict[str, bytes] = {}

    @property
    def content_ids(self) -> tuple[str, ...]:
        return tuple(self._objects_by_content_id)

    @property
    def byte_sha256s(self) -> tuple[str, ...]:
        return tuple(self._bytes_by_sha256)

    @property
    def resolved_contents(self) -> tuple[ResolvedContent, ...]:
        return tuple(self._resolved_content(retained) for retained in self._objects_by_content_id.values())

    def resolve_object(self, content_id: str) -> ResolvedContent | None:
        retained = self._objects_by_content_id.get(content_id)
        return None if retained is None else self._resolved_content(retained)

    def resolve_bytes(self, sha256: str) -> bytes | None:
        return self._bytes_by_sha256.get(sha256)

    def retain_bytes(self, sha256: str, payload: bytes) -> None:
        """Retain exact bytes at their SHA-256 key, rejecting collisions and mismatches."""
        retained = bytes(payload)
        existing = self._bytes_by_sha256.get(sha256)
        if existing is not None and existing != retained:
            raise ValueError(f"duplicate retained-byte SHA-256 {sha256!r} has different bytes")
        if sha256_hex(retained) != sha256:
            raise ValueError("retained-byte SHA-256 does not match the supplied bytes")
        self._bytes_by_sha256[sha256] = retained

    def retain_payload(self, payload: bytes) -> str:
        """Retain exact bytes and return their independently keyed SHA-256."""
        digest = sha256_hex(payload)
        self.retain_bytes(digest, payload)
        return digest

    def retain_record(self, record: bytes, *, assurance: Assurance = "SCHEMA_VALID") -> JsonObject:
        """Validate and retain one primary record with internally derived assurance."""
        if assurance not in ("DIGEST_ONLY", "SCHEMA_VALID"):
            raise ValueError(f"invalid assurance: {assurance!r}")
        if assurance != "SCHEMA_VALID":
            raise ValueError("DIGEST_ONLY retention is restricted to the supporting builder")
        return self._retain_record(record, assurance="SCHEMA_VALID", expected_family="PRIMARY")

    @staticmethod
    def _resolved_content(retained: _RetainedRecord) -> ResolvedContent:
        return ResolvedContent(
            record=retained.record,
            document=parse_canonical_record(retained.record),
            assurance=retained.assurance,
        )

    def _retain_digest_only_supporting_record(self, record: bytes) -> JsonObject:
        return self._retain_record(record, assurance="DIGEST_ONLY", expected_family="SUPPORTING")

    def _retain_record(
        self,
        record: bytes,
        *,
        assurance: object,
        expected_family: ContractFamily,
    ) -> JsonObject:
        if assurance not in ("DIGEST_ONLY", "SCHEMA_VALID"):
            raise ValueError(f"invalid assurance: {assurance!r}")
        if (assurance, expected_family) not in {
            ("SCHEMA_VALID", "PRIMARY"),
            ("DIGEST_ONLY", "SUPPORTING"),
        }:
            raise ValueError("assurance does not match the internally owned contract family")

        retained_record = bytes(record)
        document = parse_canonical_record(retained_record)
        if canonical_record_bytes(document) != retained_record:
            raise ValueError("content preimage is not the complete canonical LF record")
        if not verify_content_id(document):
            raise ValueError("content preimage has an invalid self-ID")
        schema_id = document["schema"]
        if not isinstance(schema_id, str):
            raise ValueError("content preimage requires a string schema tag")
        family = CONTRACT_SPECS_BY_SCHEMA[schema_id].family
        if family != expected_family:
            raise ValueError(f"record family is {family}, expected {expected_family}")
        if assurance == "SCHEMA_VALID":
            require_valid_contract(document, expected_schema=schema_id)

        content_id = compute_content_id(document)
        retained = _RetainedRecord(record=retained_record, assurance=assurance)
        record_sha256 = sha256_hex(retained_record)
        existing = self._objects_by_content_id.get(content_id)
        if existing is not None and existing.record != retained_record:
            raise ValueError(f"duplicate ContentID {content_id!r} has different bytes")
        if existing is not None and existing != retained:
            raise ValueError(f"duplicate ContentID {content_id!r} has different assurance or content")
        existing_bytes = self._bytes_by_sha256.get(record_sha256)
        if existing_bytes is not None and existing_bytes != retained_record:
            raise ValueError(f"duplicate retained-byte SHA-256 {record_sha256!r} has different bytes")

        self._bytes_by_sha256[record_sha256] = retained_record
        self._objects_by_content_id[content_id] = retained
        return parse_canonical_record(retained_record)


def build_primary_document(
    document: Mapping[str, JsonValue],
    resolver: InMemoryResolver,
) -> JsonObject:
    """Seal, serialize, reparse, validate, and retain one primary record."""
    sealed = seal_content_id(document)
    return resolver.retain_record(canonical_record_bytes(sealed))


def build_digest_only_supporting_document(
    document: Mapping[str, JsonValue],
    resolver: InMemoryResolver,
) -> JsonObject:
    """Seal and retain a supporting preimage without asserting its T02 schema."""
    sealed = seal_content_id(document)
    return resolver._retain_digest_only_supporting_record(canonical_record_bytes(sealed))


def synthetic_payload(label: str) -> bytes:
    """Return clearly synthetic retained bytes for a contract-only digest field."""
    if not label or "\n" in label or "\r" in label:
        raise ValueError("synthetic payload label must be one non-empty line")
    return f"SYNTHETIC_T01_CONTRACT_VECTOR\n{label}\n".encode("ascii")
