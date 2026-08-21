"""G2 RED tests for deterministic offline paper-kernel replay."""

from __future__ import annotations

import copy
import json
from typing import Any

_EXPECTED_PRICE_Q18 = "100000000000000000000"


def _synthetic_verified_inputs() -> dict[str, Any]:
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
        "initial_portfolio": {"base_atoms": "0", "quote_atoms": "100000000"},
        "risk": {
            "deterministic_risk_only": True,
            "max_notional_quote_atoms": "10000000",
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


def _canonical_json_bytes(value: Any) -> bytes:
    _reject_float(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _reject_float(value: Any) -> None:
    if isinstance(value, float):
        raise TypeError("G2 deterministic contracts use integer atoms/q18 strings, never floats")
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("G2 deterministic contracts use string object keys")
            _reject_float(item)
    elif isinstance(value, list):
        for item in value:
            _reject_float(item)


def test_kernel_replay_is_byte_stable_and_does_not_mutate_verified_input() -> None:
    """Equivalent synthetic verified inputs must produce identical canonical bytes."""

    from build_finance.live_paper.kernel import run_offline_paper_kernel

    first_inputs = _synthetic_verified_inputs()
    first_before = copy.deepcopy(first_inputs)
    second_inputs = _synthetic_verified_inputs()

    first_result = run_offline_paper_kernel(first_inputs)
    second_result = run_offline_paper_kernel(second_inputs)

    assert first_inputs == first_before
    assert first_result == second_result
    assert _canonical_json_bytes(first_result) == _canonical_json_bytes(second_result)
    assert first_result["closure"]["determinism"] == {
        "ambient_environment_used": False,
        "dynamic_import_used": False,
        "process_or_network_used": False,
        "status": "PASS",
        "wall_clock_used": False,
    }


def test_kernel_replay_is_independent_of_input_mapping_order() -> None:
    """Input key order must not change deterministic evidence, IDs, or ledger closure."""

    from build_finance.live_paper.kernel import run_offline_paper_kernel

    original_inputs = _synthetic_verified_inputs()
    canonicalized_inputs = json.loads(_canonical_json_bytes(original_inputs).decode("utf-8"))

    assert list(original_inputs) != list(canonicalized_inputs)
    assert run_offline_paper_kernel(original_inputs) == run_offline_paper_kernel(canonicalized_inputs)
