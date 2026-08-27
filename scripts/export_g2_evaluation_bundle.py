"""Export one reproducible synthetic G2 PAPER ONLY evaluation bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

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
    if destination.exists():
        if destination.is_symlink() or not destination.is_dir() or any(destination.iterdir()):
            raise ExportError(f"destination must be an empty directory: {destination}")
    else:
        destination.mkdir(parents=True)
    return destination


def _projection_document(result_payload: JsonObject) -> JsonObject:
    projection = result_payload.get("projection")
    closure = result_payload.get("closure")
    if not isinstance(projection, dict) or not isinstance(closure, dict):
        raise ExportError("kernel result did not contain projection and closure objects")
    if closure.get("status") != "CLOSED" or closure.get("reason_codes") != []:
        raise ExportError("synthetic evaluation replay did not close cleanly")
    model_rows = projection.get("model_validation")
    if not isinstance(model_rows, list) or [row.get("disposition") for row in model_rows] != [
        "ABSTAIN",
        "ABSTAIN",
    ]:
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
    return EvaluationBundleExport(
        destination=destination,
        fixture_root=bundle.fixture_root,
        checksum_manifest=checksum_manifest,
        kernel_projection=projection_path,
    )


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        exported = export_g2_evaluation_bundle(args.destination)
    except (ExportError, OSError, ValueError, AssertionError) as error:
        print(f"G2 evaluation export failed: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "checksum_manifest": str(exported.checksum_manifest),
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
