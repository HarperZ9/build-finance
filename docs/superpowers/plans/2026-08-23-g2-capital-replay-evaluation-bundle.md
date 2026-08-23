# G2 Capital Replay Evaluation Bundle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the verified G2 offline paper kernel and Build Engine shell into a reproducible, positive, disk-backed PAPER ONLY evaluation workflow without adding any live-data, credential, broker, wallet, signer, or order-transport capability.

**Architecture:** Build Finance owns a small explicit disk adapter that loads the exact run receipt, content-addressed evidence, and immutable paper profiles already required by `build_verified_run_inputs`; it does not mint or repair authority. A deterministic development exporter materializes one synthetic evaluation bundle from the reviewed G2 vectors, and the dedicated paper-core artifact is resealed around the new loader. Build Engine remains a thin product shell that lazily binds the loader, runs the real paper core, and emits a stable evaluator receipt.

**Tech Stack:** Python 3.10+, pathlib, dataclasses, existing Build Finance canonical/content-ID contracts, pytest, Ruff, mypy, setuptools/build.

**Spec:** `C:/dev/worktrees/build-finance-live-paper-design/docs/superpowers/specs/2026-07-13-live-market-data-paper-execution-engine-design.md`

## Global Constraints

- PAPER ONLY: no live orders, broker calls, account access, wallets, signers, transfers, or real funds.
- No network access or provider SDK is permitted in the paper-core artifact or evaluation workflow.
- Model mode remains `DISABLED`; the product reports deterministic `ABSTAIN / MODEL_DISABLED` evidence only.
- Deterministic admission, run-input verification, kernel decisions, risk, simulated fills, ledger, reconciliation, and kill behavior remain owned by Build Finance; Build Engine may not reimplement or weaken them.
- The replay envelope is transport for already-authoritative bytes. It may not synthesize missing records, search for a default run, repair digests, or infer profile values.
- All paths are explicit, local, bounded, no-follow, and confined beneath the supplied fixture root. Missing, linked/reparse, malformed, non-canonical, wrong-version, or digest-mismatched material fails closed.
- Preserve the existing Build Finance commits `9926754` and `4c5bf2f`; do not rewrite neighboring-session work.
- Current user instruction withholds release actions. Do not merge, push, publish, tag, upload, contact organizations, access credentials/accounts/wallets, or enable live execution.
- Any newly captured promotion state for a changed implementation must remain `publication: BLOCKED` unless the user separately authorizes that exact new implementation node.
- Prefer one strong positive vertical test and compact representative failure tables. Do not duplicate exhaustive lower-layer matrices.

## Verified Starting Point

- Build Finance worktree: `C:/dev/worktrees/build-finance-g2-offline-paper`, branch `feat/g2-offline-paper-kernel`, current baseline `4c5bf2f`.
- Build Engine worktree: `C:/dev/worktrees/build-engine-capital-g2`, branch `feat/capital-g2-product-adapter`, current baseline `5a45c2d`.
- Fresh controller baseline on 2026-08-23: Build Finance `588 passed, 7 skipped`; artifact gate `22 passed`; Build Engine `186 passed, 4 skipped`.
- G2 kernel, confinement, dedicated paper-core artifact, and Build Engine low-level adapter are complete. The remaining explicit integration gap is the on-disk run-level replay envelope.

## File Map

### Build Finance

- Create `build_finance/live_paper/replay_envelope.py`: strict disk loader, confined resolver, immutable `ReplayEnvelopeContext`.
- Modify `build_finance/live_paper/__init__.py`: export the loader/context only.
- Create `tests/live_paper/test_replay_envelope.py`: positive vertical and representative fail-closed cases.
- Create `tests/live_paper/support/g2_disk_bundle.py`: test/development-only deterministic materializer built from existing G2 vectors and synthetic local-fixture helpers.
- Create `scripts/export_g2_evaluation_bundle.py`: source-checkout exporter that writes a complete synthetic bundle and a checksum manifest; it is not included in paper-core.
- Modify `build_finance/live_paper/paper_core_manifest.json`, artifact tests/scripts, and evidence files only as required to include and reseal `replay_envelope.py`.
- Create `docs/live-paper/evaluation/README.md`: Build Finance fixture/export/verification instructions and explicit limitations.

### Build Engine

- Modify `build_engine/capital/supervisor.py`: lazily bind and use `load_replay_envelope_context` as the default run-context loader.
- Modify `build_engine/capital/contracts.py`: add stable evaluator-receipt serialization without filesystem-specific authority.
- Modify `build_engine/cli.py`: support an explicit optional receipt output and label all results PAPER ONLY / SIMULATED / MODEL DISABLED.
- Modify `pyproject.toml`: bind the `capital` extra to the reviewed paper-core interface version.
- Modify `tests/test_capital_supervisor.py` and add or modify one focused CLI test for the actual disk-backed positive path.
- Modify `README.md` and create `docs/capital-evaluation.md`: one-command evaluator workflow, receipt interpretation, failure recovery, and non-profitability/non-live limitations.

## Replay Envelope v1 Layout

The existing admitted source fixture remains unchanged. It may contain one sibling `replay-envelope/` directory because local admission closes the declared `payloads/` set and does not treat the envelope as market input.

```text
<fixture>/
  manifest.json
  rights/rights-manifest.json
  terms/...
  payloads/...
  witnesses/...
  replay-envelope/
    envelope.json
    run-receipt.json
    records/<content-id>.json
    bytes/<sha256>.bin
    profiles/feature.bin
    profiles/algorithm-0.bin
    profiles/model-validation.bin
    profiles/fusion.bin
    profiles/fill.bin
```

`envelope.json` is exact canonical JSON with this closed body:

```json
{"layout":"content-addressed-v1","model_signal_mode":"DISABLED","paper_core_distribution":"build-finance-paper-core","paper_core_version":"1.1.0","schema":"build-finance.paper-core.replay-envelope/v1"}
```

The loader derives the normalization profile from the exact captured fixture-manifest record and the risk profile from the exact rooted replay-risk-config record. It reads the single G2 algorithm profile from the fixed filename. All other record/byte lookups are keyed by the exact lowercase 64-hex identity supplied to `resolve_record` or `resolve_bytes`; filenames never grant authority.

## Task 1: Add the Strict Build Finance Disk Envelope Adapter

**Files:**

- Create: `build_finance/live_paper/replay_envelope.py`
- Modify: `build_finance/live_paper/__init__.py`
- Create: `tests/live_paper/test_replay_envelope.py`
- Create: `tests/live_paper/support/g2_disk_bundle.py`

**Public interface:**

```python
@dataclass(frozen=True, slots=True)
class ReplayEnvelopeContext:
    run_receipt_record: bytes
    resolver: EvidenceResolver
    profiles: PaperKernelProfiles

def load_replay_envelope_context(
    fixture_root: Path,
    captured: CapturedFixture,
    admission: AdmissionBatch,
) -> ReplayEnvelopeContext: ...
```

- [ ] Write `test_replay_envelope_loader_builds_positive_g2_context`: materialize one source fixture plus envelope, run production capture/admission/loader, call the actual `build_verified_run_inputs` and `run_offline_paper_kernel`, and assert CLOSED output plus `ABSTAIN / MODEL_DISABLED` evidence.
- [ ] Run only that test and confirm RED because the public loader is absent.
- [ ] Write a compact parameterized failure test covering a digest-mismatched `bytes/<sha256>.bin`, a content-mismatched `records/<content-id>.json`, a linked/reparse envelope member where supported, and any non-`DISABLED` envelope mode. Assert failure before kernel execution.
- [ ] Run the failure test and confirm RED for the missing behavior, not test setup.
- [ ] Implement the minimum strict loader and resolver. Validate exact `Path`/captured-root binding, admitted status, fixed canonical envelope bytes, current paper-core version, lowercase 64-hex keys, no-follow regular files, bounded reads, record LF/canonical form, record ContentID, byte digest, and profile snapshots.
- [ ] Do not enumerate records/bytes, add a generic path field, search for another run, import test support from production, or add provider/network behavior.
- [ ] Run `python -m pytest tests/live_paper/test_replay_envelope.py tests/live_paper/test_kernel_determinism.py tests/live_paper/test_g2_confinement.py -q -p no:cacheprovider`.
- [ ] Run `python -m ruff check build_finance/live_paper/replay_envelope.py tests/live_paper/test_replay_envelope.py tests/live_paper/support/g2_disk_bundle.py` and `python -m mypy build_finance/live_paper`.
- [ ] Commit the task and write the SDD report with explicit RED/GREEN evidence.

## Task 2: Export and Reseal the Reproducible Evaluation Bundle

**Files:**

- Create: `scripts/export_g2_evaluation_bundle.py`
- Create: `docs/live-paper/evaluation/README.md`
- Modify: `tests/live_paper/test_replay_envelope.py`
- Modify as required: `build_finance/live_paper/paper_core_manifest.json`
- Modify as required: `tests/live_paper/test_task13_artifact_gate.py`
- Refresh only generated local artifacts/evidence required by the prescribed gate.

- [ ] Write a failing test that exports the same G2 bundle twice into separate temporary directories and asserts a byte-identical sorted checksum manifest and identical positive kernel projection bytes.
- [ ] Write a failing artifact-closure assertion that the built paper-core includes `build_finance/live_paper/replay_envelope.py` and still excludes broker, autotrader, provider SDK, wallet, signer, credential, and order-transport members.
- [ ] Run both focused tests and confirm the expected RED causes.
- [ ] Implement the minimal explicit exporter by reusing the existing test/development materializer. It must refuse a non-empty destination, write only synthetic data, produce a sorted SHA-256 manifest, and never contact a provider.
- [ ] Document the export, inspect, replay, verify, and cleanup commands. Label data SYNTHETIC and results PAPER ONLY / SIMULATED; state that no profitability claim is made.
- [ ] Update/reseal the paper-core manifest and build artifacts for version 1.1.0.
- [ ] Capture fresh gate evidence for the changed implementation without an authorization node; verify the resulting promotion state is `publication: BLOCKED` and `live_readiness: BLOCKED`.
- [ ] Run the full prescribed artifact gate, including normal and network-denied suites, archive closure, Ruff, mypy, schema/registry checks, and `git diff --check`.
- [ ] Commit the task and write the SDD report with artifact paths and hashes.

## Task 3: Complete the Build Engine Disk-Backed Capital Replay Product Shell

**Files:**

- Modify: `build_engine/capital/supervisor.py`
- Modify: `build_engine/capital/contracts.py`
- Modify: `build_engine/cli.py`
- Modify: `pyproject.toml`
- Modify: `tests/test_capital_supervisor.py`
- Create or modify: `tests/test_capital_cli.py`
- Modify: `README.md`
- Create: `docs/capital-evaluation.md`

- [ ] Write a failing integration test that loads the actual Build Finance worktree or freshly built local paper-core artifact, executes `capital-replay` against the exported disk bundle with no injected run context, and asserts CLOSED output, stable projection/closure IDs, and `ABSTAIN / MODEL_DISABLED` evidence.
- [ ] Write a failing test for an explicit receipt-output path. Assert canonical stable JSON excludes absolute fixture paths and contains mode `PAPER_ONLY`, execution `SIMULATED`, model mode `DISABLED_ABSTAIN`, projection/closure/receipt IDs, and evidence summaries.
- [ ] Run focused tests and confirm RED because the actual disk loader is not bound and receipt output is absent.
- [ ] Extend the lazy paper-core adapter with `load_replay_envelope_context`; use it only when no test/integration loader was injected. Keep missing/incompatible optional dependency failure before fixture access.
- [ ] Add minimal stable receipt serialization and the CLI output option. Do not import legacy `AutoTrader`, broker, config live-mode paths, wallet, signer, or provider modules from the capital package.
- [ ] Pin the optional `capital` dependency to `build-finance-paper-core>=1.1.0,<1.2`.
- [ ] Document install-from-local-artifact, export, run, receipt verification, expected failure modes, and the explicit boundary that no live order or profitability claim exists.
- [ ] Run `python -m pytest tests/test_capital_model_boundary.py tests/test_capital_supervisor.py tests/test_capital_feedback.py tests/test_capital_cli.py -q`.
- [ ] Run both legacy focused suites from `AGENTS.md`, then `python -m pytest -q`, Ruff on changed files, mypy on `build_engine/capital`, a credential/capability-shaped-content scan, and `git diff --check`.
- [ ] Commit the task and write the SDD report with the exact one-command demo and receipt path.

## Completion Gate

- Both repository worktrees receive separate whole-branch reviews against their task bases.
- Controller reruns the Build Finance prescribed artifact gate and the Build Engine full suite from current HEADs.
- Controller exports a fresh bundle, runs the real CLI twice from clean output directories, and verifies byte-identical evaluator receipts.
- The final audit records artifact hashes, fixture checksum manifest, exact commands, known limitations, and current authorization state.
- No merge, push, publication, tag, upload, external contact, credential/account/wallet access, live provider use, or live order occurs.

## Explicit Deferrals to the Next Approved Plans

- G3 run-guard contract, separate guard evidence chain, synthetic tick source, watchdog, and two-chain closure.
- G4 provider-neutral sensor protocol, synthetic adapter, pure decoder boundary, and live-shadow capture.
- One rights-approved real read-only provider adapter and protected credential workflow.
- Optional isolated local-model signal worker.
- Soak/performance campaign and paper-only publication promotion.

