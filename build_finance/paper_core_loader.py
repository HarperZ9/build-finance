"""Strict local disk adapter for the offline paper-core replay envelope."""

from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any, cast

from build_finance.crypto_replay.admission import AdmissionBatch
from build_finance.crypto_replay.canonical import canonical_json_bytes, parse_canonical_record, sha256_hex
from build_finance.crypto_replay.content_ids import compute_content_id, verify_content_id
from build_finance.crypto_replay.local_fixture import CapturedFixture
from build_finance.live_paper.profiles import PaperKernelProfiles
from build_finance.live_paper.resolver import EvidenceResolver

_EXPECTED_ENVELOPE = {
    "layout": "content-addressed-v1",
    "model_signal_mode": "DISABLED",
    "paper_core_distribution": "build-finance-paper-core",
    "paper_core_version": "1.1.0",
    "schema": "build-finance.paper-core.replay-envelope/v1",
}
_EXPECTED_ENVELOPE_BYTES = canonical_json_bytes(_EXPECTED_ENVELOPE)
_ENVELOPE_ROOT = "replay-envelope"
_MAX_RECORD_BYTES = 2 * 1024 * 1024
_MAX_PROFILE_BYTES = 2 * 1024 * 1024
_MAX_DIGEST_BYTES = 32 * 1024 * 1024
_READ_CHUNK_SIZE = 1024 * 1024
_O_BINARY = int(vars(os).get("O_BINARY", 0))
_O_CLOEXEC = int(vars(os).get("O_CLOEXEC", 0))
_O_NOFOLLOW = int(vars(os).get("O_NOFOLLOW", 0))
_FILE_ATTRIBUTE_REPARSE_POINT = 0x400


@dataclass(frozen=True, slots=True)
class ReplayEnvelopeContext:
    """Closed paper-core inputs loaded from exact replay-envelope bytes."""

    run_receipt_record: bytes
    resolver: EvidenceResolver
    profiles: PaperKernelProfiles

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_receipt_record", bytes(self.run_receipt_record))


@dataclass(frozen=True, slots=True)
class _FileIdentity:
    device: int
    inode: int
    mode_type: int
    size: int
    modified_ns: int


class _DiskReplayResolver:
    """Resolve only fixed content-addressed members below one replay envelope."""

    __slots__ = ("_root_path",)

    def __init__(self, root_path: str) -> None:
        self._root_path = root_path

    def resolve_record(self, content_id: str) -> bytes:
        _require_sha256_key(content_id, "record ContentID")
        record = _read_member(
            self._root_path,
            f"{_ENVELOPE_ROOT}/records/{content_id}.json",
            limit=_MAX_RECORD_BYTES,
            label="self-addressed record",
        )
        try:
            document = parse_canonical_record(record)
            valid = verify_content_id(document)
            actual = compute_content_id(document)
        except Exception as error:  # noqa: BLE001 - normalize all malformed record failures.
            raise ValueError(f"self-addressed record {content_id} is malformed: {error}") from error
        if not valid or actual != content_id:
            raise ValueError(f"self-addressed record {content_id} does not match its ContentID")
        return record

    def resolve_bytes(self, sha256: str) -> bytes:
        _require_sha256_key(sha256, "byte SHA-256")
        payload = _read_member(
            self._root_path,
            f"{_ENVELOPE_ROOT}/bytes/{sha256}.bin",
            limit=_MAX_DIGEST_BYTES,
            label="digest-addressed bytes",
        )
        if sha256_hex(payload) != sha256:
            raise ValueError(f"digest-addressed bytes {sha256} do not match their filename digest")
        return payload


def load_replay_envelope_context(
    fixture_root: Path,
    captured: CapturedFixture,
    admission: AdmissionBatch,
) -> ReplayEnvelopeContext:
    """Load exact disk replay authority for an already captured and admitted fixture."""

    root_path = _validated_root_path(fixture_root, captured)
    _require_admitted(admission)
    _require_current_paper_core_version()
    envelope = _read_member(
        root_path,
        f"{_ENVELOPE_ROOT}/envelope.json",
        limit=_MAX_RECORD_BYTES,
        label="replay envelope",
    )
    if envelope != _EXPECTED_ENVELOPE_BYTES:
        raise ValueError("replay envelope bytes do not match the fixed v1 disabled-model contract")
    run_receipt_record = _read_member(
        root_path,
        f"{_ENVELOPE_ROOT}/run-receipt.json",
        limit=_MAX_RECORD_BYTES,
        label="run receipt record",
    )
    run_receipt = _verified_run_receipt(run_receipt_record)
    resolver = _DiskReplayResolver(root_path)
    risk_config_id = run_receipt.get("validated_config_sha256")
    if not isinstance(risk_config_id, str):
        raise ValueError("run receipt does not root a replay-risk-config record")
    if captured.manifest_payload is None:
        raise ValueError("captured fixture did not retain exact fixture manifest bytes")
    profiles = PaperKernelProfiles(
        normalization_profile_record=captured.manifest_payload,
        feature_profile_record=_read_profile(root_path, "feature.bin"),
        algorithm_profile_records=(_read_profile(root_path, "algorithm-0.bin"),),
        model_validation_profile_record=_read_profile(root_path, "model-validation.bin"),
        fusion_profile_record=_read_profile(root_path, "fusion.bin"),
        risk_config_record=resolver.resolve_record(risk_config_id),
        fill_profile_record=_read_profile(root_path, "fill.bin"),
    )
    return ReplayEnvelopeContext(
        run_receipt_record=run_receipt_record,
        resolver=cast(EvidenceResolver, resolver),
        profiles=profiles,
    )


def _validated_root_path(fixture_root: Path, captured: CapturedFixture) -> str:
    if not isinstance(fixture_root, Path):
        raise TypeError("load_replay_envelope_context requires an explicit pathlib.Path fixture_root")
    root_path = os.path.abspath(os.fspath(fixture_root))
    if captured.root != fixture_root or captured.root_path != root_path:
        raise ValueError("fixture_root must exactly match the captured fixture root")
    try:
        metadata = os.lstat(root_path)
    except OSError as error:
        raise ValueError(f"fixture root cannot be classified: {error}") from error
    if _is_link_or_reparse(metadata) or not stat.S_ISDIR(metadata.st_mode):
        raise ValueError("fixture root must be a local non-linked directory")
    return root_path


def _require_admitted(admission: AdmissionBatch) -> None:
    if not isinstance(admission, AdmissionBatch):
        raise TypeError("load_replay_envelope_context requires an AdmissionBatch")
    if admission.status != "ADMITTED" or admission.reason_codes:
        raise ValueError("replay envelope requires an admitted source fixture")
    if not admission.candidates or len(admission.candidates) != len(admission.source_receipt_records):
        raise ValueError("replay envelope requires paired admitted candidates and source receipts")


def _require_current_paper_core_version() -> None:
    manifest_path = resources.files("build_finance.live_paper").joinpath("paper_core_manifest.json")
    manifest = json.loads(manifest_path.read_bytes().decode("utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("paper-core manifest is malformed")
    if manifest.get("distribution_name") != _EXPECTED_ENVELOPE["paper_core_distribution"]:
        raise ValueError("paper-core distribution does not match replay envelope contract")
    if manifest.get("distribution_version") != _EXPECTED_ENVELOPE["paper_core_version"]:
        raise ValueError("paper-core version does not match replay envelope contract")


def _verified_run_receipt(record: bytes) -> dict[str, Any]:
    try:
        run_receipt = parse_canonical_record(record)
        valid = verify_content_id(run_receipt)
    except Exception as error:  # noqa: BLE001 - normalize all malformed run receipt failures.
        raise ValueError(f"run receipt record is malformed: {error}") from error
    if not valid:
        raise ValueError("run receipt record self-ID does not match its canonical body")
    if (
        run_receipt.get("model_signal_mode") != "DISABLED"
        or run_receipt.get("model_registry_sha256") is not None
        or run_receipt.get("model_signal_manifest_sha256") is not None
    ):
        raise ValueError("run receipt must bind disabled model mode with no model bodies")
    return run_receipt


def _read_profile(root_path: str, filename: str) -> bytes:
    return _read_member(
        root_path,
        f"{_ENVELOPE_ROOT}/profiles/{filename}",
        limit=_MAX_PROFILE_BYTES,
        label="profile snapshot",
    )


def _read_member(root_path: str, relative_path: str, *, limit: int, label: str) -> bytes:
    absolute_path = _absolute_member(root_path, relative_path)
    components = tuple(relative_path.split("/"))
    _require_local_prefixes(root_path, components, label)
    try:
        before = os.lstat(absolute_path)
    except OSError as error:
        raise FileNotFoundError(f"{label} {relative_path} cannot be classified: {error}") from error
    if _is_link_or_reparse(before):
        raise OSError(f"{label} {relative_path} is a link/reparse member")
    if not stat.S_ISREG(before.st_mode):
        raise OSError(f"{label} {relative_path} is not a regular file")
    if int(before.st_size) > limit:
        raise ValueError(f"{label} {relative_path} exceeds the bounded read size")

    flags = os.O_RDONLY | _O_BINARY | _O_CLOEXEC | _O_NOFOLLOW
    try:
        fd = os.open(absolute_path, flags)
    except OSError as error:
        raise OSError(f"{label} {relative_path} cannot be opened without following links: {error}") from error
    chunks: list[bytes] = []
    byte_count = 0
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or _identity(opened) != _identity(before):
            raise OSError(f"{label} {relative_path} changed identity before read")
        while True:
            chunk = os.read(fd, min(_READ_CHUNK_SIZE, limit + 1 - byte_count))
            if not chunk:
                break
            chunks.append(chunk)
            byte_count += len(chunk)
            if byte_count > limit:
                raise ValueError(f"{label} {relative_path} exceeds the bounded read size")
        after_open = os.fstat(fd)
        if _identity(after_open) != _identity(before) or byte_count != int(after_open.st_size):
            raise OSError(f"{label} {relative_path} changed while being read")
    finally:
        os.close(fd)

    try:
        after = os.lstat(absolute_path)
    except OSError as error:
        raise OSError(f"{label} {relative_path} disappeared after read: {error}") from error
    if _is_link_or_reparse(after) or _identity(after) != _identity(before):
        raise OSError(f"{label} {relative_path} changed identity after read")
    return b"".join(chunks)


def _absolute_member(root_path: str, relative_path: str) -> str:
    components = relative_path.split("/")
    if any(component in {"", ".", ".."} for component in components):
        raise ValueError(f"unsafe replay envelope path: {relative_path!r}")
    absolute_path = os.path.abspath(os.path.join(root_path, *components))
    try:
        common = os.path.commonpath((os.path.normcase(root_path), os.path.normcase(absolute_path)))
    except ValueError as error:
        raise ValueError("replay envelope path is outside the fixture root") from error
    if common != os.path.normcase(root_path):
        raise ValueError("replay envelope path escapes the fixture root")
    return absolute_path


def _require_local_prefixes(root_path: str, components: tuple[str, ...], label: str) -> None:
    prefix = root_path
    for component in components[:-1]:
        prefix = os.path.join(prefix, component)
        try:
            metadata = os.lstat(prefix)
        except OSError as error:
            raise FileNotFoundError(f"{label} path prefix cannot be classified: {error}") from error
        if _is_link_or_reparse(metadata):
            raise OSError(f"{label} path prefix is a link/reparse member")
        if not stat.S_ISDIR(metadata.st_mode):
            raise OSError(f"{label} path prefix is not a directory")


def _require_sha256_key(value: str, label: str) -> None:
    if not isinstance(value, str) or len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{label} must be a lowercase 64-hex key")


def _is_link_or_reparse(metadata: os.stat_result) -> bool:
    attributes = int(getattr(metadata, "st_file_attributes", 0))
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & _FILE_ATTRIBUTE_REPARSE_POINT)


def _identity(metadata: os.stat_result) -> _FileIdentity:
    return _FileIdentity(
        device=int(metadata.st_dev),
        inode=int(metadata.st_ino),
        mode_type=stat.S_IFMT(metadata.st_mode),
        size=int(metadata.st_size),
        modified_ns=int(metadata.st_mtime_ns),
    )


__all__ = ["ReplayEnvelopeContext", "load_replay_envelope_context"]

