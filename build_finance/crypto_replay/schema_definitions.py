"""Frozen contract inventory and explicit in-repository schema definitions.

Task T01 adds primary schema dictionaries to ``PRIMARY_SCHEMA_DOCUMENTS``;
later T02 tasks populate the supporting and attachment dictionaries.  The
inventory is complete from the start so content-ID and code-generation scope
cannot drift while those definitions are added incrementally.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from build_finance.crypto_replay.canonical import JsonObject
from build_finance.crypto_replay.schema_model import ContractFamily, ContractSpec

_PRIMARY_SELF_ID_FIELDS = {
    "trading.raw-event/v1": "event_id",
    "trading.feature-snapshot/v1": "snapshot_id",
    "trading.model-signal/v1": "signal_id",
    "trading.risk-decision/v1": "risk_decision_id",
    "trading.simulated-order-intent/v1": "intent_id",
    "trading.simulated-fill-receipt/v1": "fill_receipt_id",
    "trading.portfolio-state/v1": "portfolio_state_id",
    "trading.ledger-record/v1": "ledger_record_id",
}
_SUPPORTING_SELF_ID_FIELDS = {
    "trading.fixture-manifest/v1": "fixture_manifest_sha256",
    "trading.replay-risk-config/v1": "config_sha256",
    "trading.source-admission-receipt/v1": "source_admission_receipt_id",
    "trading.config-admission-receipt/v1": "config_admission_receipt_id",
    "trading.run-closure-receipt/v1": "run_closure_receipt_id",
    "trading.execution-quarantine-receipt/v1": "execution_quarantine_receipt_id",
    "trading.model-registry/v1": "model_registry_sha256",
    "trading.model-signal-manifest/v1": "model_signal_manifest_sha256",
    "trading.model-validation-receipt/v1": "model_validation_receipt_id",
    "trading.reconciliation-receipt/v1": "reconciliation_receipt_id",
    "trading.run-receipt/v1": "run_receipt_id",
    "trading.benchmark-measurement/v1": "benchmark_measurement_id",
    "trading.benchmark-receipt/v1": "benchmark_receipt_id",
}

PRIMARY_SELF_ID_FIELDS = MappingProxyType(_PRIMARY_SELF_ID_FIELDS)
SUPPORTING_SELF_ID_FIELDS = MappingProxyType(_SUPPORTING_SELF_ID_FIELDS)
SELF_ID_FIELDS = MappingProxyType({**_PRIMARY_SELF_ID_FIELDS, **_SUPPORTING_SELF_ID_FIELDS})

PRIMARY_SCHEMA_IDS = tuple(_PRIMARY_SELF_ID_FIELDS)
SUPPORTING_SCHEMA_IDS = tuple(_SUPPORTING_SELF_ID_FIELDS)
ATTACHMENT_SCHEMA_IDS = (
    "trading.adverse-fill-draw-key/v1",
    "trading.availability-schedule/v1",
    "trading.benchmark-manifest/v1",
    "trading.benchmark-metrics/v1",
    "trading.benchmark-request/v1",
    "trading.counter-capacity/v1",
    "trading.execution-footprint-component/v1",
    "trading.execution-transition-footprint/v1",
    "trading.execution-transition-key/v1",
    "trading.fill-idempotency-key/v1",
    "trading.force-close-state-envelope/v1",
    "trading.group-mark-key/v1",
    "trading.hardware-profile/v1",
    "trading.model-attempt-footprint/v1",
    "trading.model-request-key/v1",
    "trading.model-validation-attempt-key/v1",
    "trading.normalized-event-set/v1",
    "trading.preregistered-thresholds/v1",
    "trading.reconciliation-arithmetic-operands/v1",
    "trading.reconciliation-arithmetic-range-key/v1",
    "trading.reservation-key/v1",
    "trading.risk-idempotency-key/v1",
    "trading.run-closure-fill-candidate-semantic/v1",
    "trading.run-closure-full-fill-proof-row/v1",
    "trading.run-closure-full-fill-proof-set/v1",
    "trading.run-closure-reference-set/v1",
    "trading.source-tree/v1",
)
ALL_JSON_SCHEMA_IDS = (*PRIMARY_SCHEMA_IDS, *SUPPORTING_SCHEMA_IDS, *ATTACHMENT_SCHEMA_IDS)


def schema_filename(schema_id: str) -> str:
    """Return the exact generated filename for a trading contract tag."""
    if not schema_id.startswith("trading.") or not schema_id.endswith("/v1"):
        raise ValueError(f"invalid trading contract schema tag: {schema_id!r}")
    return f"{schema_id.removeprefix('trading.').replace('/', '-')}.schema.json"


def json_schema_id(schema_id: str) -> str:
    """Return the local absolute JSON Schema URN for a contract tag."""
    if not schema_id.startswith("trading.") or not schema_id.endswith("/v1"):
        raise ValueError(f"invalid trading contract schema tag: {schema_id!r}")
    contract_name, version = schema_id.removeprefix("trading.").split("/", maxsplit=1)
    if not contract_name or not version:
        raise ValueError(f"invalid trading contract schema tag: {schema_id!r}")
    return f"urn:build-finance:contract:{contract_name}:{version}"


def _specs(
    schema_ids: tuple[str, ...],
    family: ContractFamily,
    self_id_fields: dict[str, str] | None = None,
) -> tuple[ContractSpec, ...]:
    return tuple(
        ContractSpec(
            schema_id=schema_id,
            self_id_field=None if self_id_fields is None else self_id_fields[schema_id],
            family=family,
            schema_filename=schema_filename(schema_id),
        )
        for schema_id in schema_ids
    )


PRIMARY_CONTRACT_SPECS = _specs(PRIMARY_SCHEMA_IDS, "PRIMARY", _PRIMARY_SELF_ID_FIELDS)
SUPPORTING_CONTRACT_SPECS = _specs(SUPPORTING_SCHEMA_IDS, "SUPPORTING", _SUPPORTING_SELF_ID_FIELDS)
ATTACHMENT_CONTRACT_SPECS = _specs(ATTACHMENT_SCHEMA_IDS, "ATTACHMENT")
CONTRACT_SPECS = (*PRIMARY_CONTRACT_SPECS, *SUPPORTING_CONTRACT_SPECS, *ATTACHMENT_CONTRACT_SPECS)
CONTRACT_SPECS_BY_SCHEMA = MappingProxyType({spec.schema_id: spec for spec in CONTRACT_SPECS})

_DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"
_SHA256_PATTERN = "^[0-9a-f]{64}$"
_U64_PATTERN = "^(0|[1-9][0-9]*)$"
_I128_PATTERN = "^(0|-?[1-9][0-9]*)$"
_RFC3339_NS_UTC_PATTERN = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{9}Z$"
_RFC3339_FULL_DATE_PATTERN = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$"
_SAFE_RELATIVE_PATH_PATTERN = (
    r"^(?![A-Za-z]:)(?!/)(?!\.{1,2}(?:/|$))(?!.*(?:/\.{1,2})(?:/|$))(?!.*//)[^/\\:\x00]+(?:/[^/\\:\x00]+)*$"
)


def _closed_object(properties: Mapping[str, JsonObject]) -> JsonObject:
    """Return one recursively closed object node with every property required."""
    copied = dict(properties)
    return {
        "type": "object",
        "required": list(copied),
        "properties": copied,
        "additionalProperties": False,
    }


def _array(items: JsonObject, *, unique: bool = False, maximum: int | None = None) -> JsonObject:
    schema: JsonObject = {"type": "array", "items": items}
    if unique:
        schema["uniqueItems"] = True
    if maximum is not None:
        schema["maxItems"] = maximum
    return schema


def _ref(name: str) -> JsonObject:
    return {"$ref": f"#/$defs/{name}"}


def _nullable_ref(name: str) -> JsonObject:
    return {"anyOf": [_ref(name), {"type": "null"}]}


def _shared_scalar_definitions() -> JsonObject:
    """Return the frozen scalar aliases embedded in every primary schema."""
    return {
        "sha256": {"type": "string", "pattern": _SHA256_PATTERN},
        "ContentID": {"type": "string", "pattern": _SHA256_PATTERN},
        "CausalDigest": {"type": "string", "pattern": _SHA256_PATTERN},
        "u64s": {"type": "string", "pattern": _U64_PATTERN},
        "uints": {"type": "string", "pattern": _U64_PATTERN},
        "i128s": {"type": "string", "pattern": _I128_PATTERN},
        "sq18s": {"type": "string", "pattern": _I128_PATTERN},
        "uq18s": {"type": "string", "pattern": _U64_PATTERN},
        "rfc3339_ns_utc": {"type": "string", "pattern": _RFC3339_NS_UTC_PATTERN},
        "rfc3339_full_date": {"type": "string", "pattern": _RFC3339_FULL_DATE_PATTERN},
        "safe_relative_path": {"type": "string", "pattern": _SAFE_RELATIVE_PATH_PATTERN},
        "bounded_utf8_registry_string": {"type": "string", "minLength": 1, "maxLength": 128},
        "bounded_utf8_registry_string_256": {"type": "string", "minLength": 1, "maxLength": 256},
    }


def _primary_schema(schema_id: str, properties: Mapping[str, JsonObject]) -> JsonObject:
    document = _closed_object(properties)
    document.update(
        {
            "$schema": _DRAFT_2020_12,
            "$id": json_schema_id(schema_id),
            "x-contract-schema": schema_id,
            "$defs": _shared_scalar_definitions(),
        }
    )
    return document


_QUALITY_FLAGS = [
    "GAP_BEFORE",
    "MISSING_EVENT_TIME",
    "NON_EXECUTABLE",
    "PROVIDER_REVISION",
    "RETRACTED_SOURCE",
    "STALE_SOURCE",
]

_RISK_REASON_CODES = [
    "RISK_CONFIG_MISSING",
    "RISK_CONFIG_INVALID",
    "RISK_SEQUENCE_INVALID",
    "RISK_STATE_UNRECONCILED",
    "RISK_KILL_LATCHED",
    "RISK_SESSION_CLOSED",
    "RISK_EVENT_STALE",
    "RISK_DECIMALS_MISMATCH",
    "RISK_ARITHMETIC_RANGE",
    "RISK_NONPOSITIVE_EQUITY",
    "RISK_SESSION_LOSS",
    "RISK_DRAWDOWN",
    "RISK_STOP_MISSING",
    "RISK_INSUFFICIENT_BALANCE",
    "RISK_RESERVATION_CONFLICT",
    "RISK_INTENT_PENDING",
    "RISK_MIN_NOTIONAL",
    "RISK_MAX_NOTIONAL",
    "RISK_PARTICIPATION",
    "RISK_IMPACT",
    "RISK_CONCENTRATION",
    "RISK_NO_ACTION",
    "RISK_RUN_END_EXIT",
    "RISK_KILL_EXIT",
    "RISK_STOP_TRIGGERED",
    "RISK_TAKE_TRIGGERED",
]

_FILL_REASON_CODES = [
    "FILL_SAME_OR_EARLIER_EVENT",
    "FILL_KILL_LATCHED",
    "FILL_SESSION_END",
    "FILL_NO_NEXT_EVENT",
    "FILL_STALE_EVENT",
    "FILL_NEXT_EVENT_NON_EXECUTABLE",
    "FILL_DECIMALS_MISMATCH",
    "FILL_ZERO_CAPACITY",
    "FILL_PARTICIPATION",
    "FILL_ARITHMETIC_RANGE",
    "FILL_IMPACT",
    "FILL_FEE_CAP",
    "FILL_FEE_EXCEEDS_PROCEEDS",
    "FILL_INSUFFICIENT_RESERVATION",
    "FILL_PARTIAL",
]

_RECONCILIATION_REASON_CODES = [
    "RECONCILIATION_IDEMPOTENCY_CONFLICT",
    "RECONCILIATION_MODEL_ATTEMPT_INTEGRITY",
    "RECONCILIATION_EXECUTION_TRANSITION_INTEGRITY",
    "RECONCILIATION_ARITHMETIC_RANGE",
    "RECONCILIATION_ACCOUNT_RESIDUAL",
    "RECONCILIATION_ASSET_RESIDUAL",
    "RECONCILIATION_PNL_RESIDUAL",
    "RECONCILIATION_FEE_RESIDUAL",
    "RECONCILIATION_EQUITY_RESIDUAL",
    "RECONCILIATION_RESERVATION_RESIDUAL",
    "RECONCILIATION_INTENT_CARDINALITY",
    "RECONCILIATION_INTENT_RESERVATION_BIJECTION",
    "RECONCILIATION_ABSOLUTE_STATE_INVARIANT",
    "RECONCILIATION_RUN_END_UNCLOSED",
    "RECONCILIATION_MISMATCH",
]

_LATCHING_RISK_REASON_CODES = [
    "RISK_CONFIG_MISSING",
    "RISK_CONFIG_INVALID",
    "RISK_SEQUENCE_INVALID",
    "RISK_STATE_UNRECONCILED",
    "RISK_DECIMALS_MISMATCH",
    "RISK_ARITHMETIC_RANGE",
    "RISK_NONPOSITIVE_EQUITY",
    "RISK_SESSION_LOSS",
    "RISK_DRAWDOWN",
    "RISK_RESERVATION_CONFLICT",
]


def raw_event_schema() -> JsonObject:
    """Return the exhaustive closed ``trading.raw-event/v1`` JSON Schema."""
    source_position = _closed_object(
        {
            "slot": _ref("u64s"),
            "transaction_index": {"type": "integer", "minimum": 0, "maximum": 4_294_967_295},
            "instruction_index": {"type": "integer", "minimum": 0, "maximum": 4_294_967_295},
            "event_index": {"type": "integer", "minimum": 0, "maximum": 4_294_967_295},
            "source_native_event_id": _ref("bounded_utf8_registry_string_256"),
            "source_subsequence": _ref("u64s"),
        }
    )
    revision = _closed_object(
        {
            "kind": {"enum": ["ORIGINAL", "CORRECTION", "RETRACTION"]},
            "supersedes_event_id": _nullable_ref("ContentID"),
            "retracts_event_id": _nullable_ref("ContentID"),
            "availability_slot": _ref("u64s"),
            "availability_admission_sequence": _ref("u64s"),
        }
    )
    market = _closed_object(
        {
            "base_amount_atoms": _ref("u64s"),
            "quote_amount_atoms": _ref("u64s"),
            "route_capacity_base_atoms": _ref("u64s"),
            "liquidity_quote_atoms": _ref("u64s"),
            "venue_fee_quote_atoms": _ref("u64s"),
            "priority_fee_quote_atoms": _ref("u64s"),
            "route_impact_bps": {"type": "integer", "minimum": 0, "maximum": 1_000_000},
        }
    )
    schema_id = "trading.raw-event/v1"
    return _primary_schema(
        schema_id,
        {
            "schema": {"const": schema_id},
            "event_id": _ref("ContentID"),
            "fixture_manifest_sha256": _ref("ContentID"),
            "raw_payload_sha256": _ref("sha256"),
            "source_admission_receipt_id": _ref("ContentID"),
            "source_id": _ref("bounded_utf8_registry_string"),
            "source_kind": _ref("bounded_utf8_registry_string"),
            "source_revision": _ref("bounded_utf8_registry_string"),
            "network": {"const": "solana-mainnet"},
            "venue_profile": {"const": "solana-jupiter-fixture/v1"},
            "market_id": _ref("bounded_utf8_registry_string"),
            "base_mint": _ref("bounded_utf8_registry_string"),
            "quote_mint": _ref("bounded_utf8_registry_string"),
            "base_decimals": {"type": "integer", "minimum": 0, "maximum": 18},
            "quote_decimals": {"type": "integer", "minimum": 0, "maximum": 18},
            "event_kind": {"enum": ["ROUTE_QUOTE", "SWAP_OBSERVATION", "LIQUIDITY_SNAPSHOT", "SESSION_BOUNDARY"]},
            "source_position": source_position,
            "revision": revision,
            "event_time": _nullable_ref("rfc3339_ns_utc"),
            "observed_at": _ref("rfc3339_ns_utc"),
            "ingested_at": _ref("rfc3339_ns_utc"),
            "admission_sequence": _ref("u64s"),
            "source_sequence": _ref("u64s"),
            "ingest_sequence": _ref("u64s"),
            "equal_time_group": _ref("u64s"),
            "replay_clock_ns": _ref("u64s"),
            "executable": {"type": "boolean"},
            "market": market,
            "quality_flags": _array({"enum": _QUALITY_FLAGS}, unique=True, maximum=len(_QUALITY_FLAGS)),
        },
    )


_FEATURE_NAMES = [
    "atr_14_price_q18",
    "breakout_high_20_price_q18",
    "breakout_low_20_price_q18",
    "ema_fast_price_q18",
    "ema_slow_price_q18",
    "liquidity_quote_atoms",
    "mid_price_q18",
    "return_1_q18",
    "route_impact_bps",
    "rsi_14_q18",
    "stale_age_ns",
    "volume_20_base_atoms",
]


def feature_snapshot_schema() -> JsonObject:
    """Return the exhaustive closed ``trading.feature-snapshot/v1`` JSON Schema."""
    features = _closed_object(
        {
            "mid_price_q18": _nullable_ref("sq18s"),
            "return_1_q18": _nullable_ref("sq18s"),
            "ema_fast_price_q18": _nullable_ref("sq18s"),
            "ema_slow_price_q18": _nullable_ref("sq18s"),
            "rsi_14_q18": _nullable_ref("sq18s"),
            "atr_14_price_q18": _nullable_ref("sq18s"),
            "breakout_high_20_price_q18": _nullable_ref("sq18s"),
            "breakout_low_20_price_q18": _nullable_ref("sq18s"),
            "volume_20_base_atoms": _nullable_ref("u64s"),
            "liquidity_quote_atoms": _nullable_ref("u64s"),
            "stale_age_ns": _nullable_ref("u64s"),
            "route_impact_bps": {
                "anyOf": [
                    {"type": "integer", "minimum": 0, "maximum": 1_000_000},
                    {"type": "null"},
                ]
            },
            "history_count": {"type": "integer", "minimum": 0, "maximum": 4_294_967_295},
        }
    )
    schema_id = "trading.feature-snapshot/v1"
    return _primary_schema(
        schema_id,
        {
            "schema": {"const": schema_id},
            "snapshot_id": _ref("ContentID"),
            "feature_set_version": {"const": "solana-jupiter-deterministic-features/v1"},
            "feature_code_sha256": _ref("sha256"),
            "input_merkle_root_sha256": _nullable_ref("sha256"),
            "market_id": _ref("bounded_utf8_registry_string"),
            "base_mint": _ref("bounded_utf8_registry_string"),
            "quote_mint": _ref("bounded_utf8_registry_string"),
            "base_decimals": {"type": "integer", "minimum": 0, "maximum": 18},
            "quote_decimals": {"type": "integer", "minimum": 0, "maximum": 18},
            "decision_sequence": _ref("u64s"),
            "as_of_event_id": _nullable_ref("ContentID"),
            "as_of_admission_sequence": _ref("u64s"),
            "as_of_ingest_sequence": _ref("u64s"),
            "equal_time_group": _ref("u64s"),
            "replay_clock_ns": _ref("u64s"),
            "event_time": _nullable_ref("rfc3339_ns_utc"),
            "observed_at": _nullable_ref("rfc3339_ns_utc"),
            "ingested_at": _nullable_ref("rfc3339_ns_utc"),
            "features": features,
            "missing_features": _array(
                {"enum": _FEATURE_NAMES},
                unique=True,
                maximum=len(_FEATURE_NAMES),
            ),
        },
    )


def model_signal_schema() -> JsonObject:
    """Return the exhaustive closed ``trading.model-signal/v1`` JSON Schema."""
    schema_id = "trading.model-signal/v1"
    return _primary_schema(
        schema_id,
        {
            "schema": {"const": schema_id},
            "signal_id": _ref("ContentID"),
            "producer_id": _ref("bounded_utf8_registry_string"),
            "producer_sequence": _ref("u64s"),
            "model_id": _ref("bounded_utf8_registry_string"),
            "model_version": _ref("bounded_utf8_registry_string"),
            "runtime_profile_id": _ref("bounded_utf8_registry_string"),
            "calibration_version": _ref("bounded_utf8_registry_string"),
            "model_artifact_sha256": _ref("sha256"),
            "adapter_sha256": _nullable_ref("sha256"),
            "calibration_sha256": _ref("sha256"),
            "feature_snapshot_id": _ref("ContentID"),
            "feature_set_version": _ref("bounded_utf8_registry_string"),
            "market_id": _ref("bounded_utf8_registry_string"),
            "horizon_ns": _ref("u64s"),
            "decision_sequence": _ref("u64s"),
            "as_of_ingest_sequence": _ref("u64s"),
            "issued_replay_clock_ns": _ref("u64s"),
            "available_replay_clock_ns": _ref("u64s"),
            "decision_close_replay_clock_ns": _ref("u64s"),
            "ttl_ns": _ref("u64s"),
            "expires_replay_clock_ns": _ref("u64s"),
            "action": {"enum": ["ABSTAIN", "LONG_BIAS", "EXIT_BIAS"]},
            "score_q18": _ref("sq18s"),
            "probability_abstain_q18": _ref("uq18s"),
            "probability_long_bias_q18": _ref("uq18s"),
            "probability_exit_bias_q18": _ref("uq18s"),
            "uncertainty_q18": _ref("uq18s"),
            "ood_score_q18": _ref("uq18s"),
            "inference_duration_ns": _ref("u64s"),
        },
    )


def risk_decision_schema() -> JsonObject:
    """Return the exhaustive closed ``trading.risk-decision/v1`` JSON Schema."""
    nullable_bps: JsonObject = {
        "anyOf": [
            {"type": "integer", "minimum": 0, "maximum": 2_147_483_647},
            {"type": "null"},
        ]
    }
    measures = _closed_object(
        {
            "participation_bps": nullable_bps,
            "impact_bps": nullable_bps,
            "concentration_bps": nullable_bps,
            "drawdown_bps": nullable_bps,
            "projected_market_value_quote_atoms": _nullable_ref("u64s"),
            "projected_equity_quote_atoms": _nullable_ref("u64s"),
            "session_pnl_quote_atoms": _nullable_ref("i128s"),
            "stale_age_ns": _nullable_ref("u64s"),
        }
    )
    schema_id = "trading.risk-decision/v1"
    action: JsonObject = {"enum": ["HOLD", "ENTER_LONG", "EXIT_LONG"]}
    return _primary_schema(
        schema_id,
        {
            "schema": {"const": schema_id},
            "risk_decision_id": _ref("ContentID"),
            "decision_sequence": _ref("u64s"),
            "replay_clock_ns": _ref("u64s"),
            "feature_snapshot_id": _ref("ContentID"),
            "config_admission_receipt_id": _ref("ContentID"),
            "validated_config_sha256": _nullable_ref("ContentID"),
            "portfolio_state_before_id": _ref("ContentID"),
            "model_signal_status": {"enum": ["ABSENT", "ACCEPTED", "REJECTED", "EXPIRED", "DRIFT_DISABLED"]},
            "model_signal_id": _nullable_ref("ContentID"),
            "model_validation_receipt_id": _nullable_ref("ContentID"),
            "baseline_id": {
                "enum": [
                    "ALWAYS_HOLD_V1",
                    "MEAN_REVERSION_V1",
                    "BREAKOUT_V1",
                    "MOMENTUM_V1",
                    "TREND_V1",
                    None,
                ]
            },
            "baseline_action": action,
            "fused_action": action,
            "effective_action": action,
            "market_id": _ref("bounded_utf8_registry_string"),
            "verdict": {"enum": ["APPROVE", "REJECT", "KILL"]},
            "reason_codes": _array(
                {"enum": _RISK_REASON_CODES},
                unique=True,
                maximum=len(_RISK_REASON_CODES),
            ),
            "reference_price_q18": _nullable_ref("sq18s"),
            "requested_base_atoms": _ref("u64s"),
            "approved_base_atoms": _ref("u64s"),
            "requested_notional_quote_atoms": _ref("u64s"),
            "approved_notional_quote_atoms": _ref("u64s"),
            "measures": measures,
            "stop_price_q18": _nullable_ref("sq18s"),
            "take_price_q18": _nullable_ref("sq18s"),
            "reservation_id": _nullable_ref("ContentID"),
            "reserved_quote_atoms": _ref("u64s"),
            "reserved_base_atoms": _ref("u64s"),
        },
    )


def simulated_order_intent_schema() -> JsonObject:
    """Return the exhaustive closed simulated-order-intent v1 JSON Schema."""
    schema_id = "trading.simulated-order-intent/v1"
    return _primary_schema(
        schema_id,
        {
            "schema": {"const": schema_id},
            "intent_id": _ref("ContentID"),
            "intent_sequence": _ref("u64s"),
            "decision_sequence": _ref("u64s"),
            "risk_decision_id": _ref("ContentID"),
            "config_admission_receipt_id": _ref("ContentID"),
            "validated_config_sha256": _ref("ContentID"),
            "portfolio_state_before_id": _ref("ContentID"),
            "reservation_id": _ref("ContentID"),
            "market_id": _ref("bounded_utf8_registry_string"),
            "base_mint": _ref("bounded_utf8_registry_string"),
            "quote_mint": _ref("bounded_utf8_registry_string"),
            "base_decimals": {"type": "integer", "minimum": 0, "maximum": 18},
            "quote_decimals": {"type": "integer", "minimum": 0, "maximum": 18},
            "action": {"enum": ["OPEN_LONG", "CLOSE_LONG"]},
            "quantity_base_atoms": _ref("u64s"),
            "reference_price_q18": _ref("sq18s"),
            "stop_price_q18": _nullable_ref("sq18s"),
            "take_price_q18": _nullable_ref("sq18s"),
            "max_participation_bps": {"type": "integer", "minimum": 0, "maximum": 2_147_483_647},
            "max_impact_bps": {"type": "integer", "minimum": 0, "maximum": 2_147_483_647},
            "reserved_quote_atoms": _ref("u64s"),
            "reserved_base_atoms": _ref("u64s"),
            "created_replay_clock_ns": _ref("u64s"),
            "decision_ingest_sequence": _ref("u64s"),
            "decision_equal_time_group": _ref("u64s"),
            "fill_policy": {"const": "STRICT_NEXT_EVENT"},
            "time_in_force": {"const": "ONE_EVENT_GROUP"},
        },
    )


def simulated_fill_receipt_schema() -> JsonObject:
    """Return the exhaustive closed simulated-fill-receipt v1 JSON Schema."""
    schema_id = "trading.simulated-fill-receipt/v1"
    nonnegative_bps: JsonObject = {"type": "integer", "minimum": 0, "maximum": 2_147_483_647}
    return _primary_schema(
        schema_id,
        {
            "schema": {"const": schema_id},
            "fill_receipt_id": _ref("ContentID"),
            "receipt_sequence": _ref("u64s"),
            "decision_sequence": _ref("u64s"),
            "intent_id": _ref("ContentID"),
            "portfolio_state_before_id": _ref("ContentID"),
            "status": {"enum": ["FILLED", "PARTIAL", "REJECTED", "EXPIRED"]},
            "reason_codes": _array(
                {"enum": _FILL_REASON_CODES},
                unique=True,
                maximum=len(_FILL_REASON_CODES),
            ),
            "fill_event_id": _nullable_ref("ContentID"),
            "decision_ingest_sequence": _ref("u64s"),
            "decision_equal_time_group": _ref("u64s"),
            "fill_ingest_sequence": _nullable_ref("u64s"),
            "fill_equal_time_group": _nullable_ref("u64s"),
            "fill_replay_clock_ns": _nullable_ref("u64s"),
            "requested_base_atoms": _ref("u64s"),
            "filled_base_atoms": _ref("u64s"),
            "unfilled_base_atoms": _ref("u64s"),
            "gross_quote_atoms": _ref("u64s"),
            "venue_fee_quote_atoms": _ref("u64s"),
            "priority_fee_quote_atoms": _ref("u64s"),
            "simulation_fee_quote_atoms": _ref("u64s"),
            "cash_delta_quote_atoms": _ref("i128s"),
            "execution_price_q18": _nullable_ref("sq18s"),
            "participation_bps": nonnegative_bps,
            "reference_deviation_bps": nonnegative_bps,
            "impact_bps": nonnegative_bps,
            "fee_bps": nonnegative_bps,
            "adverse_fill_bps": nonnegative_bps,
            "adverse_fill_draw_key_sha256": _ref("sha256"),
            "adverse_fill_draw_sha256": _ref("sha256"),
            "released_quote_atoms": _ref("u64s"),
            "released_base_atoms": _ref("u64s"),
        },
    )


def portfolio_state_schema() -> JsonObject:
    """Return the exhaustive closed ``trading.portfolio-state/v1`` JSON Schema."""
    balance = _closed_object(
        {
            "mint": _ref("bounded_utf8_registry_string"),
            "decimals": {"type": "integer", "minimum": 0, "maximum": 18},
            "available_atoms": _ref("u64s"),
            "reserved_atoms": _ref("u64s"),
            "total_atoms": _ref("u64s"),
        }
    )
    position = _closed_object(
        {
            "market_id": _ref("bounded_utf8_registry_string"),
            "base_mint": _ref("bounded_utf8_registry_string"),
            "base_decimals": {"type": "integer", "minimum": 0, "maximum": 18},
            "quantity_base_atoms": _ref("u64s"),
            "reserved_base_atoms": _ref("u64s"),
            "cost_basis_quote_atoms": _ref("u64s"),
            "mark_price_q18": _ref("sq18s"),
            "market_value_quote_atoms": _ref("u64s"),
            "unrealized_pnl_quote_atoms": _ref("i128s"),
            "stop_price_q18": _ref("sq18s"),
            "take_price_q18": _ref("sq18s"),
        }
    )
    summary = _closed_object(
        {
            "realized_pnl_quote_atoms": _ref("i128s"),
            "unrealized_pnl_quote_atoms": _ref("i128s"),
            "cumulative_fees_quote_atoms": _ref("u64s"),
            "session_pnl_quote_atoms": _ref("i128s"),
            "equity_quote_atoms": _ref("u64s"),
            "peak_equity_quote_atoms": _ref("u64s"),
            "drawdown_bps": {"type": "integer", "minimum": 0, "maximum": 10_000},
        }
    )
    schema_id = "trading.portfolio-state/v1"
    kill_codes = [*_LATCHING_RISK_REASON_CODES, *_RECONCILIATION_REASON_CODES]
    return _primary_schema(
        schema_id,
        {
            "schema": {"const": schema_id},
            "portfolio_state_id": _ref("ContentID"),
            "state_sequence": _ref("u64s"),
            "as_of_ingest_sequence": _ref("u64s"),
            "equal_time_group": _ref("u64s"),
            "replay_clock_ns": _ref("u64s"),
            "previous_portfolio_state_id": _nullable_ref("ContentID"),
            "causation_schema": {
                "enum": [
                    "RUN_INITIALIZATION",
                    "GROUP_MARK_TO_MARKET",
                    "trading.simulated-order-intent/v1",
                    "trading.simulated-fill-receipt/v1",
                    "RISK_KILL",
                ]
            },
            "causation_id": _ref("CausalDigest"),
            "fixture_manifest_sha256": _ref("ContentID"),
            "config_admission_receipt_id": _ref("ContentID"),
            "validated_config_sha256": _nullable_ref("ContentID"),
            "quote_mint": _ref("bounded_utf8_registry_string"),
            "quote_decimals": {"type": "integer", "minimum": 0, "maximum": 18},
            "balances": _array(balance, unique=True),
            "positions": _array(position, unique=True),
            "summary": summary,
            "kill_latched": {"type": "boolean"},
            "kill_reason_codes": _array(
                {"enum": kill_codes},
                unique=True,
                maximum=len(kill_codes),
            ),
            "open_intent_ids": _array(_ref("ContentID"), unique=True),
        },
    )


_LEDGER_ACCOUNTS = [
    "CASH_AVAILABLE",
    "CASH_RESERVED",
    "POSITION_AVAILABLE",
    "POSITION_RESERVED",
    "TRADE_CLEARING",
    "FEE_EXPENSE",
    "REALIZED_PNL",
    "UNREALIZED_PNL",
    "EQUITY_CONTROL",
]

_STATE_BEARING_ACCOUNTS = [
    "CASH_AVAILABLE",
    "CASH_RESERVED",
    "POSITION_AVAILABLE",
    "POSITION_RESERVED",
]

_LEDGER_RECORD_TYPES = [
    "SOURCE_ADMISSION",
    "CONFIG_ADMISSION",
    "RAW_ADMISSION",
    "FEATURE_SNAPSHOT",
    "MODEL_VALIDATION",
    "MODEL_SIGNAL_ACCEPTED",
    "RISK_DECISION",
    "SIMULATED_INTENT",
    "SIMULATED_FILL",
    "PORTFOLIO_STATE",
    "RECONCILIATION",
    "KILL_STATE",
    "RUN_RECEIPT",
    "RUN_END",
]

_LEDGER_OBJECT_SCHEMAS = [
    "trading.source-admission-receipt/v1",
    "trading.config-admission-receipt/v1",
    "trading.raw-event/v1",
    "trading.feature-snapshot/v1",
    "trading.model-validation-receipt/v1",
    "trading.model-signal/v1",
    "trading.risk-decision/v1",
    "trading.simulated-order-intent/v1",
    "trading.simulated-fill-receipt/v1",
    "trading.portfolio-state/v1",
    "trading.reconciliation-receipt/v1",
    "trading.run-receipt/v1",
]


def ledger_record_schema() -> JsonObject:
    """Return the exhaustive closed ``trading.ledger-record/v1`` JSON Schema."""
    entry = _closed_object(
        {
            "account": {"enum": _LEDGER_ACCOUNTS},
            "asset_mint": _ref("bounded_utf8_registry_string"),
            "decimals": {"type": "integer", "minimum": 0, "maximum": 18},
            "amount_atoms": _ref("i128s"),
        }
    )
    asset_residual = _closed_object(
        {
            "asset_mint": _ref("bounded_utf8_registry_string"),
            "residual_atoms": _ref("i128s"),
        }
    )
    account_residual = _closed_object(
        {
            "asset_mint": _ref("bounded_utf8_registry_string"),
            "account": {"enum": _STATE_BEARING_ACCOUNTS},
            "residual_atoms": _ref("i128s"),
        }
    )
    reconciliation = _closed_object(
        {
            "portfolio_state_id": _ref("ContentID"),
            "asset_residuals": _array(asset_residual, unique=True),
            "equity_residual_quote_atoms": _ref("i128s"),
            "unmatched_reservation_count": _ref("u64s"),
            "account_residuals": _array(account_residual, unique=True),
            "realized_pnl_residual_quote_atoms": _ref("i128s"),
            "unrealized_pnl_residual_quote_atoms": _ref("i128s"),
            "fee_residual_quote_atoms": _ref("i128s"),
            "peak_equity_residual_quote_atoms": _ref("i128s"),
            "drawdown_residual_bps": _ref("i128s"),
        }
    )
    schema_id = "trading.ledger-record/v1"
    return _primary_schema(
        schema_id,
        {
            "schema": {"const": schema_id},
            "ledger_record_id": _ref("ContentID"),
            "ledger_sequence": _ref("u64s"),
            "previous_ledger_record_id": _nullable_ref("ContentID"),
            "run_receipt_id": _ref("ContentID"),
            "fixture_manifest_sha256": _ref("ContentID"),
            "config_admission_receipt_id": _ref("ContentID"),
            "validated_config_sha256": _nullable_ref("ContentID"),
            "record_type": {"enum": _LEDGER_RECORD_TYPES},
            "object_schema": {"enum": _LEDGER_OBJECT_SCHEMAS},
            "object_id": _ref("ContentID"),
            "object_sha256": _ref("sha256"),
            "decision_sequence": _nullable_ref("u64s"),
            "ingest_sequence": _nullable_ref("u64s"),
            "equal_time_group": _nullable_ref("u64s"),
            "replay_clock_ns": _nullable_ref("u64s"),
            "causation_ids": _array(_ref("CausalDigest"), unique=True),
            "entries": _array(entry, unique=True),
            "reconciliation": reconciliation,
        },
    )


PRIMARY_SCHEMA_DOCUMENTS: dict[str, JsonObject] = {
    "trading.raw-event/v1": raw_event_schema(),
    "trading.feature-snapshot/v1": feature_snapshot_schema(),
    "trading.model-signal/v1": model_signal_schema(),
    "trading.risk-decision/v1": risk_decision_schema(),
    "trading.simulated-order-intent/v1": simulated_order_intent_schema(),
    "trading.simulated-fill-receipt/v1": simulated_fill_receipt_schema(),
    "trading.portfolio-state/v1": portfolio_state_schema(),
    "trading.ledger-record/v1": ledger_record_schema(),
}
SUPPORTING_SCHEMA_DOCUMENTS: dict[str, JsonObject] = {}
ATTACHMENT_SCHEMA_DOCUMENTS: dict[str, JsonObject] = {}


def get_defined_schema_documents() -> dict[str, JsonObject]:
    """Return a fresh combined mapping after checking inventory ownership."""
    combined: dict[str, JsonObject] = {}
    families = (
        (PRIMARY_SCHEMA_DOCUMENTS, frozenset(PRIMARY_SCHEMA_IDS), "PRIMARY"),
        (SUPPORTING_SCHEMA_DOCUMENTS, frozenset(SUPPORTING_SCHEMA_IDS), "SUPPORTING"),
        (ATTACHMENT_SCHEMA_DOCUMENTS, frozenset(ATTACHMENT_SCHEMA_IDS), "ATTACHMENT"),
    )
    for documents, allowed, family in families:
        unknown = set(documents).difference(allowed)
        if unknown:
            raise ValueError(f"{family} schema definitions contain unknown contracts: {sorted(unknown)!r}")
        overlap = set(documents).intersection(combined)
        if overlap:
            raise ValueError(f"duplicate schema definitions: {sorted(overlap)!r}")
        combined.update(documents)
    return combined
