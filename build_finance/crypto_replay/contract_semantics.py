"""Pure cross-field semantics for primary and supporting replay contracts.

JSON Schema owns lexical shape.  These validators own only relationships
that the generated schema subset cannot express.  They perform no I/O and do
not resolve content identifiers.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Iterable, Mapping
from datetime import datetime
from typing import Any, Literal

from build_finance.crypto_replay.canonical import JsonValue
from build_finance.crypto_replay.formats import parse_bounded_decimal_string
from build_finance.crypto_replay.schema_model import ValidationIssue

_MAX_U64 = 18_446_744_073_709_551_615
_MIN_I128 = -170_141_183_460_469_231_731_687_303_715_884_105_728
_MAX_I128 = 170_141_183_460_469_231_731_687_303_715_884_105_727
_RFC3339_NS_UTC = re.compile(
    r"(?P<year>[0-9]{4})-(?P<month>[0-9]{2})-(?P<day>[0-9]{2})"
    r"T(?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}):(?P<second>[0-9]{2})"
    r"\.(?P<nanosecond>[0-9]{9})Z\Z"
)
_RFC3339_FULL_DATE = re.compile(r"(?P<year>[0-9]{4})-(?P<month>[0-9]{2})-(?P<day>[0-9]{2})\Z")

SOURCE_ADMISSION_REASON_PRECEDENCE = (
    "ADMISSION_NOT_LOCAL",
    "ADMISSION_RIGHTS_MISSING",
    "ADMISSION_MANIFEST_MISMATCH",
    "ADMISSION_HASH_MISMATCH",
    "ADMISSION_POINT_IN_TIME_MISSING",
    "ADMISSION_LEAKAGE_FIELD",
    "ADMISSION_UNIVERSE_BIASED",
    "ADMISSION_PROFILE_MISMATCH",
    "ADMISSION_POSITION_CONFLICT",
    "ADMISSION_SEQUENCE_INVALID",
    "ADMISSION_REVISION_CAUSALITY",
    "ADMISSION_REVISION_FORK",
    "ADMISSION_SET_NOT_CLOSED",
)
SOURCE_ADMISSION_QUARANTINE_REASONS = frozenset(SOURCE_ADMISSION_REASON_PRECEDENCE[8:])
CONFIG_ADMISSION_REASON_PRECEDENCE = (
    "CONFIG_MISSING",
    "CONFIG_BYTES_INVALID",
    "CONFIG_SCHEMA_INVALID",
    "CONFIG_ID_MISMATCH",
    "CONFIG_RANGE_INVALID",
)
_MAX_RUN_CLOSURE_PROOF_ROWS_V0 = 1_000_000

SemanticValidator = Callable[[Mapping[str, JsonValue]], tuple[ValidationIssue, ...]]


def _issue(code: str, path: tuple[str | int, ...], message: str) -> ValidationIssue:
    return ValidationIssue(code=code, path=path, message=message)


def _u64(value: object) -> int | None:
    try:
        return parse_bounded_decimal_string(value, minimum=0, maximum=_MAX_U64)
    except ValueError:
        return None


def _i128(value: object) -> int | None:
    try:
        return parse_bounded_decimal_string(value, minimum=_MIN_I128, maximum=_MAX_I128)
    except ValueError:
        return None


def _valid_utf8_registry(value: object, maximum_bytes: int) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        return len(value.encode("utf-8", errors="strict")) <= maximum_bytes
    except UnicodeEncodeError:
        return False


def _instant_key(value: object) -> tuple[int, ...] | None:
    if not isinstance(value, str):
        return None
    match = _RFC3339_NS_UTC.fullmatch(value)
    if match is None:
        return None
    parts = tuple(int(match.group(name)) for name in ("year", "month", "day", "hour", "minute", "second"))
    try:
        datetime(parts[0], parts[1], parts[2], parts[3], parts[4], parts[5])
    except ValueError:
        return None
    return (*parts, int(match.group("nanosecond")))


def _full_date_key(value: object) -> tuple[int, int, int] | None:
    if not isinstance(value, str):
        return None
    match = _RFC3339_FULL_DATE.fullmatch(value)
    if match is None:
        return None
    parts = tuple(int(match.group(name)) for name in ("year", "month", "day"))
    try:
        datetime(parts[0], parts[1], parts[2])
    except ValueError:
        return None
    return (parts[0], parts[1], parts[2])


def _sorted_unique(values: object, *, key: Callable[[Any], Any]) -> bool:
    return isinstance(values, list) and len(values) == len(set(values)) and values == sorted(values, key=key)


def _normalize_reason_codes(
    reason_codes: Iterable[str],
    precedence: tuple[str, ...],
) -> tuple[str, ...]:
    codes = tuple(reason_codes)
    if any(not isinstance(code, str) for code in codes):
        raise ValueError("reason code is not a string")
    if len(codes) != len(set(codes)):
        raise ValueError("duplicate reason code")
    unknown = tuple(code for code in codes if code not in precedence)
    if unknown:
        raise ValueError(f"unknown reason code: {unknown[0]}")
    order = {code: index for index, code in enumerate(precedence)}
    return tuple(sorted(codes, key=order.__getitem__))


def normalize_source_admission_reason_codes(reason_codes: Iterable[str]) -> tuple[str, ...]:
    """Return the unique closed source reason set in normative precedence."""
    return _normalize_reason_codes(reason_codes, SOURCE_ADMISSION_REASON_PRECEDENCE)


def derive_source_admission_status(
    reason_codes: Iterable[str],
) -> Literal["ADMITTED", "REJECTED", "QUARANTINED"]:
    """Derive source status from only the complete closed reason set."""
    normalized = normalize_source_admission_reason_codes(reason_codes)
    if not normalized:
        return "ADMITTED"
    if SOURCE_ADMISSION_QUARANTINE_REASONS.intersection(normalized):
        return "QUARANTINED"
    return "REJECTED"


def normalize_config_admission_reason_codes(reason_codes: Iterable[str]) -> tuple[str, ...]:
    """Return the unique closed config reason set in normative precedence."""
    return _normalize_reason_codes(reason_codes, CONFIG_ADMISSION_REASON_PRECEDENCE)


def validate_raw_event_semantics(document: Mapping[str, JsonValue]) -> tuple[ValidationIssue, ...]:
    """Validate RawEvent revision, availability, quality, and time semantics."""
    issues: list[ValidationIssue] = []
    registry_paths = (
        ("source_id",),
        ("source_kind",),
        ("source_revision",),
        ("market_id",),
        ("base_mint",),
        ("quote_mint",),
    )
    for registry_path in registry_paths:
        if not _valid_utf8_registry(document[registry_path[0]], 128):
            issues.append(_issue("semantic_registry", registry_path, "registry string exceeds 128 UTF-8 bytes"))

    source_position = document["source_position"]
    revision = document["revision"]
    market = document["market"]
    assert isinstance(source_position, Mapping) and isinstance(revision, Mapping) and isinstance(market, Mapping)
    if not _valid_utf8_registry(source_position["source_native_event_id"], 256):
        issues.append(
            _issue(
                "semantic_registry",
                ("source_position", "source_native_event_id"),
                "native event ID exceeds 256 UTF-8 bytes",
            )
        )

    u64_paths: tuple[tuple[str, ...], ...] = (
        ("source_position", "slot"),
        ("source_position", "source_subsequence"),
        ("revision", "availability_slot"),
        ("revision", "availability_admission_sequence"),
        ("admission_sequence",),
        ("source_sequence",),
        ("ingest_sequence",),
        ("equal_time_group",),
        ("replay_clock_ns",),
        ("market", "base_amount_atoms"),
        ("market", "quote_amount_atoms"),
        ("market", "route_capacity_base_atoms"),
        ("market", "liquidity_quote_atoms"),
        ("market", "venue_fee_quote_atoms"),
        ("market", "priority_fee_quote_atoms"),
    )
    parsed_u64: dict[tuple[str, ...], int] = {}
    for u64_path in u64_paths:
        value: object = document[u64_path[0]]
        if len(u64_path) == 2:
            assert isinstance(value, Mapping)
            value = value[u64_path[1]]
        parsed = _u64(value)
        if parsed is None:
            issues.append(_issue("semantic_u64", u64_path, "value exceeds the u64 authority range"))
        else:
            parsed_u64[u64_path] = parsed

    if document["base_mint"] == document["quote_mint"]:
        issues.append(_issue("semantic_mints", ("base_mint",), "base and quote mints must differ"))

    kind = revision["kind"]
    supersedes = revision["supersedes_event_id"]
    retracts = revision["retracts_event_id"]
    flags = document["quality_flags"]
    assert isinstance(flags, list)
    if kind == "ORIGINAL":
        if supersedes is not None or retracts is not None:
            issues.append(_issue("semantic_revision", ("revision",), "ORIGINAL requires both target IDs null"))
        availability = parsed_u64.get(("revision", "availability_slot"))
        slot = parsed_u64.get(("source_position", "slot"))
        if availability is not None and slot is not None and availability != slot:
            issues.append(
                _issue(
                    "semantic_availability",
                    ("revision", "availability_slot"),
                    "ORIGINAL availability slot must equal its source slot",
                )
            )
    elif kind == "CORRECTION":
        if supersedes is None or retracts is not None:
            issues.append(_issue("semantic_revision", ("revision",), "CORRECTION requires only supersedes_event_id"))
        if "PROVIDER_REVISION" not in flags:
            issues.append(_issue("semantic_revision", ("quality_flags",), "CORRECTION requires PROVIDER_REVISION"))
    elif kind == "RETRACTION":
        if retracts is None or supersedes is not None:
            issues.append(_issue("semantic_revision", ("revision",), "RETRACTION requires only retracts_event_id"))
        if "RETRACTED_SOURCE" not in flags or document["executable"] is not False:
            issues.append(
                _issue(
                    "semantic_revision",
                    ("quality_flags",),
                    "RETRACTION requires RETRACTED_SOURCE and non-executable status",
                )
            )

    availability_admission = parsed_u64.get(("revision", "availability_admission_sequence"))
    admission = parsed_u64.get(("admission_sequence",))
    if availability_admission is not None and admission is not None and availability_admission != admission:
        issues.append(
            _issue(
                "semantic_availability",
                ("revision", "availability_admission_sequence"),
                "revision availability admission sequence must equal admission_sequence",
            )
        )

    if not _sorted_unique(flags, key=lambda value: value.encode("utf-8")):
        issues.append(_issue("semantic_order", ("quality_flags",), "quality flags must be UTF-8 sorted and unique"))
    missing_time = "MISSING_EVENT_TIME" in flags
    if (document["event_time"] is None) != missing_time:
        issues.append(
            _issue(
                "semantic_event_time",
                ("event_time",),
                "event_time nullability must match MISSING_EVENT_TIME",
            )
        )

    event_key = None if document["event_time"] is None else _instant_key(document["event_time"])
    observed_key = _instant_key(document["observed_at"])
    ingested_key = _instant_key(document["ingested_at"])
    if observed_key is None:
        issues.append(_issue("semantic_time", ("observed_at",), "invalid RFC 3339 nanosecond UTC instant"))
    if ingested_key is None:
        issues.append(_issue("semantic_time", ("ingested_at",), "invalid RFC 3339 nanosecond UTC instant"))
    if document["event_time"] is not None and event_key is None:
        issues.append(_issue("semantic_time", ("event_time",), "invalid RFC 3339 nanosecond UTC instant"))
    if event_key is not None and observed_key is not None and event_key > observed_key:
        issues.append(_issue("semantic_time", ("event_time",), "event_time must not follow observed_at"))
    if observed_key is not None and ingested_key is not None and observed_key > ingested_key:
        issues.append(_issue("semantic_time", ("ingested_at",), "ingested_at must not precede observed_at"))

    blocking_flags = {"NON_EXECUTABLE", "RETRACTED_SOURCE", "STALE_SOURCE"}
    if blocking_flags.intersection(flags) and document["executable"] is not False:
        issues.append(_issue("semantic_executable", ("executable",), "blocking quality flags forbid execution"))
    if document["executable"] is True:
        positive_fields = (
            "base_amount_atoms",
            "quote_amount_atoms",
            "route_capacity_base_atoms",
            "liquidity_quote_atoms",
        )
        if document["event_kind"] not in {"ROUTE_QUOTE", "SWAP_OBSERVATION"} or kind == "RETRACTION":
            issues.append(_issue("semantic_executable", ("event_kind",), "event kind/revision cannot be executable"))
        for field in positive_fields:
            value = parsed_u64.get(("market", field))
            if value is not None and value <= 0:
                issues.append(
                    _issue("semantic_executable", ("market", field), "executable event value must be positive")
                )
    return tuple(issues)


_FEATURE_NAMES = (
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
)
_SIGNED_FEATURE_NAMES = (
    "mid_price_q18",
    "return_1_q18",
    "ema_fast_price_q18",
    "ema_slow_price_q18",
    "rsi_14_q18",
    "atr_14_price_q18",
    "breakout_high_20_price_q18",
    "breakout_low_20_price_q18",
)
_U64_FEATURE_NAMES = ("volume_20_base_atoms", "liquidity_quote_atoms", "stale_age_ns")


def validate_feature_snapshot_semantics(document: Mapping[str, JsonValue]) -> tuple[ValidationIssue, ...]:
    """Validate FeatureSnapshot zero-history and missing-feature alignment."""
    issues: list[ValidationIssue] = []
    for field in ("market_id", "base_mint", "quote_mint"):
        if not _valid_utf8_registry(document[field], 128):
            issues.append(_issue("semantic_registry", (field,), "registry string exceeds 128 UTF-8 bytes"))
    if document["base_mint"] == document["quote_mint"]:
        issues.append(_issue("semantic_mints", ("base_mint",), "base and quote mints must differ"))

    for field in (
        "decision_sequence",
        "as_of_admission_sequence",
        "as_of_ingest_sequence",
        "equal_time_group",
        "replay_clock_ns",
    ):
        if _u64(document[field]) is None:
            issues.append(_issue("semantic_u64", (field,), "value exceeds the u64 authority range"))

    features = document["features"]
    assert isinstance(features, Mapping)
    for field in _SIGNED_FEATURE_NAMES:
        value = features[field]
        if value is not None and _i128(value) is None:
            issues.append(_issue("semantic_i128", ("features", field), "feature exceeds signed i128 range"))
    for field in _U64_FEATURE_NAMES:
        value = features[field]
        if value is not None and _u64(value) is None:
            issues.append(_issue("semantic_u64", ("features", field), "feature exceeds the u64 range"))

    missing = document["missing_features"]
    expected_missing = [name for name in _FEATURE_NAMES if features[name] is None]
    if missing != expected_missing:
        issues.append(
            _issue(
                "semantic_missing_features",
                ("missing_features",),
                "missing_features must exactly name every null nullable feature in UTF-8 order",
            )
        )

    history_count = features["history_count"]
    assert isinstance(history_count, int)
    if history_count == 0 and any(features[name] is not None for name in _FEATURE_NAMES):
        issues.append(
            _issue(
                "semantic_zero_history",
                ("features", "history_count"),
                "zero history requires every nullable feature to be null",
            )
        )

    as_of_event_id = document["as_of_event_id"]
    merkle_root = document["input_merkle_root_sha256"]
    if (as_of_event_id is None) != (merkle_root is None):
        issues.append(
            _issue(
                "semantic_zero_history",
                ("as_of_event_id",),
                "as_of_event_id and input Merkle root must be null together",
            )
        )
    observed_at = document["observed_at"]
    ingested_at = document["ingested_at"]
    if (observed_at is None) != (ingested_at is None):
        issues.append(_issue("semantic_time", ("observed_at",), "observed_at and ingested_at must be null together"))
    if as_of_event_id is not None and (observed_at is None or ingested_at is None):
        issues.append(
            _issue(
                "semantic_time",
                ("observed_at",),
                "populated event evidence requires observed_at and ingested_at",
            )
        )
    if as_of_event_id is None:
        if any(document[field] is not None for field in ("event_time", "observed_at", "ingested_at")):
            issues.append(
                _issue(
                    "semantic_zero_history",
                    ("event_time",),
                    "a true zero-event snapshot requires all descriptive times null",
                )
            )
        if history_count != 0:
            issues.append(
                _issue(
                    "semantic_zero_history",
                    ("features", "history_count"),
                    "a true zero-event snapshot requires history_count zero",
                )
            )

    event_key = None if document["event_time"] is None else _instant_key(document["event_time"])
    observed_key = None if observed_at is None else _instant_key(observed_at)
    ingested_key = None if ingested_at is None else _instant_key(ingested_at)
    for field, value, key in (
        ("event_time", document["event_time"], event_key),
        ("observed_at", observed_at, observed_key),
        ("ingested_at", ingested_at, ingested_key),
    ):
        if value is not None and key is None:
            issues.append(_issue("semantic_time", (field,), "invalid RFC 3339 nanosecond UTC instant"))
    if event_key is not None and observed_key is not None and event_key > observed_key:
        issues.append(_issue("semantic_time", ("event_time",), "event_time must not follow observed_at"))
    if observed_key is not None and ingested_key is not None and observed_key > ingested_key:
        issues.append(_issue("semantic_time", ("ingested_at",), "ingested_at must not precede observed_at"))

    rsi = features["rsi_14_q18"]
    parsed_rsi = None if rsi is None else _i128(rsi)
    if parsed_rsi is not None and not 0 <= parsed_rsi <= 100_000_000_000_000_000_000:
        issues.append(_issue("semantic_rsi", ("features", "rsi_14_q18"), "RSI must be in [0,100*10^18]"))
    return tuple(issues)


def validate_model_signal_semantics(document: Mapping[str, JsonValue]) -> tuple[ValidationIssue, ...]:
    """Validate the flat directional signal's clocks and numeric tuple."""
    issues: list[ValidationIssue] = []
    for field in (
        "producer_id",
        "model_id",
        "model_version",
        "runtime_profile_id",
        "calibration_version",
        "feature_set_version",
        "market_id",
    ):
        if not _valid_utf8_registry(document[field], 128):
            issues.append(_issue("semantic_registry", (field,), "registry string exceeds 128 UTF-8 bytes"))

    u64_fields = (
        "producer_sequence",
        "horizon_ns",
        "decision_sequence",
        "as_of_ingest_sequence",
        "issued_replay_clock_ns",
        "available_replay_clock_ns",
        "decision_close_replay_clock_ns",
        "ttl_ns",
        "expires_replay_clock_ns",
        "inference_duration_ns",
    )
    parsed: dict[str, int] = {}
    for field in u64_fields:
        value = _u64(document[field])
        if value is None:
            issues.append(_issue("semantic_u64", (field,), "value exceeds the u64 authority range"))
        else:
            parsed[field] = value

    clock_fields = (
        "issued_replay_clock_ns",
        "available_replay_clock_ns",
        "decision_close_replay_clock_ns",
        "expires_replay_clock_ns",
    )
    if all(field in parsed for field in clock_fields):
        issued, available, close, expires = (parsed[field] for field in clock_fields)
        if not issued <= available <= close < expires:
            issues.append(
                _issue(
                    "semantic_clock_order",
                    ("issued_replay_clock_ns",),
                    "required clock order is issued <= available <= close < expires",
                )
            )
        ttl = parsed.get("ttl_ns")
        if ttl is not None and (issued + ttl > _MAX_U64 or issued + ttl != expires):
            issues.append(
                _issue(
                    "semantic_expiry",
                    ("expires_replay_clock_ns",),
                    "expires must equal issued + ttl without overflow",
                )
            )

    score = _i128(document["score_q18"])
    if score is None or not -1_000_000_000_000_000_000 <= score <= 1_000_000_000_000_000_000:
        issues.append(_issue("semantic_score", ("score_q18",), "score must be in [-10^18,10^18]"))

    probability_fields = (
        "probability_abstain_q18",
        "probability_long_bias_q18",
        "probability_exit_bias_q18",
    )
    probabilities: dict[str, int] = {}
    for field in (*probability_fields, "uncertainty_q18", "ood_score_q18"):
        value = _u64(document[field])
        if value is None or value > 1_000_000_000_000_000_000:
            issues.append(_issue("semantic_uq18", (field,), "value must be in [0,10^18]"))
        elif field in probability_fields:
            probabilities[field] = value
    if len(probabilities) == len(probability_fields):
        if sum(probabilities.values()) != 1_000_000_000_000_000_000:
            issues.append(_issue("semantic_probability", probability_fields, "probabilities must sum exactly to 10^18"))
        abstain = probabilities["probability_abstain_q18"]
        long_bias = probabilities["probability_long_bias_q18"]
        exit_bias = probabilities["probability_exit_bias_q18"]
        if long_bias > exit_bias and long_bias > abstain:
            probability_action = "LONG_BIAS"
        elif exit_bias > long_bias and exit_bias > abstain:
            probability_action = "EXIT_BIAS"
        else:
            probability_action = "ABSTAIN"
        action = document["action"]
        if action != probability_action:
            issues.append(
                _issue("semantic_action", ("action",), "action must equal the deterministic probability action")
            )
        if score is not None and ((action == "LONG_BIAS" and score <= 0) or (action == "EXIT_BIAS" and score >= 0)):
            issues.append(_issue("semantic_action", ("score_q18",), "directional action has the wrong score sign"))
    return tuple(issues)


_RISK_REASON_PRECEDENCE = (
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
)
_RISK_REASON_RANK = {code: rank for rank, code in enumerate(_RISK_REASON_PRECEDENCE)}
_RISK_CONFIG_REASON_FORMS = {
    ("RISK_CONFIG_MISSING",),
    ("RISK_CONFIG_INVALID",),
}
_RISK_FATAL_REASONS = frozenset(
    {
        "RISK_SEQUENCE_INVALID",
        "RISK_STATE_UNRECONCILED",
        "RISK_DECIMALS_MISMATCH",
        "RISK_ARITHMETIC_RANGE",
        "RISK_NONPOSITIVE_EQUITY",
        "RISK_RESERVATION_CONFLICT",
    }
)
_RISK_LATCH_PREFIXES = (
    ("RISK_SESSION_LOSS",),
    ("RISK_DRAWDOWN",),
    ("RISK_SESSION_LOSS", "RISK_DRAWDOWN"),
)
_RISK_EXIT_SUFFIXES = (
    (),
    ("RISK_STOP_TRIGGERED",),
    ("RISK_TAKE_TRIGGERED",),
    ("RISK_STOP_TRIGGERED", "RISK_TAKE_TRIGGERED"),
)
_RISK_EXIT_BOUNDARIES = (("RISK_RUN_END_EXIT",), ("RISK_KILL_EXIT",))
_RISK_EXIT_REASON_FORMS = (
    frozenset(_RISK_EXIT_SUFFIXES)
    | frozenset((*boundary, *suffix) for boundary in _RISK_EXIT_BOUNDARIES for suffix in _RISK_EXIT_SUFFIXES)
    | frozenset(
        (*latch, *boundary, *suffix)
        for latch in _RISK_LATCH_PREFIXES
        for boundary in _RISK_EXIT_BOUNDARIES
        for suffix in _RISK_EXIT_SUFFIXES
    )
)
_RISK_SUPPRESSED_EXIT_REASON_FORMS = _RISK_EXIT_REASON_FORMS - {()}
_RISK_KILL_LOSS_FORMS = frozenset(
    (*latch, *suffix) for latch in _RISK_LATCH_PREFIXES for suffix in ((), ("RISK_INTENT_PENDING",))
)
_RISK_REJECT_SINGLETONS = {
    ("RISK_SESSION_CLOSED",),
    ("RISK_INTENT_PENDING",),
}
_RISK_FORCE_DENIAL_REASONS = frozenset({"RISK_EVENT_STALE", "RISK_INSUFFICIENT_BALANCE", "RISK_NO_ACTION"})
_RISK_ORDINARY_DENIAL_REASONS = frozenset(
    {
        "RISK_EVENT_STALE",
        "RISK_STOP_MISSING",
        "RISK_INSUFFICIENT_BALANCE",
        "RISK_MIN_NOTIONAL",
        "RISK_MAX_NOTIONAL",
        "RISK_PARTICIPATION",
        "RISK_IMPACT",
        "RISK_CONCENTRATION",
    }
)


def _risk_reason_family_is_valid(
    *,
    verdict: object,
    action: object,
    reasons: list[JsonValue],
    validated_config: object,
) -> bool:
    reason_tuple = tuple(reasons)
    if verdict == "APPROVE":
        if action == "ENTER_LONG":
            return reason_tuple == ()
        if action == "EXIT_LONG":
            return reason_tuple in _RISK_EXIT_REASON_FORMS
        return False
    if verdict == "REJECT":
        if action != "HOLD":
            return False
        if reason_tuple in _RISK_REJECT_SINGLETONS:
            return True
        if "RISK_NO_ACTION" in reason_tuple:
            return bool(reason_tuple) and all(reason in _RISK_FORCE_DENIAL_REASONS for reason in reason_tuple)
        return bool(reason_tuple) and all(reason in _RISK_ORDINARY_DENIAL_REASONS for reason in reason_tuple)
    if verdict != "KILL" or action != "HOLD":
        return False
    if reason_tuple in _RISK_CONFIG_REASON_FORMS:
        return validated_config is None
    if validated_config is None:
        return False
    if reason_tuple == ("RISK_KILL_LATCHED",) or reason_tuple in _RISK_KILL_LOSS_FORMS:
        return True
    if "RISK_STATE_UNRECONCILED" in reason_tuple:
        return all(reason in {"RISK_SEQUENCE_INVALID", "RISK_STATE_UNRECONCILED"} for reason in reason_tuple)
    return bool(reason_tuple) and all(reason in _RISK_FATAL_REASONS for reason in reason_tuple)


def validate_risk_decision_semantics(document: Mapping[str, JsonValue]) -> tuple[ValidationIssue, ...]:
    """Validate RiskDecision evidence nullability, ordering, and authority tuple."""
    issues: list[ValidationIssue] = []
    if not _valid_utf8_registry(document["market_id"], 128):
        issues.append(_issue("semantic_registry", ("market_id",), "registry string exceeds 128 UTF-8 bytes"))
    for field in ("decision_sequence", "replay_clock_ns"):
        if _u64(document[field]) is None:
            issues.append(_issue("semantic_u64", (field,), "value exceeds the u64 authority range"))

    status = document["model_signal_status"]
    signal_id = document["model_signal_id"]
    validation_id = document["model_validation_receipt_id"]
    evidence_valid = (
        (status == "ABSENT" and signal_id is None and validation_id is None)
        or (status == "ACCEPTED" and signal_id is not None and validation_id is not None)
        or (status in {"REJECTED", "EXPIRED", "DRIFT_DISABLED"} and signal_id is None and validation_id is not None)
    )
    if not evidence_valid:
        issues.append(
            _issue(
                "semantic_model_evidence",
                ("model_signal_status",),
                "model status and nullable evidence IDs form an invalid tuple",
            )
        )

    reasons = document["reason_codes"]
    assert isinstance(reasons, list)
    if reasons != sorted(reasons, key=_RISK_REASON_RANK.__getitem__) or len(reasons) != len(set(reasons)):
        issues.append(
            _issue("semantic_reason_order", ("reason_codes",), "risk reasons must be unique and precedence sorted")
        )

    validated_config = document["validated_config_sha256"]
    baseline_id = document["baseline_id"]
    if (validated_config is None) != (baseline_id is None):
        issues.append(
            _issue(
                "semantic_config_tuple",
                ("validated_config_sha256",),
                "validated config and baseline ID must be null together",
            )
        )
    amount_fields = (
        "requested_base_atoms",
        "approved_base_atoms",
        "requested_notional_quote_atoms",
        "approved_notional_quote_atoms",
        "reserved_quote_atoms",
        "reserved_base_atoms",
    )
    amounts: dict[str, int] = {}
    for field in amount_fields:
        parsed_amount = _u64(document[field])
        if parsed_amount is None:
            issues.append(_issue("semantic_u64", (field,), "value exceeds the u64 authority range"))
        else:
            amounts[field] = parsed_amount

    for field in ("reference_price_q18", "stop_price_q18", "take_price_q18"):
        price_value = document[field]
        if price_value is not None and _i128(price_value) is None:
            issues.append(_issue("semantic_i128", (field,), "price exceeds the signed i128 range"))
    measures = document["measures"]
    assert isinstance(measures, Mapping)
    for field in (
        "projected_market_value_quote_atoms",
        "projected_equity_quote_atoms",
        "stale_age_ns",
    ):
        measure_value = measures[field]
        if measure_value is not None and _u64(measure_value) is None:
            issues.append(_issue("semantic_u64", ("measures", field), "measure exceeds the u64 range"))
    session_pnl = measures["session_pnl_quote_atoms"]
    if session_pnl is not None and _i128(session_pnl) is None:
        issues.append(_issue("semantic_i128", ("measures", "session_pnl_quote_atoms"), "measure exceeds i128 range"))

    verdict = document["verdict"]
    action = document["effective_action"]
    if not _risk_reason_family_is_valid(
        verdict=verdict,
        action=action,
        reasons=reasons,
        validated_config=validated_config,
    ):
        issues.append(
            _issue(
                "semantic_reason_family",
                ("reason_codes",),
                "verdict, effective action, and reasons do not match a closed risk family",
            )
        )

    suppressed_evidence = (
        status == "ABSENT"
        and signal_id is None
        and validation_id is None
        and document["baseline_action"] == "HOLD"
        and document["fused_action"] == "HOLD"
    )
    if (
        verdict == "APPROVE"
        and action == "EXIT_LONG"
        and tuple(reasons) in _RISK_SUPPRESSED_EXIT_REASON_FORMS
        and not suppressed_evidence
    ):
        issues.append(
            _issue(
                "semantic_suppressed_evidence",
                ("reason_codes",),
                "nonempty approved exit reasons require the exact suppressed-evidence tuple",
            )
        )
    zero_amount_authority = len(amounts) == len(amount_fields) and all(amounts[field] == 0 for field in amount_fields)
    zero_levels_and_reservation = (
        document["stop_price_q18"] is None and document["take_price_q18"] is None and document["reservation_id"] is None
    )
    zero_measures = all(measures[field] is None for field in measures)
    canonical_zero_authority = (
        document["reference_price_q18"] is None
        and zero_amount_authority
        and zero_levels_and_reservation
        and zero_measures
    )
    if validated_config is None:
        exact_config_tuple = (
            tuple(reasons) in _RISK_CONFIG_REASON_FORMS
            and baseline_id is None
            and suppressed_evidence
            and action == "HOLD"
            and verdict == "KILL"
            and canonical_zero_authority
        )
        if not exact_config_tuple:
            issues.append(
                _issue(
                    "semantic_config_tuple",
                    ("validated_config_sha256",),
                    "null config requires the complete missing/invalid zero-authority tuple",
                )
            )

    if len(amounts) == len(amount_fields):
        base_authority_valid = amounts["approved_base_atoms"] == amounts["requested_base_atoms"] > 0
        notional_authority_valid = amounts["approved_notional_quote_atoms"] == amounts[
            "requested_notional_quote_atoms"
        ] and (action == "EXIT_LONG" or amounts["approved_notional_quote_atoms"] > 0)
        approved_tuple = (
            base_authority_valid
            and notional_authority_valid
            and document["reservation_id"] is not None
            and action in {"ENTER_LONG", "EXIT_LONG"}
        )
        if verdict == "APPROVE":
            if not approved_tuple:
                issues.append(
                    _issue("semantic_approval", ("verdict",), "approved decision must preserve requested authority")
                )
            if action == "ENTER_LONG":
                reservation_valid = amounts["reserved_quote_atoms"] > 0 and amounts["reserved_base_atoms"] == 0
                reservation_path = ("reserved_quote_atoms",)
            elif action == "EXIT_LONG":
                reservation_valid = (
                    amounts["reserved_base_atoms"] == amounts["approved_base_atoms"] > 0
                    and amounts["reserved_quote_atoms"] == 0
                )
                reservation_path = ("reserved_base_atoms",)
            else:
                reservation_valid = False
                reservation_path = ("reserved_quote_atoms",)
            if not reservation_valid:
                issues.append(_issue("semantic_reservation", reservation_path, "reservation does not match action"))
        elif not (
            amounts["approved_base_atoms"] == 0
            and amounts["approved_notional_quote_atoms"] == 0
            and amounts["reserved_quote_atoms"] == 0
            and amounts["reserved_base_atoms"] == 0
            and document["reservation_id"] is None
            and action == "HOLD"
        ):
            issues.append(_issue("semantic_approval", ("verdict",), "non-approved decision retains authority"))

    reference = None if document["reference_price_q18"] is None else _i128(document["reference_price_q18"])
    stop = None if document["stop_price_q18"] is None else _i128(document["stop_price_q18"])
    take = None if document["take_price_q18"] is None else _i128(document["take_price_q18"])
    if verdict == "APPROVE":
        if reference is None or reference <= 0 or stop is None or stop <= 0 or take is None or take <= 0:
            issues.append(_issue("semantic_prices", ("reference_price_q18",), "approved prices must be positive"))
        elif action == "ENTER_LONG" and not stop < reference < take:
            issues.append(_issue("semantic_prices", ("stop_price_q18",), "entry requires stop < reference < take"))

    nonpositive_equity = "RISK_NONPOSITIVE_EQUITY" in reasons
    fatal_without_nonpositive = (
        verdict == "KILL"
        and bool(reasons)
        and all(reason in _RISK_FATAL_REASONS for reason in reasons)
        and not nonpositive_equity
    )
    latching_loss = verdict == "KILL" and action == "HOLD" and tuple(reasons) in _RISK_KILL_LOSS_FORMS
    if nonpositive_equity:
        levels_are_flat_or_positive_pair = (stop is None and take is None) or (
            stop is not None and stop > 0 and take is not None and take > 0
        )
        nonpositive_tuple = (
            validated_config is not None
            and baseline_id is not None
            and suppressed_evidence
            and verdict == "KILL"
            and action == "HOLD"
            and zero_amount_authority
            and document["reservation_id"] is None
            and (reference is None or reference > 0)
            and measures["participation_bps"] == 0
            and measures["concentration_bps"] is None
            and measures["drawdown_bps"] is not None
            and _u64(measures["projected_market_value_quote_atoms"]) is not None
            and _u64(measures["projected_equity_quote_atoms"]) == 0
            and _i128(measures["session_pnl_quote_atoms"]) is not None
            and levels_are_flat_or_positive_pair
        )
        if not nonpositive_tuple:
            issues.append(
                _issue(
                    "semantic_zero_authority",
                    ("reference_price_q18",),
                    "nonpositive equity requires its exact reason-owned authority tuple",
                )
            )
    elif fatal_without_nonpositive:
        exact_fatal_zero_tuple = (
            validated_config is not None
            and baseline_id is not None
            and suppressed_evidence
            and action == "HOLD"
            and canonical_zero_authority
        )
        if not exact_fatal_zero_tuple:
            issues.append(
                _issue(
                    "semantic_zero_authority",
                    ("reference_price_q18",),
                    "fatal zero reasons require the canonical valid-config zero tuple",
                )
            )
    elif latching_loss:
        levels_are_flat_or_positive_pair = (stop is None and take is None) or (
            stop is not None and stop > 0 and take is not None and take > 0
        )
        impact = measures["impact_bps"]
        stale_age = measures["stale_age_ns"]
        projected_market_value = _u64(measures["projected_market_value_quote_atoms"])
        projected_equity = _u64(measures["projected_equity_quote_atoms"])
        exact_latching_loss_tuple = (
            validated_config is not None
            and baseline_id is not None
            and suppressed_evidence
            and zero_amount_authority
            and document["reservation_id"] is None
            and (reference is None or reference > 0)
            and measures["participation_bps"] == 0
            and (impact is None) == (stale_age is None)
            and measures["concentration_bps"] is not None
            and measures["drawdown_bps"] is not None
            and projected_market_value is not None
            and projected_equity is not None
            and projected_equity > 0
            and _i128(measures["session_pnl_quote_atoms"]) is not None
            and levels_are_flat_or_positive_pair
        )
        if not exact_latching_loss_tuple:
            issues.append(
                _issue(
                    "semantic_loss_authority",
                    ("reason_codes",),
                    "latching loss reasons require suppressed zero authority and retained state measures",
                )
            )
    elif document["reference_price_q18"] is None and validated_config is not None:
        zero_history_levels = (stop is None and take is None) or (
            stop is not None and stop > 0 and take is not None and take > 0
        )
        zero_history_tuple = (
            validated_config is not None
            and baseline_id is not None
            and suppressed_evidence
            and action == "HOLD"
            and zero_amount_authority
            and document["reservation_id"] is None
            and zero_measures
            and zero_history_levels
        )
        if not zero_history_tuple:
            issues.append(
                _issue(
                    "semantic_zero_authority",
                    ("reference_price_q18",),
                    "this null-reference reason family requires the suppressed zero-history tuple",
                )
            )
    return tuple(issues)


def validate_simulated_order_intent_semantics(
    document: Mapping[str, JsonValue],
) -> tuple[ValidationIssue, ...]:
    """Validate intent action, quantity, reservation, and protective levels."""
    issues: list[ValidationIssue] = []
    for field in ("market_id", "base_mint", "quote_mint"):
        if not _valid_utf8_registry(document[field], 128):
            issues.append(_issue("semantic_registry", (field,), "registry string exceeds 128 UTF-8 bytes"))
    if document["base_mint"] == document["quote_mint"]:
        issues.append(_issue("semantic_mints", ("base_mint",), "base and quote mints must differ"))

    u64_fields = (
        "intent_sequence",
        "decision_sequence",
        "quantity_base_atoms",
        "reserved_quote_atoms",
        "reserved_base_atoms",
        "created_replay_clock_ns",
        "decision_ingest_sequence",
        "decision_equal_time_group",
    )
    parsed: dict[str, int] = {}
    for field in u64_fields:
        parsed_authority = _u64(document[field])
        if parsed_authority is None:
            issues.append(_issue("semantic_u64", (field,), "value exceeds the u64 authority range"))
        else:
            parsed[field] = parsed_authority
    if parsed.get("intent_sequence") == 0:
        issues.append(_issue("semantic_sequence", ("intent_sequence",), "intent sequence starts at one"))
    if parsed.get("quantity_base_atoms") == 0:
        issues.append(_issue("semantic_quantity", ("quantity_base_atoms",), "intent quantity must be positive"))

    reference = _i128(document["reference_price_q18"])
    stop = None if document["stop_price_q18"] is None else _i128(document["stop_price_q18"])
    take = None if document["take_price_q18"] is None else _i128(document["take_price_q18"])
    if reference is None or reference <= 0:
        issues.append(_issue("semantic_prices", ("reference_price_q18",), "reference price must be positive"))
    if stop is None or stop <= 0 or take is None or take <= 0:
        issues.append(_issue("semantic_prices", ("stop_price_q18",), "both protective levels must be positive"))

    action = document["action"]
    reserved_quote = parsed.get("reserved_quote_atoms")
    reserved_base = parsed.get("reserved_base_atoms")
    quantity = parsed.get("quantity_base_atoms")
    if action == "OPEN_LONG":
        if reserved_quote is not None and reserved_base is not None and not (reserved_quote > 0 and reserved_base == 0):
            issues.append(
                _issue("semantic_reservation", ("reserved_quote_atoms",), "OPEN_LONG requires quote reservation only")
            )
        if reference is not None and stop is not None and take is not None and not stop < reference < take:
            issues.append(_issue("semantic_prices", ("stop_price_q18",), "OPEN_LONG requires stop < reference < take"))
    elif (
        reserved_quote is not None
        and reserved_base is not None
        and quantity is not None
        and not (reserved_quote == 0 and reserved_base == quantity > 0)
    ):
        issues.append(
            _issue(
                "semantic_reservation",
                ("reserved_base_atoms",),
                "CLOSE_LONG requires full base-quantity reservation only",
            )
        )
    return tuple(issues)


_FILL_REASON_PRECEDENCE = (
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
)
_EXPIRY_FILL_REASONS = {"FILL_KILL_LATCHED", "FILL_SESSION_END", "FILL_NO_NEXT_EVENT"}


def validate_simulated_fill_receipt_semantics(
    document: Mapping[str, JsonValue],
) -> tuple[ValidationIssue, ...]:
    """Validate fill trigger, terminal status, quantity, fee, and release tuples."""
    issues: list[ValidationIssue] = []
    u64_fields = (
        "receipt_sequence",
        "decision_sequence",
        "decision_ingest_sequence",
        "decision_equal_time_group",
        "requested_base_atoms",
        "filled_base_atoms",
        "unfilled_base_atoms",
        "gross_quote_atoms",
        "venue_fee_quote_atoms",
        "priority_fee_quote_atoms",
        "simulation_fee_quote_atoms",
        "released_quote_atoms",
        "released_base_atoms",
    )
    parsed: dict[str, int] = {}
    for field in u64_fields:
        value = _u64(document[field])
        if value is None:
            issues.append(_issue("semantic_u64", (field,), "value exceeds the u64 authority range"))
        else:
            parsed[field] = value
    released_quote = parsed.get("released_quote_atoms")
    released_base = parsed.get("released_base_atoms")
    if released_quote is not None and released_base is not None and released_quote > 0 and released_base > 0:
        issues.append(
            _issue(
                "semantic_fill_release",
                ("released_quote_atoms",),
                "a terminal fill may release at most one reservation asset",
            )
        )
    if parsed.get("receipt_sequence") == 0:
        issues.append(_issue("semantic_sequence", ("receipt_sequence",), "receipt sequence starts at one"))

    fill_coordinate_fields = ("fill_ingest_sequence", "fill_equal_time_group", "fill_replay_clock_ns")
    fill_coordinates: dict[str, int] = {}
    for field in fill_coordinate_fields:
        coordinate_value = document[field]
        if coordinate_value is not None:
            parsed_value = _u64(coordinate_value)
            if parsed_value is None:
                issues.append(_issue("semantic_u64", (field,), "fill coordinate exceeds u64 range"))
            else:
                fill_coordinates[field] = parsed_value
    has_event = document["fill_event_id"] is not None
    coordinates_populated = len(fill_coordinates) == len(fill_coordinate_fields)
    coordinates_null = all(document[field] is None for field in fill_coordinate_fields)
    if not ((has_event and coordinates_populated) or (not has_event and coordinates_null)):
        issues.append(
            _issue(
                "semantic_fill_trigger",
                ("fill_event_id",),
                "fill event and all three fill coordinates must be populated or null together",
            )
        )

    reasons = document["reason_codes"]
    assert isinstance(reasons, list)
    status = document["status"]
    if status == "FILLED":
        expected_reason_tuple = reasons == []
    elif status == "PARTIAL":
        expected_reason_tuple = reasons == ["FILL_PARTIAL"]
    elif status == "EXPIRED":
        expected_reason_tuple = len(reasons) == 1 and reasons[0] in _EXPIRY_FILL_REASONS
    else:
        expected_reason_tuple = (
            len(reasons) == 1 and reasons[0] not in _EXPIRY_FILL_REASONS and reasons[0] != "FILL_PARTIAL"
        )
    if not expected_reason_tuple:
        issues.append(_issue("semantic_fill_status", ("reason_codes",), "status has the wrong exact reason tuple"))
    if not has_event and not (status == "EXPIRED" and set(reasons).issubset(_EXPIRY_FILL_REASONS)):
        issues.append(
            _issue("semantic_fill_trigger", ("fill_event_id",), "null fill event is reserved for exact expiry reasons")
        )
    if has_event and reasons and reasons[0] in _EXPIRY_FILL_REASONS:
        issues.append(_issue("semantic_fill_trigger", ("fill_event_id",), "expiry reason requires a null fill event"))

    decision_group = parsed.get("decision_equal_time_group")
    decision_ingest = parsed.get("decision_ingest_sequence")
    fill_group = fill_coordinates.get("fill_equal_time_group")
    fill_ingest = fill_coordinates.get("fill_ingest_sequence")
    same_or_earlier = reasons == ["FILL_SAME_OR_EARLIER_EVENT"]
    if has_event and fill_group is not None and decision_group is not None:
        if same_or_earlier and fill_group > decision_group:
            issues.append(
                _issue(
                    "semantic_fill_trigger",
                    ("fill_equal_time_group",),
                    "same-or-earlier reason requires a non-later group",
                )
            )
        elif not same_or_earlier and fill_group <= decision_group:
            issues.append(
                _issue(
                    "semantic_fill_trigger",
                    ("fill_equal_time_group",),
                    "ordinary event fill group must strictly follow the decision group",
                )
            )
    if has_event and not same_or_earlier and fill_ingest is not None and decision_ingest is not None:
        if fill_ingest <= decision_ingest:
            issues.append(
                _issue(
                    "semantic_fill_trigger",
                    ("fill_ingest_sequence",),
                    "ordinary fill ingest sequence must strictly follow the decision cutoff",
                )
            )

    if len(parsed) == len(u64_fields):
        requested = parsed["requested_base_atoms"]
        filled = parsed["filled_base_atoms"]
        unfilled = parsed["unfilled_base_atoms"]
        if requested <= 0 or filled + unfilled != requested:
            issues.append(
                _issue(
                    "semantic_fill_quantity", ("filled_base_atoms",), "filled + unfilled must equal positive requested"
                )
            )
        if status == "FILLED" and not (filled == requested and unfilled == 0):
            issues.append(_issue("semantic_fill_quantity", ("status",), "FILLED requires a complete fill"))
        if status == "PARTIAL" and not (0 < filled < requested and unfilled > 0):
            issues.append(
                _issue("semantic_fill_quantity", ("status",), "PARTIAL requires positive filled and unfilled")
            )

        fees = (
            parsed["venue_fee_quote_atoms"] + parsed["priority_fee_quote_atoms"] + parsed["simulation_fee_quote_atoms"]
        )
        cash_delta = _i128(document["cash_delta_quote_atoms"])
        if cash_delta is None:
            issues.append(_issue("semantic_i128", ("cash_delta_quote_atoms",), "cash delta exceeds i128 range"))
        if status in {"REJECTED", "EXPIRED"}:
            zero_fields = (
                "filled_base_atoms",
                "gross_quote_atoms",
                "venue_fee_quote_atoms",
                "priority_fee_quote_atoms",
                "simulation_fee_quote_atoms",
            )
            diagnostics_zero = all(
                document[field] == 0
                for field in (
                    "participation_bps",
                    "reference_deviation_bps",
                    "impact_bps",
                    "fee_bps",
                    "adverse_fill_bps",
                )
            )
            release_is_full_side = (parsed["released_quote_atoms"] > 0) != (parsed["released_base_atoms"] > 0)
            if not (
                all(parsed[field] == 0 for field in zero_fields)
                and unfilled == requested
                and cash_delta == 0
                and document["execution_price_q18"] is None
                and diagnostics_zero
                and release_is_full_side
            ):
                issues.append(
                    _issue("semantic_fill_denial", ("status",), "denial/expiry must use the exact zero/release tuple")
                )
        else:
            execution_price = _i128(document["execution_price_q18"])
            gross = parsed["gross_quote_atoms"]
            if filled <= 0 or gross <= 0 or execution_price is None or execution_price <= 0:
                issues.append(
                    _issue(
                        "semantic_fill_execution", ("execution_price_q18",), "non-zero fill requires positive execution"
                    )
                )
            if cash_delta is not None:
                buy_cash = -(gross + fees)
                sell_cash = gross - fees
                if cash_delta != buy_cash and not (sell_cash >= 0 and cash_delta == sell_cash):
                    issues.append(
                        _issue(
                            "semantic_fill_fees", ("cash_delta_quote_atoms",), "cash delta does not bind gross and fees"
                        )
                    )
    return tuple(issues)


_LATCHING_RISK_CODES = (
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
)
_RECONCILIATION_CODES = (
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
)
_KILL_REASON_PRECEDENCE = (*_LATCHING_RISK_CODES, *_RECONCILIATION_CODES)
_KILL_REASON_RANK = {code: rank for rank, code in enumerate(_KILL_REASON_PRECEDENCE)}


def validate_portfolio_state_semantics(document: Mapping[str, JsonValue]) -> tuple[ValidationIssue, ...]:
    """Validate portfolio ordering, reservation bijection, and exact summary fields."""
    issues: list[ValidationIssue] = []
    if not _valid_utf8_registry(document["quote_mint"], 128):
        issues.append(_issue("semantic_registry", ("quote_mint",), "registry string exceeds 128 UTF-8 bytes"))
    top_u64_fields = ("state_sequence", "as_of_ingest_sequence", "equal_time_group", "replay_clock_ns")
    top_values: dict[str, int] = {}
    for field in top_u64_fields:
        value = _u64(document[field])
        if value is None:
            issues.append(_issue("semantic_u64", (field,), "value exceeds the u64 authority range"))
        else:
            top_values[field] = value
    state_sequence = top_values.get("state_sequence")
    if state_sequence is not None:
        genesis_tuple = (
            state_sequence == 0
            and document["previous_portfolio_state_id"] is None
            and document["causation_schema"] == "RUN_INITIALIZATION"
        )
        non_genesis_tuple = (
            state_sequence > 0
            and document["previous_portfolio_state_id"] is not None
            and document["causation_schema"] != "RUN_INITIALIZATION"
        )
        if not (genesis_tuple or non_genesis_tuple):
            issues.append(
                _issue("semantic_state_lineage", ("state_sequence",), "state sequence and predecessor tuple is invalid")
            )

    balances = document["balances"]
    positions = document["positions"]
    open_intents = document["open_intent_ids"]
    kill_reasons = document["kill_reason_codes"]
    assert isinstance(balances, list) and isinstance(positions, list)
    assert isinstance(open_intents, list) and isinstance(kill_reasons, list)
    balance_mints = [row["mint"] for row in balances]
    position_markets = [row["market_id"] for row in positions]
    position_mints = [row["base_mint"] for row in positions]
    if balance_mints != sorted(balance_mints, key=lambda value: value.encode("utf-8")) or len(balance_mints) != len(
        set(balance_mints)
    ):
        issues.append(_issue("semantic_order", ("balances",), "balances must be sorted and unique by mint"))
    if position_markets != sorted(position_markets, key=lambda value: value.encode("utf-8")) or len(
        position_markets
    ) != len(set(position_markets)):
        issues.append(_issue("semantic_order", ("positions",), "positions must be sorted and unique by market"))
    if len(position_mints) != len(set(position_mints)):
        issues.append(_issue("semantic_positions", ("positions",), "position base mints must be unique"))
    if not _sorted_unique(open_intents, key=lambda value: value.encode("utf-8")):
        issues.append(_issue("semantic_order", ("open_intent_ids",), "open intent IDs must be sorted and unique"))
    if kill_reasons != sorted(kill_reasons, key=_KILL_REASON_RANK.__getitem__) or len(kill_reasons) != len(
        set(kill_reasons)
    ):
        issues.append(
            _issue("semantic_reason_order", ("kill_reason_codes",), "kill reasons must use global precedence")
        )
    if bool(kill_reasons) != bool(document["kill_latched"]):
        issues.append(
            _issue("semantic_kill_latch", ("kill_latched",), "kill latch is true iff kill reasons are non-empty")
        )

    parsed_balances: dict[str, tuple[int, int, int, int]] = {}
    for index, row in enumerate(balances):
        assert isinstance(row, Mapping)
        mint = row["mint"]
        assert isinstance(mint, str)
        if not _valid_utf8_registry(mint, 128):
            issues.append(_issue("semantic_registry", ("balances", index, "mint"), "mint exceeds 128 UTF-8 bytes"))
        balance_values = tuple(_u64(row[field]) for field in ("available_atoms", "reserved_atoms", "total_atoms"))
        if any(value is None for value in balance_values):
            issues.append(_issue("semantic_u64", ("balances", index), "balance exceeds the u64 authority range"))
            continue
        available, reserved, total = balance_values
        assert available is not None and reserved is not None and total is not None
        if available + reserved != total:
            issues.append(
                _issue("semantic_balance", ("balances", index, "total_atoms"), "total must equal available + reserved")
            )
        if mint != document["quote_mint"] and total == 0:
            issues.append(_issue("semantic_balance", ("balances",), "zero non-quote balances must be omitted"))
        parsed_balances[mint] = (available, reserved, total, row["decimals"])

    quote_mint = document["quote_mint"]
    quote_balance = parsed_balances.get(quote_mint) if isinstance(quote_mint, str) else None
    if quote_balance is None or quote_balance[3] != document["quote_decimals"]:
        issues.append(
            _issue("semantic_quote_balance", ("quote_mint",), "quote balance must exist with matching decimals")
        )

    position_unrealized = 0
    market_value_total = 0
    for index, row in enumerate(positions):
        assert isinstance(row, Mapping)
        for field in ("market_id", "base_mint"):
            if not _valid_utf8_registry(row[field], 128):
                issues.append(
                    _issue("semantic_registry", ("positions", index, field), "registry string exceeds 128 UTF-8 bytes")
                )
        u64_fields = (
            "quantity_base_atoms",
            "reserved_base_atoms",
            "cost_basis_quote_atoms",
            "market_value_quote_atoms",
        )
        position_values = {field: _u64(row[field]) for field in u64_fields}
        if any(value is None for value in position_values.values()):
            issues.append(_issue("semantic_u64", ("positions", index), "position exceeds the u64 authority range"))
            continue
        quantity = position_values["quantity_base_atoms"]
        reserved = position_values["reserved_base_atoms"]
        cost_basis = position_values["cost_basis_quote_atoms"]
        market_value = position_values["market_value_quote_atoms"]
        assert quantity is not None and reserved is not None and cost_basis is not None and market_value is not None
        if quantity <= 0:
            issues.append(
                _issue(
                    "semantic_position", ("positions", index, "quantity_base_atoms"), "open position must be positive"
                )
            )
        balance = parsed_balances.get(row["base_mint"])
        if balance is None or balance[2] != quantity or balance[1] != reserved or balance[3] != row["base_decimals"]:
            issues.append(
                _issue("semantic_position", ("positions", index), "position must exactly match its base balance")
            )
        unrealized = _i128(row["unrealized_pnl_quote_atoms"])
        if unrealized is None or unrealized != market_value - cost_basis:
            issues.append(
                _issue(
                    "semantic_position", ("positions", index, "unrealized_pnl_quote_atoms"), "unrealized P&L mismatch"
                )
            )
        else:
            position_unrealized += unrealized
        for field in ("mark_price_q18", "stop_price_q18", "take_price_q18"):
            price = _i128(row[field])
            if price is None or price <= 0:
                issues.append(_issue("semantic_prices", ("positions", index, field), "position price must be positive"))
        market_value_total += market_value

    non_quote_balance_mints = {mint for mint, values in parsed_balances.items() if mint != quote_mint and values[2] > 0}
    if non_quote_balance_mints != set(position_mints):
        issues.append(
            _issue("semantic_positions", ("balances",), "positive non-quote balances and positions must be bijective")
        )
    has_reservation = any(values[1] > 0 for values in parsed_balances.values())
    if has_reservation != bool(open_intents):
        issues.append(
            _issue("semantic_reservation", ("open_intent_ids",), "open intents and active reservations must coexist")
        )

    summary = document["summary"]
    assert isinstance(summary, Mapping)
    realized = _i128(summary["realized_pnl_quote_atoms"])
    unrealized = _i128(summary["unrealized_pnl_quote_atoms"])
    session = _i128(summary["session_pnl_quote_atoms"])
    for field in ("cumulative_fees_quote_atoms", "equity_quote_atoms", "peak_equity_quote_atoms"):
        if _u64(summary[field]) is None:
            issues.append(_issue("semantic_u64", ("summary", field), "summary value exceeds u64 range"))
    equity = _u64(summary["equity_quote_atoms"])
    peak = _u64(summary["peak_equity_quote_atoms"])
    if unrealized is None or unrealized != position_unrealized:
        issues.append(
            _issue("semantic_summary", ("summary", "unrealized_pnl_quote_atoms"), "summary unrealized P&L mismatch")
        )
    if realized is None or unrealized is None or session is None or session != realized + unrealized:
        issues.append(
            _issue(
                "semantic_summary",
                ("summary", "session_pnl_quote_atoms"),
                "session P&L must equal realized + unrealized",
            )
        )
    if equity is not None and quote_balance is not None and equity != quote_balance[2] + market_value_total:
        issues.append(_issue("semantic_summary", ("summary", "equity_quote_atoms"), "equity total mismatch"))
    if equity is not None and peak is not None:
        if peak < equity:
            issues.append(_issue("semantic_summary", ("summary", "peak_equity_quote_atoms"), "peak is below equity"))
        expected_drawdown = 0 if peak == 0 else ((peak - equity) * 10_000 + peak - 1) // peak
        if summary["drawdown_bps"] != expected_drawdown:
            issues.append(_issue("semantic_summary", ("summary", "drawdown_bps"), "drawdown ceiling mismatch"))
    return tuple(issues)


_LEDGER_OBJECT_SCHEMA_BY_TYPE = {
    "SOURCE_ADMISSION": "trading.source-admission-receipt/v1",
    "CONFIG_ADMISSION": "trading.config-admission-receipt/v1",
    "RAW_ADMISSION": "trading.raw-event/v1",
    "FEATURE_SNAPSHOT": "trading.feature-snapshot/v1",
    "MODEL_VALIDATION": "trading.model-validation-receipt/v1",
    "MODEL_SIGNAL_ACCEPTED": "trading.model-signal/v1",
    "RISK_DECISION": "trading.risk-decision/v1",
    "SIMULATED_INTENT": "trading.simulated-order-intent/v1",
    "SIMULATED_FILL": "trading.simulated-fill-receipt/v1",
    "PORTFOLIO_STATE": "trading.portfolio-state/v1",
    "RECONCILIATION": "trading.reconciliation-receipt/v1",
    "KILL_STATE": "trading.portfolio-state/v1",
    "RUN_RECEIPT": "trading.run-receipt/v1",
    "RUN_END": "trading.portfolio-state/v1",
}
_LEDGER_POSTING_REQUIRED_TYPES = {"SIMULATED_INTENT", "SIMULATED_FILL"}
_LEDGER_POSTING_PERMITTED_TYPES = {*_LEDGER_POSTING_REQUIRED_TYPES, "PORTFOLIO_STATE"}


def validate_ledger_record_semantics(document: Mapping[str, JsonValue]) -> tuple[ValidationIssue, ...]:
    """Validate ledger mapping, ordering, prior-head, balance, and self-cause rules."""
    issues: list[ValidationIssue] = []
    record_type = document["record_type"]
    assert isinstance(record_type, str)
    if document["object_schema"] != _LEDGER_OBJECT_SCHEMA_BY_TYPE[record_type]:
        issues.append(
            _issue(
                "semantic_object_schema",
                ("object_schema",),
                "object schema does not match the closed record-type mapping",
            )
        )
    if document["object_sha256"] != document["object_id"]:
        issues.append(_issue("semantic_object_digest", ("object_sha256",), "object digest must equal object ID"))

    ledger_sequence = _u64(document["ledger_sequence"])
    previous_ledger_record_id = document["previous_ledger_record_id"]
    if ledger_sequence is None:
        issues.append(_issue("semantic_u64", ("ledger_sequence",), "ledger sequence exceeds u64 range"))
    elif (ledger_sequence == 0) != (previous_ledger_record_id is None):
        issues.append(
            _issue(
                "semantic_ledger_head",
                ("previous_ledger_record_id",),
                "previous ledger ID is null exactly at sequence zero",
            )
        )
    if previous_ledger_record_id == document["ledger_record_id"]:
        issues.append(
            _issue(
                "semantic_ledger_head",
                ("previous_ledger_record_id",),
                "previous ledger ID must differ from the current record ID",
            )
        )
    for field in ("decision_sequence", "ingest_sequence", "equal_time_group", "replay_clock_ns"):
        value = document[field]
        if value is not None and _u64(value) is None:
            issues.append(_issue("semantic_u64", (field,), "causal coordinate exceeds u64 range"))

    causes = document["causation_ids"]
    assert isinstance(causes, list)
    if not _sorted_unique(causes, key=lambda value: value.encode("utf-8")):
        issues.append(_issue("semantic_order", ("causation_ids",), "causes must be digest-byte sorted and unique"))
    if (
        document["ledger_record_id"] in causes
        or document["object_id"] in causes
        or (previous_ledger_record_id is not None and previous_ledger_record_id in causes)
    ):
        issues.append(_issue("semantic_self_cause", ("causation_ids",), "record/object self-cause is forbidden"))

    entries = document["entries"]
    assert isinstance(entries, list)
    entry_keys = [(row["asset_mint"], row["account"]) for row in entries]
    sorted_entry_keys = sorted(entry_keys, key=lambda pair: (pair[0].encode("utf-8"), pair[1].encode("utf-8")))
    if entry_keys != sorted_entry_keys or len(entry_keys) != len(set(entry_keys)):
        issues.append(
            _issue("semantic_order", ("entries",), "entries must be sorted and unique by (asset_mint, account)")
        )
    if record_type in _LEDGER_POSTING_REQUIRED_TYPES and not entries:
        issues.append(_issue("semantic_entries", ("entries",), "reservation/fill ledger record requires postings"))
    elif record_type not in _LEDGER_POSTING_PERMITTED_TYPES and entries:
        issues.append(_issue("semantic_entries", ("entries",), "evidence-only ledger record forbids postings"))
    sums: dict[str, int] = {}
    decimals_by_asset: dict[str, int] = {}
    for index, row in enumerate(entries):
        assert isinstance(row, Mapping)
        asset = row["asset_mint"]
        assert isinstance(asset, str)
        if not _valid_utf8_registry(asset, 128):
            issues.append(
                _issue("semantic_registry", ("entries", index, "asset_mint"), "asset mint exceeds 128 UTF-8 bytes")
            )
        amount = _i128(row["amount_atoms"])
        if amount is None:
            issues.append(_issue("semantic_i128", ("entries", index, "amount_atoms"), "entry exceeds i128 range"))
            continue
        if amount == 0:
            issues.append(_issue("semantic_entries", ("entries", index, "amount_atoms"), "zero entry must be omitted"))
        sums[asset] = sums.get(asset, 0) + amount
        decimals = row["decimals"]
        assert isinstance(decimals, int)
        if asset in decimals_by_asset and decimals_by_asset[asset] != decimals:
            issues.append(_issue("semantic_entries", ("entries", index, "decimals"), "asset decimals disagree"))
        decimals_by_asset[asset] = decimals
    for asset, total in sums.items():
        if total != 0:
            issues.append(_issue("semantic_entries", ("entries",), f"entries for {asset!r} do not balance"))

    reconciliation = document["reconciliation"]
    assert isinstance(reconciliation, Mapping)
    asset_residuals = reconciliation["asset_residuals"]
    account_residuals = reconciliation["account_residuals"]
    assert isinstance(asset_residuals, list) and isinstance(account_residuals, list)
    asset_keys = [row["asset_mint"] for row in asset_residuals]
    if asset_keys != sorted(asset_keys, key=lambda value: value.encode("utf-8")) or len(asset_keys) != len(
        set(asset_keys)
    ):
        issues.append(
            _issue("semantic_order", ("reconciliation", "asset_residuals"), "asset residuals are not sorted unique")
        )
    account_keys = [(row["asset_mint"], row["account"]) for row in account_residuals]
    sorted_account_keys = sorted(
        account_keys,
        key=lambda pair: (pair[0].encode("utf-8"), pair[1].encode("utf-8")),
    )
    if account_keys != sorted_account_keys or len(account_keys) != len(set(account_keys)):
        issues.append(
            _issue(
                "semantic_order",
                ("reconciliation", "account_residuals"),
                "account residuals are not sorted unique",
            )
        )
    for collection_name, rows in (("asset_residuals", asset_residuals), ("account_residuals", account_residuals)):
        for index, row in enumerate(rows):
            if not _valid_utf8_registry(row["asset_mint"], 128):
                issues.append(
                    _issue(
                        "semantic_registry",
                        ("reconciliation", collection_name, index, "asset_mint"),
                        "asset mint exceeds 128 UTF-8 bytes",
                    )
                )
            if _i128(row["residual_atoms"]) != 0:
                issues.append(
                    _issue(
                        "semantic_residual",
                        ("reconciliation", collection_name, index, "residual_atoms"),
                        "persisted ledger residual must be zero",
                    )
                )
    for field in (
        "equity_residual_quote_atoms",
        "realized_pnl_residual_quote_atoms",
        "unrealized_pnl_residual_quote_atoms",
        "fee_residual_quote_atoms",
        "peak_equity_residual_quote_atoms",
        "drawdown_residual_bps",
    ):
        if _i128(reconciliation[field]) != 0:
            issues.append(
                _issue("semantic_residual", ("reconciliation", field), "persisted ledger residual must be zero")
            )
    unmatched_reservation_count = _u64(reconciliation["unmatched_reservation_count"])
    if unmatched_reservation_count is None:
        issues.append(
            _issue(
                "semantic_u64",
                ("reconciliation", "unmatched_reservation_count"),
                "unmatched reservation count exceeds u64 range",
            )
        )
    elif unmatched_reservation_count != 0:
        issues.append(
            _issue(
                "semantic_residual",
                ("reconciliation", "unmatched_reservation_count"),
                "persisted unmatched reservation count must be zero",
            )
        )
    return tuple(issues)


def validate_fixture_manifest_semantics(document: Mapping[str, JsonValue]) -> tuple[ValidationIssue, ...]:
    """Validate fixture keyed sets, identities, paths, and scalar authority."""
    issues: list[ValidationIssue] = []
    parsed_root: dict[str, int] = {}
    for field in (
        "initial_quote_atoms",
        "replay_tick_ns",
        "session_start_availability_slot",
        "session_end_availability_slot",
    ):
        parsed = _u64(document[field])
        if parsed is None:
            issues.append(_issue("semantic_u64", (field,), "value exceeds the u64 authority range"))
        else:
            parsed_root[field] = parsed
    for field in ("initial_quote_atoms", "replay_tick_ns", "session_start_availability_slot"):
        if parsed_root.get(field) == 0:
            issues.append(_issue("semantic_positive", (field,), "value must be positive"))
    start_slot = parsed_root.get("session_start_availability_slot")
    end_slot = parsed_root.get("session_end_availability_slot")
    if end_slot == 0:
        issues.append(_issue("semantic_positive", ("session_end_availability_slot",), "value must be positive"))
    if start_slot is not None and end_slot is not None and start_slot >= end_slot:
        issues.append(
            _issue(
                "semantic_session_order",
                ("session_end_availability_slot",),
                "session start must be strictly before session end",
            )
        )

    if not _valid_utf8_registry(document["quote_mint"], 128):
        issues.append(_issue("semantic_registry", ("quote_mint",), "registry string exceeds 128 UTF-8 bytes"))

    allowed_markets = document["allowed_markets"]
    files = document["files"]
    assert isinstance(allowed_markets, list) and isinstance(files, list)
    if len(allowed_markets) > _MAX_U64:
        issues.append(_issue("semantic_count", ("allowed_markets",), "market count exceeds MAX_U64_V0"))

    market_ids: list[str] = []
    base_mints: list[str] = []
    for index, row_value in enumerate(allowed_markets):
        assert isinstance(row_value, Mapping)
        row = row_value
        for field in ("market_id", "base_mint", "quote_mint"):
            if not _valid_utf8_registry(row[field], 128):
                issues.append(
                    _issue(
                        "semantic_registry",
                        ("allowed_markets", index, field),
                        "registry string exceeds 128 UTF-8 bytes",
                    )
                )
        market_id = row["market_id"]
        base_mint = row["base_mint"]
        assert isinstance(market_id, str) and isinstance(base_mint, str)
        market_ids.append(market_id)
        base_mints.append(base_mint)
        if base_mint == document["quote_mint"]:
            issues.append(
                _issue("semantic_mints", ("allowed_markets", index, "base_mint"), "base and quote mints must differ")
            )
        if row["quote_mint"] != document["quote_mint"]:
            issues.append(
                _issue(
                    "semantic_quote_identity",
                    ("allowed_markets", index, "quote_mint"),
                    "market quote mint must match the manifest",
                )
            )
        if row["quote_decimals"] != document["quote_decimals"]:
            issues.append(
                _issue(
                    "semantic_quote_decimals",
                    ("allowed_markets", index, "quote_decimals"),
                    "market quote decimals must match the manifest",
                )
            )
    if len(market_ids) != len(set(market_ids)):
        issues.append(_issue("semantic_market_set", ("allowed_markets",), "market_id values must be unique"))
    if len(base_mints) != len(set(base_mints)):
        issues.append(_issue("semantic_market_set", ("allowed_markets",), "base_mint values must be unique"))
    try:
        sorted_market_ids = sorted(market_ids, key=lambda value: value.encode("utf-8", errors="strict"))
    except UnicodeEncodeError:
        sorted_market_ids = market_ids
    if market_ids != sorted_market_ids:
        issues.append(
            _issue("semantic_market_order", ("allowed_markets",), "markets must be sorted by unsigned UTF-8 market_id")
        )

    file_paths: list[str] = []
    admission_sequences: list[int] = []
    allowed_market_ids = set(market_ids)
    for index, row_value in enumerate(files):
        assert isinstance(row_value, Mapping)
        row = row_value
        for field in ("source_id", "source_kind", "source_revision", "market_id"):
            if not _valid_utf8_registry(row[field], 128):
                issues.append(
                    _issue(
                        "semantic_registry",
                        ("files", index, field),
                        "registry string exceeds 128 UTF-8 bytes",
                    )
                )
        path = row["relative_path"]
        assert isinstance(path, str)
        file_paths.append(path)
        if unicodedata.normalize("NFC", path) != path:
            issues.append(_issue("semantic_path", ("files", index, "relative_path"), "path must be NFC-normalized"))
        if row["market_id"] not in allowed_market_ids:
            issues.append(
                _issue("semantic_file_market", ("files", index, "market_id"), "file market is not allowlisted")
            )
        for field in ("byte_length", "admission_sequence", "availability_slot"):
            parsed = _u64(row[field])
            if parsed is None:
                issues.append(_issue("semantic_u64", ("files", index, field), "value exceeds the u64 authority range"))
            elif field == "admission_sequence":
                if parsed == 0:
                    issues.append(
                        _issue(
                            "semantic_admission_sequence",
                            ("files", index, field),
                            "admission sequence must be one-based",
                        )
                    )
                admission_sequences.append(parsed)
    if len(file_paths) != len(set(file_paths)):
        issues.append(_issue("semantic_file_set", ("files",), "relative_path values must be unique"))
    try:
        sorted_paths = sorted(file_paths, key=lambda value: value.encode("utf-8", errors="strict"))
    except UnicodeEncodeError:
        sorted_paths = file_paths
    if file_paths != sorted_paths:
        issues.append(_issue("semantic_file_order", ("files",), "files must be sorted by unsigned UTF-8 path"))
    if len(admission_sequences) != len(set(admission_sequences)):
        issues.append(_issue("semantic_admission_sequence", ("files",), "file admission sequences must be unique"))
    return tuple(issues)


def validate_replay_risk_config_semantics(document: Mapping[str, JsonValue]) -> tuple[ValidationIssue, ...]:
    """Validate all string-authority bounds and config cross-field relations."""
    issues: list[ValidationIssue] = []
    parsed: dict[str, int] = {}
    u64_fields = (
        "target_entry_notional_quote_atoms",
        "min_notional_quote_atoms",
        "max_notional_quote_atoms",
        "max_session_loss_quote_atoms",
        "stale_after_ns",
        "max_run_closure_proof_rows",
        "session_start_replay_clock_ns",
        "session_end_replay_clock_ns",
    )
    for field in u64_fields:
        value = _u64(document[field])
        if value is None:
            issues.append(_issue("semantic_u64", (field,), "value exceeds the u64 authority range"))
        else:
            parsed[field] = value
    for field in (
        "target_entry_notional_quote_atoms",
        "min_notional_quote_atoms",
        "max_notional_quote_atoms",
    ):
        if parsed.get(field) == 0:
            issues.append(_issue("semantic_positive", (field,), "notional must be positive"))
    minimum = parsed.get("min_notional_quote_atoms")
    target = parsed.get("target_entry_notional_quote_atoms")
    maximum = parsed.get("max_notional_quote_atoms")
    if minimum is not None and target is not None and maximum is not None and not minimum <= target <= maximum:
        issues.append(
            _issue(
                "semantic_notional_order",
                ("target_entry_notional_quote_atoms",),
                "min_notional must not exceed target, which must not exceed max_notional",
            )
        )
    tick = _i128(document["price_tick_q18"])
    if tick is None:
        issues.append(_issue("semantic_i128", ("price_tick_q18",), "price tick exceeds signed-i128 range"))
    elif tick <= 0:
        issues.append(_issue("semantic_positive", ("price_tick_q18",), "price tick must be positive"))
    proof_rows = parsed.get("max_run_closure_proof_rows")
    if proof_rows is not None and not 1 <= proof_rows <= _MAX_RUN_CLOSURE_PROOF_ROWS_V0:
        issues.append(
            _issue(
                "semantic_proof_cap",
                ("max_run_closure_proof_rows",),
                "proof-row limit must be within the v0 protocol cap",
            )
        )
    start = parsed.get("session_start_replay_clock_ns")
    end = parsed.get("session_end_replay_clock_ns")
    if start is not None and end is not None and start >= end:
        issues.append(
            _issue(
                "semantic_session_order",
                ("session_end_replay_clock_ns",),
                "session start must be strictly before session end",
            )
        )
    return tuple(issues)


def validate_source_admission_receipt_semantics(
    document: Mapping[str, JsonValue],
) -> tuple[ValidationIssue, ...]:
    """Validate pure source status, preservation-compatible nullability, and time rules."""
    issues: list[ValidationIssue] = []
    reason_values = document["reason_codes"]
    assert isinstance(reason_values, list)
    reason_codes = tuple(reason_values)
    try:
        normalized = normalize_source_admission_reason_codes(reason_codes)
    except ValueError as error:
        issues.append(_issue("semantic_reason_codes", ("reason_codes",), str(error)))
        normalized = reason_codes
    if reason_codes != normalized:
        issues.append(
            _issue("semantic_reason_order", ("reason_codes",), "reason codes are not in normative precedence")
        )
    try:
        derived_status = derive_source_admission_status(reason_codes)
    except ValueError:
        derived_status = None
    if document["status"] != derived_status:
        issues.append(_issue("semantic_status", ("status",), "status does not match the complete reason set"))

    reason_set = set(reason_codes)
    for field in ("terms_sha256", "rights_role", "rights_effective_date", "rights_review_date"):
        if document[field] is None and "ADMISSION_RIGHTS_MISSING" not in reason_set:
            issues.append(
                _issue(
                    "semantic_reason_completeness",
                    (field,),
                    "missing rights evidence requires ADMISSION_RIGHTS_MISSING",
                )
            )

    def require_null_owner(field: str, owner_codes: frozenset[str], message: str) -> None:
        if document[field] is None and reason_set.isdisjoint(owner_codes):
            issues.append(
                _issue(
                    "semantic_reason_completeness",
                    (field,),
                    message,
                )
            )

    manifest_owner = frozenset({"ADMISSION_MANIFEST_MISMATCH"})
    local_owner = frozenset({"ADMISSION_NOT_LOCAL"})
    profile_owner = frozenset({"ADMISSION_PROFILE_MISMATCH"})
    revision_owners = frozenset({"ADMISSION_PROFILE_MISMATCH", "ADMISSION_POINT_IN_TIME_MISSING"})
    point_in_time_owner = frozenset({"ADMISSION_POINT_IN_TIME_MISSING"})

    require_null_owner(
        "fixture_manifest_sha256",
        manifest_owner,
        "missing manifest identity requires ADMISSION_MANIFEST_MISMATCH",
    )
    manifest_blocked = document["fixture_manifest_sha256"] is None and not reason_set.isdisjoint(manifest_owner)

    local_fields = ("raw_payload_sha256", "relative_path", "byte_length")
    if not manifest_blocked:
        for field in local_fields:
            require_null_owner(field, local_owner, "missing local evidence requires ADMISSION_NOT_LOCAL")
    local_blocked = manifest_blocked or (
        any(document[field] is None for field in local_fields) and not reason_set.isdisjoint(local_owner)
    )

    profile_field_owners = {
        "source_id": profile_owner,
        "source_kind": profile_owner,
        "source_revision": revision_owners,
        "market_id": profile_owner,
        "media_type": profile_owner,
    }
    if not local_blocked:
        for field, owner_codes in profile_field_owners.items():
            require_null_owner(
                field, owner_codes, "missing parsed source identity requires a profile/point-in-time code"
            )
        require_null_owner(
            "availability_slot",
            point_in_time_owner,
            "missing availability evidence requires ADMISSION_POINT_IN_TIME_MISSING",
        )
    for field in ("observed_at", "ingested_at"):
        require_null_owner(
            field,
            point_in_time_owner,
            "missing witness evidence requires ADMISSION_POINT_IN_TIME_MISSING",
        )

    for field in ("source_id", "source_kind", "source_revision", "market_id"):
        value = document[field]
        if value is not None and not _valid_utf8_registry(value, 128):
            issues.append(_issue("semantic_registry", (field,), "registry string exceeds 128 UTF-8 bytes"))
    relative_path = document["relative_path"]
    if isinstance(relative_path, str) and unicodedata.normalize("NFC", relative_path) != relative_path:
        issues.append(_issue("semantic_path", ("relative_path",), "path must be NFC-normalized"))

    parsed_admission = _u64(document["admission_sequence"])
    if parsed_admission is None:
        issues.append(_issue("semantic_u64", ("admission_sequence",), "value exceeds the u64 authority range"))
    elif parsed_admission == 0:
        issues.append(
            _issue("semantic_admission_sequence", ("admission_sequence",), "admission sequence must be one-based")
        )
    for field in ("byte_length", "availability_slot"):
        value = document[field]
        if value is not None and _u64(value) is None:
            issues.append(_issue("semantic_u64", (field,), "value exceeds the u64 authority range"))

    observed = document["observed_at"]
    ingested = document["ingested_at"]
    observed_key = None if observed is None else _instant_key(observed)
    ingested_key = None if ingested is None else _instant_key(ingested)
    if observed is not None and observed_key is None:
        issues.append(_issue("semantic_timestamp", ("observed_at",), "timestamp is not a real UTC instant"))
    if ingested is not None and ingested_key is None:
        issues.append(_issue("semantic_timestamp", ("ingested_at",), "timestamp is not a real UTC instant"))
    if observed_key is not None and ingested_key is not None and ingested_key < observed_key:
        issues.append(_issue("semantic_time_order", ("ingested_at",), "ingested_at precedes observed_at"))

    effective = document["rights_effective_date"]
    review = document["rights_review_date"]
    effective_key = None if effective is None else _full_date_key(effective)
    review_key = None if review is None else _full_date_key(review)
    if effective is not None and effective_key is None:
        issues.append(_issue("semantic_date", ("rights_effective_date",), "date is not a real calendar date"))
    if review is not None and review_key is None:
        issues.append(_issue("semantic_date", ("rights_review_date",), "date is not a real calendar date"))
    if effective_key is not None and review_key is not None and review_key < effective_key:
        issues.append(_issue("semantic_rights_order", ("rights_review_date",), "rights review precedes effective date"))

    if document["status"] == "ADMITTED":
        admitted_required = (
            "fixture_manifest_sha256",
            "raw_payload_sha256",
            "terms_sha256",
            "source_id",
            "source_kind",
            "source_revision",
            "market_id",
            "relative_path",
            "media_type",
            "byte_length",
            "availability_slot",
            "observed_at",
            "ingested_at",
            "rights_role",
            "rights_effective_date",
            "rights_review_date",
        )
        for field in admitted_required:
            if document[field] is None:
                issues.append(
                    _issue("semantic_admitted_totality", (field,), "admitted receipt requires this witnessed field")
                )
    return tuple(issues)


def validate_config_admission_receipt_semantics(
    document: Mapping[str, JsonValue],
) -> tuple[ValidationIssue, ...]:
    """Validate the pure config status/reason/nullability tuple."""
    issues: list[ValidationIssue] = []
    reason_values = document["reason_codes"]
    assert isinstance(reason_values, list)
    reason_codes = tuple(reason_values)
    try:
        normalized = normalize_config_admission_reason_codes(reason_codes)
    except ValueError as error:
        issues.append(_issue("semantic_reason_codes", ("reason_codes",), str(error)))
        normalized = reason_codes
    if reason_codes != normalized:
        issues.append(
            _issue("semantic_reason_order", ("reason_codes",), "reason codes are not in normative precedence")
        )

    raw_length = _u64(document["raw_byte_length"])
    if raw_length is None:
        issues.append(_issue("semantic_u64", ("raw_byte_length",), "value exceeds the u64 authority range"))
    admission_sequence = _u64(document["admission_sequence"])
    if admission_sequence is None:
        issues.append(_issue("semantic_u64", ("admission_sequence",), "value exceeds the u64 authority range"))
    elif admission_sequence == 0:
        issues.append(
            _issue("semantic_admission_sequence", ("admission_sequence",), "admission sequence must be one-based")
        )

    status = document["status"]
    raw_digest = document["raw_config_sha256"]
    validated_digest = document["validated_config_sha256"]
    if status == "MISSING":
        if reason_codes != ("CONFIG_MISSING",):
            issues.append(_issue("semantic_config_tuple", ("reason_codes",), "MISSING requires exactly CONFIG_MISSING"))
        if raw_digest is not None or validated_digest is not None or raw_length != 0:
            issues.append(_issue("semantic_config_tuple", ("status",), "MISSING requires null digests and zero length"))
    elif status == "INVALID":
        if not reason_codes or "CONFIG_MISSING" in reason_codes:
            issues.append(
                _issue(
                    "semantic_config_tuple",
                    ("reason_codes",),
                    "INVALID requires non-missing rejection reasons",
                )
            )
        if raw_digest is None or validated_digest is not None:
            issues.append(
                _issue("semantic_config_tuple", ("status",), "INVALID requires raw digest and null validated digest")
            )
    else:
        if reason_codes:
            issues.append(_issue("semantic_config_tuple", ("reason_codes",), "VALID requires empty reasons"))
        if raw_digest is None or validated_digest is None:
            issues.append(
                _issue("semantic_config_tuple", ("status",), "VALID requires raw and validated config digests")
            )
        if raw_length == 0:
            issues.append(
                _issue("semantic_config_tuple", ("raw_byte_length",), "VALID canonical record cannot be empty")
            )
    return tuple(issues)


SEMANTIC_VALIDATORS: dict[str, SemanticValidator] = {
    "trading.raw-event/v1": validate_raw_event_semantics,
    "trading.feature-snapshot/v1": validate_feature_snapshot_semantics,
    "trading.model-signal/v1": validate_model_signal_semantics,
    "trading.risk-decision/v1": validate_risk_decision_semantics,
    "trading.simulated-order-intent/v1": validate_simulated_order_intent_semantics,
    "trading.simulated-fill-receipt/v1": validate_simulated_fill_receipt_semantics,
    "trading.portfolio-state/v1": validate_portfolio_state_semantics,
    "trading.ledger-record/v1": validate_ledger_record_semantics,
}

SUPPORTING_SEMANTIC_VALIDATORS: dict[str, SemanticValidator] = {
    "trading.fixture-manifest/v1": validate_fixture_manifest_semantics,
    "trading.replay-risk-config/v1": validate_replay_risk_config_semantics,
    "trading.source-admission-receipt/v1": validate_source_admission_receipt_semantics,
    "trading.config-admission-receipt/v1": validate_config_admission_receipt_semantics,
}


def validate_contract_semantics(document: Mapping[str, JsonValue]) -> tuple[ValidationIssue, ...]:
    """Dispatch one structurally valid document to its pure semantic validator."""
    schema_id = document.get("schema")
    if not isinstance(schema_id, str):
        return ()
    validator = SEMANTIC_VALIDATORS.get(schema_id)
    if validator is None:
        validator = SUPPORTING_SEMANTIC_VALIDATORS.get(schema_id)
    return () if validator is None else validator(document)
