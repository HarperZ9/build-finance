"""T01 RED contract for the eight closed primary v1 schemas."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

EXAMPLE_ROOT = Path(__file__).parent / "resources" / "primary-v1" / "examples"
EXAMPLES = {
    "trading.feature-snapshot/v1": ("feature-snapshot.json", "snapshot_id"),
    "trading.ledger-record/v1": ("ledger-record.json", "ledger_record_id"),
    "trading.model-signal/v1": ("model-signal.json", "signal_id"),
    "trading.portfolio-state/v1": ("portfolio-state.json", "portfolio_state_id"),
    "trading.raw-event/v1": ("raw-event.json", "event_id"),
    "trading.risk-decision/v1": ("risk-decision.json", "risk_decision_id"),
    "trading.simulated-fill-receipt/v1": ("simulated-fill-receipt.json", "fill_receipt_id"),
    "trading.simulated-order-intent/v1": ("simulated-order-intent.json", "intent_id"),
}


def _example(schema_id: str) -> dict[str, Any]:
    filename, _ = EXAMPLES[schema_id]
    document = json.loads((EXAMPLE_ROOT / filename).read_text(encoding="utf-8"))
    assert document["schema"] == schema_id
    return document


def _changed(document: Mapping[str, Any], path: Sequence[str | int], value: Any) -> dict[str, Any]:
    result = deepcopy(document)
    target: Any = result
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    return result


def _different(value: Any) -> Any:
    if value is None:
        return "mutation"
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 1
    if isinstance(value, str):
        return value + "~"
    if isinstance(value, list):
        return [*value, "mutation"]
    if isinstance(value, dict):
        return {**value, "mutation": True}
    raise AssertionError(f"unhandled JSON value: {type(value)!r}")


def _assert_semantic_mutations_rejected(
    document: Mapping[str, Any],
    mutations: Sequence[tuple[Sequence[str | int], Any]],
    *,
    seal_content_id: Callable[[Mapping[str, Any]], dict[str, Any]],
    validate_contract: Callable[..., tuple[Any, ...]],
) -> None:
    _, self_id_field = EXAMPLES[str(document["schema"])]
    for path, value in mutations:
        mutation = _changed(document, path, value)
        mutation.pop(self_id_field)
        sealed = seal_content_id(mutation)
        issues = validate_contract(sealed, expected_schema=document["schema"])
        dotted_path = ".".join(str(part) for part in path)
        assert issues, f"semantic mutation unexpectedly accepted: {dotted_path}"


def test_unknown_property_rejected_for_all_primary_v1_schemas() -> None:
    from build_finance.crypto_replay.content_ids import seal_content_id
    from build_finance.crypto_replay.schema_registry import validate_contract

    for schema_id, (_, self_id_field) in EXAMPLES.items():
        mutation = _example(schema_id)
        mutation["unknown_property"] = True
        mutation.pop(self_id_field)
        mutation = seal_content_id(mutation)
        assert validate_contract(mutation, expected_schema=schema_id)


def test_primary_id_digest_excludes_only_self_id() -> None:
    from build_finance.crypto_replay.content_ids import compute_content_id

    for schema_id, (_, self_id_field) in EXAMPLES.items():
        document = _example(schema_id)
        expected = document[self_id_field]
        assert compute_content_id(document) == expected

        without_self_id = dict(document)
        without_self_id.pop(self_id_field)
        assert compute_content_id(without_self_id) == expected

        changed_self_id = dict(document)
        changed_self_id[self_id_field] = "0" * 64
        assert compute_content_id(changed_self_id) == expected

        for field, value in document.items():
            if field in {"schema", self_id_field}:
                continue
            mutation = dict(document)
            mutation[field] = _different(value)
            assert compute_content_id(mutation) != expected, f"digest ignored {schema_id}.{field}"

        changed_schema = dict(document)
        changed_schema["schema"] = "trading.unsupported/v1"
        with pytest.raises((KeyError, ValueError)):
            compute_content_id(changed_schema)


def test_primary_examples_validate_and_self_ids_recompute() -> None:
    from build_finance.crypto_replay.content_ids import compute_content_id, verify_content_id
    from build_finance.crypto_replay.schema_registry import require_valid_contract

    for schema_id, (_, self_id_field) in EXAMPLES.items():
        document = _example(schema_id)
        require_valid_contract(document, expected_schema=schema_id)
        assert compute_content_id(document) == document[self_id_field]
        assert verify_content_id(document)


def test_raw_event_example_validates() -> None:
    from build_finance.crypto_replay.schema_registry import require_valid_contract

    require_valid_contract(_example("trading.raw-event/v1"), expected_schema="trading.raw-event/v1")


def test_feature_snapshot_example_validates() -> None:
    from build_finance.crypto_replay.schema_registry import require_valid_contract

    require_valid_contract(_example("trading.feature-snapshot/v1"), expected_schema="trading.feature-snapshot/v1")


def test_model_signal_example_validates() -> None:
    from build_finance.crypto_replay.schema_registry import require_valid_contract

    require_valid_contract(_example("trading.model-signal/v1"), expected_schema="trading.model-signal/v1")


def test_risk_decision_example_validates() -> None:
    from build_finance.crypto_replay.schema_registry import require_valid_contract

    require_valid_contract(_example("trading.risk-decision/v1"), expected_schema="trading.risk-decision/v1")


def test_simulated_order_intent_example_validates() -> None:
    from build_finance.crypto_replay.schema_registry import require_valid_contract

    require_valid_contract(
        _example("trading.simulated-order-intent/v1"),
        expected_schema="trading.simulated-order-intent/v1",
    )


def test_simulated_fill_receipt_example_validates() -> None:
    from build_finance.crypto_replay.schema_registry import require_valid_contract

    require_valid_contract(
        _example("trading.simulated-fill-receipt/v1"),
        expected_schema="trading.simulated-fill-receipt/v1",
    )


def test_portfolio_state_example_validates() -> None:
    from build_finance.crypto_replay.schema_registry import require_valid_contract

    require_valid_contract(_example("trading.portfolio-state/v1"), expected_schema="trading.portfolio-state/v1")


def test_ledger_record_example_validates() -> None:
    from build_finance.crypto_replay.schema_registry import require_valid_contract

    require_valid_contract(_example("trading.ledger-record/v1"), expected_schema="trading.ledger-record/v1")


def test_raw_event_semantic_matrix() -> None:
    from build_finance.crypto_replay.content_ids import seal_content_id
    from build_finance.crypto_replay.schema_registry import validate_contract

    document = _example("trading.raw-event/v1")
    _assert_semantic_mutations_rejected(
        document,
        [
            (("base_mint",), document["quote_mint"]),
            (("revision", "availability_slot"), "2"),
            (("quality_flags",), ["NON_EXECUTABLE"]),
            (("ingested_at",), "2025-01-01T00:00:00.000000000Z"),
            (("quality_flags",), ["STALE_SOURCE", "NON_EXECUTABLE"]),
        ],
        seal_content_id=seal_content_id,
        validate_contract=validate_contract,
    )


def test_feature_snapshot_semantic_matrix() -> None:
    from build_finance.crypto_replay.content_ids import seal_content_id
    from build_finance.crypto_replay.schema_registry import validate_contract

    document = _example("trading.feature-snapshot/v1")
    _assert_semantic_mutations_rejected(
        document,
        [
            (("features", "history_count"), 0),
            (("missing_features",), ["mid_price_q18"]),
            (("as_of_event_id",), None),
        ],
        seal_content_id=seal_content_id,
        validate_contract=validate_contract,
    )


def test_model_signal_semantic_matrix() -> None:
    from build_finance.crypto_replay.content_ids import seal_content_id
    from build_finance.crypto_replay.schema_registry import validate_contract

    document = _example("trading.model-signal/v1")
    _assert_semantic_mutations_rejected(
        document,
        [
            (("probability_long_bias_q18",), "1"),
            (("decision_close_replay_clock_ns",), "0"),
            (("expires_replay_clock_ns",), "4"),
        ],
        seal_content_id=seal_content_id,
        validate_contract=validate_contract,
    )


def test_risk_decision_semantic_matrix() -> None:
    from build_finance.crypto_replay.content_ids import seal_content_id
    from build_finance.crypto_replay.schema_registry import validate_contract

    document = _example("trading.risk-decision/v1")
    _assert_semantic_mutations_rejected(
        document,
        [
            (("model_signal_status",), "ACCEPTED"),
            (("approved_base_atoms",), "999"),
            (("reservation_id",), None),
        ],
        seal_content_id=seal_content_id,
        validate_contract=validate_contract,
    )


def test_simulated_order_intent_semantic_matrix() -> None:
    from build_finance.crypto_replay.content_ids import seal_content_id
    from build_finance.crypto_replay.schema_registry import validate_contract

    document = _example("trading.simulated-order-intent/v1")
    _assert_semantic_mutations_rejected(
        document,
        [
            (("quantity_base_atoms",), "0"),
            (("reserved_quote_atoms",), "0"),
            (("stop_price_q18",), "1200000000000000000"),
        ],
        seal_content_id=seal_content_id,
        validate_contract=validate_contract,
    )


def test_simulated_fill_receipt_semantic_matrix() -> None:
    from build_finance.crypto_replay.content_ids import seal_content_id
    from build_finance.crypto_replay.schema_registry import validate_contract

    document = _example("trading.simulated-fill-receipt/v1")
    _assert_semantic_mutations_rejected(
        document,
        [
            (("filled_base_atoms",), "999"),
            (("fill_equal_time_group",), "1"),
            (("cash_delta_quote_atoms",), "0"),
        ],
        seal_content_id=seal_content_id,
        validate_contract=validate_contract,
    )


def test_portfolio_state_semantic_matrix() -> None:
    from build_finance.crypto_replay.content_ids import seal_content_id
    from build_finance.crypto_replay.schema_registry import validate_contract

    document = _example("trading.portfolio-state/v1")
    duplicate_balance = [document["balances"][0], document["balances"][0]]
    _assert_semantic_mutations_rejected(
        document,
        [
            (("balances", 0, "total_atoms"), "0"),
            (("balances",), duplicate_balance),
            (("kill_latched",), True),
        ],
        seal_content_id=seal_content_id,
        validate_contract=validate_contract,
    )


def test_ledger_record_semantic_matrix() -> None:
    from build_finance.crypto_replay.content_ids import seal_content_id
    from build_finance.crypto_replay.schema_registry import validate_contract

    document = _example("trading.ledger-record/v1")
    _assert_semantic_mutations_rejected(
        document,
        [
            (("object_schema",), "trading.raw-event/v1"),
            (("object_sha256",), "0" * 64),
            (("entries",), []),
        ],
        seal_content_id=seal_content_id,
        validate_contract=validate_contract,
    )


def test_registry_rejects_unsupported_keywords_and_remote_refs() -> None:
    from build_finance.crypto_replay.schema_registry import SchemaRegistry

    base = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:build-finance:contract:test-contract:v1",
        "x-contract-schema": "trading.test-contract/v1",
        "type": "object",
        "required": [],
        "properties": {},
        "additionalProperties": False,
    }
    unsupported = {**base, "format": "custom"}
    remote_ref = {**base, "$ref": "https://example.invalid/remote.schema.json"}

    with pytest.raises(ValueError):
        SchemaRegistry.from_documents([unsupported])
    with pytest.raises(ValueError):
        SchemaRegistry.from_documents([remote_ref])


def test_local_and_jsonschema_oracles_agree_on_structural_vectors() -> None:
    from build_finance.crypto_replay.schema_registry import get_schema_document, validate_contract
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource

    schemas = {schema_id: get_schema_document(schema_id) for schema_id in EXAMPLES}

    def reject_unknown_uri(uri: str) -> Resource[Any]:
        raise AssertionError(f"unexpected schema retrieval: {uri}")

    registry = Registry(retrieve=reject_unknown_uri).with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas.values()
    )

    for schema_id, schema in schemas.items():
        Draft202012Validator.check_schema(schema)
        positive = _example(schema_id)
        negative = {**positive, "unknown_property": True}
        validator = Draft202012Validator(schema, registry=registry)
        for document in (positive, negative):
            local_valid = not validate_contract(document, expected_schema=schema_id)
            oracle_valid = not tuple(validator.iter_errors(document))
            assert local_valid == oracle_valid
