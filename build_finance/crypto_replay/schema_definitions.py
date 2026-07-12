"""Frozen contract inventory and explicit in-repository schema definitions.

Task T01 adds primary schema dictionaries to ``PRIMARY_SCHEMA_DOCUMENTS``;
later T02 tasks populate the supporting and attachment dictionaries.  The
inventory is complete from the start so content-ID and code-generation scope
cannot drift while those definitions are added incrementally.
"""

from __future__ import annotations

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

# These dictionaries are intentionally empty in Task 3.  Exhaustive schema
# definitions and generated resources are owned by Tasks 4 and 7-10.
PRIMARY_SCHEMA_DOCUMENTS: dict[str, JsonObject] = {}
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
