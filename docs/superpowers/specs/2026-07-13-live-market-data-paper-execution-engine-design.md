# Live Market Data and Paper Execution Engine Design

## Document control

| Field | Value |
| --- | --- |
| Status | WRITTEN SPECIFICATION APPROVED — IMPLEMENTATION PLANNING OPEN |
| Approval record | On 2026-07-13 the user approved the isolated deterministic architecture, selected live market data with paper execution as the first trading milestone, and then approved this exact written specification. |
| Review gate | Satisfied on 2026-07-13; ordered implementation planning may proceed. |
| Repository | Build Finance |
| Design worktree | C:/dev/worktrees/build-finance-live-paper-design |
| Base | origin/main at 9c9f5c2f15ee037d450bacc3e6a8f8be704d507e |
| First acceptance target | Read-only live market-data sensing plus autonomous paper-only execution |
| Authority boundary | Read-only market-data connections only; no broker or exchange trading/account capability, wallet, signer, transaction builder, order-submission endpoint, real account, or real funds |

In this document, live means live market observations only. Execution means deterministic mutation of an internal paper portfolio. It never means sending an order to a venue.

This is a design specification, not evidence that the described system exists, is profitable, or is production-ready. It makes no profitability, win-rate, latency, or loss-prevention promise.

## Verified baseline and prerequisite state

The following facts were verified from the named local repository artifacts. They are not architectural assumptions.

| Fact | Evidence |
| --- | --- |
| The maintained branch is origin/main at 9c9f5c2. | Git state in this design worktree |
| The existing public package couples its legacy AutoTrader directly to PaperBroker by default and permits an injected broker with submit_order behavior. | build_finance/autotrader.py and build_finance/broker.py |
| The current legacy paper broker uses floating-point amounts, wall-clock timestamps, and immediate fills. | build_finance/broker.py |
| Build Finance repository policy requires paper-by-default behavior, explicit live opt-in, focused numerical tests, and exclusion of credentials, account history, and generated private artifacts. | AGENTS.md and SECURITY.md |
| The replay branch exists at 4b786bf2af8fe6c8d2ddfdb68d3491f737344647 but is not merged into main. | Local Git branch and worktree state |
| A durable T01 GREEN receipt exists and names commit 63decb07a722f36c21bbb7a813b44444f9d5c9c2. | docs/crypto-replay/evidence/T01-green.json on the replay branch |
| No durable T02 GREEN receipt exists. The durable T02 receipt is RED, and the branch contains additional incomplete T02 work. | docs/crypto-replay/evidence/T02-red.json and the 4b786bf tree |
| T03 sensor and source-admission implementation files and GREEN evidence are absent. | The 4b786bf tree compared with the approved T01–T03 plan |
| The replay branch defines eight primary and thirteen supporting closed contract families, including RawEvent, FeatureSnapshot, ModelSignal, RiskDecision, SimulatedOrderIntent, SimulatedFillReceipt, PortfolioState, LedgerRecord, source/config admission, reconciliation, run, and benchmark receipts. | build_finance/crypto_replay/schema_definitions.py at 4b786bf |

Therefore, the replay branch is prerequisite evidence, not merged behavior. This design may reuse its contracts only after T02 and T03 are completed, independently reviewed, verified, and integrated without weakening their closed semantics.

## Decision

Build a new capability island under Build Finance for provider-neutral read-only sensing and deterministic paper execution. Do not extend the legacy AutoTrader-to-Broker path in place.

The new engine has five separately constrained processes:

1. A read-only market-data sensor process with narrowly allowlisted outbound access.
2. A minimal local run-guard process that emits authenticated schedule ticks,
   accepts an out-of-band kill request, and watchdogs the core.
3. A deterministic core process with no network capability.
4. An optional local-model signal worker with typed input and output only.
5. A local operator/supervisor surface that can start, stop, inspect, and kill a paper run but cannot place or route orders.

All authoritative state is event-sourced, integer or fixed-point, content-addressed, and reconciled. The paper actuator is an internal ledger state transition, not a broker adapter. Existing live-capable modules are neither imported by nor packaged into the paper runtime candidate.

## Goals

- Ingest live market observations through provider-neutral, read-only sensor contracts.
- Preserve exact source bytes and admission evidence before normalization.
- Normalize market observations into immutable, replayable events with explicit asset identity, time, precision, and provenance.
- Combine deterministic facts, explicit heuristics, and versioned algorithms without hiding authority in a model.
- Permit an optional local model to emit only a closed directional signal or ABSTAIN.
- Keep sizing, exposure, stop-loss, take-profit, trailing-stop, stale-data, drawdown, and kill-switch decisions deterministic and fail-closed.
- Simulate orders and fills using declared latency, fees, spread, slippage, impact, liquidity, and partial-fill rules without future information.
- Maintain a reconciled, hash-chained paper portfolio ledger and complete run receipts.
- Reproduce a captured live paper run offline with byte-identical authoritative outputs.
- Leave behind reusable contract, benchmark, fault-injection, packaging, and promotion workflows.
- Make continuous autonomous paper operation observable and recoverable without granting an agent trading authority.

## Non-goals

- No real-money trading, exchange order, broker order, wallet operation, signing, transaction construction, or custody.
- No live-execution adapter, dormant live-order switch, or interface compatible with submit_order in the milestone artifact.
- No claim that a stop order prevents loss, that a strategy is profitable, or that paper results predict live results.
- No model-selected size, leverage, stop, take-profit, route, fee, market, asset, risk limit, or execution parameter.
- No model training, fine-tuning, autonomous retraining, or automatic model promotion in this milestone.
- No arbitrary dynamic plugin loading or execution of provider payloads.
- No options, puts, leverage, margin, short selling, perpetuals, or liquidation modeling. Version 1 is long-or-flat spot paper trading because the prerequisite signal vocabulary is ABSTAIN, LONG_BIAS, and EXIT_BIAS.
- No provider network, session, credential, or rate-limit logic in the
  deterministic core. Pinned provider-specific pure decoders are permitted
  only behind the closed decoder protocol described below.
- No acquisition, redistribution, or publication of a dataset without a verified rights record.
- No replacement of the legacy broker path by implication. Legacy live-capable modules remain outside this milestone and outside its runtime package.

## Architectural principles

### Authority is explicit

Every component has one narrow authority:

| Component | May do | Must never do |
| --- | --- | --- |
| Sensor adapter | Read declared market-data channels and emit raw envelopes | Accept order intents, call trade endpoints, hold order-capable scopes, or mutate portfolio state |
| Run guard | Emit sealed-schedule ticks, persist kill requests, monitor core heartbeat, and terminate a stalled paper core | Read market payloads or portfolio strategy, choose trades, edit a running profile, or mutate the ledger |
| Admission layer | Validate source identity, bytes, sequence, rights, size, and time | Repair malformed data or infer missing facts |
| Pure provider decoder and normalizer | Decode admitted bytes with a pinned provider-specific pure decoder, then convert facts to canonical integer/fixed-point events | Open a connection, read credentials, guess decimals, asset identity, venue, pool, or price |
| Feature engine | Derive versioned deterministic values from committed events | Access the network, wall clock, secrets, or portfolio mutation |
| Strategy algorithms | Emit inspectable candidate direction and rationale codes | Size or execute a position |
| Local model worker | Emit ModelSignal or ABSTAIN from a closed snapshot | Access raw provider bytes, secrets, tools, network, risk configuration, or actuator |
| Fusion | Combine candidate evidence using sealed rules | Override a hard risk veto |
| Risk engine | Reject or mint a paper SimulatedOrderIntent | Call a venue or delegate limits to the model |
| Paper fill engine | Evaluate an intent against later committed market events | Use future events, invent liquidity, or send an order |
| Ledger | Commit paper balances, positions, fees, and receipts atomically | Accept an unreceipted state mutation |
| Supervisor agent | Start an approved profile, report, pause, resume, or kill | Change a running risk profile, choose arbitrary assets, or bypass a rejection |

### Determinism is an end-to-end property

The core consumes only committed events, sealed configuration, and
content-bound seeds. It does not read civil/wall time for market decisions,
environment variables, provider connections, random system state, or mutable
configuration. It may read a monotonic counter only for run-guard liveness;
that counter can block or terminate a run but can never create an entry, set a
price, advance replay time, derive a feature, or alter a fill. The resulting
guard-loss decision is captured for replay. Concurrent sensors may arrive in
any order; a single-writer admission sequencer turns accepted input into one
durable order before the core's decision pipeline sees it.

### Failure closes entries

Missing, stale, conflicting, malformed, over-precision, out-of-order, rights-ineligible, or unreconciled input cannot create an entry. A failure may preserve an already-determined paper exit where the sealed risk policy requires reducing exposure. No fallback may silently use cached data as current data.

### Paper and live execution are different capability classes

The paper actuator changes only local, synthetic portfolio state. It has no URL, credential, broker object, wallet object, signing key, transaction type, or order transport. Names, protocols, dependency manifests, import graphs, package contents, and executable scans enforce this distinction.

## System boundary and package layout

The proposed source boundary is:

    build_finance/
      crypto_replay/              prerequisite canonical contracts and replay kernel
      live_paper/
        contracts/                live-only closed schemas; no mutation of frozen replay v1 schemas
        admission/                raw-envelope validation, deduplication, gap and rights gates
        normalization/            closed decoder protocol and provider facts to canonical RawEvent
          providers/              allowlisted pure decoders; no I/O, SDK, credentials, or network
        guard/                    sealed tick, heartbeat, and out-of-band kill contracts
        event_store/              append-only records, checkpoints, hash-chain verification
        features/                 deterministic fact, heuristic, and algorithmic feature families
        signals/                  strategy candidates, model validation, deterministic fusion
        risk/                     sizing, hard limits, stops, circuit breakers, kill latch
        paper/                    order-intent state machine and fill simulator
        ledger/                   portfolio state, accounting, reconciliation, closure
        observability/            authoritative receipts and non-authoritative local metrics
        cli/                      paper-run control and inspection
      market_sensors/
        protocol/                 read-only provider protocol and capability declarations
        providers/                separately packaged provider adapters

The deployment artifacts are separate:

- build-finance-paper-core contains only the canonical/replay and live_paper
  allowlist, including only the selected pure decoder modules. It has no
  networking dependency or provider SDK.
- build-finance-market-sensor contains the read-only sensor protocol and only the selected provider adapters.
- build-finance-paper-guard contains the minimal tick, heartbeat, kill-journal,
  and watchdog implementation. It contains no strategy, model, provider, or
  ledger mutation code.
- build-finance-model-signal is optional and contains the local-model adapter and typed IPC boundary.
- build-finance-paper-console contains local control and read-only observability.

The normal source repository may continue to contain legacy modules, but no milestone runtime artifact may contain build_finance/broker.py, build_finance/autotrader.py, live broker documentation, broker SDKs, wallet libraries, signing libraries, or exchange trading clients. Package-closure tests inspect the actual built artifact, not only source imports.

## Process isolation

### Market-data sensor

- Runs under a dedicated local identity where practical.
- Receives a sealed subscription manifest and a provider capability declaration.
- Has outbound access only to declared market-data hosts and channels.
- Rejects an adapter that declares order, account, transfer, wallet, or signing capability.
- Writes raw envelopes through one bounded local IPC/spool interface.
- Cannot read the paper ledger, model files, risk configuration beyond subscription safety limits, or operator account data.
- Loads any read-only provider credential by an external secret reference. It never serializes, logs, hashes into a receipt, or passes the secret downstream.

### Run guard

- Receives the sealed `TickSchedule`, run ID, heartbeat deadline, watchdog
  deadline, and per-run guard-evidence signing identity before the core starts.
- Launches or adopts the core inside a verified platform containment primitive
  whose contract terminates the paper-core process if the guard process exits.
- Owns the only live clock read used to schedule decisions and emits
  `CapturedDecisionTick` messages over a dedicated authenticated local channel.
- Owns an out-of-band local KILL endpoint independent of the UI process and
  persists each request to a minimal signed, hash-chained guard journal before
  acknowledging it.
- Forwards a responsive-core kill request into the core's admission channel.
  If the core misses its heartbeat or kill-ack deadline, the guard appends and
  flushes `ExternalKillRequested`, terminates that paper-core process, and then
  appends `ExternalKillReceipt`. Either an unacknowledged request or completed
  receipt makes the old run terminal.
- Cannot write the core market/paper ledger. On restart, recovery must verify
  the separate guard-evidence chain before replay and must refuse to resume a
  run that the guard externally killed.
- Has no provider, model, feature, strategy, risk-profile, paper-order, or
  portfolio-state access.

### Deterministic core

- Has no outbound network capability and imports no networking, broker, wallet, or signer module.
- Is the single authoritative writer for the core market/paper chain:
  admission order, events, paper intents, fills, ledger state, and internal run
  receipts.
- Reads only the local sensor channel, run-guard channel, sealed run inputs, and optional typed model-signal channel.
- Uses a bounded queue. Crossing the configured high-water mark blocks new entries and then latches a circuit breaker before data can become silently stale.
- Maintains a non-authoritative monotonic guard-heartbeat timer. It checks guard
  liveness before starting and before committing every decision/control group;
  expiry may only abort uncommitted work, block entries, record guard loss when
  storage remains available, and terminate the run.

### Local-model signal worker

- Runs separately with no network or tools.
- Receives a closed FeatureSnapshot and immutable model/runtime identity.
- Returns one closed ModelSignal within the sealed deadline or produces no accepted output.
- Has no paper-ledger write handle and no risk, order, provider, or supervisor interface.

### Supervisor and UI

- Communicates over authenticated local IPC.
- May select only a pre-admitted run profile before start.
- May request PAUSE_NEW_ENTRIES or RESUME_AFTER_REVALIDATION through the core,
  and KILL through the independent run guard.
- Cannot edit config in place. A profile change ends the current run and starts a new content-addressed run.
- Cannot inject a BUY, SELL, price, fill, model signal, or portfolio state.
- A supervisory agent may summarize receipts and restart failed read-only sensors under policy; it has the same limits as the human-facing console.

## Provider-neutral sensor contract

Every provider adapter implements a deliberately non-trading protocol:

| Operation | Result |
| --- | --- |
| describe | Immutable provider, adapter build, supported channel, precision, sequence, capability, and required pure-decoder identity metadata |
| open | Opens only subscriptions from a sealed SubscriptionPlan |
| next_envelope | Emits CapturedMarketEnvelope or ProviderStatus |
| close | Closes the read-only session |

There is no generic request method and no order-shaped parameter. Provider adapters cannot expose account, balance, quote-to-trade, submit, cancel, transfer, sign, or wallet operations through this protocol.

A `CapturedMarketEnvelope` contains only pre-admission evidence:

- schema and content ID;
- run and sensor-session IDs;
- provider, adapter version, required decoder ID/version/digest, venue, network, and channel IDs;
- stable market identity based on network plus mint/contract IDs, never display symbol alone;
- base/quote asset IDs and declared decimals;
- provider event time when supplied;
- observed_at lineage time;
- provider sequence or source cursor when supplied;
- payload encoding, exact byte length, and raw payload SHA-256;
- read-only capability declaration digest;
- rights-record digest;
- sensor build and subscription-manifest digests.

Supported version-1 observation families are trade, best quote, order-book snapshot/delta, candle, pool reserve/state, venue status, and chain finality/status. A provider need not support every family. Missing fields remain explicitly unavailable; they are never synthesized.

The initial real provider is selected only after endpoint availability, rate limits, channel semantics, and rights are verified. The core design does not depend on that selection. A synthetic/reference adapter is required for deterministic CI.

## Admission and normalization

### Admission order

1. Receive a `CapturedMarketEnvelope` and its exact payload bytes. Recompute
   length and digest before trusting its metadata.
2. Enforce envelope size, encoding, schema, provider, decoder, channel, market,
   rights, and capability allowlists.
3. Validate provider cursor and sequence rules without inventing missing
   records, then determine admitted, rejected, duplicate, quarantined, or gap
   status.
4. In one single-writer append transaction, assign a total `ingest_sequence`
   and, only for an admitted observation, the next `admission_sequence`; append
   the content-addressed raw object and the complete `AdmissionReceipt` binding
   those sequences, status, and payload digest; flush; then acknowledge the
   sensor. No receipt or pre-admission envelope contains a sequence before this
   transaction assigns it.
5. Deduplicate by provider session, stream identity, cursor/sequence, and
   payload digest. A duplicate receives a total receipt but no second
   `admission_sequence` or state effect.
6. Quarantine conflicts. The same source identity with different bytes latches
   the stream circuit breaker.
7. Send only a durably admitted raw object and receipt to the pinned pure
   decoder and normalizer.

A gap is not silently bridged. Backfill may be admitted only through the same read-only contract and must close the exact missing range before the stream becomes entry-eligible again.

### Pure decoder boundary

Every admitted provider/channel pair resolves through the sealed
`DecoderManifest`. Its record binds provider and channel IDs, decoder schema,
decoder version, complete source/resource digest, accepted media type,
observation family, and required asset/precision registry digests.

The selected provider-specific decoder is a pure function of exact admitted
bytes, the admitted envelope, and sealed registries. It has no I/O, network,
SDK, credential, environment, wall-clock, randomness, or portfolio access. It
returns a closed `ParsedMarketCandidate` containing exact numeric text and
source-field presence; the provider-neutral normalizer independently enforces
asset identity, precision, ranges, and fixed-point conversion before minting a
`RawEvent`.

Provider adapters identify a decoder but cannot supply code at runtime. The
paper-core artifact contains only reviewed decoder modules named by its build
allowlist. An unknown decoder, digest mismatch, parse ambiguity, or candidate
that cannot be re-derived from the admitted bytes fails closed with a total
normalization receipt.

### Offline verified-run authority root

The G2 offline run-input builder receives one explicit canonical
`trading.run-receipt/v1` LF record as its authority root. It does not search a
directory, enumerate an object store, infer a default run, or synthesize
missing authority. The public construction boundary is:

```python
def build_verified_run_inputs(
    run_receipt_record: bytes,
    admitted_candidates: Sequence[ParsedSourceCandidate],
    source_receipt_records: Sequence[bytes],
    resolver: EvidenceResolver,
    profiles: PaperKernelProfiles,
) -> ContractVerifiedRunInputs: ...
```

The builder first parses and verifies the run receipt's canonical bytes,
schema, and self ContentID. It may then resolve only identities explicitly
reachable from that receipt and its verified descendants. A record ContentID
is resolved with `resolve_record(content_id)`, which returns the exact
LF-terminated canonical record. A SHA-256 digest is resolved with
`resolve_bytes(sha256)`, which returns the exact digest-addressed bytes. The
latter includes raw source/config payloads, the public seed, code preimages,
and canonical JSON attachment payloads; attachments are canonical JSON bytes,
not LF records.

This closed traversal supplies the fixture manifest, config admission receipt,
optional validated risk config and raw config bytes, source admission receipts,
run-closure receipt, availability schedule, counter-capacity evidence, source
tree, optional model registry/manifest, public seed, and all ten code
preimages. The run-closure receipt is the verified parent of the
counter-capacity digest. In G2, model mode is `DISABLED`, so both model bodies
must be absent and the receipt fields must be null. Supplied source receipts
must exactly match the run receipt's declared source-receipt set; normalized
events are derived only from those admitted candidates and exact source
payload bytes.

`normalization_profile_record` is the exact fixture-manifest record bound by
the run receipt and the source receipts. It is validated before normalization.
The remaining immutable `PaperKernelProfiles` byte records are not aliases for
the frozen run-receipt code-preimage fields; each later deterministic consumer
validates its own profile immediately before use. After normalization, the
builder constructs the existing frozen `RunInputBundle` and calls
`verify_contract_run_inputs`. No new run-input authority contract and no
mutation of the reviewed replay registry are permitted for G2.

### Canonical time and ordering

The inherited vocabulary remains:

- event_time is provider-declared market time when available.
- observed_at is when the sensor first possessed complete bytes.
- ingested_at is optional non-authoritative operational metadata captured by
  the storage boundary after durability; it is excluded from decision logic and
  canonical replay equality.
- ingest_sequence is the immutable total local order of all admission outcomes.
- admission_sequence is the immutable local order of admitted observations.
- replay_clock_ns is a logical clock, not UTC.

The core does not derive decisions from the wall clock. The run guard is the
sole live tick source. It receives a sealed `TickSchedule` and emits an
authenticated `CapturedDecisionTick` containing run ID, schedule digest,
strictly increasing ordinal, planned logical clock, guard monotonic reading,
observed UTC for diagnostics, and prior-tick ID.

The single-writer core admits each tick through the guard channel. The admitted
`DecisionTick` binds the greatest `admission_sequence` durably committed before
the tick transaction as its cutoff. Duplicate, skipped, out-of-order,
wrong-schedule, late-beyond-tolerance, or unauthenticated ticks block new
entries and emit a clock-breaker receipt. A restarted guard must present the
next expected ordinal and prior-tick ID after ledger-head validation; otherwise
the old run cannot resume. Offline replay disables the guard and consumes the
captured admitted ticks and cutoffs exactly.

For each tick, all admitted events within its declared cutoff form an atomic decision group. The group is ordered by the frozen tuple:

    admission_sequence, provider_id, stream_id, provider_sequence_or_null, raw_payload_sha256

Late events are recorded but cannot be inserted into an already committed group. Their policy is explicit: quarantine, or admit to a later correction group with a correction reason. A correction never rewrites history.

### Numerical authority

- Authoritative amounts use integer atoms of an explicitly identified asset.
- Prices, returns, scores, probabilities, uncertainty, and ratios use declared fixed-point integer scales compatible with the replay contracts.
- Float and Decimal objects are rejected at authoritative boundaries.
- Provider numeric text is parsed as exact decimal text, range-checked, and converted according to declared asset decimals and venue tick/lot sizes.
- More precision than the declared contract permits is rejected. The normalizer does not round an observation into validity.
- Sizing rounds quantity down to the allowed lot so risk cannot increase through rounding.
- Arithmetic uses checked bounds. Overflow, division by zero, unknown decimals, non-positive price, or inconsistent asset identity rejects the candidate and records a reason.
- Canonical objects are strict UTF-8 deterministic JSON plus one record newline. Content IDs omit only their designated self-ID field.

## Event sourcing and lifecycle

The authoritative flow is:

    CapturedMarketEnvelope
      -> AdmissionReceipt
      -> pinned pure decoder and ParsedMarketCandidate
      -> RawEvent
      -> atomic decision group
      -> FeatureSnapshot
      -> candidate signals
      -> optional validated ModelSignal or ABSTAIN
      -> FusionDecision
      -> RiskDecision
      -> optional SimulatedOrderIntent
      -> later SimulatedFillReceipt
      -> PortfolioState
      -> ReconciliationReceipt
      -> LedgerRecord

The run has two non-competing evidence domains:

- `CoreLedgerChain` is the only authoritative market/paper-state chain. The core
  is its sole writer. Each ledger record binds the prior ledger ID, object ID,
  object digest, schema, sequence, causation IDs, config digest, and build
  digests.
- `GuardEvidenceChain` is a separate canonical, hash-chained, per-run signed
  safety journal written only by the guard. It may record guard heartbeats,
  captured ticks, kill requests, kill acknowledgements, watchdog decisions,
  and `ExternalKillReceipt`, but it has no market, portfolio, or fill authority.
  The public verification identity and initial guard-chain anchor are sealed
  into the run inputs; the private signing material never enters the core,
  receipts, logs, or build artifacts.

The core event store uses one writer and atomic append-before-acknowledge
semantics. A checkpoint is only a performance cache. On restart, the recovery
verifier checks both chain heads, signatures, run IDs, and cross-referenced tick
or kill IDs before re-deriving state. An incomplete core group is discarded and
replayed from its first event. Corrupt or missing records in either domain
prevent resume.

A read-only closure verifier produces a content-addressed `RunClosureManifest`
that binds both final chain heads without appending to a killed core chain. PASS
requires a valid guard chain with no external kill or unacknowledged kill
request and a valid reconciled core chain. An external kill produces a terminal
KILLED manifest; it can never be imported as a paper-ledger mutation or converted
to PASS.

## Feature and signal architecture

### Deterministic facts

Facts are direct, versioned transforms of committed events:

- last valid price and return at declared windows;
- spread, midprice, depth, and order-book imbalance;
- trade-flow imbalance and volume;
- pool reserves, quoted price impact, and available route depth when supplied;
- realized volatility, range, gap, drawdown, and volume change;
- provider lag, staleness, sequence-gap state, and cross-provider disagreement;
- asset/pool age and immutable on-chain flags only when supplied by an admitted source.

Every fact identifies its input event range, formula version, scale, warm-up state, and validity state.

### Heuristics

Heuristics are explicit deterministic rules, not learned intuition. Version 1 includes:

- stale or incomplete source veto;
- excessive spread, price impact, or provider disagreement veto;
- minimum liquidity and volume gates;
- price-jump, volatility-regime, and liquidity-collapse circuit breakers;
- concentration and market-age gates when admitted evidence exists;
- cooldown after a stop, loss streak, provider reconnect, or circuit-breaker reset;
- anomaly scores from approved deterministic kernels, with formula and threshold receipts.

Unknown evidence fails the rule according to its declared policy. A risk-relevant unknown defaults to no new entry.

### Algorithms

Algorithm modules may emit LONG_CANDIDATE, EXIT_CANDIDATE, or NO_ACTION with normalized score, horizon, warm-up state, input IDs, formula version, and reason codes. Initial families may include trend/momentum, breakout, mean reversion, volatility-adjusted trend, liquidity-aware flow, and a deterministic ensemble.

No algorithm may size, bypass a risk rule, or directly create an intent. Every algorithm must have known-value, invariant, causality, and no-lookahead tests before admission to a run profile.

### Optional local-model signal

The model input is exactly a closed FeatureSnapshot plus immutable model/runtime identity. It receives no raw provider payload, news text, secret, tool handle, network access, order state, or mutable prompt.

The accepted output vocabulary remains:

- ABSTAIN
- LONG_BIAS
- EXIT_BIAS

The model may include bounded confidence, uncertainty, and out-of-distribution evidence defined by the inherited schema, but those values are evidence rather than authority.

Missing, late, malformed, replayed, wrong-version, wrong-feature, wrong-model, over-TTL, out-of-distribution, or unregistered output becomes ABSTAIN with a ModelValidationReceipt. The deterministic path never waits beyond the sealed deadline. A model cannot originate an entry without an independently eligible algorithmic candidate, cannot weaken an exit or veto, and cannot delay a risk exit.

### Deterministic fusion

Fusion is a pure directional-evidence function of the `FeatureSnapshot`,
admitted algorithm outputs, optional validated `ModelSignal`, and sealed fusion
profile. It does not receive the risk profile, portfolio state, stop state,
kill state, exposure, cash, or drawdown.

Precedence is fixed:

1. Eligible deterministic EXIT candidates.
2. Eligible deterministic LONG candidates meeting the declared quorum.
3. Optional model evidence as a bounded tie-breaker or confirmation only; it
   cannot reverse an eligible deterministic exit.
4. Otherwise NO_ACTION.

Weights, quorum, directional-evidence thresholds, and required feature families
are content-addressed fusion configuration. The model cannot supply them.

## Deterministic risk and sizing

The risk profile owns every authority-bearing parameter:

- initial paper cash and one declared quote asset;
- allowed markets and asset identities;
- minimum and maximum entry notional;
- maximum per-position, per-market, per-venue, and total exposure;
- maximum concurrent positions;
- per-trade loss budget;
- maximum participation, spread, impact, fee, and slippage assumptions;
- minimum liquidity and volume;
- maximum session loss and drawdown;
- stop-loss, take-profit, and trailing-stop distances;
- cooldowns and loss-streak breaker;
- stale-after, provider-gap, queue-lag, and clock-skew limits;
- market-intent expiry and latency model;
- kill-exit mode and run-end close policy.

The risk engine receives the `FusionDecision`, committed `PortfolioState`,
sealed risk profile, current breaker/kill state, and valid mark evidence. Its
authority precedence is fixed:

1. Global kill, reconciliation failure, invalid configuration, and hard
   capability failures prevent every new BUY.
2. Mandatory stop-loss, trailing-stop, session-loss, drawdown, run-end, and
   sealed kill-exit conditions may mint a `CLOSE_LONG` intent regardless of
   fusion output.
3. An eligible fused exit may mint a `CLOSE_LONG` intent.
4. A fused long candidate may proceed only after every entry veto and sizing
   limit passes.
5. Otherwise risk emits a receipted rejection or no-action decision.

For a long entry, the deterministic size is the minimum of:

- quantity allowed by the per-trade loss budget at the effective stop distance;
- quantity allowed by remaining position, market, venue, and portfolio exposure;
- quantity allowed by available unreserved paper cash including worst-case fees;
- quantity allowed by the maximum participation and observed eligible liquidity;
- quantity allowed by the maximum notional.

The result rounds down to the venue lot. If it falls below the minimum notional or one lot, risk rejects the entry. The calculation and every limiting term are emitted in the RiskDecision.

No short inventory, borrowed funds, margin, or negative cash is allowed.

## Stop-loss, take-profit, and trailing-stop behavior

- Entry fills establish a content-addressed cost basis and initial stop/take thresholds.
- A stop-loss triggers when the committed mark reaches or crosses the configured adverse threshold.
- A take-profit triggers when the committed mark reaches or crosses the configured favorable threshold.
- A trailing stop uses the highest committed post-entry mark. Its watermark updates only at atomic group close, so an event cannot both create an unseen watermark and fill against it.
- Stop-loss and trailing-stop exits outrank take-profit and strategy exits.
- A trigger creates a paper CLOSE_LONG intent; it does not assume execution at the trigger price.
- The close is evaluated at the earliest eligible later event after configured latency. Gaps, spread, fees, impact, and limited liquidity therefore affect the simulated result.
- Simultaneous triggers use the fixed precedence above and emit all observed trigger reasons.
- Stale or missing prices never reset a stop or watermark. They block entries and preserve the last valid risk state.
- A stop is risk control, not loss insurance. The UI and reports must say this plainly.

## Paper order and fill simulation

### Intent state machine

Version 1 supports long-only spot `MARKET` intents with `BUY` and `CLOSE_LONG`
sides. Stops and takes are risk triggers that create `CLOSE_LONG` intents; they
are not venue-native orders. Limit-price crossing, queue priority, and
time-in-force semantics are deferred rather than represented incompletely.

States are PENDING, FILLED, PARTIAL, REJECTED, EXPIRED, and
CANCELLED_BY_KILL. Each intent has exactly one terminal receipt. A partial fill
is terminal for that intent; any later attempt to fill a remainder requires a
newly risk-approved intent. This preserves the prerequisite
one-intent/one-receipt contract.

For a partially filled `BUY`, the unfilled reservation is released and no
automatic entry retry occurs. For a partially filled mandatory `CLOSE_LONG`,
the ledger commits the filled portion, releases the old reservation, and
records `ResidualExitRequired` for the remaining base atoms. Before any later
entry decision, the next eligible group must either mint a linked replacement
`CLOSE_LONG` intent for the residual inventory or emit a receipted reason why
no executable close is currently possible. New BUY intents remain blocked
while mandatory residual inventory exists. Attempts repeat under the sealed
exit-attempt policy until flat; exhausting the policy or ending the run with
residual inventory globally kills the run and prevents PASS closure with
`UNFLATTENED_PAPER_INVENTORY`.

### No-lookahead fill policy

- An intent cannot fill in its decision group.
- eligible_after_replay_clock_ns is derived from the sealed latency profile and content-bound seed.
- The simulator evaluates the earliest later eligible market group. It may not skip an adverse group for a favorable one.
- A missing or non-executable selected group rejects or expires according to the sealed policy.
- Randomized adverse selection, when enabled, uses a documented deterministic generator and a seed bound to run, intent, model version, and config. System randomness is forbidden.

### Fill price and quantity

The simulator derives:

- reference mid or executable side price from the committed event;
- spread crossing;
- declared latency movement;
- deterministic market impact from requested participation and admitted depth;
- capped adverse-fill draw when enabled;
- venue, priority, and simulation fees as explicit quote atoms;
- available quantity after configured participation limits;
- filled and unfilled base atoms.

No hidden fee or liquidity exists. If depth is unavailable, a profile requiring depth cannot enter. Partial fills release reservation for the unfilled remainder. Every fill records the exact source event/group, formula versions, assumptions, and arithmetic terms.

## Portfolio ledger and reconciliation

PortfolioState contains:

- quote cash, reserved quote, and cumulative explicit fees in quote atoms;
- per-market base atoms, reserved base atoms, cost basis, realized P&L, and last valid mark;
- unrealized P&L plus valuation validity/staleness state;
- peak equity, current drawdown, session loss, loss streak, cooldowns, and circuit breakers;
- pending intent IDs and the global kill-latch state.

The ledger maintains balanced quote-value postings for cash, inventory cost, fees, realized P&L, and reservations, plus exact base-asset inventory conservation.

Reconciliation occurs after every decision group and at closure. It recomputes state independently from the ledger and verifies:

- cash plus reserved cash conservation;
- base inventory plus reserved base conservation;
- no negative cash or long inventory;
- cost basis and realized P&L identities;
- pending-intent reservation coverage;
- fill-to-intent quantity identity;
- fee totals;
- state and ledger sequence continuity;
- drawdown and peak-equity monotonic rules;
- content IDs and hash-chain continuity.

A mismatch emits KILLED reconciliation evidence, latches the global kill switch, and prevents further entries. The run cannot report PASS until closure reconciliation succeeds.

## Circuit breakers and kill switch

Circuit breakers exist at stream, provider, market, portfolio, and engine levels.

Triggers include:

- stale data or missed decision ticks;
- sequence gaps, conflicting duplicates, or clock rollback;
- provider disconnect, degraded venue, or cross-provider divergence;
- excessive spread, impact, volatility, price jump, or liquidity collapse;
- queue backlog, CPU deadline miss, disk pressure, or append failure;
- invalid configuration or contract mismatch;
- maximum session loss, drawdown, exposure, or loss streak;
- reconciliation or hash-chain failure;
- explicit local KILL request.

The global kill latch is one-way within a run. It immediately prevents new BUY intents. The sealed kill-exit mode is either FREEZE_NO_NEW_INTENTS or PAPER_CLOSE_ON_NEXT_ELIGIBLE_EVENT. A CLOSE_LONG intent already required by risk is never converted into an entry and is not cancelled merely because a new-entry breaker fired.

For a responsive core, the run guard first persists the KILL request, the core
admits it on a dedicated control lane ahead of sensor/model work, and commits a
control group containing the internal kill-latch receipt without waiting for
the next scheduled market tick. For a stalled core, the guard does
not claim an internal latch: after the sealed watchdog deadline it flushes an
`ExternalKillRequested` record, terminates the process, and appends an
`ExternalKillReceipt`. Either record makes the old run terminal on recovery and
prevents it from reporting PASS.

The core treats guard heartbeat as a fail-closed liveness input, not market
time. Before starting and before committing each group, it compares its
monotonic liveness counter with the last authenticated heartbeat. When the
sealed guard-loss deadline has expired, it discards the uncommitted group,
admits no new BUY, writes an internal `GuardLostReceipt` when its event store is
available, and terminates. “Immediately” means the first pre-group or
pre-commit guard check after deadline expiry; a group durably committed before
expiry is not rewritten. If the guard exits rather than hangs, the verified OS
containment primitive terminates the core independently of that check.

Resume after a non-global breaker requires fresh valid data, gap closure, a new validation receipt, and completion of the configured cooldown. Global kill requires a new run.

## Receipts and evidence

Where semantics match, the implementation reuses the frozen replay contracts after their prerequisite gate passes. It does not silently alter a v1 schema. Live-only evidence receives new versioned schema IDs.

The minimum evidence set is:

- provider capability and rights record;
- subscription manifest and sensor-session receipt;
- captured market envelope and total admission receipt;
- decoder manifest, parsed-candidate digest, and total normalization receipt;
- tick schedule, captured/admitted decision ticks, group cutoffs, heartbeat
  evidence, and internal or external kill receipts;
- normalized RawEvent and decision-group manifest;
- FeatureSnapshot;
- algorithm candidate receipts and FusionDecision;
- ModelValidationReceipt whether accepted or converted to ABSTAIN;
- RiskDecision for every candidate, including every rejection;
- SimulatedOrderIntent and one terminal SimulatedFillReceipt;
- PortfolioState, ReconciliationReceipt, and LedgerRecord;
- circuit-breaker and kill-latch receipt;
- run input, run closure, and benchmark receipts.

Core authoritative receipts are canonical and content-addressed in the
`CoreLedgerChain`. Guard safety records are canonical and signed in the
separate `GuardEvidenceChain`; they carry no portfolio authority. The closure
manifest binds both domains. Operational logs are explicitly non-authoritative,
structured, local by default, and reference IDs rather than copying secrets or
raw account/provider data.

## Replay parity

A live paper capture is reproducible only if it preserves:

- exact admitted provider bytes;
- admission and gap decisions;
- asset and precision registries;
- captured and admitted DecisionTick events, ordinals, cutoffs, schedule digest,
  and group boundaries;
- guard journal evidence for kill, heartbeat failure, guard loss, or external
  process termination;
- all sealed configuration and build digests;
- provider, feature, algorithm, fusion, risk, fee, liquidity, latency, and model-profile versions;
- accepted model-signal bytes or the exact ABSTAIN receipt;
- content-bound seeds.

Offline replay disables all networking and reads the captured ledger inputs. The required result is byte-identical IDs and canonical bytes for normalized events, feature snapshots, fusion decisions, risk decisions, intents, fills, portfolio states, reconciliation, ledger records, and run closure.

Offline replay verifies the captured `GuardEvidenceChain` byte-for-byte and
uses its admitted tick/kill cross-references; it does not regenerate live
heartbeat timestamps or external termination evidence. The replay closure binds
the original verified guard-chain head.

Wall-clock operational metrics, process IDs, host counters, and UI refresh timing are not authoritative and are compared separately.

## Observability and operator experience

The console presents:

- run mode prominently as PAPER ONLY;
- provider/session health, gaps, reconnects, lag, and staleness;
- event and decision queue depth;
- feature warm-up and invalidity reasons;
- algorithm candidates, model ABSTAIN rate, validation failures, and latency;
- risk rejections and the exact limiting control;
- pending paper intents, simulated fills, exposure, reservations, fees, P&L, drawdown, and stop levels;
- reconciliation status and ledger head;
- circuit-breaker and kill-latch state;
- artifact and receipt locations.

Metrics include p50/p95/p99 ingestion, normalization, feature, fusion, risk, fill, and reconciliation latency; event throughput; dropped/rejected/duplicate/gap counts; queue saturation; reconnect time; model deadline rate; fill participation and deviation; memory; CPU; and disk growth.

No external telemetry is enabled by default. Logs redact credential-shaped values and never contain provider secrets, account identifiers, real trade history, wallet material, or full raw private payloads.

## Data, endpoint, and rights gates

Every real provider and dataset requires a reviewed rights record containing:

- provider/data identity and official source URL;
- access method and channel names;
- terms/license snapshot digest and review date;
- permitted research, storage, retention, derivative, publication, and redistribution uses;
- rate limits and required attribution;
- data classification and deletion policy;
- reviewer and approval status.

Provider-derived raw data is private and non-redistributable by default. Synthetic fixtures are labeled synthetic. Provider fixtures used in CI must be independently permitted, minimized, scrubbed, and content-addressed.

Endpoint onboarding verifies current availability and semantics before implementation. No key, token, cookie, account number, wallet, or payment credential enters source, config committed to Git, logs, tests, fixtures, receipts, build artifacts, or chat. A previously shared credential is never reused.

## Configuration and secret handling

- Run, subscription, provider-capability, decoder, rights, tick-schedule,
  guard/watchdog, model, feature, fusion, and risk profiles are immutable
  content-addressed inputs.
- Environment variables may contain only secret references or read-only sensor credentials in the sensor process.
- The core and model worker receive no credential environment.
- The guard's per-run signing key is generated into guard-only OS-protected
  storage, never supplied through source or environment, and never serialized
  into a receipt or log. Only its public verification identity is a sealed run
  input. Loss of the private key prevents resuming the old run.
- Logs show provider_id and secret-reference ID, never secret values.
- Dumps and crash reports are scrubbed before preservation.
- CI uses synthetic adapters by default.
- A manual provider workflow may use a protected read-only environment only after scope verification. It cannot possess order, account, transfer, or wallet permissions.
- Secret scanning runs on source, fixtures, receipts, logs, and built artifacts.

## CI and release workflows

The implementation plan will introduce separate workflows with least privilege:

### paper-engine-ci

Runs on pull requests and pushes with network disabled for the core:

- contract generation and byte-lock checks;
- unit, invariant, property, adversarial, overflow, no-lookahead, and state-machine tests;
- deterministic replay golden vectors;
- import/capability graph checks;
- type, lint, coverage, and documentation checks;
- secret and credential-shaped content scanning.

### replay-parity

Runs a pinned fixture matrix on supported Python and operating-system versions. It executes repeated clean replays and compares canonical bytes, object IDs, ledger heads, and closure receipts. Any byte difference fails.

### sensor-contract

Uses the synthetic adapter on every pull request. Real-provider contract checks are scheduled or manually dispatched in a protected read-only environment. They test subscription, parsing, sequence, reconnect, rate-limit, and gap behavior only. They cannot load the paper core's state or any trading credential.

### guard-contract

Runs the tick source, authenticated local kill endpoint, heartbeat monitor, and
watchdog against responsive, slow, hung, crashed, duplicate-tick,
missing-tick, wrong-schedule, and restart fixtures. It verifies exact ordinal
and cutoff rules, persistence-before-acknowledgement, internal versus external
kill evidence, process termination deadlines, and old-run non-resumability.

### fault-and-soak

Injects disconnects, duplicates, conflicting duplicates, gaps, delayed
messages, decoder failures, tick faults, guard loss, kill-ack stalls, malformed
payloads, queue pressure, disk faults, model timeouts, process crashes, and
ledger corruption. It verifies deterministic recovery or fail-closed terminal
behavior.

### paper-package

Builds the allowlisted paper artifacts, then:

- compares contents to the package manifest;
- rejects live broker, order transport, wallet, signer, and forbidden networking modules;
- verifies the exact allowlisted pure decoders and the separately minimal guard
  artifact contain no provider SDK, strategy, model, or ledger mutation code;
- produces dependency lock, SBOM, provenance statement, checksums, and license inventory;
- scans secrets and forbidden endpoint/capability strings;
- smoke-runs with synthetic data and no network;
- uploads an unsigned release candidate for review without publishing it.

### promote-paper

Requires all receipts, review approvals, artifact digest matches, soak evidence, known-limit documentation, and a manual environment approval. It cannot publish a real-money actuator because none exists in the artifact graph.

Workflow tokens are read-only by default. Write permissions are scoped only to an explicitly approved release job.

## Promotion stages

| Stage | Required evidence | Capability |
| --- | --- | --- |
| G0 Written design | User approves this exact document | No implementation |
| G1 Replay prerequisite | T01, T02, and T03 durable GREEN evidence; independent review; clean integration | Offline contracts and source admission only |
| G2 Offline paper kernel | Deterministic end-to-end replay, risk, fills, ledger, and closure | No network |
| G3 Run-guard boundary | Synthetic tick, heartbeat, kill, containment, two-chain closure, and watchdog gates pass | No live sensor |
| G4 Live shadow sensor | Qualified run guard plus rights-approved read-only sensor captures and replays observations | No paper intents |
| G5 Live paper candidate | Sensor, guard, and deterministic core emit autonomous paper intents/fills | Paper state only |
| G6 Soak and fault candidate | Performance, recovery, breaker, reconciliation, guard, and parity gates pass | Paper state only |
| G7 Paper-only release | Allowlisted artifacts, SBOM, provenance, docs, checksums, and review pass | Published paper-only product |

Any real execution would require a separate future design, threat model, authorization, implementation plan, and release artifact. Passing G7 grants no such promotion.

## Benchmark methodology

Benchmarks use declared hardware, OS, Python/runtime, build digest, provider/fixture digest, run config, and sample counts. They report distributions, not only averages.

Required benchmark families:

- canonical parsing, admission, normalization, and ledger throughput;
- event-to-feature, feature-to-risk, eligible-event-to-fill, and reconciliation latency;
- queue stability and resource use at increasing event and market counts;
- deterministic parity across clean processes and supported platforms;
- disconnect, gap, late-event, duplicate, overload, disk-fault, and crash recovery;
- model-worker latency and ABSTAIN/deadline behavior measured separately from the nonblocking deterministic path;
- fill-model sensitivity to fee, spread, liquidity, impact, latency, and partial-fill assumptions;
- walk-forward and point-in-time research reports with leakage checks, clearly separated from engineering acceptance.

Backtest or paper P&L is descriptive research output only. It is not a release gate and cannot support a profitability claim.

## Measurable success criteria

### Confinement

- The paper-core artifact contains zero live broker, wallet, signer, transaction, transfer, or order-transport modules.
- Static and runtime capability tests find zero path from ModelSignal, FusionDecision, RiskDecision, or SimulatedOrderIntent to a network call.
- The core completes its full test and replay suite with networking denied.
- All provider credentials used in a protected sensor check are verified read-only, and scans find zero credential value in preserved artifacts.

### Correctness and determinism

- One hundred clean replays of each release fixture produce byte-identical authoritative objects, IDs, ledger heads, and closure receipts.
- The version-1 release matrix—CPython 3.10 and 3.12 on Windows Server 2022 and Ubuntu 24.04, with runner image version captured—produces identical canonical object bytes.
- Pre-admission envelopes contain no core-assigned sequence; each total receipt,
  stored raw object, `ingest_sequence`, and admitted-only
  `admission_sequence` becomes visible atomically or not at all.
- Every selected pure decoder re-derives byte-identical parsed candidates from
  exact admitted bytes, and unknown or digest-mismatched decoders fail closed.
- Tick fixtures cover exact ordinal, prior-ID, cutoff, duplicate, gap,
  authentication, restart, and wrong-schedule behavior.
- Every run has exactly one core-ledger head and one separately verified
  guard-evidence head. A guard record cannot mutate portfolio state, and PASS
  closure is impossible after an external or unacknowledged kill.
- Every admitted decision group reconciles; release fixtures and a 72-hour paper soak contain zero unresolved reconciliation failure.
- Every intent has exactly one terminal fill receipt, and no intent fills from its own or an earlier group.
- Every mandatory partial `CLOSE_LONG` fill either reaches flat through linked
  replacement intents or ends in a deterministic globally killed
  `UNFLATTENED_PAPER_INVENTORY` closure.
- All overflow, over-precision, unknown-decimal, negative-cash, negative-inventory, and sequence-conflict vectors fail closed with stable reason codes.

### Risk behavior

- Stale data, an unclosed sequence gap, invalid config, ledger mismatch, or global kill produces zero new BUY intents after the triggering group.
- Stop-loss, take-profit, and trailing-stop tests cover exact threshold, gap-through, simultaneous trigger, partial fill, fee, and stale-mark cases.
- Mandatory-exit tests cover repeated partial fills, no-liquidity residuals,
  exit-attempt exhaustion, run-end residual inventory, and the prohibition on
  new BUY intents while a residual exit is required.
- Position, market, venue, portfolio, session-loss, drawdown, participation, spread, impact, liquidity, and concurrent-position limits have boundary tests at below, equal, and above each threshold.
- A model failure or adversarial model output can change only accepted directional evidence or ABSTAIN; it cannot change any authority-bearing parameter.

### Reliability

- A 72-hour live-data paper soak completes without an unreceipted state mutation or lost admitted event.
- At least 1,000 deterministic disconnect, gap, duplicate, conflicting,
  late-message, decoder, tick, guard, and core-stall scenarios reach their
  specified recovered state or specified fail-closed terminal state, with the
  expected breaker/kill evidence and byte-identical offline replay.
- Crash recovery resumes from the last valid ledger anchor or refuses to resume; it never skips an unverifiable record.
- Queue saturation triggers the configured breaker before admitted data exceeds stale limits.
- Guard-hang tests prove the core aborts uncommitted work at its first
  pre-group/pre-commit liveness check after deadline; guard-exit tests prove the
  platform containment primitive terminates the core without relying on that
  check.

### Performance on the declared reference profile

The reference profile is the user's primary Windows development machine. Its CPU model, logical-core count, RAM, storage type, power mode, OS build, Python build, process affinity, and background-load declaration are sealed into the benchmark receipt before measurement. Changing any field creates a different profile and prevents a direct comparison.

- At 1,000 admitted events per second across 50 markets, the non-model deterministic core sustains the load for 30 minutes with zero lost admitted event.
- Event-group commit through RiskDecision is at or below 50 ms p99, excluding provider transit and optional model inference.
- Eligible event through simulated fill, ledger commit, and reconciliation is at or below 25 ms p99.
- With a responsive core, a local KILL request is durably accepted by the guard
  and internally latched within 100 ms p99 and no later than the next engine
  group.
- With an injected hung core, the guard flushes `ExternalKillRequested` and
  terminates the paper-core process within the sealed watchdog deadline, then
  appends `ExternalKillReceipt`; the release reference profile sets and
  measures the request-through-termination deadline at no more than 1,000 ms
  p99.
- Model latency is reported separately; a slow model causes ABSTAIN and never causes the deterministic path to miss its budget.

### Operability and release

- A new operator can run the synthetic quickstart, inspect the paper ledger, trigger a kill drill, replay the run, and verify receipt digests from documented commands.
- The release candidate includes an allowlist manifest, SBOM, license inventory, checksums, provenance, security posture, limitations, troubleshooting, and recovery guide.
- The UI, CLI, logs, and reports label the mode PAPER ONLY and distinguish estimated fills from market facts.

## Failure modes and required responses

| Failure | Required response |
| --- | --- |
| Provider disconnect | Mark stream degraded, block entries, preserve existing risk state, reconnect under backoff, and require sequence continuity or admitted backfill |
| Sequence gap | Quarantine the affected stream and market; no entry until exact closure |
| Duplicate with same digest | Emit duplicate receipt; no second state effect |
| Duplicate identity with different bytes | Latch stream breaker and require operator review |
| Unknown or digest-mismatched pure decoder | Reject before parsing; block the affected stream; do not load code supplied by an adapter |
| Clock rollback or impossible time order | Reject observation and degrade the stream |
| Missing, duplicate, out-of-order, or unauthenticated decision tick | Block entries, emit a clock-breaker receipt, and require exact ordinal continuity or a new run |
| Unknown asset, decimals, tick, or lot | Reject; never infer from symbol or prior market |
| Malformed or over-precision number | Reject before authority conversion |
| Stale mark | Block entry; do not reset stops, watermark, peak equity, or drawdown |
| Queue overload | Pause entries, drain within limits, then latch engine breaker if stale boundary approaches |
| Model timeout, invalid output, or OOD | ABSTAIN with receipt |
| Model worker crash | Continue deterministic path with ABSTAIN |
| Disk full or atomic append failure | Stop before acknowledging or mutating authoritative state |
| Ledger or reconciliation mismatch | Global kill and refuse PASS closure |
| Core crash mid-group | Discard incomplete group and replay from the last committed anchor |
| Core heartbeat or kill acknowledgement stalls | Run guard flushes a signed external-kill request to its separate evidence chain, terminates the core after the sealed deadline, appends the result receipt, and makes the old run non-resumable |
| Run guard hangs or its authenticated channel times out | Core aborts uncommitted work at the first pre-group/pre-commit liveness check after the sealed deadline, records internal guard loss when possible, and terminates the run |
| Run guard process exits | Verified platform containment terminates the core; an absent or incomplete guard chain prevents resume and PASS closure |
| Sensor credential exposure | Stop sensor, rotate credential externally, scrub untrusted artifacts, and invalidate the session |
| UI or supervisor crash | Core remains governed by sealed limits; local kill remains available through the separately packaged run-guard endpoint |

## Alternatives considered

### Recommended: isolated event-sourced capability island

This design maximizes deterministic replay, numerical authority, process confinement, and future provider portability. It costs more initial contract and packaging work, but it makes paper behavior inspectable and prevents the existing live-capable broker surface from becoming an accidental dependency.

### Rejected: extend AutoTrader and PaperBroker in place

This is faster initially, but the current path uses floats, immediate fills, wall-clock state, and an interface that can reach submit_order. Retrofitting receipts and confinement around that graph would leave ambiguous authority and weak replay parity.

### Rejected: provider-specific autonomous bot

A single-provider loop could reach a demo sooner, but provider semantics would leak into strategy, risk, and state. It would make rights, fault injection, replay, and provider replacement harder.

### Rejected: model-first agent with tools

Giving a local model market, risk, or execution tools would make behavior non-deterministic and difficult to constrain. The approved architecture deliberately reduces the model to typed directional evidence with ABSTAIN.

## Implementation decomposition after written-spec approval

This architecture is too broad for one safe big-bang implementation plan. After the user approves this written specification, Superpowers planning will create ordered, reviewable plans:

1. Complete and integrate the T01–T03 replay prerequisite.
2. Build the offline event, feature, fusion, risk, paper fill, ledger, and reconciliation vertical slice.
3. Build the run-guard contract, separate guard-evidence chain, synthetic tick
   source, heartbeat timers, kill endpoint, containment adapter, watchdog tests,
   and two-chain closure verifier.
4. Add the provider-neutral sensor protocol, synthetic adapter, pure decoder
   boundary, and live-shadow capture path.
5. Add one rights-approved real read-only provider adapter and prove replay parity.
6. Add the optional isolated local-model signal worker.
7. Add operator workflows, fault/soak benchmarks, allowlisted packaging, and paper-only promotion.

Each plan begins test-first in its own worktree, uses focused review, and must preserve all earlier gates. No phase may pre-create a live actuator.

## Written-spec approval checklist

- [x] The user confirms that version 1 is live data plus paper-only long-or-flat spot execution.
- [x] The user confirms that stops, takes, trailing stops, sizing, and every hard limit remain deterministic.
- [x] The user confirms that the optional local model emits directional evidence or ABSTAIN only.
- [x] The user confirms the separate sensor/run-guard/core/model/supervisor
  process boundary and the two-chain closure rule.
- [x] The user confirms that replay T01–T03 must be completed before this engine inherits its contracts.
- [x] The user confirms the staged workflow and measurable gates.
- [x] The user confirms that real execution, options, leverage, shorts, wallets, and signing remain outside this milestone.

The user approved this checklist with the complete written specification on
2026-07-13. The implementation-planning gate is open; the first plan completes
and integrates the T01–T03 replay prerequisite without creating T04+, live
sensor, model, risk, paper-order, broker, wallet, or real-execution capability.
