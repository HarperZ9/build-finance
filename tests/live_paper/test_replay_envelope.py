"""Disk replay-envelope tests for the G2 offline paper core."""

from __future__ import annotations

import importlib
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from build_finance.crypto_replay.admission import admit_local_fixture
from build_finance.crypto_replay.canonical import canonical_record_bytes, parse_canonical_record
from build_finance.crypto_replay.content_ids import seal_content_id
from build_finance.crypto_replay.local_fixture import capture_local_fixture
from build_finance.live_paper.kernel import run_offline_paper_kernel
from build_finance.live_paper.run_input_builder import build_verified_run_inputs
from tests.live_paper.support.g2_disk_bundle import (
    corrupt_first_byte_payload,
    corrupt_first_record_payload,
    replace_first_byte_with_symlink,
    rewrite_envelope_mode,
    write_g2_disk_bundle,
)


def _paper_core_loader() -> Any:
    try:
        return importlib.import_module("build_finance.paper_core_loader")
    except ModuleNotFoundError as error:
        if error.name != "build_finance.paper_core_loader":
            raise
        pytest.fail(f"public paper-core replay loader is absent: {error}")


def _replace_directory_with_link(link: Path, target: Path) -> None:
    shutil.rmtree(link)
    if os.name == "nt":
        completed = subprocess.run(
            ["cmd", "/d", "/c", "mklink", "/J", os.fspath(link), os.fspath(target)],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            pytest.skip(f"Windows junction creation unavailable: {completed.stderr.strip()}")
        return
    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"directory symlink creation unavailable: {type(error).__name__}: {error}")


def test_replay_envelope_loader_builds_positive_g2_context(tmp_path: Path) -> None:
    """Breaks if the disk envelope cannot feed production admission, verification, and kernel replay."""

    bundle = write_g2_disk_bundle(tmp_path)
    captured = capture_local_fixture(bundle.fixture_root)
    admission = admit_local_fixture(captured)
    assert admission.status == "ADMITTED"
    assert admission.reason_codes == ()
    assert all(not file.relative_path.startswith("replay-envelope/") for file in captured.files)

    loader = _paper_core_loader()
    context = loader.load_replay_envelope_context(bundle.fixture_root, captured, admission)
    verified = build_verified_run_inputs(
        context.run_receipt_record,
        admission.candidates,
        admission.source_receipt_records,
        context.resolver,
        context.profiles,
    )
    result = run_offline_paper_kernel(verified, context.resolver, context.profiles)

    assert result.closure.status == "CLOSED"
    assert result.closure.reason_codes == ()
    assert tuple(row.disposition for row in result.projection.model_validation) == ("ABSTAIN", "ABSTAIN")
    assert tuple(row.reason_code for row in result.projection.model_validation) == (
        "MODEL_DISABLED",
        "MODEL_DISABLED",
    )


def test_replay_envelope_loader_rejects_admission_from_another_captured_fixture(tmp_path: Path) -> None:
    """Breaks if an admitted batch can be cross-wired to a different captured fixture and run."""

    bundle = write_g2_disk_bundle(tmp_path / "primary")
    captured = capture_local_fixture(bundle.fixture_root)

    foreign_bundle = write_g2_disk_bundle(tmp_path / "foreign")
    foreign_manifest_path = foreign_bundle.fixture_root / "manifest.json"
    foreign_manifest = parse_canonical_record(foreign_manifest_path.read_bytes())
    foreign_manifest.pop("fixture_manifest_sha256")
    foreign_manifest["initial_quote_atoms"] = "2000000"
    foreign_manifest_path.write_bytes(canonical_record_bytes(seal_content_id(foreign_manifest)))
    foreign_captured = capture_local_fixture(foreign_bundle.fixture_root)
    foreign_admission = admit_local_fixture(foreign_captured)

    assert foreign_admission.status == "ADMITTED"
    assert foreign_admission.reason_codes == ()
    assert captured.fixture_manifest_sha256 != foreign_captured.fixture_manifest_sha256

    loader = _paper_core_loader()
    with pytest.raises(ValueError, match="captured fixture"):
        loader.load_replay_envelope_context(bundle.fixture_root, captured, foreign_admission)


def test_replay_envelope_member_read_rejects_parent_replacement_before_final_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Breaks if a fallback path read accepts a replaced prefix with the same final file identity."""

    bundle = write_g2_disk_bundle(tmp_path)
    captured = capture_local_fixture(bundle.fixture_root)
    admission = admit_local_fixture(captured)
    assert admission.status == "ADMITTED"

    loader = _paper_core_loader()
    monkeypatch.setattr(loader, "_can_use_openat", lambda: False, raising=False)
    profiles_root = bundle.fixture_root / "replay-envelope" / "profiles"
    fill_profile = profiles_root / "fill.bin"
    outside_profiles = tmp_path / "outside-profiles"
    outside_profiles.mkdir()
    os.link(fill_profile, outside_profiles / "fill.bin")

    original_open = loader.os.open
    fill_path = os.path.normcase(os.path.abspath(fill_profile))
    replaced = False

    def swap_parent_before_final_open(path: Any, *args: Any, **kwargs: Any) -> Any:
        nonlocal replaced
        candidate = os.path.normcase(os.path.abspath(os.fspath(path)))
        if not replaced and candidate == fill_path:
            _replace_directory_with_link(profiles_root, outside_profiles)
            replaced = True
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(loader.os, "open", swap_parent_before_final_open)
    with pytest.raises(OSError, match="path prefix identity changed"):
        loader.load_replay_envelope_context(bundle.fixture_root, captured, admission)
    assert replaced


@pytest.mark.parametrize(
    ("case", "expected_fragment"),
    (
        ("digest_mismatched_bytes", "digest-addressed bytes"),
        ("content_mismatched_record", "self-addressed record"),
        ("linked_envelope_member", "link"),
        ("model_mode_enabled", "replay envelope"),
    ),
)
def test_replay_envelope_loader_fails_closed_before_kernel(
    tmp_path: Path,
    case: str,
    expected_fragment: str,
) -> None:
    """Breaks if malformed disk authority can reach kernel execution."""

    bundle = write_g2_disk_bundle(tmp_path)
    if case == "digest_mismatched_bytes":
        corrupt_first_byte_payload(bundle)
    elif case == "content_mismatched_record":
        corrupt_first_record_payload(bundle)
    elif case == "linked_envelope_member":
        if not replace_first_byte_with_symlink(bundle, tmp_path):
            pytest.skip("symlink/reparse replacement is not supported by this filesystem")
    else:
        rewrite_envelope_mode(bundle, "CACHED_FIXTURES")

    captured = capture_local_fixture(bundle.fixture_root)
    admission = admit_local_fixture(captured)
    assert admission.status == "ADMITTED"
    loader = _paper_core_loader()

    with pytest.raises((KeyError, OSError, ValueError)) as failure:
        context = loader.load_replay_envelope_context(bundle.fixture_root, captured, admission)
        build_verified_run_inputs(
            context.run_receipt_record,
            admission.candidates,
            admission.source_receipt_records,
            context.resolver,
            context.profiles,
        )

    assert expected_fragment in str(failure.value)
