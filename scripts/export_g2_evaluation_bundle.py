"""Export one reproducible synthetic G2 PAPER ONLY evaluation bundle."""

# ruff: noqa: E402 - direct script execution must prefer this source checkout.

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import cast

ROOT = Path(__file__).resolve().parents[1]
while str(ROOT) in sys.path:
    sys.path.remove(str(ROOT))
sys.path.insert(0, str(ROOT))

import build_finance
from build_finance.crypto_replay.admission import admit_local_fixture
from build_finance.crypto_replay.canonical import JsonObject, canonical_record_bytes, parse_canonical_json
from build_finance.crypto_replay.local_fixture import capture_local_fixture
from build_finance.live_paper.kernel import run_offline_paper_kernel
from build_finance.live_paper.projections import kernel_result_canonical_bytes
from build_finance.live_paper.run_input_builder import build_verified_run_inputs
from build_finance.paper_core_loader import load_replay_envelope_context
from tests.live_paper.support.g2_disk_bundle import write_g2_disk_bundle

CHECKSUM_MANIFEST_NAME = "SHA256SUMS"
KERNEL_PROJECTION_NAME = "kernel-projection.json"
BUILD_FINANCE_ROOT = Path(cast(str, build_finance.__file__)).resolve().parent
_FILE_ATTRIBUTE_REPARSE_POINT = 0x400


class ExportError(RuntimeError):
    """The synthetic evaluation bundle could not be exported safely."""


@dataclass(frozen=True, slots=True)
class EvaluationBundleExport:
    """Stable paths produced by one successful local evaluation export."""

    destination: Path
    fixture_root: Path
    checksum_manifest: Path
    kernel_projection: Path


def _empty_destination(destination: Path) -> Path:
    destination = destination.absolute()
    try:
        metadata = os.lstat(destination)
    except FileNotFoundError:
        destination.mkdir(parents=True)
        return destination
    if _is_link_or_reparse(metadata):
        raise ExportError(f"destination must not be a link/reparse path: {destination}")
    if not stat.S_ISDIR(metadata.st_mode) or any(destination.iterdir()):
        raise ExportError(f"destination must be an empty directory: {destination}")
    return destination


def _is_link_or_reparse(metadata: os.stat_result) -> bool:
    attributes = int(getattr(metadata, "st_file_attributes", 0))
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & _FILE_ATTRIBUTE_REPARSE_POINT)


def _projection_document(result_payload: JsonObject) -> JsonObject:
    projection = result_payload.get("projection")
    closure = result_payload.get("closure")
    if not isinstance(projection, dict) or not isinstance(closure, dict):
        raise ExportError("kernel result did not contain projection and closure objects")
    if closure.get("status") != "CLOSED" or closure.get("reason_codes") != []:
        raise ExportError("synthetic evaluation replay did not close cleanly")
    model_rows = projection.get("model_validation")
    if (
        not isinstance(model_rows, list)
        or len(model_rows) != 2
        or not all(isinstance(row, Mapping) for row in model_rows)
        or [(row.get("disposition"), row.get("reason_code")) for row in model_rows]
        != [("ABSTAIN", "MODEL_DISABLED"), ("ABSTAIN", "MODEL_DISABLED")]
    ):
        raise ExportError("synthetic evaluation replay did not retain deterministic model abstention")
    return cast(
        JsonObject,
        {
            "closure_status": "CLOSED",
            "data_classification": "SYNTHETIC",
            "execution": "SIMULATED",
            "mode": "PAPER_ONLY",
            "model_inference": "DISABLED_ABSTAIN",
            "profitability_claim": False,
            "projection": projection,
            "schema": "build-finance.live-paper.g2-evaluation-projection/v1",
        },
    )


def _write_checksum_manifest(destination: Path) -> Path:
    manifest = destination / CHECKSUM_MANIFEST_NAME
    rows: list[tuple[str, Path]] = []
    for path in destination.rglob("*"):
        if path.is_file() and path != manifest:
            rows.append((path.relative_to(destination).as_posix(), path))
    payload = b"".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {relative}\n".encode()
        for relative, path in sorted(rows)
    )
    manifest.write_bytes(payload)
    return manifest


def _safe_checksum_path(relative: str) -> PurePosixPath:
    path = PurePosixPath(relative)
    if (
        not relative
        or "\\" in relative
        or "\0" in relative
        or path.is_absolute()
        or path.as_posix() != relative
        or any(part in {"", ".", ".."} or ":" in part for part in path.parts)
        or any(part.rstrip(" .") != part for part in path.parts)
        or relative == CHECKSUM_MANIFEST_NAME
    ):
        raise ExportError(f"checksum manifest contains an unsafe relative path: {relative!r}")
    return path


def _checksum_rows(payload: bytes) -> list[tuple[str, str]]:
    if not payload.endswith(b"\n") or b"\r" in payload:
        raise ExportError("checksum manifest must be LF-terminated")
    lines = payload[:-1].split(b"\n")
    if not lines or lines == [b""]:
        raise ExportError("checksum manifest must contain at least one row")
    rows: list[tuple[str, str]] = []
    for line in lines:
        if len(line) < 67 or line[64:66] != b"  ":
            raise ExportError("checksum manifest row must be '<lowercase-sha256>  <relative-path>'")
        try:
            digest = line[:64].decode("ascii")
            relative = line[66:].decode("utf-8", errors="strict")
        except UnicodeDecodeError as error:
            raise ExportError(f"checksum manifest row encoding is invalid: {error}") from error
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise ExportError("checksum manifest digest must be lowercase 64-hex")
        _safe_checksum_path(relative)
        rows.append((digest, relative))
    relative_paths = [relative for _digest, relative in rows]
    normalized = [os.path.normcase(relative) for relative in relative_paths]
    if relative_paths != sorted(relative_paths) or len(set(normalized)) != len(normalized):
        raise ExportError("checksum manifest paths must be sorted and unique")
    return rows


def _regular_exported_files(destination: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for current, directory_names, file_names in os.walk(destination, followlinks=False):
        current_path = Path(current)
        for name in directory_names:
            path = current_path / name
            metadata = os.lstat(path)
            if _is_link_or_reparse(metadata) or not stat.S_ISDIR(metadata.st_mode):
                raise ExportError(f"evaluation bundle contains a linked/reparse directory: {path}")
        for name in file_names:
            path = current_path / name
            metadata = os.lstat(path)
            if _is_link_or_reparse(metadata) or not stat.S_ISREG(metadata.st_mode):
                raise ExportError(f"evaluation bundle contains a non-regular file: {path}")
            relative = path.relative_to(destination).as_posix()
            files[relative] = path
    return files


def verify_g2_evaluation_bundle(destination: Path) -> int:
    """Verify exact sorted checksum closure for one exported evaluation bundle."""

    destination = destination.absolute()
    try:
        root_metadata = os.lstat(destination)
    except FileNotFoundError as error:
        raise ExportError(f"evaluation bundle destination does not exist: {destination}") from error
    if _is_link_or_reparse(root_metadata) or not stat.S_ISDIR(root_metadata.st_mode):
        raise ExportError(f"evaluation bundle destination must be a real directory: {destination}")
    files = _regular_exported_files(destination)
    manifest = files.pop(CHECKSUM_MANIFEST_NAME, None)
    if manifest is None:
        raise ExportError("evaluation bundle checksum manifest is missing")
    rows = _checksum_rows(manifest.read_bytes())
    claimed = {relative: digest for digest, relative in rows}
    if set(claimed) != set(files):
        raise ExportError(
            "checksum manifest file set mismatch: "
            f"missing={sorted(set(files) - set(claimed))!r} extra={sorted(set(claimed) - set(files))!r}"
        )
    for relative, expected in claimed.items():
        if hashlib.sha256(files[relative].read_bytes()).hexdigest() != expected:
            raise ExportError(f"checksum mismatch: {relative}")
    return len(files)


def export_g2_evaluation_bundle(destination: Path) -> EvaluationBundleExport:
    """Materialize, replay, and seal one offline synthetic evaluation bundle."""

    destination = _empty_destination(destination)
    bundle = write_g2_disk_bundle(destination)
    captured = capture_local_fixture(bundle.fixture_root)
    admission = admit_local_fixture(captured)
    if admission.status != "ADMITTED" or admission.reason_codes:
        raise ExportError(f"synthetic fixture admission failed: {admission.status} {admission.reason_codes}")
    context = load_replay_envelope_context(bundle.fixture_root, captured, admission)
    verified = build_verified_run_inputs(
        context.run_receipt_record,
        admission.candidates,
        admission.source_receipt_records,
        context.resolver,
        context.profiles,
    )
    result = run_offline_paper_kernel(verified, context.resolver, context.profiles)
    result_document = parse_canonical_json(kernel_result_canonical_bytes(result))
    result_payload = result_document.get("result")
    if not isinstance(result_payload, dict):
        raise ExportError("kernel result payload is invalid")
    projection_path = destination / KERNEL_PROJECTION_NAME
    projection_path.write_bytes(canonical_record_bytes(_projection_document(result_payload)))
    checksum_manifest = _write_checksum_manifest(destination)
    verify_g2_evaluation_bundle(destination)
    return EvaluationBundleExport(
        destination=destination,
        fixture_root=bundle.fixture_root,
        checksum_manifest=checksum_manifest,
        kernel_projection=projection_path,
    )


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("destination", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if args.verify:
            verified_file_count = verify_g2_evaluation_bundle(args.destination)
            print(
                json.dumps(
                    {
                        "destination": str(args.destination.absolute()),
                        "status": "PASS",
                        "verified_file_count": verified_file_count,
                    },
                    separators=(",", ":"),
                    sort_keys=True,
                )
            )
            return 0
        exported = export_g2_evaluation_bundle(args.destination)
    except (ExportError, OSError, ValueError, AssertionError) as error:
        print(f"G2 evaluation export failed: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "checksum_manifest": str(exported.checksum_manifest),
                "build_finance_root": str(BUILD_FINANCE_ROOT),
                "destination": str(exported.destination),
                "fixture_root": str(exported.fixture_root),
                "kernel_projection": str(exported.kernel_projection),
            },
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
