"""T02 RED contracts for the thirteen supporting replay records.

The vectors in this module are synthetic contract fixtures.  They deliberately
exercise only local canonical bytes, closed schemas, content IDs, and retained
preimages; they are not admitted market data and provide no replay authority.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Literal

from build_finance.crypto_replay.canonical import (
    canonical_json_bytes,
    canonical_record_bytes,
    parse_canonical_record,
    sha256_hex,
)
from build_finance.crypto_replay.content_ids import (
    compute_content_id,
    seal_content_id,
    verify_content_id,
)
from build_finance.crypto_replay.schema_model import ResolvedContent

MARKET_ID = "synthetic-base/synthetic-quote:jupiter"
BASE_MINT = "synthetic-base"
QUOTE_MINT = "synthetic-quote"
MAX_U64 = 18_446_744_073_709_551_615
MAX_PROOF_ROWS = 1_000_000


def _digest(label: str) -> str:
    return sha256(f"SYNTHETIC_T02_CONTRACT_VECTOR:{label}".encode("ascii")).hexdigest()


def _attachment(document: dict[str, Any]) -> tuple[bytes, str]:
    payload = canonical_json_bytes(document)
    return payload, sha256_hex(payload)


def _seal(schema: str, **fields: Any) -> dict[str, Any]:
    return seal_content_id({"schema": schema, **fields})


def _reseal(document: dict[str, Any]) -> dict[str, Any]:
    from build_finance.crypto_replay.schema_definitions import SELF_ID_FIELDS

    result = deepcopy(document)
    result.pop(SELF_ID_FIELDS[str(result["schema"])], None)
    return seal_content_id(result)


class SyntheticResolver:
    """Minimal immutable resolver for closed, clearly synthetic T02 vectors."""

    def __init__(
        self,
        documents: tuple[dict[str, Any], ...],
        retained_bytes: tuple[bytes, ...],
    ) -> None:
        from build_finance.crypto_replay.schema_definitions import CONTRACT_SPECS_BY_SCHEMA
        from build_finance.crypto_replay.schema_registry import require_valid_contract

        self._objects: dict[str, ResolvedContent] = {}
        for document in documents:
            record = canonical_record_bytes(document)
            parsed = parse_canonical_record(record)
            assert parsed == document
            assert verify_content_id(document)
            family = CONTRACT_SPECS_BY_SCHEMA[str(document["schema"])].family
            assurance: Literal["DIGEST_ONLY", "SCHEMA_VALID"]
            if family == "PRIMARY":
                require_valid_contract(document, expected_schema=str(document["schema"]))
                assurance = "SCHEMA_VALID"
            elif family == "SUPPORTING":
                assurance = "DIGEST_ONLY"
            else:
                raise AssertionError(f"unexpected self-addressed family: {family}")
            content_id = compute_content_id(document)
            existing = self._objects.get(content_id)
            if existing is not None and existing.record != record:
                raise AssertionError("synthetic resolver ContentID collision")
            self._objects[content_id] = ResolvedContent(
                record=record,
                document=deepcopy(document),
                assurance=assurance,
            )
        self._bytes = {sha256_hex(payload): bytes(payload) for payload in retained_bytes}

    def __repr__(self) -> str:
        return f"SyntheticResolver(objects={len(self._objects)}, retained_byte_digests={len(self._bytes)})"

    def resolve_object(self, content_id: str) -> ResolvedContent | None:
        resolved = self._objects.get(content_id)
        if resolved is None:
            return None
        return ResolvedContent(
            record=bytes(resolved.record),
            document=deepcopy(dict(resolved.document)),
            assurance=resolved.assurance,
        )

    def resolve_bytes(self, digest: str) -> bytes | None:
        payload = self._bytes.get(digest)
        return None if payload is None else bytes(payload)


@dataclass(frozen=True, slots=True)
class T02Vector:
    documents: dict[str, dict[str, Any]]
    attachments: dict[str, dict[str, Any]]
    attachment_payloads: dict[str, bytes]
    raw_payloads: tuple[bytes, bytes]
    raw_config_bytes: bytes
    public_seed_bytes: bytes
    code_preimages: dict[str, bytes]
    source_receipts: tuple[dict[str, Any], dict[str, Any]]
    raw_events: tuple[dict[str, Any], dict[str, Any]]

    @property
    def resolver(self) -> SyntheticResolver:
        return SyntheticResolver(
            (*self.documents.values(), *self.source_receipts, *self.raw_events),
            (
                *self.attachment_payloads.values(),
                *self.raw_payloads,
                self.raw_config_bytes,
                self.public_seed_bytes,
                *self.code_preimages.values(),
            ),
        )


def _code_preimages() -> dict[str, bytes]:
    names = (
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
    )
    return {name: f"SYNTHETIC T02 CONTRACT-ONLY CODE PREIMAGE: {name}\n".encode("ascii") for name in names}


def build_t02_vector() -> T02Vector:
    """Build one bottom-up, disabled-model, contract-only T02 graph."""
    raw_payloads = (
        b"SYNTHETIC T02 FIXTURE PAYLOAD - NOT MARKET DATA - GROUP 1\n",
        b"SYNTHETIC T02 FIXTURE PAYLOAD - NOT MARKET DATA - GROUP 2\n",
    )
    raw_payload_digests = tuple(sha256_hex(payload) for payload in raw_payloads)
    schema_bundle_sha256 = _digest("schema-bundle")
    code_preimages = _code_preimages()
    code_hashes = {name: sha256_hex(payload) for name, payload in code_preimages.items()}

    fixture = _seal(
        "trading.fixture-manifest/v1",
        network="solana-mainnet",
        venue_profile="solana-jupiter-fixture/v1",
        quote_mint=QUOTE_MINT,
        quote_decimals=6,
        initial_quote_atoms="1000000",
        replay_tick_ns="1000000000",
        universe_policy="FULL_DECLARED_SOURCE_UNIVERSE",
        point_in_time_mode="PROVEN_AVAILABILITY_SLOT",
        run_end_position_policy="LEAVE_MARKED_OPEN",
        session_start_availability_slot="1",
        session_end_availability_slot="2",
        rights_manifest_sha256=_digest("rights-manifest"),
        selection_failures_retained=True,
        no_route_observations_retained=True,
        inactive_assets_retained=True,
        gaps_retained=True,
        allowed_markets=[
            {
                "market_id": MARKET_ID,
                "base_mint": BASE_MINT,
                "quote_mint": QUOTE_MINT,
                "base_decimals": 9,
                "quote_decimals": 6,
            }
        ],
        files=[
            {
                "relative_path": "quotes/group-1.json",
                "raw_payload_sha256": raw_payload_digests[0],
                "byte_length": str(len(raw_payloads[0])),
                "admission_sequence": "1",
                "availability_slot": "1",
                "media_type": "application/json",
                "source_id": "synthetic-local-fixture",
                "source_kind": "JUPITER_ROUTE_QUOTE_FIXTURE",
                "source_revision": "synthetic-revision-1",
                "market_id": MARKET_ID,
            },
            {
                "relative_path": "quotes/group-2.json",
                "raw_payload_sha256": raw_payload_digests[1],
                "byte_length": str(len(raw_payloads[1])),
                "admission_sequence": "3",
                "availability_slot": "2",
                "media_type": "application/json",
                "source_id": "synthetic-local-fixture",
                "source_kind": "JUPITER_ROUTE_QUOTE_FIXTURE",
                "source_revision": "synthetic-revision-1",
                "market_id": MARKET_ID,
            },
        ],
    )

    config = _seal(
        "trading.replay-risk-config/v1",
        baseline_id="MOMENTUM_V1",
        target_entry_notional_quote_atoms="100000",
        min_notional_quote_atoms="1000",
        max_notional_quote_atoms="500000",
        price_tick_q18="1000000000000",
        max_participation_bps=500,
        max_impact_bps=50,
        max_fee_bps=50,
        max_concentration_bps=2500,
        max_session_loss_quote_atoms="100000",
        max_drawdown_bps=1000,
        stale_after_ns="5000000000",
        stop_loss_bps=500,
        take_profit_bps=1000,
        adverse_fill_bps_max=10,
        max_run_closure_proof_rows=str(MAX_PROOF_ROWS),
        fee_model_version="solana-jupiter-fixture-fee-proration/v1",
        liquidity_model_version="solana-jupiter-route-capacity/v1",
        session_start_replay_clock_ns="0",
        session_end_replay_clock_ns="1000000000",
        kill_exit_mode="CLOSE_ON_NEXT_EVENT",
    )
    raw_config_bytes = canonical_record_bytes(config)
    config_receipt = _seal(
        "trading.config-admission-receipt/v1",
        status="VALID",
        reason_codes=[],
        raw_config_sha256=sha256_hex(raw_config_bytes),
        validated_config_sha256=config["config_sha256"],
        raw_byte_length=str(len(raw_config_bytes)),
        admission_sequence="2",
        validator_code_sha256=_digest("config-validator"),
        schema_bundle_sha256=schema_bundle_sha256,
    )

    source_receipts: list[dict[str, Any]] = []
    for index, (payload, availability_slot, admission_sequence) in enumerate(
        ((raw_payloads[0], "1", "1"), (raw_payloads[1], "2", "3")),
        start=1,
    ):
        source_receipts.append(
            _seal(
                "trading.source-admission-receipt/v1",
                status="ADMITTED",
                reason_codes=[],
                fixture_manifest_sha256=fixture["fixture_manifest_sha256"],
                raw_payload_sha256=sha256_hex(payload),
                terms_sha256=_digest(f"terms-{index}"),
                parser_code_sha256=_digest("source-parser"),
                source_id="synthetic-local-fixture",
                source_kind="JUPITER_ROUTE_QUOTE_FIXTURE",
                source_revision="synthetic-revision-1",
                market_id=MARKET_ID,
                relative_path=f"quotes/group-{index}.json",
                media_type="application/json",
                byte_length=str(len(payload)),
                admission_sequence=admission_sequence,
                availability_slot=availability_slot,
                observed_at=f"2026-01-02T00:00:0{index}.000000000Z",
                ingested_at=f"2026-01-02T00:00:0{index}.000000001Z",
                rights_role="offline_research_replay",
                rights_effective_date="2026-01-01",
                rights_review_date="2026-01-02",
                parser_version="solana-jupiter-fixture-parser/v1",
            )
        )

    raw_events: list[dict[str, Any]] = []
    for index, source_receipt in enumerate(source_receipts, start=1):
        raw_events.append(
            _seal(
                "trading.raw-event/v1",
                fixture_manifest_sha256=fixture["fixture_manifest_sha256"],
                raw_payload_sha256=raw_payload_digests[index - 1],
                source_admission_receipt_id=source_receipt["source_admission_receipt_id"],
                source_id="synthetic-local-fixture",
                source_kind="JUPITER_ROUTE_QUOTE_FIXTURE",
                source_revision="synthetic-revision-1",
                network="solana-mainnet",
                venue_profile="solana-jupiter-fixture/v1",
                market_id=MARKET_ID,
                base_mint=BASE_MINT,
                quote_mint=QUOTE_MINT,
                base_decimals=9,
                quote_decimals=6,
                event_kind="ROUTE_QUOTE",
                source_position={
                    "slot": str(index),
                    "transaction_index": 0,
                    "instruction_index": 0,
                    "event_index": 0,
                    "source_native_event_id": f"synthetic-quote-{index}",
                    "source_subsequence": "0",
                },
                revision={
                    "kind": "ORIGINAL",
                    "supersedes_event_id": None,
                    "retracts_event_id": None,
                    "availability_slot": str(index),
                    "availability_admission_sequence": source_receipt["admission_sequence"],
                },
                event_time=f"2026-01-01T00:00:0{index}.000000000Z",
                observed_at=source_receipt["observed_at"],
                ingested_at=source_receipt["ingested_at"],
                admission_sequence=source_receipt["admission_sequence"],
                source_sequence=str(index),
                ingest_sequence=str(index),
                equal_time_group=str(index),
                replay_clock_ns=str((index - 1) * 1_000_000_000),
                executable=True,
                market={
                    "base_amount_atoms": "1000000000",
                    "quote_amount_atoms": str(1_000_000 + index),
                    "route_capacity_base_atoms": "5000000000",
                    "liquidity_quote_atoms": "10000000",
                    "venue_fee_quote_atoms": "2500",
                    "priority_fee_quote_atoms": "0",
                    "route_impact_bps": 25,
                },
                quality_flags=[],
            )
        )

    source_ids = sorted(receipt["source_admission_receipt_id"] for receipt in source_receipts)
    availability_schedule = {
        "schema": "trading.availability-schedule/v1",
        "fixture_manifest_sha256": fixture["fixture_manifest_sha256"],
        "config_admission_receipt_id": config_receipt["config_admission_receipt_id"],
        "source_admission_receipt_ids": source_ids,
        "availability_groups": [
            {"availability_slot": "1", "equal_time_group": "1", "admission_cutoff": "2"},
            {"availability_slot": "2", "equal_time_group": "2", "admission_cutoff": "3"},
        ],
    }
    normalized_event_set = {
        "schema": "trading.normalized-event-set/v1",
        "fixture_manifest_sha256": fixture["fixture_manifest_sha256"],
        "raw_event_count": "2",
        "event_ids": [event["event_id"] for event in raw_events],
    }
    normalized_payload, normalized_digest = _attachment(normalized_event_set)
    counter_capacity = {
        "schema": "trading.counter-capacity/v1",
        "model_signal_mode": "DISABLED",
        "model_registry_sha256": None,
        "model_signal_manifest_sha256": None,
        "normalized_event_set_sha256": normalized_digest,
        "source_admission_count": "2",
        "raw_event_count": "2",
        "availability_group_count": "2",
        "market_count": "1",
        "model_candidate_count": "0",
        "decision_attempt_upper_bound": "2",
        "decision_sequence_next_upper_bound": "3",
        "producer_sequence_next_upper_bound": "0",
        "intent_sequence_next_upper_bound": "3",
        "fill_receipt_sequence_next_upper_bound": "3",
        "unmatched_reservation_count_upper_bound": "4",
        "state_sequence_next_upper_bound": "13",
        "ledger_sequence_next_upper_bound": "43",
        "status": "WITHIN_LIMIT",
        "first_exceeded_counter": None,
    }
    availability_payload, availability_digest = _attachment(availability_schedule)
    counter_payload, counter_digest = _attachment(counter_capacity)

    closure = _seal(
        "trading.run-closure-receipt/v1",
        status="PASS",
        reason_codes=[],
        fixture_manifest_sha256=fixture["fixture_manifest_sha256"],
        config_admission_receipt_id=config_receipt["config_admission_receipt_id"],
        validated_config_sha256=config["config_sha256"],
        model_signal_mode="DISABLED",
        model_registry_sha256=None,
        model_signal_manifest_sha256=None,
        schema_bundle_sha256=schema_bundle_sha256,
        admission_code_sha256=code_hashes["admission_code_sha256"],
        normalization_code_sha256=code_hashes["normalization_code_sha256"],
        availability_grouping_code_sha256=code_hashes["availability_grouping_code_sha256"],
        run_closure_code_sha256=code_hashes["run_closure_code_sha256"],
        risk_code_sha256=code_hashes["risk_code_sha256"],
        feature_code_sha256=code_hashes["feature_code_sha256"],
        fill_code_sha256=code_hashes["fill_code_sha256"],
        accounting_code_sha256=code_hashes["accounting_code_sha256"],
        source_admission_receipt_ids=source_ids,
        availability_schedule_sha256=availability_digest,
        counter_capacity_sha256=counter_digest,
        counter_capacity_status="WITHIN_LIMIT",
        run_end_position_policy="LEAVE_MARKED_OPEN",
        terminal_equal_time_group="2",
        proof_row_limit=str(MAX_PROOF_ROWS),
        proof_row_count_total="0",
        proof_budget_status="NOT_REQUIRED",
        market_proofs=[],
    )

    source_tree = {
        "schema": "trading.source-tree/v1",
        "root_label": "repository-root",
        "path_policy": "UTF8_NFC_POSIX_RELATIVE_NO_SYMLINK_V1",
        "exclusion_prefixes": [
            ".git/",
            ".hg/",
            ".mypy_cache/",
            ".nox/",
            ".pytest_cache/",
            ".ruff_cache/",
            ".svn/",
            ".tox/",
            ".venv/",
            "__pycache__/",
            "build/",
            "dist/",
            "node_modules/",
            "scratch/",
            "tmp/",
            "venv/",
        ],
        "files": [
            {
                "relative_path": "src/kernel.py",
                "byte_length": "3",
                "file_sha256": sha256_hex(b"abc"),
            },
            {
                "relative_path": "src/risk.py",
                "byte_length": "0",
                "file_sha256": sha256_hex(b""),
            },
        ],
    }
    source_tree_payload, source_tree_digest = _attachment(source_tree)
    public_seed_bytes = bytes.fromhex("00" * 31 + "0f")
    run_receipt = _seal(
        "trading.run-receipt/v1",
        fixture_manifest_sha256=fixture["fixture_manifest_sha256"],
        schema_bundle_sha256=schema_bundle_sha256,
        admission_code_sha256=code_hashes["admission_code_sha256"],
        normalization_code_sha256=code_hashes["normalization_code_sha256"],
        availability_grouping_code_sha256=code_hashes["availability_grouping_code_sha256"],
        run_closure_code_sha256=code_hashes["run_closure_code_sha256"],
        feature_code_sha256=code_hashes["feature_code_sha256"],
        baseline_code_sha256=code_hashes["baseline_code_sha256"],
        risk_code_sha256=code_hashes["risk_code_sha256"],
        fill_code_sha256=code_hashes["fill_code_sha256"],
        accounting_code_sha256=code_hashes["accounting_code_sha256"],
        benchmark_code_sha256=code_hashes["benchmark_code_sha256"],
        public_seed_sha256=sha256_hex(public_seed_bytes),
        source_tree_sha256=source_tree_digest,
        source_admission_receipt_ids=source_ids,
        availability_schedule_sha256=availability_digest,
        config_admission_receipt_id=config_receipt["config_admission_receipt_id"],
        validated_config_sha256=config["config_sha256"],
        run_closure_receipt_id=closure["run_closure_receipt_id"],
        model_registry_sha256=None,
        model_signal_manifest_sha256=None,
        selected_model_scopes=[],
        replay_tick_ns="1000000000",
        model_decision_budget_ns="0",
        model_signal_mode="DISABLED",
        run_end_position_policy="LEAVE_MARKED_OPEN",
        terminal_equal_time_group="2",
        availability_groups=deepcopy(availability_schedule["availability_groups"]),
        os_name="synthetic-os",
        architecture="synthetic-architecture",
        runtime_name="cpython",
        runtime_version="synthetic-runtime",
        decimal_version="1",
        jcs_implementation="build-finance",
        jcs_version="1",
        tool_versions=[{"name": "pytest", "version": "synthetic-version"}],
        public_seed_hex=public_seed_bytes.hex(),
    )

    quarantine = _seal(
        "trading.execution-quarantine-receipt/v1",
        status="QUARANTINED",
        reason_codes=[
            "QUARANTINE_INITIAL_PREFIX_ANCHOR_MISSING",
            "QUARANTINE_LEDGER_SLOT_MISSING",
            "QUARANTINE_FOOTPRINT_MISMATCH",
        ],
        run_receipt_id=run_receipt["run_receipt_id"],
        transition_kind="EXECUTION_TRANSITION",
        transition_key_sha256=_digest("transition-key"),
        expected_footprint_sha256=_digest("expected-footprint"),
        observed_footprint_sha256=_digest("observed-footprint"),
        last_verified_ledger_head_id=None,
        last_verified_portfolio_state_id=None,
        first_unsafe_ledger_sequence="0",
        slot_observations=[
            {
                "ledger_sequence": "0",
                "expected_ledger_record_id": _digest("expected-ledger-record"),
                "observed_ledger_record_id": None,
                "observed_byte_sha256": None,
                "classification": "MISSING",
            }
        ],
        component_observations=[],
    )

    producer_scope = {
        "adapter_sha256": None,
        "calibration_sha256": _digest("calibration"),
        "calibration_version": "synthetic-calibration-v1",
        "feature_set_version": "solana-jupiter-deterministic-features/v1",
        "horizon_ns": "30000000000",
        "market_id": MARKET_ID,
        "model_artifact_sha256": _digest("model-artifact"),
        "model_id": "synthetic-diagnostic-model",
        "model_version": "synthetic-model-v1",
        "producer_id": "synthetic-producer",
        "runtime_profile_id": "offline-cached-signal/v1",
    }
    _, producer_scope_key = _attachment(producer_scope)
    model_registry = _seal(
        "trading.model-registry/v1",
        promotions=[
            {
                "producer_scope_key_sha256": producer_scope_key,
                "producer_id": producer_scope["producer_id"],
                "model_id": producer_scope["model_id"],
                "model_version": producer_scope["model_version"],
                "model_artifact_sha256": producer_scope["model_artifact_sha256"],
                "adapter_sha256": None,
                "runtime_profile_id": producer_scope["runtime_profile_id"],
                "calibration_version": producer_scope["calibration_version"],
                "calibration_sha256": producer_scope["calibration_sha256"],
                "feature_set_version": producer_scope["feature_set_version"],
                "market_id": MARKET_ID,
                "horizon_ns": "30000000000",
                "max_ttl_ns": "60000000000",
                "max_uncertainty_q18": "900000000000000000",
                "max_ood_score_q18": "900000000000000000",
                "status": "DISABLED",
            }
        ],
    )
    raw_signal = b"SYNTHETIC T02 STATIC MODEL CONTRACT BYTES - NO INFERENCE\n"
    model_signal_manifest = _seal(
        "trading.model-signal-manifest/v1",
        model_registry_sha256=model_registry["model_registry_sha256"],
        candidates=[
            {
                "relative_path": "signals/decision-1.json",
                "media_type": "application/json",
                "raw_signal_sha256": sha256_hex(raw_signal),
                "raw_byte_length": str(len(raw_signal)),
                "declared_signal_id": None,
                "feature_snapshot_id": _digest("feature-snapshot"),
                "decision_sequence": "1",
                "producer_scope_key_sha256": None,
                "producer_sequence": None,
                "horizon_ns": "30000000000",
                "issued_replay_clock_ns": "0",
                "available_replay_clock_ns": "1",
                "decision_close_replay_clock_ns": "2",
                "requested_producer_scope_key_sha256": producer_scope_key,
            }
        ],
    )
    attempt_key_document = {
        "schema": "trading.model-validation-attempt-key/v1",
        "model_signal_manifest_sha256": model_signal_manifest["model_signal_manifest_sha256"],
        "relative_path": "signals/decision-1.json",
        "raw_signal_sha256": sha256_hex(raw_signal),
        "feature_snapshot_id": _digest("feature-snapshot"),
        "decision_sequence": "1",
        "requested_producer_scope_key_sha256": producer_scope_key,
        "horizon_ns": "30000000000",
    }
    _, attempt_key = _attachment(attempt_key_document)
    model_validation = _seal(
        "trading.model-validation-receipt/v1",
        validation_attempt_key_sha256=attempt_key,
        status="REJECTED",
        reason_codes=["SIG_BYTES_INVALID"],
        raw_signal_sha256=sha256_hex(raw_signal),
        declared_signal_id=None,
        accepted_signal_id=None,
        feature_snapshot_id=_digest("feature-snapshot"),
        decision_sequence="1",
        producer_sequence=None,
        producer_scope_key_sha256=None,
        issued_replay_clock_ns=None,
        available_replay_clock_ns="1",
        decision_close_replay_clock_ns="2",
        expires_replay_clock_ns=None,
        canonical_action="ABSTAIN",
        canonical_score_q18="0",
        canonical_probability_abstain_q18="1000000000000000000",
        canonical_probability_long_bias_q18="0",
        canonical_probability_exit_bias_q18="0",
        canonical_uncertainty_q18="1000000000000000000",
        canonical_ood_score_q18="1000000000000000000",
    )

    reconciliation = _seal(
        "trading.reconciliation-receipt/v1",
        status="PASS",
        reconciliation_kind="FILL_TRANSITION",
        reason_codes=[],
        decision_sequence="1",
        ingest_sequence="2",
        equal_time_group="2",
        replay_clock_ns="1000000000",
        portfolio_state_before_id=_digest("state-before"),
        portfolio_state_after_id=_digest("state-after"),
        causation_ids=[_digest("fill-receipt")],
        asset_residuals=[
            {"asset_mint": BASE_MINT, "residual_atoms": "0"},
            {"asset_mint": QUOTE_MINT, "residual_atoms": "0"},
        ],
        account_residuals=[],
        realized_pnl_residual_quote_atoms="0",
        unrealized_pnl_residual_quote_atoms="0",
        fee_residual_quote_atoms="0",
        peak_equity_residual_quote_atoms="0",
        drawdown_residual_bps="0",
        equity_residual_quote_atoms="0",
        unmatched_reservation_count="0",
        idempotency_conflict_scope=None,
        idempotency_key_sha256=None,
        original_object_id=None,
        conflicting_body_sha256=None,
        integrity_validation_attempt_key_sha256=None,
        integrity_transition_key_sha256=None,
        integrity_expected_footprint_sha256=None,
        integrity_observed_footprint_sha256=None,
        integrity_ledger_head_before_check_id=None,
        arithmetic_range_key_sha256=None,
        arithmetic_operands_sha256=None,
        arithmetic_operation=None,
        kill_latched=False,
    )

    benchmark_request = {
        "schema": "trading.benchmark-request/v1",
        "request_code_sha256": _digest("benchmark-request-code"),
        "fixture_manifest_sha256": None,
        "config_admission_receipt_id": None,
        "run_closure_receipt_id": None,
        "benchmark_manifest_raw_sha256": None,
        "preregistered_thresholds_raw_sha256": _digest("thresholds-raw"),
        "hardware_profile_raw_sha256": _digest("hardware-raw"),
        "benchmark_manifest_raw_byte_length": "0",
        "preregistered_thresholds_raw_byte_length": "1",
        "hardware_profile_raw_byte_length": "1",
        "requested_metric_set": "OFFLINE_REPLAY_CORE_V1",
    }
    benchmark_request_payload, benchmark_request_digest = _attachment(benchmark_request)
    phase_units = (
        ("admission", "RAW_EVENT", ["100", "110"]),
        ("feature", "FEATURE_SNAPSHOT", ["200", "210"]),
        ("risk", "RISK_DECISION", ["300", "310"]),
        ("fill", "SIMULATED_FILL_RECEIPT", ["400"]),
        ("accounting", "RECONCILIATION_RECEIPT", ["500", "510"]),
        ("end_to_end", "EQUAL_TIME_GROUP", ["1600", "1660"]),
    )
    benchmark_measurement = _seal(
        "trading.benchmark-measurement/v1",
        measurement_status="COMPLETE",
        first_range_failure=None,
        range_failure_fields=[],
        raw_counters=[
            {"counter": "MEASURED_WALL_DURATION", "raw_value": "3260"},
            {"counter": "PROCESS_CPU_TIME", "raw_value": "3000"},
            {"counter": "WALL_DURATION", "raw_value": "4000"},
            {"counter": "PEAK_RSS_BYTES", "raw_value": "1048576"},
            {"counter": "ALLOCATION_COUNT", "raw_value": None},
            {"counter": "INPUT_BYTES", "raw_value": "2048"},
            {"counter": "OUTPUT_BYTES", "raw_value": "4096"},
        ],
        run_receipt_id=run_receipt["run_receipt_id"],
        case_id="latency-core",
        repetition_index="0",
        benchmark_manifest_sha256=_digest("benchmark-manifest"),
        hardware_profile_sha256=_digest("hardware-profile"),
        measurement_tool_sha256=_digest("measurement-tool"),
        warmup_event_count="0",
        measured_event_count="2",
        warmup_group_count="0",
        measured_group_count="2",
        warmup_through_equal_time_group=None,
        phase_samples=[
            {"phase": phase, "unit": unit, "sample_count": str(len(samples)), "samples_ns": samples}
            for phase, unit, samples in phase_units
        ],
        measured_wall_duration_ns="3260",
        process_cpu_time_ns="3000",
        wall_duration_ns="4000",
        peak_rss_bytes="1048576",
        allocation_count=None,
        input_bytes="2048",
        output_bytes="4096",
    )
    benchmark_receipt = _seal(
        "trading.benchmark-receipt/v1",
        status="INELIGIBLE",
        reason_codes=["BENCHMARK_FIXTURE_NOT_ADMITTED", "BENCHMARK_PREREGISTRATION_MISSING"],
        benchmark_request_sha256=benchmark_request_digest,
        benchmark_manifest_sha256=None,
        preregistered_thresholds_sha256=_digest("thresholds"),
        hardware_profile_sha256=_digest("hardware"),
        metrics_artifact_sha256=None,
        percentile_method="NEAREST_RANK_CEIL",
        sample_count="0",
        run_outputs=[],
    )

    documents = {
        document["schema"]: document
        for document in (
            fixture,
            config,
            *source_receipts,
            config_receipt,
            closure,
            quarantine,
            model_registry,
            model_signal_manifest,
            model_validation,
            reconciliation,
            run_receipt,
            benchmark_measurement,
            benchmark_receipt,
        )
    }
    attachments: dict[str, dict[str, Any]] = {
        str(document["schema"]): dict(document)
        for document in (
            availability_schedule,
            normalized_event_set,
            counter_capacity,
            source_tree,
            benchmark_request,
        )
    }
    attachment_payloads = {
        availability_schedule["schema"]: availability_payload,
        normalized_event_set["schema"]: normalized_payload,
        counter_capacity["schema"]: counter_payload,
        source_tree["schema"]: source_tree_payload,
        benchmark_request["schema"]: benchmark_request_payload,
        "synthetic:model-signal-bytes": raw_signal,
    }
    return T02Vector(
        documents=documents,
        attachments=attachments,
        attachment_payloads=attachment_payloads,
        raw_payloads=raw_payloads,
        raw_config_bytes=raw_config_bytes,
        public_seed_bytes=public_seed_bytes,
        code_preimages=code_preimages,
        source_receipts=(source_receipts[0], source_receipts[1]),
        raw_events=(raw_events[0], raw_events[1]),
    )


def _issues(document: dict[str, Any], *, resolver: SyntheticResolver | None = None) -> tuple[Any, ...]:
    from build_finance.crypto_replay.schema_registry import validate_contract

    return validate_contract(document, expected_schema=document["schema"], resolver=resolver)


def _assert_invalid(document: dict[str, Any], *, resolver: SyntheticResolver | None = None) -> None:
    assert _issues(document, resolver=resolver), f"mutation unexpectedly valid: {document['schema']}"


def _schema_is_recursively_closed(schema: dict[str, Any]) -> None:
    def visit(node: Any) -> None:
        if isinstance(node, dict):
            object_keywords = {"properties", "required", "additionalProperties"} & node.keys()
            if object_keywords:
                assert node.get("type") == "object"
                assert node.get("additionalProperties") is False
                properties = node.get("properties")
                assert isinstance(properties, dict)
                assert node.get("required") == list(properties)
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(schema)


def test_all_supporting_contracts_are_closed() -> None:
    from build_finance.crypto_replay.schema_definitions import (
        SUPPORTING_SCHEMA_DOCUMENTS,
        SUPPORTING_SCHEMA_IDS,
    )

    vector = build_t02_vector()
    expected_schema_ids = tuple(sorted(SUPPORTING_SCHEMA_IDS, key=lambda value: value.encode("utf-8")))
    actual_schema_ids = tuple(sorted(SUPPORTING_SCHEMA_DOCUMENTS, key=lambda value: value.encode("utf-8")))
    vector_schema_ids = tuple(sorted(vector.documents, key=lambda value: value.encode("utf-8")))
    assert actual_schema_ids == expected_schema_ids
    assert vector_schema_ids == expected_schema_ids
    resolver = vector.resolver
    for schema_id in SUPPORTING_SCHEMA_IDS:
        schema = SUPPORTING_SCHEMA_DOCUMENTS[schema_id]
        _schema_is_recursively_closed(schema)
        document = vector.documents[schema_id]
        assert not _issues(document, resolver=resolver)
        mutation = _reseal({**document, "unknown_t02_property": True})
        _assert_invalid(mutation, resolver=resolver)


def test_supporting_self_ids_recompute() -> None:
    """T01 already owns the exact supporting ID inventory and hash omission rule."""
    from build_finance.crypto_replay.schema_definitions import SUPPORTING_SELF_ID_FIELDS

    vector = build_t02_vector()
    assert repr(vector.resolver) == "SyntheticResolver(objects=16, retained_byte_digests=20)"
    assert set(vector.documents) == set(SUPPORTING_SELF_ID_FIELDS)
    for schema_id, document in vector.documents.items():
        self_id_field = SUPPORTING_SELF_ID_FIELDS[schema_id]
        assert verify_content_id(document)
        expected = document[self_id_field]
        assert compute_content_id(document) == expected
        without_self_id = dict(document)
        without_self_id.pop(self_id_field)
        assert compute_content_id(without_self_id) == expected
        changed_self_id = dict(document)
        changed_self_id[self_id_field] = "0" * 64
        assert compute_content_id(changed_self_id) == expected
        changed_body = dict(document)
        changed_body["synthetic_digest_probe"] = True
        assert compute_content_id(changed_body) != expected


def test_fixture_manifest_is_set_closed() -> None:
    vector = build_t02_vector()
    fixture = vector.documents["trading.fixture-manifest/v1"]
    config = vector.documents["trading.replay-risk-config/v1"]
    assert not _issues(fixture, resolver=vector.resolver)
    assert not _issues(config, resolver=vector.resolver)
    mutations: list[dict[str, Any]] = []
    duplicate_market = deepcopy(fixture)
    duplicate_market["allowed_markets"].append(deepcopy(duplicate_market["allowed_markets"][0]))
    mutations.append(_reseal(duplicate_market))
    duplicate_base = deepcopy(fixture)
    duplicate_base["allowed_markets"].append(
        {**deepcopy(duplicate_base["allowed_markets"][0]), "market_id": "zz-synthetic-market"}
    )
    mutations.append(_reseal(duplicate_base))
    same_mint = deepcopy(fixture)
    same_mint["allowed_markets"][0]["base_mint"] = QUOTE_MINT
    mutations.append(_reseal(same_mint))
    unsafe_path = deepcopy(fixture)
    unsafe_path["files"][0]["relative_path"] = "../escape.json"
    mutations.append(_reseal(unsafe_path))
    reversed_files = deepcopy(fixture)
    reversed_files["files"].reverse()
    mutations.append(_reseal(reversed_files))
    for retention_field in (
        "selection_failures_retained",
        "no_route_observations_retained",
        "inactive_assets_retained",
        "gaps_retained",
    ):
        retention_false = deepcopy(fixture)
        retention_false[retention_field] = False
        mutations.append(_reseal(retention_false))
    zero_session_start = deepcopy(fixture)
    zero_session_start["session_start_availability_slot"] = "0"
    mutations.append(_reseal(zero_session_start))
    reversed_session = deepcopy(fixture)
    reversed_session["session_start_availability_slot"] = "3"
    mutations.append(_reseal(reversed_session))
    zero_admission = deepcopy(fixture)
    zero_admission["files"][0]["admission_sequence"] = "0"
    mutations.append(_reseal(zero_admission))
    duplicate_admission = deepcopy(fixture)
    duplicate_admission["files"][1]["admission_sequence"] = "1"
    mutations.append(_reseal(duplicate_admission))
    quote_mint_mismatch = deepcopy(fixture)
    quote_mint_mismatch["allowed_markets"][0]["quote_mint"] = "other-quote"
    mutations.append(_reseal(quote_mint_mismatch))
    quote_decimals_mismatch = deepcopy(fixture)
    quote_decimals_mismatch["allowed_markets"][0]["quote_decimals"] = 5
    mutations.append(_reseal(quote_decimals_mismatch))
    empty_files = deepcopy(fixture)
    empty_files["files"] = []
    mutations.append(_reseal(empty_files))
    empty_markets = deepcopy(fixture)
    empty_markets["allowed_markets"] = []
    mutations.append(_reseal(empty_markets))
    unsorted_markets = deepcopy(fixture)
    unsorted_markets["allowed_markets"].append(
        {
            **deepcopy(unsorted_markets["allowed_markets"][0]),
            "market_id": "aaa-synthetic-base/synthetic-quote:jupiter",
            "base_mint": "aaa-synthetic-base",
        }
    )
    mutations.append(_reseal(unsorted_markets))
    duplicate_file = deepcopy(fixture)
    duplicate_file["files"].append(deepcopy(duplicate_file["files"][0]))
    mutations.append(_reseal(duplicate_file))
    for field, value in (
        ("network", "synthetic-network"),
        ("venue_profile", "synthetic-venue"),
        ("universe_policy", "SUCCESSFUL_ONLY"),
        ("point_in_time_mode", "LATEST_AVAILABLE"),
        ("run_end_position_policy", "SYNTHETIC_POLICY"),
    ):
        mutation = deepcopy(fixture)
        mutation[field] = value
        mutations.append(_reseal(mutation))
    for mutation in mutations:
        _assert_invalid(mutation, resolver=vector.resolver)

    boundary_config = deepcopy(config)
    boundary_config.update(
        {
            "target_entry_notional_quote_atoms": "1",
            "min_notional_quote_atoms": "1",
            "max_notional_quote_atoms": "1",
            "price_tick_q18": "1",
            "max_participation_bps": 10000,
            "max_impact_bps": 1_000_000,
            "max_fee_bps": 10000,
            "max_concentration_bps": 10000,
            "max_session_loss_quote_atoms": "0",
            "max_drawdown_bps": 10000,
            "stale_after_ns": "0",
            "stop_loss_bps": 9999,
            "take_profit_bps": 1_000_000,
            "adverse_fill_bps_max": 9999,
            "max_run_closure_proof_rows": "1",
            "session_start_replay_clock_ns": "0",
            "session_end_replay_clock_ns": "1",
            "kill_exit_mode": "FREEZE_NO_NEW_INTENTS",
        }
    )
    baseline_ids = (
        "ALWAYS_HOLD_V1",
        "MEAN_REVERSION_V1",
        "BREAKOUT_V1",
        "MOMENTUM_V1",
        "TREND_V1",
    )
    for baseline_id in baseline_ids:
        valid_boundary = _reseal({**boundary_config, "baseline_id": baseline_id})
        assert not _issues(valid_boundary, resolver=vector.resolver)

    config_mutations: list[dict[str, Any]] = []
    for config_field, config_value in (
        ("baseline_id", "SYNTHETIC_BASELINE"),
        ("min_notional_quote_atoms", "0"),
        ("target_entry_notional_quote_atoms", "0"),
        ("max_notional_quote_atoms", "0"),
        ("target_entry_notional_quote_atoms", "999"),
        ("target_entry_notional_quote_atoms", "500001"),
        ("price_tick_q18", "0"),
        ("max_participation_bps", -1),
        ("max_participation_bps", 10001),
        ("max_impact_bps", -1),
        ("max_impact_bps", 1_000_001),
        ("max_fee_bps", -1),
        ("max_fee_bps", 10001),
        ("max_concentration_bps", -1),
        ("max_concentration_bps", 10001),
        ("max_drawdown_bps", -1),
        ("max_drawdown_bps", 10001),
        ("stop_loss_bps", 0),
        ("stop_loss_bps", 10000),
        ("take_profit_bps", 0),
        ("take_profit_bps", 1_000_001),
        ("adverse_fill_bps_max", -1),
        ("adverse_fill_bps_max", 10000),
        ("max_run_closure_proof_rows", "0"),
        ("max_run_closure_proof_rows", str(MAX_PROOF_ROWS + 1)),
        ("session_end_replay_clock_ns", "0"),
        ("session_start_replay_clock_ns", "1000000001"),
        ("fee_model_version", "synthetic-fee-model/v0"),
        ("liquidity_model_version", "synthetic-liquidity-model/v0"),
        ("kill_exit_mode", "SYNTHETIC_EXIT"),
    ):
        mutation = deepcopy(config)
        mutation[config_field] = config_value
        config_mutations.append(_reseal(mutation))
    inverted_notional = deepcopy(config)
    inverted_notional["min_notional_quote_atoms"] = "500001"
    inverted_notional["max_notional_quote_atoms"] = "500000"
    config_mutations.append(_reseal(inverted_notional))
    for mutation in config_mutations:
        _assert_invalid(mutation, resolver=vector.resolver)


def test_source_rejection_receipt_is_total() -> None:
    vector = build_t02_vector()
    admitted = vector.documents["trading.source-admission-receipt/v1"]
    rejected = _reseal(
        {
            **admitted,
            "status": "REJECTED",
            "reason_codes": ["ADMISSION_RIGHTS_MISSING"],
            "terms_sha256": admitted["terms_sha256"],
            "rights_role": "offline_research_replay",
            "rights_effective_date": "2026-01-01",
            "rights_review_date": None,
        }
    )
    assert not _issues(rejected, resolver=vector.resolver)
    for field, expected in (
        ("raw_payload_sha256", admitted["raw_payload_sha256"]),
        ("terms_sha256", admitted["terms_sha256"]),
        ("source_id", admitted["source_id"]),
        ("rights_role", "offline_research_replay"),
        ("rights_effective_date", "2026-01-01"),
    ):
        assert rejected[field] == expected
    quarantined = _reseal(
        {
            **rejected,
            "status": "QUARANTINED",
            "reason_codes": ["ADMISSION_RIGHTS_MISSING", "ADMISSION_POSITION_CONFLICT"],
        }
    )
    assert not _issues(quarantined, resolver=vector.resolver)
    assert quarantined["terms_sha256"] == admitted["terms_sha256"]
    wrong_status = _reseal({**rejected, "status": "ADMITTED"})
    rejected_conflict = _reseal({**quarantined, "status": "REJECTED"})
    admitted_with_code = _reseal({**admitted, "reason_codes": ["ADMISSION_RIGHTS_MISSING"]})
    wrong_precedence = _reseal(
        {
            **quarantined,
            "reason_codes": ["ADMISSION_POSITION_CONFLICT", "ADMISSION_RIGHTS_MISSING"],
        }
    )
    for mutation in (wrong_status, rejected_conflict, admitted_with_code, wrong_precedence):
        _assert_invalid(mutation, resolver=vector.resolver)


def test_missing_and_invalid_config_receipts_serialize() -> None:
    vector = build_t02_vector()
    valid = vector.documents["trading.config-admission-receipt/v1"]
    common = {
        "admission_sequence": valid["admission_sequence"],
        "validator_code_sha256": valid["validator_code_sha256"],
        "schema_bundle_sha256": valid["schema_bundle_sha256"],
    }
    missing = _seal(
        "trading.config-admission-receipt/v1",
        status="MISSING",
        reason_codes=["CONFIG_MISSING"],
        raw_config_sha256=None,
        validated_config_sha256=None,
        raw_byte_length="0",
        **common,
    )
    invalid_payloads = (b"", b"SYNTHETIC INVALID CONFIG BYTES\n")
    invalid_receipts = tuple(
        _seal(
            "trading.config-admission-receipt/v1",
            status="INVALID",
            reason_codes=["CONFIG_BYTES_INVALID"],
            raw_config_sha256=sha256_hex(payload),
            validated_config_sha256=None,
            raw_byte_length=str(len(payload)),
            **common,
        )
        for payload in invalid_payloads
    )
    assert vector.raw_config_bytes.endswith(b"\n")
    assert parse_canonical_record(vector.raw_config_bytes) == vector.documents["trading.replay-risk-config/v1"]
    assert valid["raw_config_sha256"] == sha256_hex(vector.raw_config_bytes)
    assert valid["raw_byte_length"] == str(len(vector.raw_config_bytes))
    resolver = SyntheticResolver(
        (*vector.documents.values(), *vector.source_receipts, *vector.raw_events),
        (
            *vector.attachment_payloads.values(),
            *invalid_payloads,
            vector.raw_config_bytes,
            vector.raw_config_bytes[:-1],
        ),
    )
    for receipt in (missing, *invalid_receipts, valid):
        record = canonical_record_bytes(receipt)
        assert parse_canonical_record(record) == receipt
        assert verify_content_id(receipt)
        assert not _issues(receipt, resolver=resolver)
    empty_invalid, invalid = invalid_receipts
    assert empty_invalid["raw_byte_length"] == "0"
    assert empty_invalid["raw_config_sha256"] == sha256_hex(b"")
    no_lf = _reseal(
        {
            **valid,
            "raw_config_sha256": sha256_hex(vector.raw_config_bytes[:-1]),
            "raw_byte_length": str(len(vector.raw_config_bytes) - 1),
        }
    )
    mutations = (
        _reseal({**missing, "raw_byte_length": "1"}),
        _reseal({**missing, "raw_config_sha256": _digest("missing-raw")}),
        _reseal(
            {
                **invalid,
                "validated_config_sha256": vector.documents["trading.replay-risk-config/v1"]["config_sha256"],
            }
        ),
        _reseal({**invalid, "raw_byte_length": str(len(invalid_payloads[1]) + 1)}),
        _reseal({**invalid, "raw_config_sha256": _digest("wrong-invalid-raw")}),
        no_lf,
    )
    for mutation in mutations:
        _assert_invalid(mutation, resolver=resolver)


def test_run_closure_receipt_is_total_by_config_status() -> None:
    vector = build_t02_vector()
    closure = vector.documents["trading.run-closure-receipt/v1"]
    assert not _issues(closure, resolver=vector.resolver)
    zero_authority_rows: list[tuple[dict[str, Any], SyntheticResolver, dict[str, Any]]] = []
    status_inputs = (
        ("MISSING", "CONFIG_MISSING", None),
        ("INVALID", "CONFIG_BYTES_INVALID", b""),
    )
    for status, code, raw_bytes in status_inputs:
        config_receipt = _reseal(
            {
                **vector.documents["trading.config-admission-receipt/v1"],
                "status": status,
                "reason_codes": [code],
                "raw_config_sha256": None if raw_bytes is None else sha256_hex(raw_bytes),
                "validated_config_sha256": None,
                "raw_byte_length": "0" if raw_bytes is None else str(len(raw_bytes)),
            }
        )
        row = _reseal(
            {
                **closure,
                "status": "NOT_REQUIRED_ZERO_AUTHORITY",
                "config_admission_receipt_id": config_receipt["config_admission_receipt_id"],
                "validated_config_sha256": None,
                "terminal_equal_time_group": "2",
                "proof_row_limit": None,
                "proof_row_count_total": "0",
                "proof_budget_status": "NOT_REQUIRED",
                "market_proofs": [],
            }
        )
        resolver = SyntheticResolver(
            (
                *vector.documents.values(),
                config_receipt,
                row,
                *vector.source_receipts,
                *vector.raw_events,
            ),
            (
                *vector.attachment_payloads.values(),
                *((raw_bytes,) if raw_bytes is not None else ()),
            ),
        )
        assert not _issues(config_receipt, resolver=resolver)
        assert not _issues(row, resolver=resolver)
        zero_authority_rows.append((row, resolver, config_receipt))
    assert len({row["run_closure_receipt_id"] for row, _, _ in zero_authority_rows}) == 2

    exceeded_capacity = {
        **vector.attachments["trading.counter-capacity/v1"],
        "decision_sequence_next_upper_bound": None,
        "status": "EXCEEDED",
        "first_exceeded_counter": "DECISION_SEQUENCE",
    }
    exceeded_payload, exceeded_digest = _attachment(exceeded_capacity)
    capacity_failures: list[dict[str, Any]] = []
    for (zero_row, _, _), (status, _, _) in zip(zero_authority_rows, status_inputs, strict=True):
        failed = _reseal(
            {
                **zero_row,
                "status": "FAIL",
                "reason_codes": ["ADMISSION_COUNTER_CAPACITY", "ADMISSION_RUN_END_UNCLOSED"],
                "counter_capacity_sha256": exceeded_digest,
                "counter_capacity_status": "EXCEEDED",
                "terminal_equal_time_group": None,
            }
        )
        assert failed["validated_config_sha256"] is None
        assert failed["proof_row_limit"] is None
        assert failed["proof_row_count_total"] == "0"
        assert failed["proof_budget_status"] == "NOT_REQUIRED"
        assert failed["market_proofs"] == []
        capacity_failures.append(failed)
        assert status in ("MISSING", "INVALID")

    valid_capacity_failure = _reseal(
        {
            **closure,
            "status": "FAIL",
            "reason_codes": ["ADMISSION_COUNTER_CAPACITY", "ADMISSION_RUN_END_UNCLOSED"],
            "counter_capacity_sha256": exceeded_digest,
            "counter_capacity_status": "EXCEEDED",
            "terminal_equal_time_group": None,
        }
    )
    assert valid_capacity_failure["proof_row_limit"] == str(MAX_PROOF_ROWS)
    assert valid_capacity_failure["proof_row_count_total"] == "0"
    assert valid_capacity_failure["proof_budget_status"] == "NOT_REQUIRED"
    capacity_resolver = SyntheticResolver(
        (
            *vector.documents.values(),
            *(config_receipt for _, _, config_receipt in zero_authority_rows),
            *capacity_failures,
            valid_capacity_failure,
            *vector.source_receipts,
            *vector.raw_events,
        ),
        (*vector.attachment_payloads.values(), exceeded_payload, b""),
    )
    for failed in (*capacity_failures, valid_capacity_failure):
        assert not _issues(failed, resolver=capacity_resolver)

    missing_row, missing_resolver, _ = zero_authority_rows[0]
    invalid_fail = _reseal({**closure, "status": "FAIL", "reason_codes": [], "terminal_equal_time_group": None})
    invalid_proof = _reseal({**closure, "proof_budget_status": "WITHIN_LIMIT"})
    valid_zero_authority = _reseal({**closure, "status": "NOT_REQUIRED_ZERO_AUTHORITY"})
    zero_authority_pass = _reseal({**missing_row, "status": "PASS"})
    zero_authority_limit = _reseal({**missing_row, "proof_row_limit": "1"})
    counter_reason_mismatch = _reseal(
        {
            **valid_capacity_failure,
            "reason_codes": ["ADMISSION_RUN_END_UNCLOSED"],
        }
    )
    for mutation, resolver in (
        (invalid_fail, vector.resolver),
        (invalid_proof, vector.resolver),
        (valid_zero_authority, vector.resolver),
        (zero_authority_pass, missing_resolver),
        (zero_authority_limit, missing_resolver),
        (counter_reason_mismatch, capacity_resolver),
    ):
        _assert_invalid(mutation, resolver=resolver)


def test_execution_quarantine_receipt_is_exhaustive() -> None:
    vector = build_t02_vector()
    base = vector.documents["trading.execution-quarantine-receipt/v1"]
    assert not _issues(base, resolver=vector.resolver)
    wrong = _reseal(
        {
            **base,
            "reason_codes": [
                "QUARANTINE_INITIAL_PREFIX_ANCHOR_MISSING",
                "QUARANTINE_LEDGER_SLOT_WRONG",
                "QUARANTINE_APPEND_SLOT_OCCUPIED",
                "QUARANTINE_FOOTPRINT_MISMATCH",
            ],
            "slot_observations": [
                {
                    "ledger_sequence": "0",
                    "expected_ledger_record_id": _digest("expected-ledger-record"),
                    "observed_ledger_record_id": _digest("wrong-ledger-record"),
                    "observed_byte_sha256": _digest("wrong-ledger-bytes"),
                    "classification": "WRONG",
                }
            ],
        }
    )
    extra = _reseal(
        {
            **base,
            "reason_codes": [
                "QUARANTINE_INITIAL_PREFIX_ANCHOR_MISSING",
                "QUARANTINE_LEDGER_SLOT_EXTRA",
                "QUARANTINE_APPEND_SLOT_OCCUPIED",
                "QUARANTINE_FOOTPRINT_MISMATCH",
            ],
            "slot_observations": [
                {
                    "ledger_sequence": "0",
                    "expected_ledger_record_id": None,
                    "observed_ledger_record_id": _digest("extra-ledger-record"),
                    "observed_byte_sha256": _digest("extra-ledger-bytes"),
                    "classification": "EXTRA",
                }
            ],
        }
    )
    for receipt in (wrong, extra):
        assert not _issues(receipt, resolver=vector.resolver)
    malformed = _reseal({**wrong, "reason_codes": ["QUARANTINE_FOOTPRINT_MISMATCH"]})
    mixed_anchor = _reseal({**base, "last_verified_ledger_head_id": _digest("head")})
    empty_observations = _reseal({**base, "slot_observations": [], "component_observations": []})
    for mutation in (malformed, mixed_anchor, empty_observations):
        _assert_invalid(mutation, resolver=vector.resolver)


def test_source_admission_is_config_independent() -> None:
    from build_finance.crypto_replay.schema_definitions import SUPPORTING_SCHEMA_DOCUMENTS

    vector = build_t02_vector()
    receipt = vector.documents["trading.source-admission-receipt/v1"]
    schema = SUPPORTING_SCHEMA_DOCUMENTS["trading.source-admission-receipt/v1"]
    property_names = set(schema["properties"])
    assert not {"config_sha256", "config_admission_receipt_id", "run_closure_receipt_id"} & property_names
    assert not _issues(receipt, resolver=vector.resolver)
    changed_config = _reseal(
        {
            **vector.documents["trading.replay-risk-config/v1"],
            "target_entry_notional_quote_atoms": "200000",
        }
    )
    resolver = SyntheticResolver(
        (*vector.documents.values(), changed_config, *vector.raw_events),
        tuple(vector.attachment_payloads.values()),
    )
    assert not _issues(receipt, resolver=resolver)
    assert canonical_record_bytes(receipt) == canonical_record_bytes(
        vector.documents["trading.source-admission-receipt/v1"]
    )


def test_model_registry_and_signal_manifest_are_set_closed() -> None:
    vector = build_t02_vector()
    registry = vector.documents["trading.model-registry/v1"]
    manifest = vector.documents["trading.model-signal-manifest/v1"]
    assert not _issues(registry, resolver=vector.resolver)
    assert not _issues(manifest, resolver=vector.resolver)
    promotion = registry["promotions"][0]
    candidate = manifest["candidates"][0]
    assert candidate["requested_producer_scope_key_sha256"] == promotion["producer_scope_key_sha256"]
    duplicate_promotion = deepcopy(registry)
    duplicate_promotion["promotions"].append(deepcopy(promotion))
    duplicate_candidate = deepcopy(manifest)
    duplicate_candidate["candidates"].append(deepcopy(candidate))
    wrong_registry = deepcopy(manifest)
    wrong_registry["model_registry_sha256"] = _digest("other-registry")
    unsafe_path = deepcopy(manifest)
    unsafe_path["candidates"][0]["relative_path"] = "../signal.json"
    for mutation in (
        _reseal(duplicate_promotion),
        _reseal(duplicate_candidate),
        _reseal(wrong_registry),
        _reseal(unsafe_path),
    ):
        _assert_invalid(mutation, resolver=vector.resolver)


def test_model_validation_fallback_tuple_is_closed() -> None:
    vector = build_t02_vector()
    rejected = vector.documents["trading.model-validation-receipt/v1"]
    fallback = {
        "accepted_signal_id": None,
        "canonical_action": "ABSTAIN",
        "canonical_score_q18": "0",
        "canonical_probability_abstain_q18": "1000000000000000000",
        "canonical_probability_long_bias_q18": "0",
        "canonical_probability_exit_bias_q18": "0",
        "canonical_uncertainty_q18": "1000000000000000000",
        "canonical_ood_score_q18": "1000000000000000000",
    }
    parsed_evidence = {
        "declared_signal_id": _digest("declared-signal"),
        "producer_sequence": "0",
        "producer_scope_key_sha256": _digest("producer-scope"),
        "issued_replay_clock_ns": "0",
        "expires_replay_clock_ns": "1",
    }
    expired = _reseal(
        {
            **rejected,
            **parsed_evidence,
            "status": "EXPIRED",
            "reason_codes": ["SIG_EXPIRED"],
        }
    )
    drift_disabled = _reseal(
        {
            **rejected,
            **parsed_evidence,
            "status": "DRIFT_DISABLED",
            "reason_codes": ["SIG_DRIFT_DISABLED"],
            "expires_replay_clock_ns": "2",
        }
    )
    receipts = (rejected, expired, drift_disabled)
    resolver = SyntheticResolver(
        (*vector.documents.values(), *receipts, *vector.source_receipts, *vector.raw_events),
        (*vector.attachment_payloads.values(),),
    )
    for receipt in receipts:
        assert not _issues(receipt, resolver=resolver)
        assert {field: receipt[field] for field in fallback} == fallback
        assert receipt["accepted_signal_id"] is None
    assert [receipt["status"] for receipt in receipts] == [
        "REJECTED",
        "EXPIRED",
        "DRIFT_DISABLED",
    ]
    mutations: list[dict[str, Any]] = []
    for receipt in receipts:
        for field, wrong in (
            ("accepted_signal_id", _digest("forbidden-accepted-signal")),
            ("canonical_action", "LONG_BIAS"),
            ("canonical_score_q18", "1"),
            ("canonical_probability_abstain_q18", "999999999999999999"),
            ("canonical_uncertainty_q18", "0"),
        ):
            mutations.append(_reseal({**receipt, field: wrong}))
    mutations.extend(
        (
            _reseal({**expired, "status": "REJECTED"}),
            _reseal({**drift_disabled, "status": "EXPIRED"}),
            _reseal({**drift_disabled, "reason_codes": ["SIG_EXPIRED"]}),
        )
    )
    for mutation in mutations:
        _assert_invalid(mutation, resolver=resolver)


def test_benchmark_measurement_sample_arrays_are_closed() -> None:
    vector = build_t02_vector()
    measurement = vector.documents["trading.benchmark-measurement/v1"]
    assert not _issues(measurement, resolver=vector.resolver)
    assert [row["phase"] for row in measurement["phase_samples"]] == [
        "admission",
        "feature",
        "risk",
        "fill",
        "accounting",
        "end_to_end",
    ]
    assert all(int(row["sample_count"]) == len(row["samples_ns"]) for row in measurement["phase_samples"])
    assert int(measurement["measured_wall_duration_ns"]) == sum(
        int(value) for value in measurement["phase_samples"][-1]["samples_ns"]
    )
    count_mismatch = deepcopy(measurement)
    count_mismatch["phase_samples"][0]["sample_count"] = "1"
    wrong_unit = deepcopy(measurement)
    wrong_unit["phase_samples"][0]["unit"] = "EQUAL_TIME_GROUP"
    wrong_order = deepcopy(measurement)
    wrong_order["phase_samples"].reverse()
    missing_counter = deepcopy(measurement)
    missing_counter["raw_counters"].pop()
    for mutation in (count_mismatch, wrong_unit, wrong_order, missing_counter):
        _assert_invalid(_reseal(mutation), resolver=vector.resolver)
