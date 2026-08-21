"""G2 RED contract for the offline live-paper capital engine.

The production package intentionally does not exist at this RED stage.  These
tests freeze the smallest acceptable vertical behavior before Task 2 builds it.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

import pytest

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_EXPECTED_PRICE_Q18 = "100000000000000000000"
_EXPECTED_INITIAL_QUOTE_ATOMS = "100000000"
_EXPECTED_ORDER_BASE_ATOMS = "100000"
_EXPECTED_GROSS_QUOTE_ATOMS = "10000000"
_EXPECTED_FEE_QUOTE_ATOMS = "10000"
_EXPECTED_RESERVED_QUOTE_ATOMS = "10010000"
_EXPECTED_CASH_AFTER_FILL_ATOMS = "89990000"
_EXPECTED_BASE_AFTER_FILL_ATOMS = "100000"


def _synthetic_verified_inputs() -> dict[str, Any]:
    """Return the hand-derived synthetic fixture used by the G2 vertical contract."""

    return {
        "schema": "build-finance.live-paper.synthetic-verified-input/v1",
        "evidence_classification": "SYNTHETIC_CONTRACT_VECTOR",
        "synthetic_notice": "Synthetic fixture; never observed market data, credentials, or venue state.",
        "run_id": "g2-red-synthetic-long-flat-001",
        "market_id": "SYNTH_BASE_SYNTH_QUOTE_SPOT",
        "base_mint": "SYNTH_BASE_MINT",
        "quote_mint": "SYNTH_QUOTE_MINT",
        "base_decimals": 6,
        "quote_decimals": 6,
        "positioning": "LONG_OR_FLAT_SPOT",
        "execution_mode": "OFFLINE_PAPER_ONLY",
        "model_mode": "DISABLED_ABSTAIN",
        "initial_portfolio": {
            "base_atoms": "0",
            "quote_atoms": _EXPECTED_INITIAL_QUOTE_ATOMS,
        },
        "risk": {
            "deterministic_risk_only": True,
            "max_notional_quote_atoms": _EXPECTED_GROSS_QUOTE_ATOMS,
            "fee_bps": 10,
            "max_impact_bps": 0,
            "max_participation_bps": 10000,
        },
        "events": [
            {
                "source_event_id": "synthetic-event-0001",
                "ingest_sequence": "1",
                "equal_time_group": "1",
                "replay_clock_ns": "1000000000",
                "kind": "QUOTE",
                "price_q18": _EXPECTED_PRICE_Q18,
                "executable_base_atoms": "250000",
            },
            {
                "source_event_id": "synthetic-event-0002",
                "ingest_sequence": "2",
                "equal_time_group": "2",
                "replay_clock_ns": "2000000000",
                "kind": "QUOTE",
                "price_q18": _EXPECTED_PRICE_Q18,
                "executable_base_atoms": "250000",
            },
        ],
    }


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    assert isinstance(value, Mapping), f"{label} must be a mapping, got {type(value).__name__}"
    return value


def _require_hex_id(value: Any, label: str) -> str:
    assert isinstance(value, str), f"{label} must be a hex content id string"
    assert _HEX64.fullmatch(value), f"{label} must be a 64-byte lowercase hex digest"
    return value


def _require_list(value: Any, label: str, length: int) -> list[Any]:
    assert isinstance(value, list), f"{label} must be a list"
    assert len(value) == length, f"{label} must contain {length} item(s)"
    return value


def _canonical_json_bytes(value: Any) -> bytes:
    _reject_float(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _reject_float(value: Any) -> None:
    if isinstance(value, float):
        raise TypeError("G2 contract IDs are derived from integer/string canonical JSON, never floats")
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("G2 contract IDs are derived from string-keyed canonical JSON objects")
            _reject_float(item)
    elif isinstance(value, list):
        for item in value:
            _reject_float(item)


def _computed_content_id(document: Mapping[str, Any], self_id_field: str) -> str:
    body = dict(document)
    body.pop(self_id_field, None)
    return hashlib.sha256(_canonical_json_bytes(body)).hexdigest()


def _assert_self_content_id(document: Mapping[str, Any], self_id_field: str, label: str) -> str:
    supplied = _require_hex_id(document.get(self_id_field), label)
    expected = _computed_content_id(document, self_id_field)
    assert supplied == expected, f"{label} content id mismatch: expected {expected}, got {supplied}"
    return supplied


def _assert_complete_vertical_contract(result: Mapping[str, Any]) -> None:
    """Assert the full G2 RED vertical path from synthetic input to closure."""

    mode = _require_mapping(result.get("mode"), "mode")
    assert mode == {
        "data_boundary": "OFFLINE_VERIFIED_INPUT",
        "execution": "PAPER_ONLY",
        "model": "DISABLED_ABSTAIN",
        "positioning": "LONG_OR_FLAT_SPOT",
        "runtime_dependencies": "PYTHON_STDLIB_ONLY",
    }
    assert result.get("schema") == "build-finance.live-paper.g2-run-result/v1"
    assert result.get("evidence_classification") == "SYNTHETIC_CONTRACT_VECTOR"

    capability_receipt = _require_mapping(result.get("capability_receipt"), "capability_receipt")
    assert capability_receipt.get("external_io_attempts") == []
    assert capability_receipt.get("provider_sdk_touches") == []
    assert capability_receipt.get("credential_lookups") == []
    assert capability_receipt.get("broker_wallet_or_signer_touches") == []
    assert capability_receipt.get("venue_order_touches") == []

    normalized_events = _require_list(result.get("normalized_events"), "normalized_events", 2)
    first_event = _require_mapping(normalized_events[0], "normalized_events[0]")
    second_event = _require_mapping(normalized_events[1], "normalized_events[1]")
    first_event_id = _assert_self_content_id(first_event, "event_id", "first normalized event id")
    second_event_id = _assert_self_content_id(second_event, "event_id", "second normalized event id")
    assert first_event["source_event_id"] == "synthetic-event-0001"
    assert second_event["source_event_id"] == "synthetic-event-0002"
    assert first_event["price_q18"] == _EXPECTED_PRICE_Q18
    assert second_event["price_q18"] == _EXPECTED_PRICE_Q18
    assert int(second_event["replay_clock_ns"]) > int(first_event["replay_clock_ns"])

    feature = _require_mapping(result.get("feature_snapshot"), "feature_snapshot")
    feature_id = _assert_self_content_id(feature, "feature_snapshot_id", "feature snapshot id")
    assert feature["schema"] == "build-finance.live-paper.feature-snapshot/v1"
    assert feature["as_of_event_id"] == first_event_id
    assert feature["market_id"] == "SYNTH_BASE_SYNTH_QUOTE_SPOT"
    assert feature["close_price_q18"] == _EXPECTED_PRICE_Q18
    assert feature["position_base_atoms_before"] == "0"
    assert feature["cash_quote_atoms_before"] == _EXPECTED_INITIAL_QUOTE_ATOMS

    algorithm = _require_mapping(result.get("algorithm_evidence"), "algorithm_evidence")
    algorithm_id = _assert_self_content_id(algorithm, "algorithm_evidence_id", "algorithm evidence id")
    assert algorithm["schema"] == "build-finance.live-paper.algorithm-evidence/v1"
    assert algorithm["feature_snapshot_id"] == feature_id
    assert algorithm["rule_id"] == "G2_SYNTHETIC_LONG_OR_FLAT_OPEN_IF_FLAT"
    assert algorithm["candidate_action"] == "OPEN_LONG"
    assert "quantity_base_atoms" not in algorithm
    assert "venue_order" not in algorithm

    model = _require_mapping(result.get("model_signal"), "model_signal")
    model_id = _assert_self_content_id(model, "model_signal_id", "model signal id")
    assert model["schema"] == "build-finance.live-paper.model-signal/v1"
    assert model["feature_snapshot_id"] == feature_id
    assert model["mode"] == "DISABLED"
    assert model["action"] == "ABSTAIN"
    assert model["can_size"] is False
    assert model["can_execute"] is False

    fusion = _require_mapping(result.get("fusion_decision"), "fusion_decision")
    fusion_id = _assert_self_content_id(fusion, "fusion_decision_id", "fusion decision id")
    assert fusion["schema"] == "build-finance.live-paper.fusion-decision/v1"
    assert fusion["model_signal_id"] == model_id
    assert fusion["algorithm_evidence_id"] == algorithm_id
    assert fusion["model_action"] == "ABSTAIN"
    assert fusion["candidate_action"] == "OPEN_LONG"
    assert fusion["can_size"] is False
    assert fusion["can_execute"] is False
    assert "quantity_base_atoms" not in fusion

    risk = _require_mapping(result.get("risk_decision"), "risk_decision")
    risk_id = _assert_self_content_id(risk, "risk_decision_id", "risk decision id")
    assert risk["schema"] == "build-finance.live-paper.risk-decision/v1"
    assert risk["fusion_decision_id"] == fusion_id
    assert risk["authority"] == "DETERMINISTIC_RISK_ONLY"
    assert risk["decision"] == "MINT_PAPER_INTENT"
    assert risk["reference_price_q18"] == _EXPECTED_PRICE_Q18
    assert risk["quantity_base_atoms"] == _EXPECTED_ORDER_BASE_ATOMS
    assert risk["max_notional_quote_atoms"] == _EXPECTED_GROSS_QUOTE_ATOMS
    assert risk["reserved_quote_atoms"] == _EXPECTED_RESERVED_QUOTE_ATOMS
    assert risk["model_sized"] is False

    intents = _require_list(result.get("paper_intents"), "paper_intents", 1)
    intent = _require_mapping(intents[0], "paper_intents[0]")
    intent_id = _assert_self_content_id(intent, "intent_id", "paper intent id")
    assert intent["schema"] == "build-finance.live-paper.paper-intent/v1"
    assert intent["risk_decision_id"] == risk_id
    assert intent["created_by"] == "DETERMINISTIC_RISK_ONLY"
    assert intent["action"] == "OPEN_LONG"
    assert intent["paper_only"] is True
    assert intent["quantity_base_atoms"] == _EXPECTED_ORDER_BASE_ATOMS
    assert intent["reserved_quote_atoms"] == _EXPECTED_RESERVED_QUOTE_ATOMS
    assert intent["broker_order_id"] is None
    assert intent["wallet_signature"] is None

    fills = _require_list(result.get("paper_fills"), "paper_fills", 1)
    fill = _require_mapping(fills[0], "paper_fills[0]")
    fill_id = _assert_self_content_id(fill, "fill_id", "paper fill id")
    assert fill["schema"] == "build-finance.live-paper.paper-fill/v1"
    assert fill["intent_id"] == intent_id
    assert fill["decision_event_id"] == first_event_id
    assert fill["fill_event_id"] == second_event_id
    assert fill["fill_policy"] == "STRICT_NEXT_EVENT"
    assert fill["filled_base_atoms"] == _EXPECTED_ORDER_BASE_ATOMS
    assert fill["gross_quote_atoms"] == _EXPECTED_GROSS_QUOTE_ATOMS
    assert fill["simulation_fee_quote_atoms"] == _EXPECTED_FEE_QUOTE_ATOMS
    assert fill["cash_delta_quote_atoms"] == f"-{_EXPECTED_RESERVED_QUOTE_ATOMS}"

    ledger = _require_mapping(result.get("ledger"), "ledger")
    ledger_id = _assert_self_content_id(ledger, "ledger_record_id", "ledger record id")
    assert ledger["schema"] == "build-finance.live-paper.ledger-record/v1"
    assert ledger["fill_id"] == fill_id
    assert ledger["cash_quote_atoms_after"] == _EXPECTED_CASH_AFTER_FILL_ATOMS
    assert ledger["position_base_atoms_after"] == _EXPECTED_BASE_AFTER_FILL_ATOMS
    assert ledger["postings"] == [
        {
            "account": "CASH_AVAILABLE",
            "asset_mint": "SYNTH_QUOTE_MINT",
            "delta_atoms": f"-{_EXPECTED_RESERVED_QUOTE_ATOMS}",
        },
        {
            "account": "POSITION_AVAILABLE",
            "asset_mint": "SYNTH_BASE_MINT",
            "delta_atoms": _EXPECTED_ORDER_BASE_ATOMS,
        },
        {
            "account": "FEES_PAID",
            "asset_mint": "SYNTH_QUOTE_MINT",
            "delta_atoms": _EXPECTED_FEE_QUOTE_ATOMS,
        },
    ]

    reconciliation = _require_mapping(result.get("reconciliation"), "reconciliation")
    reconciliation_id = _assert_self_content_id(reconciliation, "reconciliation_id", "reconciliation id")
    assert reconciliation["schema"] == "build-finance.live-paper.reconciliation/v1"
    assert reconciliation["ledger_record_id"] == ledger_id
    assert reconciliation["status"] == "PASS"
    assert reconciliation["cash_residual_quote_atoms"] == "0"
    assert reconciliation["position_residual_base_atoms"] == "0"
    assert reconciliation["unmatched_paper_intent_count"] == 0
    assert reconciliation["external_position_source"] is None

    closure = _require_mapping(result.get("closure"), "closure")
    _assert_self_content_id(closure, "closure_id", "closure id")
    assert closure["schema"] == "build-finance.live-paper.run-closure/v1"
    assert closure["reconciliation_id"] == reconciliation_id
    assert closure["status"] == "CLOSED"
    assert closure["final_position_state"] == "LONG"
    assert closure["open_paper_intent_count"] == 0
    assert closure["open_venue_order_count"] == 0
    assert closure["final_cash_quote_atoms"] == _EXPECTED_CASH_AFTER_FILL_ATOMS
    assert closure["final_position_base_atoms"] == _EXPECTED_BASE_AFTER_FILL_ATOMS


def test_vertical_contract_assertions_reject_placeholders() -> None:
    """The contract helper must fail empty or top-level-only placeholders."""

    with pytest.raises(AssertionError, match="mode"):
        _assert_complete_vertical_contract({})

    placeholder = {
        "schema": "build-finance.live-paper.g2-run-result/v1",
        "evidence_classification": "SYNTHETIC_CONTRACT_VECTOR",
        "mode": {
            "data_boundary": "OFFLINE_VERIFIED_INPUT",
            "execution": "PAPER_ONLY",
            "model": "DISABLED_ABSTAIN",
            "positioning": "LONG_OR_FLAT_SPOT",
            "runtime_dependencies": "PYTHON_STDLIB_ONLY",
        },
        "capability_receipt": {
            "external_io_attempts": [],
            "provider_sdk_touches": [],
            "credential_lookups": [],
            "broker_wallet_or_signer_touches": [],
            "venue_order_touches": [],
        },
    }
    with pytest.raises(AssertionError, match="normalized_events"):
        _assert_complete_vertical_contract(placeholder)


def _complete_placeholder_result(content_id: str = "0" * 64) -> dict[str, Any]:
    return {
        "schema": "build-finance.live-paper.g2-run-result/v1",
        "evidence_classification": "SYNTHETIC_CONTRACT_VECTOR",
        "mode": {
            "data_boundary": "OFFLINE_VERIFIED_INPUT",
            "execution": "PAPER_ONLY",
            "model": "DISABLED_ABSTAIN",
            "positioning": "LONG_OR_FLAT_SPOT",
            "runtime_dependencies": "PYTHON_STDLIB_ONLY",
        },
        "capability_receipt": {
            "external_io_attempts": [],
            "provider_sdk_touches": [],
            "credential_lookups": [],
            "broker_wallet_or_signer_touches": [],
            "venue_order_touches": [],
        },
        "normalized_events": [
            {
                "event_id": content_id,
                "source_event_id": "synthetic-event-0001",
                "price_q18": _EXPECTED_PRICE_Q18,
                "replay_clock_ns": "1000000000",
            },
            {
                "event_id": content_id,
                "source_event_id": "synthetic-event-0002",
                "price_q18": _EXPECTED_PRICE_Q18,
                "replay_clock_ns": "2000000000",
            },
        ],
        "feature_snapshot": {
            "schema": "build-finance.live-paper.feature-snapshot/v1",
            "feature_snapshot_id": content_id,
            "as_of_event_id": content_id,
            "market_id": "SYNTH_BASE_SYNTH_QUOTE_SPOT",
            "close_price_q18": _EXPECTED_PRICE_Q18,
            "position_base_atoms_before": "0",
            "cash_quote_atoms_before": _EXPECTED_INITIAL_QUOTE_ATOMS,
        },
        "algorithm_evidence": {
            "schema": "build-finance.live-paper.algorithm-evidence/v1",
            "algorithm_evidence_id": content_id,
            "feature_snapshot_id": content_id,
            "rule_id": "G2_SYNTHETIC_LONG_OR_FLAT_OPEN_IF_FLAT",
            "candidate_action": "OPEN_LONG",
        },
        "model_signal": {
            "schema": "build-finance.live-paper.model-signal/v1",
            "model_signal_id": content_id,
            "feature_snapshot_id": content_id,
            "mode": "DISABLED",
            "action": "ABSTAIN",
            "can_size": False,
            "can_execute": False,
        },
        "fusion_decision": {
            "schema": "build-finance.live-paper.fusion-decision/v1",
            "fusion_decision_id": content_id,
            "model_signal_id": content_id,
            "algorithm_evidence_id": content_id,
            "model_action": "ABSTAIN",
            "candidate_action": "OPEN_LONG",
            "can_size": False,
            "can_execute": False,
        },
        "risk_decision": {
            "schema": "build-finance.live-paper.risk-decision/v1",
            "risk_decision_id": content_id,
            "fusion_decision_id": content_id,
            "authority": "DETERMINISTIC_RISK_ONLY",
            "decision": "MINT_PAPER_INTENT",
            "reference_price_q18": _EXPECTED_PRICE_Q18,
            "quantity_base_atoms": _EXPECTED_ORDER_BASE_ATOMS,
            "max_notional_quote_atoms": _EXPECTED_GROSS_QUOTE_ATOMS,
            "reserved_quote_atoms": _EXPECTED_RESERVED_QUOTE_ATOMS,
            "model_sized": False,
        },
        "paper_intents": [
            {
                "schema": "build-finance.live-paper.paper-intent/v1",
                "intent_id": content_id,
                "risk_decision_id": content_id,
                "created_by": "DETERMINISTIC_RISK_ONLY",
                "action": "OPEN_LONG",
                "paper_only": True,
                "quantity_base_atoms": _EXPECTED_ORDER_BASE_ATOMS,
                "reserved_quote_atoms": _EXPECTED_RESERVED_QUOTE_ATOMS,
                "broker_order_id": None,
                "wallet_signature": None,
            }
        ],
        "paper_fills": [
            {
                "schema": "build-finance.live-paper.paper-fill/v1",
                "fill_id": content_id,
                "intent_id": content_id,
                "decision_event_id": content_id,
                "fill_event_id": content_id,
                "fill_policy": "STRICT_NEXT_EVENT",
                "filled_base_atoms": _EXPECTED_ORDER_BASE_ATOMS,
                "gross_quote_atoms": _EXPECTED_GROSS_QUOTE_ATOMS,
                "simulation_fee_quote_atoms": _EXPECTED_FEE_QUOTE_ATOMS,
                "cash_delta_quote_atoms": f"-{_EXPECTED_RESERVED_QUOTE_ATOMS}",
            }
        ],
        "ledger": {
            "schema": "build-finance.live-paper.ledger-record/v1",
            "ledger_record_id": content_id,
            "fill_id": content_id,
            "cash_quote_atoms_after": _EXPECTED_CASH_AFTER_FILL_ATOMS,
            "position_base_atoms_after": _EXPECTED_BASE_AFTER_FILL_ATOMS,
            "postings": [
                {
                    "account": "CASH_AVAILABLE",
                    "asset_mint": "SYNTH_QUOTE_MINT",
                    "delta_atoms": f"-{_EXPECTED_RESERVED_QUOTE_ATOMS}",
                },
                {
                    "account": "POSITION_AVAILABLE",
                    "asset_mint": "SYNTH_BASE_MINT",
                    "delta_atoms": _EXPECTED_ORDER_BASE_ATOMS,
                },
                {
                    "account": "FEES_PAID",
                    "asset_mint": "SYNTH_QUOTE_MINT",
                    "delta_atoms": _EXPECTED_FEE_QUOTE_ATOMS,
                },
            ],
        },
        "reconciliation": {
            "schema": "build-finance.live-paper.reconciliation/v1",
            "reconciliation_id": content_id,
            "ledger_record_id": content_id,
            "status": "PASS",
            "cash_residual_quote_atoms": "0",
            "position_residual_base_atoms": "0",
            "unmatched_paper_intent_count": 0,
            "external_position_source": None,
        },
        "closure": {
            "schema": "build-finance.live-paper.run-closure/v1",
            "closure_id": content_id,
            "reconciliation_id": content_id,
            "status": "CLOSED",
            "final_position_state": "LONG",
            "open_paper_intent_count": 0,
            "open_venue_order_count": 0,
            "final_cash_quote_atoms": _EXPECTED_CASH_AFTER_FILL_ATOMS,
            "final_position_base_atoms": _EXPECTED_BASE_AFTER_FILL_ATOMS,
        },
    }


def test_vertical_contract_assertions_reject_consistent_placeholder_content_ids() -> None:
    """Consistent 64-hex placeholders must not satisfy self-addressed authority IDs."""

    with pytest.raises(AssertionError, match="content id"):
        _assert_complete_vertical_contract(_complete_placeholder_result())


def test_synthetic_long_or_flat_run_reaches_paper_fill_ledger_reconciliation_and_closure() -> None:
    """Future G2 production must satisfy the full synthetic offline-paper vertical contract."""

    from build_finance.live_paper.kernel import run_offline_paper_kernel

    inputs = _synthetic_verified_inputs()
    original_inputs = copy.deepcopy(inputs)
    result = run_offline_paper_kernel(inputs)

    assert inputs == original_inputs, "kernel must not mutate verified input fixtures"
    _assert_complete_vertical_contract(_require_mapping(result, "G2 run result"))
