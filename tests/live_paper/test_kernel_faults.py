"""Task 11 fail-closed boundary tests for the G2 offline paper kernel."""

from __future__ import annotations

from typing import Any

import pytest

from build_finance.crypto_replay.canonical import canonical_record_bytes
from build_finance.crypto_replay.content_ids import seal_content_id as seal_replay_content_id
from build_finance.live_paper.profiles import PaperKernelProfiles
from build_finance.live_paper.run_input_builder import build_verified_run_inputs
from tests.live_paper.support.g2_vectors import G2Vector, build_g2_vector


def _profiles(vector: G2Vector, **overrides: object) -> PaperKernelProfiles:
    values = {
        **vector.profile_records,
        "risk_config_record": canonical_record_bytes(vector.run_input_bundle.replay_risk_config),
        **overrides,
    }
    return PaperKernelProfiles(**values)  # type: ignore[arg-type]


def _verified_case() -> tuple[G2Vector, Any, PaperKernelProfiles]:
    vector = build_g2_vector()
    profiles = _profiles(vector)
    verified = build_verified_run_inputs(
        vector.run_receipt_record,
        vector.admitted_candidates,
        vector.source_receipt_records,
        vector.resolver,
        profiles,
    )
    return vector, verified, profiles


def _valid_foreign_risk_config_record(vector: G2Vector) -> bytes:
    document = dict(vector.run_input_bundle.replay_risk_config)
    document.pop("config_sha256")
    document["session_end_replay_clock_ns"] = "1000000001"
    return canonical_record_bytes(seal_replay_content_id(document))


@pytest.mark.parametrize(
    ("case_name", "fault", "boundary", "reason_code", "retained_intents", "retained_fills"),
    (
        ("bad verified carrier", "bad_verified", "GROUPING", "KERNEL_GROUPING_FAILED", 0, 0),
        ("bad risk profile", "bad_risk_profile", "PROFILE_VALIDATION", "KERNEL_PROFILE_INVALID", 0, 0),
        ("foreign risk config", "foreign_risk_config", "RISK_EVALUATION", "KERNEL_RISK_FAILED", 0, 0),
    ),
)
def test_kernel_fault_boundaries_return_typed_fail_closed_closure(
    case_name: str,
    fault: str,
    boundary: str,
    reason_code: str,
    retained_intents: int,
    retained_fills: int,
) -> None:
    """Breaks if representative major boundaries raise instead of sealing closure evidence."""

    from build_finance.live_paper.kernel import run_offline_paper_kernel
    from build_finance.live_paper.projections import kernel_result_canonical_bytes

    vector, verified, profiles = _verified_case()
    resolver = vector.resolver
    if fault == "bad_verified":
        verified = object()
    elif fault == "bad_risk_profile":
        profiles = _profiles(vector, risk_config_record=b"not canonical json\n")
    elif fault == "foreign_risk_config":
        profiles = _profiles(vector, risk_config_record=_valid_foreign_risk_config_record(vector))
    else:  # pragma: no cover - table guard.
        raise AssertionError(case_name)

    result = run_offline_paper_kernel(verified, resolver, profiles)
    repeated = run_offline_paper_kernel(verified, resolver, profiles)

    assert kernel_result_canonical_bytes(result) == kernel_result_canonical_bytes(repeated)
    assert result.closure.status == "FAILED_CLOSED"
    assert result.closure.failure_boundary == boundary
    assert result.closure.failure_type == "ValueError"
    assert result.closure.reason_codes == (reason_code,)
    assert result.closure.error_message
    assert result.projection.breaker_state.status == "FAILED_CLOSED"
    assert result.projection.breaker_state.reason_codes == (reason_code,)
    assert result.projection.receipt_ids.closure_id == result.closure.closure_id
    assert len(result.simulated_order_intent_records) == retained_intents
    assert len(result.simulated_fill_receipt_records) == retained_fills
