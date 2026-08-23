"""Disk replay-envelope tests for the G2 offline paper core."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

import pytest

from build_finance.crypto_replay.admission import admit_local_fixture
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
