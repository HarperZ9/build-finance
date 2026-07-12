"""Strict in-memory builders for synthetic crypto-replay contract vectors."""

from __future__ import annotations

from collections.abc import Mapping

from build_finance.crypto_replay.canonical import (
    JsonObject,
    JsonValue,
    canonical_record_bytes,
    parse_canonical_record,
    sha256_hex,
)
from build_finance.crypto_replay.content_ids import compute_content_id, seal_content_id, verify_content_id
from build_finance.crypto_replay.schema_model import Assurance, ResolvedContent
from build_finance.crypto_replay.schema_registry import require_valid_contract


class InMemoryResolver:
    """Resolve self-addressed records and exact retained bytes in separate maps."""

    __slots__ = ("_bytes_by_sha256", "_objects_by_content_id")

    def __init__(self) -> None:
        self._objects_by_content_id: dict[str, ResolvedContent] = {}
        self._bytes_by_sha256: dict[str, bytes] = {}

    @property
    def content_ids(self) -> tuple[str, ...]:
        return tuple(self._objects_by_content_id)

    @property
    def byte_sha256s(self) -> tuple[str, ...]:
        return tuple(self._bytes_by_sha256)

    @property
    def resolved_contents(self) -> tuple[ResolvedContent, ...]:
        return tuple(self._objects_by_content_id.values())

    def resolve_object(self, content_id: str) -> ResolvedContent | None:
        return self._objects_by_content_id.get(content_id)

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

    def retain_record(self, record: bytes, *, assurance: Assurance) -> JsonObject:
        """Retain one complete canonical LF record at its verified ContentID."""
        document = parse_canonical_record(record)
        if canonical_record_bytes(document) != record:
            raise ValueError("content preimage is not the complete canonical LF record")
        if not verify_content_id(document):
            raise ValueError("content preimage has an invalid self-ID")
        content_id = compute_content_id(document)
        resolved = ResolvedContent(record=record, document=document, assurance=assurance)
        existing = self._objects_by_content_id.get(content_id)
        if existing is not None and existing.record != record:
            raise ValueError(f"duplicate ContentID {content_id!r} has different bytes")
        if existing is not None and existing != resolved:
            raise ValueError(f"duplicate ContentID {content_id!r} has different assurance or content")
        self.retain_payload(record)
        self._objects_by_content_id[content_id] = resolved
        return document


def build_primary_document(
    document: Mapping[str, JsonValue],
    resolver: InMemoryResolver,
) -> JsonObject:
    """Seal, serialize, reparse, validate, and retain one primary record."""
    sealed = seal_content_id(document)
    reparsed = parse_canonical_record(canonical_record_bytes(sealed))
    schema_id = reparsed["schema"]
    if not isinstance(schema_id, str):
        raise TypeError("primary schema tag must be a string")
    require_valid_contract(reparsed, expected_schema=schema_id)
    return resolver.retain_record(canonical_record_bytes(reparsed), assurance="SCHEMA_VALID")


def build_digest_only_supporting_document(
    document: Mapping[str, JsonValue],
    resolver: InMemoryResolver,
) -> JsonObject:
    """Seal and retain a supporting preimage without asserting its T02 schema."""
    sealed = seal_content_id(document)
    reparsed = parse_canonical_record(canonical_record_bytes(sealed))
    return resolver.retain_record(canonical_record_bytes(reparsed), assurance="DIGEST_ONLY")


def synthetic_payload(label: str) -> bytes:
    """Return clearly synthetic retained bytes for a contract-only digest field."""
    if not label or "\n" in label or "\r" in label:
        raise ValueError("synthetic payload label must be one non-empty line")
    return f"SYNTHETIC_T01_CONTRACT_VECTOR\n{label}\n".encode("ascii")
