"""Pure Task-8 run-input structures and counter-capacity preflight.

This module has no file, network, provider, model, replay, ledger, or execution
capability.  It derives only closed structural evidence from already-retained
in-memory bodies.  Contract-only RunReceipt verification is owned by Task 9.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from build_finance.crypto_replay.canonical import JsonValue

_MAX_U64 = 18_446_744_073_709_551_615

CodeFieldName = Literal[
    "admission_code_sha256",
    "normalization_code_sha256",
    "availability_grouping_code_sha256",
    "run_closure_code_sha256",
    "feature_code_sha256",
    "baseline_code_sha256",
    "risk_code_sha256",
    "fill_code_sha256",
    "accounting_code_sha256",
    "benchmark_code_sha256",
]


@dataclass(frozen=True, slots=True)
class ContractCodePreimage:
    """One retained, explicitly contract-only code preimage."""

    field_name: CodeFieldName
    payload: bytes
    assurance: Literal["CONTRACT_ONLY"] = "CONTRACT_ONLY"


@dataclass(frozen=True, slots=True)
class RunInputBundle:
    """Closed in-memory input carrier; it is not runnable authority."""

    fixture_manifest: Mapping[str, JsonValue]
    config_admission_receipt: Mapping[str, JsonValue]
    replay_risk_config: Mapping[str, JsonValue] | None
    raw_config_bytes: bytes | None
    source_admission_receipts: tuple[Mapping[str, JsonValue], ...]
    normalized_events: tuple[Mapping[str, JsonValue], ...]
    run_closure_receipt: Mapping[str, JsonValue]
    availability_schedule: Mapping[str, JsonValue]
    counter_capacity: Mapping[str, JsonValue]
    source_tree: Mapping[str, JsonValue]
    model_registry: Mapping[str, JsonValue] | None
    model_signal_manifest: Mapping[str, JsonValue] | None
    public_seed_bytes: bytes
    code_preimages: tuple[ContractCodePreimage, ...]


_COUNTER_ORDER = (
    ("decision_attempt_upper_bound", "DECISION_ATTEMPT"),
    ("decision_sequence_next_upper_bound", "DECISION_SEQUENCE"),
    ("producer_sequence_next_upper_bound", "PRODUCER_SEQUENCE"),
    ("intent_sequence_next_upper_bound", "INTENT_SEQUENCE"),
    ("fill_receipt_sequence_next_upper_bound", "FILL_RECEIPT_SEQUENCE"),
    ("unmatched_reservation_count_upper_bound", "UNMATCHED_RESERVATION_COUNT"),
    ("state_sequence_next_upper_bound", "STATE_SEQUENCE"),
    ("ledger_sequence_next_upper_bound", "LEDGER_SEQUENCE"),
)


def _require_unbounded_count(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative unbounded integer")
    return value


def _totalize_counter_capacity_bounds(unbounded: Mapping[str, int]) -> dict[str, JsonValue]:
    """Convert one complete unbounded counter map to aliases exactly once."""
    if set(unbounded) != {field for field, _ in _COUNTER_ORDER}:
        raise ValueError("counter bound map is not the exact closed field set")
    values = {field: _require_unbounded_count(unbounded[field], field=field) for field, _ in _COUNTER_ORDER}
    first_exceeded: str | None = None
    totalized: dict[str, JsonValue] = {}
    for field, code in _COUNTER_ORDER:
        value = values[field]
        if value <= _MAX_U64:
            totalized[field] = str(value)
        else:
            totalized[field] = None
            if first_exceeded is None:
                first_exceeded = code
    totalized["status"] = "WITHIN_LIMIT" if first_exceeded is None else "EXCEEDED"
    totalized["first_exceeded_counter"] = first_exceeded
    return totalized


def _derive_counter_capacity_from_counts(
    *,
    source_admission_count: int,
    raw_event_count: int,
    availability_group_count: int,
    market_count: int,
    model_candidate_count: int,
    model_signal_mode: str,
) -> dict[str, JsonValue]:
    """Plan-authorized count-only boundary probe using unbounded arithmetic."""
    source_count = _require_unbounded_count(source_admission_count, field="source_admission_count")
    event_count = _require_unbounded_count(raw_event_count, field="raw_event_count")
    group_count = _require_unbounded_count(availability_group_count, field="availability_group_count")
    markets = _require_unbounded_count(market_count, field="market_count")
    candidates = _require_unbounded_count(model_candidate_count, field="model_candidate_count")

    if not 1 <= markets <= _MAX_U64:
        return {"admissible": False, "rejection_code": "MARKET_COUNT_RANGE"}
    if source_count > _MAX_U64 or event_count > _MAX_U64 or not 1 <= group_count <= _MAX_U64:
        raise ValueError("source/event/group counts must fit their pre-closure aliases")
    if model_signal_mode == "DISABLED":
        if candidates != 0:
            return {"admissible": False, "rejection_code": "MODEL_CANDIDATE_COUNT_RANGE"}
    elif model_signal_mode == "CACHED_FIXTURES":
        if not 1 <= candidates <= _MAX_U64:
            return {"admissible": False, "rejection_code": "MODEL_CANDIDATE_COUNT_RANGE"}
    else:
        raise ValueError("model_signal_mode is not a closed value")

    decision_count = markets * group_count
    unbounded = {
        "decision_attempt_upper_bound": decision_count,
        "decision_sequence_next_upper_bound": decision_count + 1,
        "producer_sequence_next_upper_bound": candidates,
        "intent_sequence_next_upper_bound": decision_count + 1,
        "fill_receipt_sequence_next_upper_bound": decision_count + 1,
        "unmatched_reservation_count_upper_bound": 2 * decision_count,
        "state_sequence_next_upper_bound": 3 * decision_count + 2 * group_count + 3,
        "ledger_sequence_next_upper_bound": (
            source_count + event_count + 10 * decision_count + 2 * candidates + 5 * group_count + 9
        ),
    }
    return {
        "admissible": True,
        "rejection_code": None,
        "model_signal_mode": model_signal_mode,
        "source_admission_count": str(source_count),
        "raw_event_count": str(event_count),
        "availability_group_count": str(group_count),
        "market_count": str(markets),
        "model_candidate_count": str(candidates),
        **_totalize_counter_capacity_bounds(unbounded),
    }


def _selected_model_candidate_count(bundle: RunInputBundle, mode: str) -> tuple[str | None, str | None, int]:
    closure = bundle.run_closure_receipt
    closure_registry_id = closure.get("model_registry_sha256")
    closure_manifest_id = closure.get("model_signal_manifest_sha256")
    if mode == "DISABLED":
        if (
            bundle.model_registry is not None
            or bundle.model_signal_manifest is not None
            or closure_registry_id is not None
            or closure_manifest_id is not None
        ):
            raise ValueError("disabled mode requires absent model bodies and null IDs")
        return None, None, 0
    if mode != "CACHED_FIXTURES":
        raise ValueError("unknown model signal mode")
    registry = bundle.model_registry
    manifest = bundle.model_signal_manifest
    if registry is None or manifest is None:
        raise ValueError("cached mode requires registry and manifest bodies")
    if not isinstance(closure_registry_id, str) or not isinstance(closure_manifest_id, str):
        raise ValueError("cached mode requires both closure model IDs")
    candidates = manifest.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("cached model candidate array is absent")
    return closure_registry_id, closure_manifest_id, len(candidates)


def derive_counter_capacity(bundle: RunInputBundle) -> dict[str, JsonValue]:
    """Derive counter evidence from retained bodies; supplied count fields are ignored."""
    fixture_markets = bundle.fixture_manifest.get("allowed_markets")
    groups = bundle.availability_schedule.get("availability_groups")
    if not isinstance(fixture_markets, list) or not isinstance(groups, list):
        raise ValueError("retained market/group arrays are absent")
    normalized_digest = bundle.counter_capacity.get("normalized_event_set_sha256")
    if not isinstance(normalized_digest, str):
        raise ValueError("retained normalized-event-set digest is absent")
    mode_value = bundle.run_closure_receipt.get("model_signal_mode")
    if not isinstance(mode_value, str):
        raise ValueError("run closure model mode is absent")
    registry_id, manifest_id, candidate_count = _selected_model_candidate_count(bundle, mode_value)
    totalized = _derive_counter_capacity_from_counts(
        source_admission_count=len(bundle.source_admission_receipts),
        raw_event_count=len(bundle.normalized_events),
        availability_group_count=len(groups),
        market_count=len(fixture_markets),
        model_candidate_count=candidate_count,
        model_signal_mode=mode_value,
    )
    if totalized["admissible"] is not True:
        raise ValueError(f"counter-capacity preflight rejected: {totalized['rejection_code']}")
    return {
        "schema": "trading.counter-capacity/v1",
        "model_signal_mode": mode_value,
        "model_registry_sha256": registry_id,
        "model_signal_manifest_sha256": manifest_id,
        "normalized_event_set_sha256": normalized_digest,
        "source_admission_count": totalized["source_admission_count"],
        "raw_event_count": totalized["raw_event_count"],
        "availability_group_count": totalized["availability_group_count"],
        "market_count": totalized["market_count"],
        "model_candidate_count": totalized["model_candidate_count"],
        **{field: totalized[field] for field, _ in _COUNTER_ORDER},
        "status": totalized["status"],
        "first_exceeded_counter": totalized["first_exceeded_counter"],
    }
