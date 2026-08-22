# Offline Capital Engine G2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Every production change uses `superpowers:test-driven-development`; every completion claim uses `superpowers:verification-before-completion`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first deterministic, offline, paper-only capital-engine vertical slice above the reviewed Build Finance replay substrate, then connect Build Engine as an operator/feedback shell. G2 runs model-disabled and records deterministic ABSTAIN evidence; the later optional local-model milestone may emit signal evidence only and can never size, authorize, route, or execute an order.

**Architecture:** Keep the reviewed `build_finance.crypto_replay` package as the canonical contract, admission, provenance, and run-input substrate. Add a separate standard-library-only `build_finance.live_paper` capability island for normalization, deterministic event grouping, features, algorithm evidence, total model-signal validation with ABSTAIN, fusion, risk, simulated fills, hash-chained accounting, reconciliation, and run closure. Build Engine remains a separate product repository and receives a new model-disabled capital-replay supervisor that consumes read-only projections/receipts. The new path does not import or call legacy `ModelTrainer`, `PredictionStrategy`, `AutoTrader`, `PaperBroker`, `AlpacaBroker`, `market_data`, wallet, signer, provider, or network code.

**Tech Stack:** Python 3.10+, standard library in deterministic runtime packages, immutable dataclasses, integer/fixed-point arithmetic, restricted canonical JSON and SHA-256 ContentIDs, generated closed JSON Schemas, pytest, Ruff, mypy, Git worktrees, wheel/sdist closure inspection.

**Spec path:** `C:/dev/worktrees/build-finance-live-paper-design/docs/superpowers/specs/2026-07-13-live-market-data-paper-execution-engine-design.md`

## Global Constraints

- The approved design is normative. G2 is an offline paper-kernel milestone, not live trading.
- Exact reviewed prerequisite candidate: `10e629a90355fae61f60058379c4c71fe4ba8f1d` in `C:/dev/worktrees/build-finance-crypto-replay-t01-t03`.
- Exact reviewed implementation named by the final T03 receipt: `61a5e89b1fd19c54a8cb3c2461033d7abd175f2e`.
- Do not merge the prerequisite candidate into the design branch, push, publish, tag, or release without a separate explicit action authorization.
- Implement Build Finance G2 in a fresh worktree/branch derived from the exact reviewed candidate or from an explicitly authorized integration commit. Do not develop in the frozen reviewed worktree.
- Preserve `build_finance.crypto_replay` T01-T03 bytes and inventories unless a separately reviewed contract migration proves a change necessary. New G2-only contracts belong under `build_finance.live_paper`.
- Runtime core is offline and standard-library-only. It has no URL, socket, subprocess, provider SDK, dynamic import, environment-variable lookup, credential, broker, wallet, signer, transaction, or venue-order capability.
- The paper kernel accepts only `ContractVerifiedRunInputs` plus explicit in-memory profiles. A separate offline run-input builder accepts admitted candidates/source receipts and an in-memory resolver, emits sealed normalization evidence and RawEvents, constructs `RunInputBundle`, and calls `verify_contract_run_inputs`. Neither layer accepts a path, URL, account, broker, or provider object.
- The offline run-input builder also accepts one explicit canonical `trading.run-receipt/v1` LF record as the authority root. It resolves only ContentID/SHA-256 identities reachable from that verified root and its verified descendants; it never enumerates storage, infers a default run, or synthesizes missing authority.
- G2 closes the model boundary by using verified model-disabled run inputs and deterministic ABSTAIN evidence only. No model is invoked inside or after verified input construction. In the later optional-model milestone, a model may emit a pre-closed `ModelSignal` evidence record or ABSTAIN, and never quantity, leverage, order type, executable stop, order intent, fill, portfolio mutation, or kill-switch decision.
- The algorithm/fusion layer is also non-authoritative. Only deterministic risk code may produce a `RiskDecision`; only the paper kernel may produce a `SimulatedOrderIntent` and `SimulatedFillReceipt`.
- G2 is long-or-flat spot only. No shorts, puts/options, leverage, margin, borrowing, derivatives, or real assets/funds.
- All monetary, price, quantity, fee, score, and ratio values use canonical integer/fixed-point representations. No binary float enters an authority-bearing record.
- Mandatory exits, position caps, exposure caps, stale-data rejection, drawdown breaker, daily-loss breaker, kill-switch state, and idempotency are deterministic and fail closed.
- Simulated fills are estimates, explicitly labelled as such, and can consume only later committed event groups. No same-event or future-data lookahead.
- Every authority-bearing object is canonical object -> sealed ContentID -> canonical LF record. Reuse `canonical_record_bytes` and `parse_canonical_record`. Replay-schema records continue using the frozen replay `seal_content_id`/`verify_content_id`; new live-paper schemas use an explicitly tested live-paper registry/sealer with the same hash construction. Do not mutate the frozen replay registry or add ad hoc hashing.
- Every task begins RED, implements the smallest GREEN, runs focused and regression gates, receives spec/code review, and ends with a narrow commit. No task may weaken a prior test.
- Synthetic fixtures and model outputs must be labelled synthetic and cannot satisfy real-source promotion gates.
- Do not claim profitability, execution accuracy, market impact realism, or production readiness from G2 results.

---

## Verified Starting Point

| Surface | Verified state |
| --- | --- |
| Replay candidate | Clean and independently reviewed at `10e629a90355fae61f60058379c4c71fe4ba8f1d` |
| Candidate refs | `HEAD`, `refs/crypto-replay/review-candidate`, and `refs/crypto-replay/reviewed-t01-t03` were controller-verified at the same SHA |
| Replay tests | `507 passed, 7 skipped`; skips are Windows symlink privilege denial, not product failures |
| Static gates | schema codegen, Ruff, mypy, `pip check`, artifact verifier, same-wheel import, and diff hygiene passed |
| Canonical inventory | 8 primary, 13 supporting, 27 attachments, 1 formula, 48 generated JSON resources, 49 total authority contracts |
| Current promotion status | Honest/blocking: P0 blocked, P2 zero admitted real fixture, whole-repository P5 unchanged |
| Build Engine | Clean `C:/dev/public/build-engine`, branch `feat/zentropy-branding`, one commit ahead of `origin/main` |
| Current product coupling | `PredictionStrategy` returns `build_finance.data.Signal`; `AdaptiveEngine` constructs broker/AutoTrader and calls private `_process_signals` |
| Current feedback gap | Runtime reads tracker weights but does not call `record_prediction` or `evaluate_past` in its cycle |
| Live behavior in this plan | None; no broker, wallet, provider, credential, network, or order endpoint |

The final controller verification of the reviewed candidate was:

```text
whole tests: 507 passed, 7 skipped
schema_codegen --scope full --check: pass
ruff check .: pass
mypy: success (39 files)
pip check: no broken requirements
artifact verifier: pass
same-wheel clean import: module_count=15
```

---

## Product Boundary and File Map

### Build Finance deterministic substrate and G2 core

Retain unchanged:

- `build_finance/crypto_replay/canonical.py`
- `build_finance/crypto_replay/content_ids.py`
- `build_finance/crypto_replay/schema_registry.py`
- `build_finance/crypto_replay/run_inputs.py`
- `build_finance/crypto_replay/admission.py`
- `build_finance/crypto_replay/jupiter_fixture.py`
- `build_finance/crypto_replay/local_fixture.py`

Create:

- `build_finance/live_paper/__init__.py`
- `build_finance/live_paper/contracts.py`
- `build_finance/live_paper/registry.py`
- `build_finance/live_paper/content_ids.py`
- `build_finance/live_paper/profiles.py`
- `build_finance/live_paper/resolver.py`
- `build_finance/live_paper/normalization.py`
- `build_finance/live_paper/run_input_builder.py`
- `build_finance/live_paper/grouping.py`
- `build_finance/live_paper/features.py`
- `build_finance/live_paper/algorithms.py`
- `build_finance/live_paper/model_validation.py`
- `build_finance/live_paper/fusion.py`
- `build_finance/live_paper/risk.py`
- `build_finance/live_paper/fills.py`
- `build_finance/live_paper/accounting.py`
- `build_finance/live_paper/reconciliation.py`
- `build_finance/live_paper/event_store.py`
- `build_finance/live_paper/kernel.py`
- `build_finance/live_paper/projections.py`
- `build_finance/live_paper/resources/schemas/*.schema.json`
- `build_finance/live_paper/resources/schema-bundle.json`
- `build_finance/live_paper/resources/schema-bundle.sha256`
- `build_finance/live_paper/resources/schema-lock.json`
- `tests/live_paper/**`
- `scripts/capture_live_paper_gate.py`
- `scripts/verify_live_paper_artifacts.py`
- `scripts/run_network_denied.py`
- `scripts/build_paper_core_artifacts.py`
- `build_finance/live_paper/paper_core_manifest.json`
- `docs/live-paper/README.md`
- `docs/live-paper/promotion-status.json`
- `docs/live-paper/evidence/G2-red.json`
- `docs/live-paper/evidence/G2-green.json`

Forbidden imports in the G2 runtime closure:

- `build_finance.autotrader`
- `build_finance.broker`
- `build_finance.market_data`
- `build_finance.risk`
- `requests`, `urllib`, `httpx`, `aiohttp`, `websockets`
- provider/exchange/wallet/signer SDKs

The distributable G2 artifact is a dedicated `build-finance-paper-core` wheel/sdist or equivalent explicit allowlist artifact. It physically contains only the approved canonical/replay and `live_paper` files/resources. Presence of `build_finance/autotrader.py`, `broker.py`, `market_data.py`, live broker documentation, provider SDKs, wallet/signing code, or exchange clients is a gate failure even if unreachable by import.

### Build Engine product shell

Retain:

- `build_engine/model_trainer.py` only as a legacy compatibility surface; it is not used by G2 capital replay
- `build_engine/performance_tracker.py` calculations
- `build_engine/persistence.py` non-secret persistence posture
- CLI/GUI shells as operator adapters

Create or rewire only after Build Finance G2 is durably green:

- `build_engine/capital/contracts.py`: product-side evidence DTOs/adapters
- `build_engine/capital/supervisor.py`: offline kernel invocation and read-only projections
- `build_engine/capital/feedback.py`: outcome observations from closed receipts, ready for later model scoring
- `tests/test_capital_model_boundary.py`
- `tests/test_capital_supervisor.py`
- `tests/test_capital_feedback.py`

Do not route the new capital mode through:

- `PredictionStrategy.generate_signals()` returning `build_finance.data.Signal`
- `AdaptiveEngine._setup_broker()`
- `AdaptiveEngine._setup_trader()`
- `AutoTrader._process_signals()`
- `fetch_yahoo()`

Legacy commands remain compatibility surfaces until a later separately approved migration. The new G2 product command is offline and paper-only.

---

## Required Interfaces

```python
# build_finance/live_paper/resolver.py
class EvidenceResolver(Protocol):
    # Return the exact LF-terminated canonical record for a self ContentID.
    def resolve_record(self, content_id: str) -> bytes: ...
    # Return exact digest-addressed bytes. Canonical JSON attachments have no LF.
    def resolve_bytes(self, sha256: str) -> bytes: ...
```

```python
# build_finance/live_paper/normalization.py
@dataclass(frozen=True)
class NormalizedCandidate:
    raw_event_record: bytes
    normalization_receipt_record: bytes

def normalize_admitted_candidate(
    candidate: ParsedSourceCandidate,
    source_receipt_record: bytes,
    resolver: EvidenceResolver,
    profile_record: bytes,
) -> NormalizedCandidate:
    """Return a sealed RawEvent plus total sealed normalization evidence."""
```

```python
# build_finance/live_paper/run_input_builder.py
@dataclass(frozen=True)
class PaperKernelProfiles:
    normalization_profile_record: bytes
    feature_profile_record: bytes
    algorithm_profile_records: tuple[bytes, ...]
    model_validation_profile_record: bytes
    fusion_profile_record: bytes
    risk_config_record: bytes
    fill_profile_record: bytes

def build_verified_run_inputs(
    run_receipt_record: bytes,
    admitted_candidates: Sequence[ParsedSourceCandidate],
    source_receipt_records: Sequence[bytes],
    resolver: EvidenceResolver,
    profiles: PaperKernelProfiles,
) -> ContractVerifiedRunInputs:
    """Normalize offline, build RunInputBundle, and verify it before kernel entry."""
```

```python
# build_finance/live_paper/grouping.py
@dataclass(frozen=True)
class EventGroup:
    group_sequence: str
    event_ids: tuple[str, ...]
    availability_slot: str
    event_records: tuple[bytes, ...]
    normalization_receipt_record: bytes

def group_committed_events(verified: ContractVerifiedRunInputs) -> tuple[EventGroup, ...]: ...
```

```python
# build_finance/live_paper/features.py
def derive_feature_snapshot(
    committed_history: Sequence[EventGroup],
) -> bytes:
    """Return one sealed canonical trading.feature-snapshot/v1 record."""
```

```python
# build_finance/live_paper/algorithms.py
def derive_algorithm_candidates(
    event_group: EventGroup,
    feature_snapshot_record: bytes,
) -> tuple[bytes, ...]:
    """Return sealed non-authoritative trading.algorithm-candidate/v1 records."""
```

```python
# build_finance/live_paper/model_validation.py
@dataclass(frozen=True)
class ValidatedModelEvidence:
    accepted_signal_record: bytes | None
    feature_snapshot_id: str
    disposition: Literal["ABSTAIN"]
    reason_code: Literal["MODEL_DISABLED"]

def validate_model_signal(
    signal_record: bytes | None,
    signal_manifest_record: bytes | None,
    model_registry_record: bytes | None,
    feature_snapshot_record: bytes,
) -> ValidatedModelEvidence: ...
```

```python
# build_finance/live_paper/fusion.py
@dataclass(frozen=True)
class FusionResult:
    fusion_decision_record: bytes
    decision_group_manifest_record: bytes

def fuse_signal_evidence(
    event_group: EventGroup,
    feature_snapshot_record: bytes,
    algorithm_candidate_records: Sequence[bytes],
    model_evidence: ValidatedModelEvidence,
) -> FusionResult:
    """Return sealed non-authoritative fusion and final group-membership evidence."""
```

```python
# build_finance/live_paper/risk.py
@dataclass(frozen=True, slots=True)
class RiskEvaluation:
    fusion_decision_id: str
    risk_decision_record: bytes
    simulated_order_intent_record: bytes | None

def evaluate_risk(
    event_group: EventGroup,
    feature_snapshot_record: bytes,
    algorithm_candidate_records: Sequence[bytes],
    model_evidence: ValidatedModelEvidence,
    fusion_result: FusionResult,
    portfolio_state_record: bytes,
    risk_config_record: bytes,
) -> RiskEvaluation: ...
```

```python
# build_finance/live_paper/fills.py
def simulate_terminal_fill(
    order_intent_record: bytes,
    later_event_group: EventGroup,
    fill_profile_record: bytes,
    public_seed: bytes,
    resolver: EvidenceResolver,
) -> bytes:
    """Return exactly one sealed trading.simulated-fill-receipt/v1 record."""
```

```python
# build_finance/live_paper/kernel.py
@dataclass(frozen=True)
class PaperKernelResult:
    run_receipt_record: bytes
    run_closure_receipt_record: bytes
    ledger_head_id: str
    portfolio_state_id: str
    projection: Mapping[str, JsonValue]

def run_offline_paper_kernel(
    verified: ContractVerifiedRunInputs,
    resolver: EvidenceResolver,
    profiles: PaperKernelProfiles,
) -> PaperKernelResult: ...

# The kernel begins at verified.bundle.normalized_events. It does not normalize
# admitted candidates or rebuild the verified bundle internally.
```

---

## Task 0: Authorized Integration or Exact-Candidate Worktree

**Files:**
- Read: `docs/crypto-replay/evidence/T03-green.json`
- Read: `docs/crypto-replay/promotion-status.json`
- Create: a fresh G2 worktree only after selecting the authorized integration route

- [ ] **Step 1: Reconfirm exact reviewed state**

```powershell
git -C C:/dev/worktrees/build-finance-crypto-replay-t01-t03 status --short
git -C C:/dev/worktrees/build-finance-crypto-replay-t01-t03 rev-parse HEAD
git -C C:/dev/worktrees/build-finance-crypto-replay-t01-t03 rev-parse refs/crypto-replay/review-candidate
git -C C:/dev/worktrees/build-finance-crypto-replay-t01-t03 rev-parse refs/crypto-replay/reviewed-t01-t03
```

Expected: clean output and all three SHAs equal `10e629a90355fae61f60058379c4c71fe4ba8f1d`.

- [ ] **Step 2: Stop if integration authority is absent**

Do not infer permission to merge. Either:

1. receive explicit authorization to merge the reviewed candidate into `design/live-data-paper-engine-20260713`, then create the G2 branch from that merge; or
2. create the G2 branch directly from exact candidate `10e629a...`, leaving design-branch integration for a later authorized task.

- [ ] **Step 3: Create isolated G2 worktree**

```powershell
git -C C:/dev/worktrees/build-finance-crypto-replay-t01-t03 worktree add C:/dev/worktrees/build-finance-g2-offline-paper -b feat/g2-offline-paper-kernel 10e629a90355fae61f60058379c4c71fe4ba8f1d
```

Expected: new clean worktree at the exact reviewed candidate.

### Execution order after Task 0

Execute Tasks 1 through 11 in numeric order, then Task 13 to produce and verify the dedicated Build Finance paper-core artifact, then Task 12 against that exact local artifact. Finish with separate whole-branch reviews for both repositories. This dependency order overrides the document's section order; Build Engine must not guess or predeclare an artifact that has not been built and verified.

---

## Task 1: Freeze G2 RED and Confinement Gates

**Files:**
- Create: `tests/live_paper/test_g2_contracts.py`
- Create: `tests/live_paper/test_g2_confinement.py`
- Create: `tests/live_paper/test_kernel_determinism.py`
- Create: `scripts/capture_live_paper_gate.py`
- Create: `docs/live-paper/evidence/G2-red.json`

- [ ] **Step 1: Write package-enumerating confinement tests**

Require recursive AST enumeration independent of `__init__.py`. Fail on forbidden imports/calls, path/environment lookup, network/process primitives, legacy trading modules, and import-time side effects.

- [ ] **Step 2: Write the vertical RED contract**

Pin a minimal synthetic long-or-flat run from verified input to normalized event, feature, algorithm evidence, model ABSTAIN, fusion, deterministic risk, one simulated intent, later-event fill, ledger, reconciliation, and closure.

- [ ] **Step 3: Capture exact RED**

```powershell
python -m pytest tests/live_paper/test_g2_contracts.py tests/live_paper/test_g2_confinement.py tests/live_paper/test_kernel_determinism.py -q -p no:cacheprovider -rA
```

Expected: only missing-G2-production failures; confinement self-test passes.

- [ ] **Step 4: Record canonical RED receipt and review the tests**

Commit tests and `G2-red.json` separately. Independent review must approve that tests cannot pass with placeholders and enforce the closed model/execution boundary.

---

## Task 2: Add a Separate Live-Paper Contract and Content-ID Registry

**Files:**
- Create: `build_finance/live_paper/__init__.py`
- Create: `build_finance/live_paper/contracts.py`
- Create: `build_finance/live_paper/registry.py`
- Create: `build_finance/live_paper/content_ids.py`
- Create: `build_finance/live_paper/resources/schemas/algorithm-candidate-v1.schema.json`
- Create: `build_finance/live_paper/resources/schemas/fusion-decision-v1.schema.json`
- Create: `build_finance/live_paper/resources/schemas/normalization-receipt-v1.schema.json`
- Create: `build_finance/live_paper/resources/schemas/decision-group-manifest-v1.schema.json`
- Create: `tests/live_paper/test_g2_contracts.py`

- [ ] **Step 1: Add failing contract vectors**

Test closed keys, canonical integer strings, fixed-point scale declarations, exact self-ID fields, input ContentID closure, ABSTAIN representation, total normalization evidence, sealed decision-group membership, and rejection of quantity/order/execution fields in algorithm/model/fusion records.

- [ ] **Step 2: Implement minimal schemas and local registry**

Add `trading.algorithm-candidate/v1`, `trading.fusion-decision/v1`, `trading.normalization-receipt/v1`, and `trading.decision-group-manifest/v1` without altering the frozen replay schema bundle.

- [ ] **Step 3: Implement the live-paper content-ID sealer**

Use the same omit-self-ID/canonical/SHA-256 construction as the replay helper, but resolve schemas and self-ID fields from the live-paper registry. Tests must prove new records seal/verify while the frozen replay `CONTRACT_SPECS_BY_SCHEMA` and resource digests remain byte-identical.

- [ ] **Step 4: Generate and verify bundle/lock**

```powershell
python -m pytest tests/live_paper/test_g2_contracts.py -q -k "not synthetic_long_or_flat_run_reaches_paper_fill_ledger_reconciliation_and_closure"
python -m build_finance.live_paper.registry --check
```

Expected: the Task 2 contract slice passes with the Task 1 vertical kernel test explicitly deselected, and resources match generated definitions byte-for-byte. The vertical test remains RED until Task 11.

- [ ] **Step 5: Review and commit**

Commit message: `feat(live-paper): add closed G2 evidence contracts`.

---

## Task 3: Normalize Admitted Inputs into Raw Events

**Files:**
- Create: `build_finance/live_paper/resolver.py`
- Create: `build_finance/live_paper/profiles.py`
- Create: `build_finance/live_paper/normalization.py`
- Create: `build_finance/live_paper/run_input_builder.py`
- Create: `tests/live_paper/test_offline_normalization.py`
- Create: `tests/live_paper/support/g2_vectors.py`

**Interfaces:**
- Consumes: frozen `ParsedSourceCandidate`, canonical replay records, `RunInputBundle`, `ContractCodePreimage`, and `verify_contract_run_inputs`; Task 2 live-paper normalization receipt sealer.
- Produces: the exact `EvidenceResolver`, `NormalizedCandidate`, `PaperKernelProfiles`, `normalize_admitted_candidate`, and five-argument `build_verified_run_inputs` interfaces above.
- Authority root: `run_receipt_record` is first and mandatory. Every resolved body must be reachable from its verified identity graph; resolver contents that are not referenced by that graph grant no authority.

- [ ] **Step 1: Write failing exact-byte and provenance tests**

Cover canonical run-receipt parsing/self-ID, admitted receipt/raw-byte SHA binding, parser identity, point-in-time fields, integer scaling, closed source profile, copied-root stability, missing evidence, mismatched evidence, non-admitted candidates, decoder manifest binding, parsed-candidate digest, one total normalization receipt per candidate, and a closed immutable `PaperKernelProfiles` carrier. The normalization profile is the exact fixture-manifest LF record bound by the run receipt and source receipts and is validated before normalization; each remaining profile is validated by its later consumer immediately before use.

Add a compact, behavior-focused root suite: one complete valid graph; tampered run receipt; one representative missing/wrong ContentID record; one representative wrong SHA-addressed body or LF-encoded attachment; source-set/model-disabled closure; copied-root determinism; and profile immutability. Reuse the frozen verifier's existing exhaustive field/cross-binding coverage instead of duplicating a mutation for every artifact or code preimage.

- [ ] **Step 2: Run the new tests and preserve RED evidence**

```powershell
python -m pytest tests/live_paper/test_offline_normalization.py -q -p no:cacheprovider
```

Expected: fail only because the Task 3 modules/interfaces are absent. Record the exact command, exit code, failing test IDs, and representative tracebacks before production edits.

- [ ] **Step 3: Implement resolver protocol and normalizer**

The normalizer accepts only a `ParsedSourceCandidate`, canonical source receipt, resolver, and the verified fixture-manifest normalization profile record. It returns exactly one sealed `trading.raw-event/v1` record plus one sealed `trading.normalization-receipt/v1` that binds decoder manifest, candidate digest, input identities, disposition, and output ID. It performs no I/O.

- [ ] **Step 4: Implement rooted run-input construction**

`build_verified_run_inputs` first validates the explicit canonical run-receipt record. It resolves only the fixture manifest, config evidence/raw bytes, risk config, declared source receipts, run closure, availability schedule, counter capacity, source tree, optional model records, public seed, and all ten code preimages reachable from that root. `resolve_record` returns an exact LF record; `resolve_bytes` returns exact hash-addressed bytes, including canonical JSON attachments without LF. Supplied source receipts must exactly match the run receipt's declared set. In G2, model mode is `DISABLED` and model registry/manifest bodies are absent. The builder retains normalized records, constructs the frozen `RunInputBundle`, and calls `verify_contract_run_inputs`. Its result is the only input accepted by `run_offline_paper_kernel`. Decision grouping remains a kernel step over `verified.bundle.normalized_events`.

- [ ] **Step 5: Run focused GREEN and frozen admission regression**

```powershell
python -m pytest tests/live_paper/test_offline_normalization.py tests/crypto_replay/test_t03_fixture_admission.py -q -p no:cacheprovider
```

Expected: normalization tests and T03 admission regression pass.

- [ ] **Step 6: Run contract, confinement, and static regressions**

```powershell
python -m pytest tests/live_paper/test_g2_contracts.py tests/live_paper/test_g2_confinement.py -q -p no:cacheprovider -k "not synthetic_long_or_flat_run_reaches_paper_fill_ledger_reconciliation_and_closure"
python -m build_finance.live_paper.registry --check
python -m ruff check build_finance/live_paper tests/live_paper/test_offline_normalization.py tests/live_paper/support/g2_vectors.py
python -m mypy build_finance/live_paper
git diff --check
```

Expected: all commands pass. The Task 1 vertical test remains separately RED only because `build_finance.live_paper.kernel` is absent.

- [ ] **Step 7: Review and commit**

Commit message: `feat(live-paper): normalize admitted evidence offline`.

---

## Task 4: Deterministic Grouping and Feature Snapshots

**Files:**
- Create: `build_finance/live_paper/grouping.py`
- Create: `build_finance/live_paper/features.py`
- Create: `tests/live_paper/test_feature_snapshot.py`

- [ ] **Step 1: Write failing causal-order tests**

Pin one two-group causal vertical, caller-order invariance, and one revision lifecycle/fail-closed target case. Rely on the frozen run-input verifier for duplicate rejection and exact global/per-source/availability rank validation rather than duplicating its mutation matrix.

- [ ] **Step 2: Implement grouping**

Group only `verified.bundle.normalized_events` using the verified availability schedule and already-verified ingest rank. Retain exact canonical RawEvent records and emit one group-total `trading.normalization-receipt/v1`. Do not consult wall clock. A final `trading.decision-group-manifest/v1` cannot be sealed here because its closed schema requires nonempty algorithm and fusion IDs; Task 7 seals it after those records exist.

- [ ] **Step 3: Implement integer/fixed-point features**

Start with the smallest approved feature set needed by the vertical slice: exact integer mid price, one-period return, liquidity, route impact, causal age, and warm-up/missing-feature flags. Use the frozen `trading.feature-snapshot/v1` contract and bind the verified run receipt's `feature_code_sha256`; do not introduce portfolio authority or a new feature-profile schema in G2.

- [ ] **Step 4: Verify and commit**

```powershell
python -m pytest tests/live_paper/test_feature_snapshot.py tests/live_paper/test_offline_normalization.py -q
```

Commit message: `feat(live-paper): derive causal feature snapshots`.

---

## Task 5: Deterministic Algorithm Evidence

**Files:**
- Create: `build_finance/live_paper/algorithms.py`
- Create: `tests/live_paper/test_algorithm_candidates.py`

- [ ] **Step 1: Write failing algorithm-evidence tests**

Pin three deliberately simple, auditable candidates: momentum, mean-reversion guard, and liquidity/data-quality veto. Use one positive vertical, one warm-up/veto vertical, and one evidence-binding failure; do not duplicate scalar boundary matrices already enforced by the Task 2 registry.

- [ ] **Step 2: Implement candidate derivation**

Algorithms consume the exact `EventGroup` plus its frozen FeatureSnapshot so every candidate can bind the group-total normalization receipt and decision sequence. G2 algorithms are fixed/non-configurable and may emit directional/ABSTAIN evidence, score, horizon, reasons, input IDs, and formula version only. Opaque synthetic algorithm-profile sentinels remain inert in 1.0.0.

- [ ] **Step 3: Verify and commit**

```powershell
python -m pytest tests/live_paper/test_algorithm_candidates.py tests/live_paper/test_feature_snapshot.py -q
```

Commit message: `feat(live-paper): emit deterministic algorithm evidence`.

---

## Task 6: Validate Optional Model Evidence and Default to ABSTAIN

**Files:**
- Create: `build_finance/live_paper/model_validation.py`
- Create: `tests/live_paper/test_model_validation_abstain.py`

- [ ] **Step 1: Write failing validation tests**

Cover the exact G2 boundary only: absent signal/manifest/registry produces a frozen FeatureSnapshot-bound ABSTAIN; any supplied model body rejects; a tampered FeatureSnapshot self-ID rejects. Active/cached model acceptance is not part of the model-disabled G2 release.

- [ ] **Step 2: Implement total validation**

The verified G2 run is model `DISABLED`. Return an immutable in-memory `ValidatedModelEvidence` with `ABSTAIN/MODEL_DISABLED` and no accepted signal. Do not invent a durable model-validation receipt for an absent model: the frozen receipt requires manifest/signal hashes, while Task 7's sealed FusionDecision already records the total disabled-model ABSTAIN.

- [ ] **Step 3: Verify and commit**

```powershell
python -m pytest tests/live_paper/test_model_validation_abstain.py tests/crypto_replay/test_t02_supporting_contracts.py -q
```

Commit message: `feat(live-paper): validate model evidence with abstain fallback`.

---

## Task 7: Fuse Evidence Without Portfolio Authority

**Files:**
- Create: `build_finance/live_paper/fusion.py`
- Create: `tests/live_paper/test_fusion.py`

- [ ] **Step 1: Write failing fusion tests**

Cover the positive deterministic vertical with caller-order invariance, one liquidity-veto plus directional-conflict case, and one evidence-binding failure. Active-model support/conflict is outside model-disabled G2.

- [ ] **Step 2: Implement profile-bound fusion**

Return one sealed FusionDecision plus the final decision-group manifest. Bind all three fixed algorithm candidates, the FeatureSnapshot, and normalization receipt in fusion inputs; select one schema-representable candidate by fixed veto-first/momentum-primary policy, with mean-reversion directional conflict forcing ABSTAIN through the neutral veto candidate. The model always ABSTAINS. Do not inspect the synthetic fusion profile or emit quantity, stop, leverage, order, or executable action.

- [ ] **Step 3: Verify and commit**

```powershell
python -m pytest tests/live_paper/test_fusion.py tests/live_paper/test_algorithm_candidates.py tests/live_paper/test_model_validation_abstain.py -q
```

Commit message: `feat(live-paper): fuse closed signal evidence`.

---

## Task 8: Deterministic Risk, Mandatory Exits, and Paper Intent

**Files:**
- Create: `build_finance/live_paper/risk.py`
- Create: `tests/live_paper/test_risk_engine.py`

- [ ] **Step 1: Write failing risk tests**

Add exactly three qualitative test functions:

1. an approved flat-to-long entry that independently pins integer sizing, quote-liquidity participation, impact/concentration/balance/notional gates, deterministic fixed stop/take levels, evidence closure, stable reservation/intent identity, and byte-for-byte repeatability;
2. a long-position mandatory full exit where kill, session-end, stop, and take conditions overlap, pinning the frozen reason-code precedence and full base reservation; and
3. a fail-closed suppression test covering a stale attempted entry plus killed/loss-latched flat state, with no intent emitted and arithmetic overflow rejected.

Mark and breaker authority must be derived from sealed `FeatureSnapshot` and `PortfolioState`; no undefined standalone mark/breaker record is permitted. Derive expected fixed-point values by hand in the tests rather than by reusing production helpers.

- [ ] **Step 2: Implement risk evaluation**

Risk receives the full `EventGroup` / `FeatureSnapshot` / fixed algorithm candidates / validated disabled-model evidence / `FusionResult` closure plus authoritative `PortfolioState` and risk-config records. It must recompute `fuse_signal_evidence(...)` and require exact `FusionResult` equality before granting sizing authority; a self-addressed or resealed standalone fusion record is insufficient. Because the frozen `RiskDecision` contract has no fusion field, return the exact FusionDecision ID in immutable in-memory `RiskEvaluation` alongside the sealed records.

Implement only the controls representable in the frozen admitted records: long-or-flat operation, integer target sizing, quote-liquidity participation, impact/concentration/staleness/balance/notional gates, fixed stop/take levels, mandatory stop/take/session-end/kill exits, session-loss/drawdown and existing kill latches, pending-intent suppression, deterministic reservation identity, and fail-closed bounded arithmetic. Use `ceil(target_notional * 10000 / liquidity_quote_atoms)` as the explicitly named G2 quote-liquidity participation proxy. Map `OPEN_LONG` to `ENTER_LONG`, `CLOSE_LONG` to `EXIT_LONG`, and neutral fusion to `HOLD`. Always emit one sealed `RiskDecision`; emit a sealed `SimulatedOrderIntent` only for an approved entry or exit. Mandatory exits are deterministic risk overrides, not model suggestions.

Do not add a schema, plug-in/profile framework, live interface, or ambient state. Cooldown, trailing-stop high-water logic, loss streaks, lot-size controls, explicit minimum-volume fields, concurrent-position caps, external kill requests, route-capacity participation, run-scoped typed reservation keys, and a separate authoritative intent counter are explicit post-1.0 deferrals because the frozen inputs cannot represent their required authority. For G2, derive a domain-separated deterministic opaque reservation digest from the exact accepted evidence and use `intent_sequence=decision_sequence`; document that this proves decision-group determinism, not a stronger run-global counter.

- [ ] **Step 3: Verify and commit**

```powershell
python -m pytest tests/live_paper/test_risk_engine.py tests/crypto_replay/test_t01_primary_semantic_authority.py -q
```

Commit message: `feat(live-paper): add fail-closed deterministic risk authority`.

---

## Task 9: No-Lookahead Simulated Fills

**Files:**
- Create: `build_finance/live_paper/fills.py`
- Create: `tests/live_paper/test_fill_engine_no_lookahead.py`

- [ ] **Step 1: Write failing fill tests**

Add exactly three qualitative test functions:

1. causal byte-stability: a valid intent cannot fill in its decision group, fills against the earliest eligible later group, verifies retained event records through the resolver, and duplicate replay emits byte-identical receipt/draw evidence;
2. terminal arithmetic: full fill, partial fill, and no-next-event expiry pin fixed-point price/fee/cash-delta/release arithmetic by hand without production helper reuse; and
3. authority binding: tampered intent, portfolio-before-fill, event bytes, event self-ID, seed/draw key, or schema self-ID fails closed without filesystem/network/broker/wallet/signer/order capability.

Do not test venue-native limit, stop, queue, retry, or time-in-force transitions in G2 1.0.0. Version 1 supports only frozen long-only spot `MARKET` intent semantics through `trading.simulated-order-intent/v1`; stops/takes are upstream risk triggers that create `CLOSE_LONG` intents and are not venue orders. Explicit estimate labelling is represented by the frozen `trading.simulated-fill-receipt/v1` schema itself; do not add a field.

- [ ] **Step 2: Implement fill state machine**

The fill engine has no broker-shaped `submit_order` interface and no I/O. It consumes an already-created frozen intent, the portfolio state before fill application, the selected later committed event group or `None`, and an explicit in-memory `EvidenceResolver` for the group's committed event records, then returns exactly one terminal simulated-fill receipt plus deterministic adverse-draw evidence.

Use this exact public interface:

```python
@dataclass(frozen=True, slots=True)
class TerminalFillEvidence:
    fill_receipt_record: bytes
    adverse_fill_draw_key_bytes: bytes
    adverse_fill_draw_bytes: bytes

def simulate_terminal_fill(
    verified: ContractVerifiedRunInputs,
    intent_record: bytes,
    portfolio_state_before_fill_record: bytes,
    selected_event_group: EventGroup | None,
    resolver: EvidenceResolver,
) -> TerminalFillEvidence: ...
```

Validate and self-ID-check the frozen `trading.simulated-order-intent/v1`, `trading.portfolio-state/v1`, selected `trading.raw-event/v1` records, and emitted `trading.simulated-fill-receipt/v1` through the existing replay registry/sealer. Verify every `selected_event_group.event_id` resolves to the exact retained record bytes before using the group. Set `portfolio_state_before_id` from the supplied portfolio record. Set `receipt_sequence=intent_sequence`.

If `selected_event_group is None`, emit `EXPIRED` with `FILL_NO_NEXT_EVENT`, null fill coordinates, zero fill arithmetic, and release the full remaining reservation. If the selected group is the decision group or earlier by group/ingest coordinate, emit `REJECTED` with `FILL_SAME_OR_EARLIER_EVENT`. Enforce `STRICT_NEXT_EVENT` / `ONE_EVENT_GROUP` as immediate next-group semantics for G2; nonzero latency, retry residuals, queue priority, limit crossing, spread fields, live transport, broker adapters, wallets/signers, and venue-native stops are explicit deferrals.

Derive the event price as `floor(quote_amount_atoms * 10**(base_decimals + 18) / (base_amount_atoms * 10**quote_decimals))`. Capacity is `min(route_capacity_base_atoms, floor(route_capacity_base_atoms * max_participation_bps / 10000))`; filled base atoms are `min(requested_base_atoms, capacity)`. `FILLED`, `PARTIAL`, `REJECTED`, and `EXPIRED` are terminal for the intent. Use deterministic public-seed adverse draw bytes from the frozen `trading.adverse-fill-draw/v1` formula and a canonical `trading.adverse-fill-draw-key/v1` object; for G2 set `adverse_fill_bps=0` unless a bounded draw is explicitly implemented and pinned by tests. Buy execution adds impact/adverse bps and rounds up; sell execution subtracts them and rounds down. Fee proration uses ceiling from event venue/priority fee atoms to the filled fraction; `simulation_fee_quote_atoms=0`. Release quote reservation for `OPEN_LONG` and base reservation for `CLOSE_LONG` according to the frozen fill semantics.

- [ ] **Step 3: Verify and commit**

```powershell
python -m pytest tests/live_paper/test_fill_engine_no_lookahead.py tests/crypto_replay/test_t02_cross_artifact.py -q
```

Commit message: `feat(live-paper): simulate causal terminal fills`.

---

## Task 10: Hash-Chained Accounting and Independent Reconciliation

**Files:**
- Create: `build_finance/live_paper/event_store.py`
- Create: `build_finance/live_paper/accounting.py`
- Create: `build_finance/live_paper/reconciliation.py`
- Create: `tests/live_paper/test_ledger_reconciliation.py`

- [ ] **Step 1: Write failing accounting tests**

Add exactly three qualitative test functions:

1. genesis plus intent reservation: construct a deterministic genesis portfolio, append a `SIMULATED_INTENT` ledger record, pin ledger sequence/previous-head, quote/base reservation postings, `open_intent_ids`, and byte-stable replay;
2. fill application plus portfolio projection: apply an `OPEN_LONG` fill and a `CLOSE_LONG` fill through frozen intents/receipts, pin cash, position quantity, cost basis, realized/unrealized P&L, fees, equity, release postings, and hash-chain head; and
3. reconciliation halt: duplicate-fill idempotency, tampered ledger/state/fill evidence, and arithmetic overflow must emit a frozen `KILLED` reconciliation receipt and prevent a successful state advance.

Use real sealed `trading.portfolio-state/v1`, `trading.ledger-record/v1`, `trading.reconciliation-receipt/v1`, `trading.simulated-order-intent/v1`, and `trading.simulated-fill-receipt/v1` records. Hand-pin consumer-visible arithmetic in the tests. Do not add a database, filesystem log, schema, external store, broker/wallet/signer/order surface, or exhaustive mutation matrix.

- [ ] **Step 2: Implement append-only in-memory store and accounting**

G2 storage is an explicit immutable in-memory authority for deterministic tests. No filesystem append is needed in this milestone.

Use these public interfaces unless implementation discovers a frozen-contract impossibility:

```python
@dataclass(frozen=True, slots=True)
class InMemoryLedgerStore:
    ledger_records: tuple[bytes, ...]

def append_ledger_record(store: InMemoryLedgerStore, ledger_record: bytes) -> InMemoryLedgerStore: ...

@dataclass(frozen=True, slots=True)
class AccountingTransition:
    store: InMemoryLedgerStore
    portfolio_state_record: bytes
    ledger_record: bytes | None
    reconciliation_receipt_record: bytes

def initialize_accounting(
    verified: ContractVerifiedRunInputs,
    *,
    quote_mint: str,
    quote_decimals: int,
    starting_quote_atoms: int,
) -> AccountingTransition: ...

def reserve_intent(
    verified: ContractVerifiedRunInputs,
    store: InMemoryLedgerStore,
    portfolio_state_record: bytes,
    intent_record: bytes,
) -> AccountingTransition: ...

def apply_fill_receipt(
    verified: ContractVerifiedRunInputs,
    store: InMemoryLedgerStore,
    portfolio_state_record: bytes,
    intent_record: bytes,
    fill_receipt_record: bytes,
) -> AccountingTransition: ...
```

`append_ledger_record` must validate/seal the frozen ledger record, require `ledger_sequence == len(store.ledger_records)`, require `previous_ledger_record_id` to match the current head or null at sequence zero, reject duplicate ledger IDs, and return a new immutable store. `initialize_accounting` creates a PASS `GENESIS` reconciliation receipt and a state-sequence-zero portfolio with one quote balance. `reserve_intent` updates only reservations/open intent IDs and appends one balanced `SIMULATED_INTENT` ledger record. `apply_fill_receipt` updates balances, positions, fees, P&L, equity, reservations, and open intents from the frozen intent/fill pair, then appends one balanced `SIMULATED_FILL` ledger record. Exact duplicate replay from the same inputs must be byte-identical; a second fill for an already-applied intent in the same store must halt through idempotency reconciliation rather than double-applying.

- [ ] **Step 3: Implement independent reconciliation**

Recompute ledger and portfolio arithmetic from retained records using a separate code path. A mismatch emits failure evidence and prevents successful closure.

Use this public interface:

```python
def reconcile_transition(
    verified: ContractVerifiedRunInputs,
    *,
    kind: Literal["GENESIS", "INTENT_RESERVATION", "FILL_TRANSITION"],
    portfolio_state_before_record: bytes | None,
    portfolio_state_after_record: bytes,
    ledger_record: bytes | None,
    causation_records: Sequence[bytes],
) -> bytes: ...
```

The reconciliation receipt must be a frozen `trading.reconciliation-receipt/v1` record. PASS receipts have empty reasons and zero residuals. KILLED receipts use the exact frozen reason owner and precedence rules, including `RECONCILIATION_IDEMPOTENCY_CONFLICT` + `RECONCILIATION_MISMATCH` for duplicate fill intent IDs and `RECONCILIATION_ARITHMETIC_RANGE` + `RECONCILIATION_MISMATCH` for arithmetic overflow. The accounting module may call this function, but reconciliation must not trust accounting's computed summaries; recompute independently from retained bytes. Do not implement group mark-to-market, residual close retries, final run-end closure, execution quarantine, model attempt integrity, or filesystem persistence in Task 10.

- [ ] **Step 4: Verify and commit**

```powershell
python -m pytest tests/live_paper/test_ledger_reconciliation.py tests/crypto_replay/test_t02_ledger_contract.py -q
```

Commit message: `feat(live-paper): reconcile hash-chained paper accounting`.

---

## Task 11: Assemble the Offline Paper Kernel

**Files:**
- Create: `build_finance/live_paper/kernel.py`
- Create: `build_finance/live_paper/projections.py`
- Modify: `tests/live_paper/test_kernel_determinism.py`
- Create: `tests/live_paper/test_kernel_faults.py`

- [ ] **Step 1: Expand RED across the full vertical slice**

Run the same verified inputs twice and require byte-identical output records, ledger head, closure, projection, and reason ordering. Add injected failures at every boundary and require typed fail-closed closure evidence.

- [ ] **Step 2: Implement the sole orchestrator/writer**

`run_offline_paper_kernel` begins at `verified.bundle.normalized_events` and sequences verified grouping -> features -> algorithms -> model validation -> fusion -> risk -> later-event fill -> accounting -> reconciliation -> closure. Pre-kernel normalization/run-input construction is outside this function. Lower layers cannot append authority independently.

- [ ] **Step 3: Complete feedback-ready projections**

Projection contains only derived read models: positions, cash/equity in fixed-point strings, breaker state, model-validation disposition, decisions, fills, reconciliation state, and receipt IDs.

- [ ] **Step 4: Verify and commit**

```powershell
python -m pytest tests/live_paper/test_kernel_determinism.py tests/live_paper/test_kernel_faults.py tests/live_paper -q
```

Commit message: `feat(live-paper): assemble deterministic G2 paper kernel`.

---

## Task 12: Add the Build Engine Model-Disabled Product Adapter

**Repository:** create `C:/dev/worktrees/build-engine-capital-g2` from the verified Build Engine commit; do not edit `C:/dev/public/build-engine` in place.

**Files:**
- Create: `build_engine/capital/__init__.py`
- Create: `build_engine/capital/contracts.py`
- Create: `build_engine/capital/supervisor.py`
- Create: `build_engine/capital/feedback.py`
- Create: `tests/test_capital_model_boundary.py`
- Create: `tests/test_capital_supervisor.py`
- Create: `tests/test_capital_feedback.py`
- Modify: `build_engine/cli.py`
- Modify: `pyproject.toml`
- Modify: `README.md`

- [ ] **Step 1: Create the isolated Build Engine worktree**

```powershell
git -C C:/dev/public/build-engine status --short
git -C C:/dev/public/build-engine rev-parse HEAD
git -C C:/dev/public/build-engine worktree add C:/dev/worktrees/build-engine-capital-g2 -b feat/capital-g2-product-adapter 00a0f4d
```

Expected: source checkout clean at verified commit `00a0f4d`; new worktree clean on the new branch. If HEAD differs, stop and record the new exact base rather than forcing the old SHA.

- [ ] **Step 2: Write failing architectural-boundary tests**

AST and runtime tests prove `build_engine.capital` does not import `ModelTrainer`, `PredictionStrategy`, `AutoTrader`, broker modules, `build_finance.data.Signal`, market-data fetchers, wallet/provider/network code, or expose a model-inference/order method. Tests pin model-disabled verified inputs and the resulting ABSTAIN validation receipt.

- [ ] **Step 3: Implement the model-disabled supervisor**

Supervisor constructs model-disabled `RunInputBundle` fields (`model_registry=None`, `model_signal_manifest=None`) before verification and invokes only the offline paper kernel. Model validation receives no signal and emits the durable ABSTAIN receipt. There is no post-verification model inference hook.

- [ ] **Step 4: Implement receipt-derived feedback observations**

Feedback reads closed decision/fill/portfolio/closure receipts and emits read-only outcome observations with evidence IDs. It does not call the existing `PerformanceTracker`, adjust model weights, or mutate risk/order state in G2. Those observations become the input authority for the later optional-model feedback milestone.

- [ ] **Step 5: Add a new offline-only CLI command**

Add `build-engine capital-replay --fixture <explicit-local-path>`. It performs local capture/admission, constructs model-disabled verified inputs, invokes the paper kernel, and prints projection/receipt IDs. It has no model, `--live`, broker, credential, provider, wallet, or order option.

Add an explicit `capital` optional dependency group or local integration instruction for the separately built `build-finance-paper-core` artifact. Core Build Engine imports/tests must remain usable without that optional dependency, and the command must fail closed with an install instruction when it is absent.

- [ ] **Step 6: Prove lazy optional dependency behavior**

Keep all paper-core imports inside `build_engine.capital` or the `capital-replay` command handler. In a clean environment with ordinary Build Engine dependencies but no Build Finance package, prove `import build_engine.cli`, `build_engine.config`, `build_engine.persistence`, and existing non-capital commands/tests still work. Invoking `capital-replay` without the optional package must fail before fixture access with a concise install instruction.

- [ ] **Step 7: Preserve legacy compatibility without using it**

Do not silently alter existing `run` behavior in G2. Mark the direct model -> AutoTrader path as legacy in docs and ensure the new capital-replay path never reaches it. A later migration plan can remove live coupling after the deterministic replacement has broader parity.

- [ ] **Step 8: Verify and commit**

```powershell
python -m pytest tests/test_capital_model_boundary.py tests/test_capital_supervisor.py tests/test_capital_feedback.py -q
python -m pytest tests/test_performance_tracker.py tests/test_persistence.py tests/test_alerts.py -q
python -m pytest tests/test_model_trainer.py tests/test_prediction_strategy.py tests/test_engine.py -q
```

Commit message: `feat(capital): add evidence-only offline paper supervisor`.

---

## Task 13: Durable G2 Gate, Package Closure, and Handoff

**Build Finance files:**
- Create: `scripts/verify_live_paper_artifacts.py`
- Create: `scripts/run_network_denied.py`
- Create: `scripts/build_paper_core_artifacts.py`
- Create: `build_finance/live_paper/paper_core_manifest.json`
- Create: `docs/live-paper/README.md`
- Create: `docs/live-paper/promotion-status.json`
- Create: `docs/live-paper/evidence/G2-green.json`
- Modify: `.github/workflows/ci.yml`
- Modify: `pyproject.toml` to include `live_paper` package data in the normal development package while leaving the frozen replay package-data rules intact

- [ ] **Step 1: Verify package closure**

`build_finance/live_paper/paper_core_manifest.json` is a canonical explicit allowlist of replay/live-paper runtime modules and resources. `scripts/build_paper_core_artifacts.py` verifies every source digest, copies only the allowlist into a clean staging tree, writes deterministic `build-finance-paper-core` metadata, and invokes the standard build backend there. Build the dedicated wheel/sdist into a clean temp directory and inspect archive members/metadata. The artifact must physically exclude legacy broker/provider/network/wallet/signer/order-transport modules and dependencies, not merely make them unreachable.

- [ ] **Step 2: Run all gates from clean state**

`scripts/run_network_denied.py` installs a process-local socket/DNS denial shim, then either imports the named module or calls `pytest.main()` in the same process. It fails if any connection/name-resolution primitive is called and emits a canonical summary. Tests must first prove the shim catches a deliberate socket/DNS attempt.

```powershell
python -m pytest tests/live_paper tests/crypto_replay -q -p no:cacheprovider
python scripts/run_network_denied.py --pytest tests/live_paper tests/crypto_replay -q -p no:cacheprovider
python scripts/run_network_denied.py --import build_finance.live_paper.kernel
python -m build_finance.crypto_replay.schema_codegen --scope full --check
python -m build_finance.live_paper.registry --check
ruff check build_finance/live_paper tests/live_paper scripts/capture_live_paper_gate.py scripts/verify_live_paper_artifacts.py scripts/run_network_denied.py scripts/build_paper_core_artifacts.py
mypy build_finance/live_paper
python scripts/verify_crypto_replay_artifacts.py --wheel <paper-core-wheel-path> --sdist <paper-core-sdist-path>
python scripts/verify_live_paper_artifacts.py --wheel <paper-core-wheel-path> --sdist <paper-core-sdist-path>
git diff --check
```

Expected: all gates pass; any Windows privilege skip is enumerated and justified; no credential-shaped content exists.

- [ ] **Step 3: Capture canonical G2 GREEN evidence**

The receipt binds exact implementation SHA, commands, pass/fail IDs, stdout digest, schema bundle digest, package artifact digests, import-closure result, determinism result, and explicit paper-only limitations.

- [ ] **Step 4: Independent final review**

Review spec compliance, code quality, model boundary, risk authority, no-lookahead behavior, ledger arithmetic, confinement, package closure, and receipt exactness. Fix findings with RED/GREEN evidence and refresh the receipt.

- [ ] **Step 5: Stop before integration/push/publication**

Report exact reviewed SHAs and artifact paths. Merge Build Finance G2, merge Build Engine adapter, push, publish, or enable a live sensor only under separate explicit authorization.

---

## Required G2 Acceptance Matrix

| Gate | Required result |
| --- | --- |
| Determinism | Same verified inputs/profile/seed produce byte-identical authority records and IDs |
| Model boundary | G2 invokes no model and records ABSTAIN; later model ports can return evidence only and expose no sizing/risk/order fields |
| Risk authority | Only deterministic risk creates decisions/intents; all rejects have durable reason codes |
| Long-or-flat | No short, derivative, margin, leverage, borrow, put, or live asset state exists |
| Stop protection | Entry intents bind deterministic mandatory exit policy; exit precedence is tested |
| No lookahead | Fill consumes only later committed event groups |
| Idempotency | Duplicate signals, decisions, intents, and fills cannot double-apply state |
| Accounting | Ledger is hash-chained; portfolio arithmetic independently reconciles |
| Confinement | No network/provider/broker/wallet/signer/subprocess/environment capability in core |
| Evidence | Every stage emits sealed canonical records with exact input IDs/profile versions |
| Packaging | Clean artifact import and resource closure pass without test/source-tree leakage |
| Product shell | Build Engine capital mode invokes the kernel and reads projections; no AutoTrader/broker path |
| Promotion honesty | G2 remains offline, synthetic/paper-only, and makes no profitability/live-readiness claim |

## Capability-Environment Improvements Left Behind

- A reusable AST/runtime confinement gate for deterministic capital packages.
- A canonical gate recorder for RED/GREEN execution evidence.
- A package-closure verifier that distinguishes installed presence from runtime reachability.
- Deterministic synthetic G2 vectors usable for later sensor, model, and fault-injection work.
- A model-disabled boundary and closed input path reusable by the later local-model milestone.
- An independent accounting/reconciliation harness.
- A Build Engine product adapter that can later accept read-only live sensors without changing risk/execution authority.

## Explicitly Deferred After G2

- Guard-boundary process isolation and OS sandboxing.
- Read-only sensor protocol and live shadow mode.
- Any rights-approved external provider adapter.
- Active local-model inference, model training/fine-tuning, or model publication. The later model milestone must define a deterministic feature-series export, run inference before run-input verification, and bind registry/manifest/signal evidence into the verified bundle.
- Broker/exchange account access, credentials, wallets, signing, transactions, or live orders.
- Options/puts, shorts, leverage, margin, derivatives, and cross-venue routing.
- Performance/profit claims and real-capital promotion.
- Removal of Build Engine legacy commands; deprecate only after replacement parity is measured.
