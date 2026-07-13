# Crypto Replay Prerequisite Completion and Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the already-started Build Finance T02 and T03 offline replay prerequisites, preserve the durable T01 result, and integrate the reviewed capability island into the approved live-data/paper-engine design branch without starting T04 or adding any network, model, paper-order, broker, wallet, signer, or real-execution capability.

**Architecture:** Continue the isolated `build_finance.crypto_replay` branch rather than rewriting it. Complete the closed schema/resource graph and contract-only verifier at T02, then add a secure explicit-local-file sensor and pure non-authoritative admission parser at T03. Build and inspect the actual archives, independently review the completed branch, and merge that exact reviewed commit into the design branch with a merge commit so provenance remains visible.

**Tech Stack:** Python 3.10+, standard-library runtime package, immutable dataclasses, restricted canonical JSON/SHA-256, generated closed JSON Schemas, pytest, Ruff, mypy, Python build/wheel/sdist inspection, Git worktrees.

## Global Constraints

- Normative product design: `docs/superpowers/specs/2026-07-13-live-market-data-paper-execution-engine-design.md` on branch `design/live-data-paper-engine-20260713`.
- Normative prerequisite plan: `docs/superpowers/plans/2026-07-11-crypto-replay-kernel-t01-t03.md` at base commit `9c9f5c2f15ee037d450bacc3e6a8f8be704d507e`.
- Continue implementation in `C:/dev/worktrees/build-finance-crypto-replay-t01-t03` on branch `feat/crypto-replay-t01-t03`; do not reimplement completed T01 work in the design worktree.
- Integration occurs only after T02 and T03 durable GREEN receipts, focused verification, independent review, and clean artifact checks.
- Stop at T03. Do not implement T04 sequencing, features, strategies, inference, fusion, risk, stop logic, sizing, paper intents, fills, portfolios, or a live sensor.
- Do not access a provider, package index, `.env`, credential, API token, exchange/broker account, wallet, signer, transaction builder, or order endpoint.
- The previously shared Jupiter credential is out of scope and must not appear in source, tests, docs, command output, evidence, archives, or commits.
- `build_finance.crypto_replay` must remain standard-library-only at runtime. `jsonschema` remains test/dev-only and is not required by an installed replay subpackage import.
- T03 reads only an explicitly supplied local directory. It has no default path, environment lookup, provider fallback, SDK, URL, socket, subprocess, or dynamic import.
- T03 emits total `SourceAdmissionReceipt` evidence and non-authoritative `ParsedSourceCandidate` values only. It does not emit `RawEvent` or any authority-bearing market decision.
- Synthetic fixtures remain test-only and can never satisfy real-fixture promotion gate P2.
- Preserve honest promotion state: P0 `BLOCKED`, P2 `FAIL_ZERO_ADMITTED_FIXTURE`, whole-repository P5 legacy state unchanged, and real fixture identity `null`.
- Every production change begins with an observed failing test, followed by the smallest implementation, focused verification, and a narrow commit.
- Never amend or rewrite the existing T01/T02 history. Never publish, tag, release, push, or delete a worktree under this plan.

---

## Verified Starting Point

The following was rechecked locally on 2026-07-13 before this plan was written:

| Item | Verified state |
| --- | --- |
| Replay branch | Clean `feat/crypto-replay-t01-t03` at `4b786bf2af8fe6c8d2ddfdb68d3491f737344647` |
| Common base | `origin/main` at `9c9f5c2f15ee037d450bacc3e6a8f8be704d507e` |
| T01 | Durable GREEN receipt at `docs/crypto-replay/evidence/T01-green.json`, naming implementation commit `63decb07a722f36c21bbb7a813b44444f9d5c9c2` |
| T02 | Durable RED only; the current focused T01+T02 run is `247 passed, 11 failed` |
| Current T02 failures | Five source-tree scanner tests, one source-tree-derived Round 18 test, and five unknown attachment schemas: benchmark request, hardware profile, force-close state envelope, run-closure fill-candidate semantic, and run-closure reference set |
| T03 | No production files, tests, or RED/GREEN evidence exist |
| Existing supporting contracts | All 13 supporting schema resources and four T02 test modules exist |
| Missing final T02 resources | 27 attachment schemas, binary formula, final bundle/digest/lock, source-tree implementation, known-good graph, and T02 GREEN receipt |

The exact baseline command is:

```powershell
python -m pytest tests/crypto_replay/test_t01_canonical.py tests/crypto_replay/test_t01_primary_bundle.py tests/crypto_replay/test_t01_primary_contracts.py tests/crypto_replay/test_t01_primary_semantic_authority.py tests/crypto_replay/test_t02_supporting_contracts.py tests/crypto_replay/test_t02_cross_artifact.py tests/crypto_replay/test_t02_round_closures.py tests/crypto_replay/test_t02_ledger_contract.py -q --tb=short
```

Expected at the starting commit: exit 1 with exactly 247 passing and 11 failing tests. Any different result is recorded before implementation; do not force the workspace to match this table.

---

## File and Interface Map

### T02 completion

- Modify `build_finance/crypto_replay/schema_definitions.py`: populate all 27 entries in `ATTACHMENT_SCHEMA_DOCUMENTS` without changing the frozen inventory.
- Modify `build_finance/crypto_replay/schema_codegen.py` only if a failing generation invariant proves it necessary; keep the existing 8/13/27/1/48/49 lock arithmetic.
- Create `build_finance/crypto_replay/source_tree.py`: fail-closed no-follow scanner.
- Modify `build_finance/crypto_replay/run_inputs.py`: compare independently derived canonical source-tree/attachment bodies where current tests require it.
- Generate `build_finance/crypto_replay/resources/formulas/adverse-fill-draw-v1.txt`.
- Generate `build_finance/crypto_replay/resources/schemas/*.schema.json` for exactly 27 attachments.
- Generate `build_finance/crypto_replay/resources/schema-bundle.json`, `schema-bundle.sha256`, and `schema-lock.json`.
- Create `tests/crypto_replay/support/known_good_graph.py` and extend `tests/crypto_replay/support/builders.py`.
- Create `docs/crypto-replay/evidence/T02-green.json` only through the gate recorder.

### T03 completion

- Create `build_finance/crypto_replay/local_fixture.py`: explicit-root, exact-byte, no-follow capture.
- Create `build_finance/crypto_replay/jupiter_fixture.py`: pure parser and internally derived parser identity; no provider I/O.
- Create `build_finance/crypto_replay/admission.py`: closed admission/status/receipt logic.
- Create `tests/crypto_replay/support/synthetic_local_fixture.py`.
- Create `tests/crypto_replay/test_t03_fixture_admission.py` and `tests/crypto_replay/test_t03_confinement.py`.
- Create `docs/crypto-replay/evidence/T03-red.json` and `T03-green.json` only through the gate recorder.

### Packaging, CI, and integration

- Create `docs/crypto-replay/README.md`, `docs/crypto-replay/promotion-status.json`, and `scripts/verify_crypto_replay_artifacts.py`.
- Modify `pyproject.toml`, `.github/workflows/ci.yml`, and T03 confinement tests only as required to prove package closure and clean-install behavior.
- Integrate the reviewed replay commit into `design/live-data-paper-engine-20260713`; preserve both the approved design and replay history.

### Required public interfaces

```python
# build_finance/crypto_replay/source_tree.py
class SourceTreeError(ValueError): ...

def scan_source_tree(root: Path, *, root_label: str) -> dict[str, JsonValue]: ...
```

`scan_source_tree` returns this closed shape, with rows sorted by unsigned UTF-8 bytes of `relative_path`:

```python
{
    "schema": "trading.source-tree/v1",
    "root_label": "repository-root",
    "files": [
        {
            "relative_path": "src/kernel.py",
            "file_sha256": sha256_hex(b"abc"),
            "byte_length": "3",
        }
    ],
}
```

```python
# build_finance/crypto_replay/local_fixture.py and admission.py
@dataclass(frozen=True)
class CapturedFile:
    admission_sequence: str
    relative_path: str
    payload: bytes
    sha256: str
    byte_length: int
    observed_at: str | None
    ingested_at: str | None

@dataclass(frozen=True)
class CapturedFixture:
    manifest: Mapping[str, JsonValue] | None
    manifest_payload: bytes | None
    rights_manifest: Mapping[str, JsonValue] | None
    rights_manifest_payload: bytes | None
    terms_by_sha256: Mapping[str, bytes]
    files: tuple[CapturedFile, ...]
    capture_issues: tuple[ValidationIssue, ...]

@dataclass(frozen=True)
class ParsedSourceCandidate:
    admission_sequence: str
    relative_path: str
    raw_payload_sha256: str
    source_id: str | None
    source_kind: str | None
    source_revision: str | None
    market_id: str | None
    source_position: Mapping[str, JsonValue] | None
    revision: Mapping[str, JsonValue] | None
    event_time: str | None
    observed_at: str
    ingested_at: str

@dataclass(frozen=True)
class AdmissionBatch:
    status: Literal["ADMITTED", "REJECTED", "QUARANTINED"]
    reason_codes: tuple[str, ...]
    source_receipt_records: tuple[bytes, ...]
    candidates: tuple[ParsedSourceCandidate, ...]

@dataclass(frozen=True)
class ParserIdentity:
    version: Literal["solana-jupiter-fixture-parser/v1"]
    code_sha256: str

def capture_local_fixture(root: Path) -> CapturedFixture: ...
def current_parser_identity() -> ParserIdentity: ...
def admit_local_fixture(captured: CapturedFixture) -> AdmissionBatch: ...
```

---

## Task 1: Reconfirm Branch, Evidence, and Exact RED Surface

**Files:**
- Read: `docs/crypto-replay/evidence/T01-green.json`
- Read: `docs/crypto-replay/evidence/T02-red.json`
- Read: `build_finance/crypto_replay/**`
- Read: `tests/crypto_replay/**`
- Create: `docs/crypto-replay/evidence/T02-continuation-baseline.json`

- [ ] **Step 1: Prove the continuation target is exact and clean**

```powershell
git status --short
git branch --show-current
git rev-parse HEAD
git merge-base HEAD origin/main
git diff --name-only 9c9f5c2f15ee037d450bacc3e6a8f8be704d507e...HEAD
$design = 'C:\dev\worktrees\build-finance-live-paper-design'
$designStatus = git -C $design status --porcelain
if ($designStatus) { throw 'approved design/spec/plan documents are not committed' }
$designCommit = git -C $design rev-parse HEAD
git -C $design show "${designCommit}:docs/superpowers/specs/2026-07-13-live-market-data-paper-execution-engine-design.md" *> $null
git -C $design show "${designCommit}:docs/superpowers/plans/2026-07-13-crypto-replay-prerequisite-completion-integration.md" *> $null
git update-ref refs/crypto-replay/design-doc-base $designCommit
```

Expected: clean replay worktree, branch `feat/crypto-replay-t01-t03`, HEAD `4b786bf2af8fe6c8d2ddfdb68d3491f737344647` before new work, no changes to legacy broker/live modules, and a clean design worktree whose HEAD contains both approved documents. The private local ref freezes that exact design-document commit for the later merge precondition; it is not a tag or publish action.

- [ ] **Step 2: Run T01 alone before touching T02**

```powershell
python scripts/capture_crypto_replay_gate.py T01 GREEN "$env:TEMP\T01-continuation-check.json" -- tests/crypto_replay/test_t01_canonical.py tests/crypto_replay/test_t01_primary_contracts.py tests/crypto_replay/test_t01_primary_bundle.py -q
python -m pytest -p no:cacheprovider tests/crypto_replay/test_t01_primary_semantic_authority.py -q
```

Expected: both commands exit 0. The captured command/test inventory must exactly match durable `T01-green.json`; the separately added semantic-authority module is regression coverage and is not compared to that receipt. Compare immutable T01 resources independently and do not overwrite `T01-green.json`.

- [ ] **Step 3: Capture the current T02 continuation baseline**

```powershell
python scripts/capture_crypto_replay_gate.py T02 RED docs/crypto-replay/evidence/T02-continuation-baseline.json -- tests/crypto_replay/test_t02_supporting_contracts.py tests/crypto_replay/test_t02_cross_artifact.py tests/crypto_replay/test_t02_ledger_contract.py tests/crypto_replay/test_t02_round_closures.py -q --tb=short
```

Expected: exit non-zero. The receipt records current HEAD and the actual failures. At the verified starting point this T02-only command is 49 passed and 11 failed; the broader T01+T02 command is 247 passed and 11 failed. Use the newly captured result as execution truth.

- [ ] **Step 4: Reproduce clean-runner installation before changing CI**

```powershell
$audit = Join-Path $env:TEMP ("bf-replay-ci-audit-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path "$audit\dist" | Out-Null
python -m build --wheel --no-isolation --outdir "$audit\dist"
$auditWheels = @(Get-ChildItem "$audit\dist\*.whl")
if ($auditWheels.Count -ne 1) { throw 'unexpected clean-runner wheel census' }
python -m venv "$audit\venv"
& "$audit\venv\Scripts\python" -m pip install --no-index --no-deps $auditWheels[0].FullName
& "$audit\venv\Scripts\python" -I -c "import build_finance; import build_finance.crypto_replay"
```

Expected: either a clean built-wheel import or a preserved exact traceback. Do not guess at a remote CI cause and do not edit CI until a local failure or package-closure requirement identifies a concrete change.

- [ ] **Step 5: Commit only the baseline receipt**

```powershell
git add docs/crypto-replay/evidence/T02-continuation-baseline.json
git diff --cached --check
git commit -m "test(crypto-replay): record T02 continuation baseline"
```

---

## Task 2: Seal the Final T02 Attachment Schema Bundle

**Files:**
- Modify: `build_finance/crypto_replay/schema_definitions.py`
- Modify only if a failing invariant requires it: `build_finance/crypto_replay/schema_codegen.py`
- Create generated resources under `build_finance/crypto_replay/resources/`
- Test: `tests/crypto_replay/test_t02_round_closures.py`

- [ ] **Step 1: Run the five currently failing attachment cases RED**

```powershell
python -m pytest -p no:cacheprovider tests/crypto_replay/test_t02_round_closures.py::test_benchmark_preflight_failure_receipt_is_total tests/crypto_replay/test_t02_round_closures.py::test_benchmark_hardware_profile_is_closed tests/crypto_replay/test_t02_round_closures.py::test_t02_force_close_sell_alias_attachment_schema_is_closed tests/crypto_replay/test_t02_round_closures.py::test_t02_force_close_fill_extreme_attachment_schema_is_closed tests/crypto_replay/test_t02_round_closures.py::test_t02_force_proof_row_attachment_schema_and_sort_order_are_closed -q
```

Expected: five failures with `unknown_schema` at the starting commit.

- [ ] **Step 2: Populate all 27 closed attachment schemas as one frozen inventory**

Do not add only the five observed schemas. Define every ID already frozen in `ATTACHMENT_SCHEMA_IDS`, including schedule, normalized set, capacity, source tree, reservation/idempotency, transition/footprint, reconciliation, force-close proof, and benchmark families. Every object schema requires all declared fields and `additionalProperties: false`; every reference is local and registered.

The completed invariant is:

```python
assert set(ATTACHMENT_SCHEMA_DOCUMENTS) == set(ATTACHMENT_SCHEMA_IDS)
assert len(ATTACHMENT_SCHEMA_DOCUMENTS) == 27
```

- [ ] **Step 3: Generate, then check, the exact full resource set**

```powershell
python -m build_finance.crypto_replay.schema_codegen --scope full --write
python -m build_finance.crypto_replay.schema_codegen --scope full --check
```

Expected: 8 primary + 13 supporting + 27 JSON attachment schemas + one binary formula; 48 generated JSON schemas and 49 total authority contracts. The sealed primary bundle and its digest are byte-identical to their T01 versions.

- [ ] **Step 4: Pin the independent final-bundle digest**

Use an independent canonical-byte test to calculate the final `schema-bundle.json` digest, pin it as `EXPECTED_SCHEMA_BUNDLE_SHA256` in `test_t02_round_closures.py`, delete/regenerate only T02-owned resources, and prove the regenerated digest matches the literal. The test must not import the code generator to create its expected rows.

- [ ] **Step 5: Run schema/oracle gates GREEN**

```powershell
python -m pytest -p no:cacheprovider tests/crypto_replay/test_t02_round_closures.py -k "benchmark_preflight or hardware_profile or force_close_sell_alias or force_close_fill_extreme or force_proof_row or attachment_schema or schema_bundle" -q
python -m build_finance.crypto_replay.schema_codegen --scope full --check
python -m ruff check build_finance/crypto_replay/schema_definitions.py build_finance/crypto_replay/schema_codegen.py
python -m mypy build_finance/crypto_replay/schema_definitions.py build_finance/crypto_replay/schema_codegen.py
```

Expected: selected tests and static checks exit 0; check mode changes no files.

- [ ] **Step 6: Commit the schema closure**

```powershell
git add build_finance/crypto_replay/schema_definitions.py build_finance/crypto_replay/schema_codegen.py build_finance/crypto_replay/resources tests/crypto_replay/test_t02_round_closures.py
git diff --cached --check
git commit -m "feat(crypto-replay): seal T02 attachment schema bundle"
```

---

## Task 3: Implement the No-Follow Source Tree and Close T02 Inputs

**Files:**
- Create: `build_finance/crypto_replay/source_tree.py`
- Modify: `build_finance/crypto_replay/run_inputs.py`
- Test: `tests/crypto_replay/test_t02_round_closures.py`
- Create: `tests/crypto_replay/support/known_good_graph.py`
- Modify: `tests/crypto_replay/support/builders.py`
- Modify: `tests/crypto_replay/test_t02_cross_artifact.py`

- [ ] **Step 1: Re-run the six source-tree-owned cases RED**

```powershell
python -m pytest -p no:cacheprovider tests/crypto_replay/test_t02_round_closures.py::test_source_tree_preimage_is_canonical tests/crypto_replay/test_t02_round_closures.py::test_source_tree_rejects_missing_extra_nonregular_unreadable_and_reparse_entries tests/crypto_replay/test_t02_round_closures.py::test_source_tree_root_junction_is_rejected_without_resolution tests/crypto_replay/test_t02_round_closures.py::test_source_tree_replacement_race_is_rejected tests/crypto_replay/test_t02_round_closures.py::test_source_tree_git_control_file_is_canonically_excluded tests/crypto_replay/test_t02_round_closures.py::test_round18_run_and_source_decision_vector_is_derived -q
```

Expected: failures identify the absent `scan_source_tree`/`SourceTreeError` surface.

- [ ] **Step 2: Implement fail-closed scanning**

The scanner must:

- reject a symlink, junction, reparse point, non-regular entry, unreadable file, path outside the explicit root, or entry whose stable identity cannot be proven;
- reject a root that is itself a link/reparse point before listing or resolving its target;
- never call `Path.resolve`, `realpath`, or follow-link stat while classifying a protected path;
- use no-follow open where available and compare pre/open/post file identity and size;
- exclude the exact Git-control entries from the frozen plan, including directory `.git/` and worktree control file `.git`;
- normalize only safe UTF-8 NFC POSIX relative paths and sort by unsigned UTF-8 bytes;
- hash exact bytes and encode byte lengths as canonical base-10 strings.

Use a typed rejection; do not silently omit unsafe entries:

```python
class SourceTreeError(ValueError):
    """The source tree cannot be represented without following or racing an entry."""
```

- [ ] **Step 3: Reconstruct and compare authoritative attachment bodies**

In `verify_contract_run_inputs`, independently reconstruct source-tree, availability-schedule, normalized-event-set, and counter-capacity bodies from retained inputs. Compare full canonical object bytes before comparing their SHA-256 bindings. Continue returning only:

```python
ContractVerifiedRunInputs(authority="CONTRACT_ONLY", ...)
```

Never create a runnable receipt, ledger, genesis state, or promotion authority.

- [ ] **Step 4: Build the joint resolving graph bottom-up**

`known_good_graph.py` must resolve all 8 primary, 13 supporting, 27 attachment, and one formula authority objects. Supporting object resolver entries become `SCHEMA_VALID` only after exact canonical bytes, schema, semantic, and self-ID validation. Keep model mode `DISABLED`, benchmark graph contract-only/ineligible, and the execution quarantine receipt outside ledger membership.

Add `test_known_good_graph_resolves_every_t02_authority()` to `test_t02_cross_artifact.py`. It independently inventories the final lock, requires exact 8/13/27/1/48/49 counts, resolves every retained ID/digest, asserts all 21 self-addressed primary/supporting contracts verify, rejects any supporting reference left at `DIGEST_ONLY`, and passes the resulting bundle to `verify_contract_run_inputs()` with authority exactly `CONTRACT_ONLY`.

Freeze these graph facts:

```python
EXPECTED_SCHEDULE = [
    {"availability_slot": "1", "equal_time_group": "1", "admission_cutoff": "2"},
    {"availability_slot": "2", "equal_time_group": "2", "admission_cutoff": "3"},
]
EXPECTED_PUBLIC_SEED_HEX = "000000000000000000000000000000000000000000000000000000000000000f"
```

The derived counts are `S=2`, `R=2`, `G=2`, `M=1`, `C=0`; next decision 3, next producer 0, next intent 3, next fill receipt 3, unmatched reservation upper bound 4, next state 13, and next ledger 43.

- [ ] **Step 5: Run all T02 tests and static checks**

```powershell
python -m build_finance.crypto_replay.schema_codegen --scope full --check
python -m pytest -p no:cacheprovider tests/crypto_replay/test_t02_supporting_contracts.py tests/crypto_replay/test_t02_cross_artifact.py tests/crypto_replay/test_t02_ledger_contract.py tests/crypto_replay/test_t02_round_closures.py -q
python -m ruff check build_finance/crypto_replay tests/crypto_replay
python -m mypy build_finance/crypto_replay
```

Expected: all T02 tests exit 0; no T01 file or resource changes.

- [ ] **Step 6: Commit the T02 implementation before evidence**

```powershell
git add build_finance/crypto_replay/source_tree.py build_finance/crypto_replay/run_inputs.py tests/crypto_replay/support/known_good_graph.py tests/crypto_replay/support/builders.py tests/crypto_replay/test_t02_cross_artifact.py tests/crypto_replay/test_t02_round_closures.py
git diff --cached --check
git commit -m "feat(crypto-replay): close T02 contract inputs"
```

---

## Task 4: Capture Durable T02 GREEN Without Regressing T01

**Files:**
- Create: `docs/crypto-replay/evidence/T02-green.json`
- Verify: all T01/T02 code and evidence

- [ ] **Step 1: Capture T02 GREEN from the implementation commit**

```powershell
python scripts/capture_crypto_replay_gate.py T02 GREEN docs/crypto-replay/evidence/T02-green.json -- tests/crypto_replay/test_t02_supporting_contracts.py tests/crypto_replay/test_t02_cross_artifact.py tests/crypto_replay/test_t02_ledger_contract.py tests/crypto_replay/test_t02_round_closures.py -q
```

Expected: exit 0, receipt status GREEN, exact command/test inventory, and receipt commit equal to the just-tested implementation commit.

- [ ] **Step 2: Re-run T01 and verify its sealed bytes**

```powershell
python -m pytest -p no:cacheprovider tests/crypto_replay/test_t01_canonical.py tests/crypto_replay/test_t01_primary_contracts.py tests/crypto_replay/test_t01_primary_bundle.py tests/crypto_replay/test_t01_primary_semantic_authority.py -q
git diff 63decb07a722f36c21bbb7a813b44444f9d5c9c2 -- build_finance/crypto_replay/resources/primary-schema-bundle.json build_finance/crypto_replay/resources/primary-schema-bundle.sha256
```

Expected: tests exit 0 and the two sealed bundle files have no diff.

- [ ] **Step 3: Commit only durable evidence**

```powershell
git add docs/crypto-replay/evidence/T02-green.json
git diff --cached --check
git commit -m "test(crypto-replay): record durable T02 green gate"
```

---

## Task 5: Write T03 RED and Implement Explicit Local Capture

**Files:**
- Create: `tests/crypto_replay/support/synthetic_local_fixture.py`
- Create: `tests/crypto_replay/test_t03_fixture_admission.py`
- Create: `tests/crypto_replay/test_t03_confinement.py`
- Create: `docs/crypto-replay/evidence/T03-red.json`
- Create: `build_finance/crypto_replay/local_fixture.py`
- Create: `build_finance/crypto_replay/jupiter_fixture.py`
- Create: `build_finance/crypto_replay/admission.py`

- [ ] **Step 1: Write the frozen admission behavior tests**

Include these exact acceptance tests:

```python
def test_fixture_hash_mismatch_quarantines_set() -> None: ...
def test_point_in_time_fields_required() -> None: ...
def test_duplicate_base_mint_quarantines_set() -> None: ...
def test_base_mint_cannot_equal_quote_mint() -> None: ...
def test_partial_rights_evidence_is_preserved() -> None: ...
def test_conflicting_source_position_rejected() -> None: ...
def test_same_slot_different_market_is_not_conflict() -> None: ...
```

Also cover traversal, absolute/drive/backslash paths, symlink/junction/reparse roots and entries, missing/extra/non-regular payloads, witness mismatch, pre/open/post replacement, distinct rights/terms digest failures, stable receipts across roots, duplicate-version idempotence, complete parser import/resource closure, and proof that universe declarations do not promote P2.

Every fixture is created under `tmp_path`. Freeze the sentinel contract exactly:

```text
source_id: SYNTHETIC_TEST_ONLY_INVALID
base_mint: SYNTHETIC_BASE_MINT_0OIl_INVALID
event_time: 2026-01-01T00:00:00.000000000Z
observed_at: 2026-01-01T00:00:01.000000000Z
ingested_at: 2026-01-01T00:00:02.000000000Z
terms byte prefix (UTF-8): SYNTHETIC TEST FIXTURE — NOT MARKET DATA
payload byte sentinels (ASCII): "source_id":"SYNTHETIC_TEST_ONLY_INVALID"
                                "base_mint":"SYNTHETIC_BASE_MINT_0OIl_INVALID"
```

Fixture helper names and docstrings contain `SYNTHETIC`. No fixture payload,
terms, witness, candidate, or ADMITTED receipt is written under package
resources or `docs/crypto-replay`.

- [ ] **Step 2: Write confinement tests before production modules**

AST and fresh-process tests deny direct/transitive network, broker, wallet, provider, process-spawn, native FFI, dynamic import, `exec`, and `eval` paths. Import every discovered `build_finance.crypto_replay` submodule in a clean process and assert it does not import `build_finance.autotrader`, `build_finance.broker`, or `build_finance.market_data`.

- [ ] **Step 3: Commit RED tests, then bind the RED receipt to that commit**

```powershell
git add tests/crypto_replay/support/synthetic_local_fixture.py tests/crypto_replay/test_t03_fixture_admission.py tests/crypto_replay/test_t03_confinement.py
git diff --cached --check
git commit -m "test(crypto-replay): add T03 red admission gates"
python scripts/capture_crypto_replay_gate.py T03 RED docs/crypto-replay/evidence/T03-red.json -- tests/crypto_replay/test_t03_fixture_admission.py tests/crypto_replay/test_t03_confinement.py -q
git add docs/crypto-replay/evidence/T03-red.json
git diff --cached --check
git commit -m "test(crypto-replay): record durable T03 red gate"
```

Expected: the gate command exits non-zero because the three production modules are absent. The receipt's `git_commit` equals the committed RED-test revision, and T01/T02 remain GREEN. Continue after the expected non-zero exit; do not use a command wrapper that aborts before staging the receipt.

- [ ] **Step 4: Implement exact-byte capture and evidence preservation**

`capture_local_fixture(root)` accepts one explicit `Path`; it performs no environment lookup or fallback. It reads canonical LF manifest/rights/witness records and exact raw payload/terms bytes. It recomputes every named digest, validates witness identity, proves stable no-follow file identity, and returns total `capture_issues` instead of repairing evidence.

Map failures exactly:

- rights-manifest digest mismatch → `ADMISSION_MANIFEST_MISMATCH`;
- absent/unreadable or digest-mismatched terms → `ADMISSION_RIGHTS_MISSING`, preserving a safely observed actual digest;
- witness sequence/path/hash mismatch → `ADMISSION_MANIFEST_MISMATCH`;
- absent/noncanonical witness or invalid/null observation timestamp → `ADMISSION_POINT_IN_TIME_MISSING`;
- payload digest mismatch → `ADMISSION_HASH_MISMATCH`.

- [ ] **Step 5: Implement the pure parser and internally derived identity**

`jupiter_fixture.py` owns `PARSER_VERSION = "solana-jupiter-fixture-parser/v1"`. The parser extracts only declared source/market identity, immutable mint decimals, source position, revision lineage, event time, and presence of route/liquidity/fee fields. It must not invent core sequences, groups, replay time, decisions, or `RawEvent` IDs.

`current_parser_identity()` hashes a canonical bundle containing every AST-reachable local runtime module and dynamically opened schema/resource from the admission/parser roots. A test independently derives the same closure and rejects omissions or extra hand-maintained rows.

- [ ] **Step 6: Make the non-position subset GREEN**

```powershell
python -m pytest -p no:cacheprovider tests/crypto_replay/test_t03_fixture_admission.py -k "hash_mismatch or point_in_time or duplicate_base_mint or base_mint_cannot_equal or partial_rights or terms_digest or witness_identity or parser_identity" -q
```

Expected: selected capture, rights, checksum, parser-lineage, and set-closure tests exit 0; position conflict tests may still fail.

- [ ] **Step 7: Commit the capture/parser slice**

```powershell
git add build_finance/crypto_replay/local_fixture.py build_finance/crypto_replay/jupiter_fixture.py build_finance/crypto_replay/admission.py tests/crypto_replay
git diff --cached --check
git commit -m "feat(crypto-replay): add confined local fixture admission"
```

---

## Task 6: Close T03 Lineage, Confinement, and Durable Evidence

**Files:**
- Modify: `build_finance/crypto_replay/admission.py`
- Modify: `build_finance/crypto_replay/jupiter_fixture.py`
- Modify: T03 tests
- Create: `docs/crypto-replay/evidence/T03-green.json`

- [ ] **Step 1: Run the lineage cases RED**

```powershell
python -m pytest -p no:cacheprovider tests/crypto_replay/test_t03_fixture_admission.py::test_conflicting_source_position_rejected tests/crypto_replay/test_t03_fixture_admission.py::test_same_slot_different_market_is_not_conflict -q
```

- [ ] **Step 2: Implement exact lineage/version keys and batch totality**

```python
lineage_key = (
    source_id,
    source_kind,
    market_id,
    slot,
    transaction_index,
    instruction_index,
    event_index,
    source_native_event_id,
    source_subsequence,
)
version_key = lineage_key + (
    revision_kind,
    revision_availability_slot,
    revision_availability_admission_sequence,
    supersedes_target or "",
    retracts_target or "",
)
```

Same version/same payload is idempotent; same version/different bytes conflicts; two distinct ORIGINAL bodies for one lineage conflict; different market/native IDs do not conflict. A conflict quarantines participating receipts and the batch. Rejected/quarantined batches expose zero candidates. Identical candidates collapse deterministically to the lowest numeric admission sequence, then unsigned UTF-8 path.

- [ ] **Step 3: Prove confinement before capturing GREEN**

```powershell
python -m pytest -p no:cacheprovider tests/crypto_replay/test_t03_confinement.py -q
$graph = index internals --root . --json | ConvertFrom-Json
$bad = @($graph.edges | Where-Object {
    $_.from -like 'build_finance/crypto_replay*' -and
    $_.to -like 'build_finance/*' -and
    $_.to -notlike 'build_finance/crypto_replay*'
})
if ($bad) { $bad | ConvertTo-Json -Depth 5; throw 'crypto_replay import escaped capability island' }
```

Expected: confinement tests pass and `index` reports zero internal import edges outside the subtree. If `index` is unavailable or its output schema differs, record that fact and rely on the mandatory AST/fresh-process tests; do not fabricate a PASS.

- [ ] **Step 4: Verify the completed implementation before committing it**

```powershell
python -m pytest -p no:cacheprovider tests/crypto_replay/test_t03_fixture_admission.py tests/crypto_replay/test_t03_confinement.py -q
python -m pytest -p no:cacheprovider tests/crypto_replay -q
python -m build_finance.crypto_replay.schema_codegen --scope full --check
```

Expected: T03, complete replay suite, T01, T02, and generated-resource check all exit 0.

- [ ] **Step 5: Commit the exact GREEN implementation**

```powershell
git add build_finance/crypto_replay/admission.py build_finance/crypto_replay/jupiter_fixture.py tests/crypto_replay
git diff --cached --check
git commit -m "feat(crypto-replay): close deterministic T03 admission"
git status --short
```

Expected: clean worktree. The new HEAD is the implementation commit that the durable receipt will name.

- [ ] **Step 6: Capture and commit durable T03 GREEN**

```powershell
python scripts/capture_crypto_replay_gate.py T03 GREEN docs/crypto-replay/evidence/T03-green.json -- tests/crypto_replay/test_t03_fixture_admission.py tests/crypto_replay/test_t03_confinement.py -q
git add docs/crypto-replay/evidence/T03-green.json
git diff --cached --check
git commit -m "test(crypto-replay): record durable T03 green gate"
```

Expected: receipt exit 0 and `git_commit` equals the immediately preceding implementation commit.

---

## Task 7: Package, Verify, Review, and Integrate the Exact Reviewed Commit

**Files:**
- Create: `docs/crypto-replay/README.md`
- Create: `docs/crypto-replay/promotion-status.json`
- Create: `scripts/verify_crypto_replay_artifacts.py`
- Modify: `pyproject.toml`
- Modify only for proven requirements: `.github/workflows/ci.yml`
- Modify: `tests/crypto_replay/test_t03_confinement.py`
- Merge into: `C:/dev/worktrees/build-finance-live-paper-design`

- [ ] **Step 1: Document honest capability and promotion state**

The README explains install/API/local fixture contract/gate commands/troubleshooting and states the limitations explicitly: no T04, live sensor, provider, model, feature, risk, fill, portfolio, broker, wallet, real fixture, profitability evidence, or trading execution.

`promotion-status.json` must contain machine-checkable values equivalent to:

```json
{
  "p0": "BLOCKED",
  "p1": "PASS",
  "p2": "FAIL_ZERO_ADMITTED_FIXTURE",
  "p5": "FAIL_WHOLE_REPOSITORY",
  "replay_subpackage_confinement": "PASS",
  "real_fixture_manifest_sha256": null,
  "next_authorized_node": null
}
```

If T01/T02/T03 or confinement is not GREEN, change the corresponding claim to the observed failure; never edit evidence to make this object pass.

- [ ] **Step 2: Build and mechanically inspect one fresh wheel and sdist**

```powershell
$artifact = Join-Path $env:TEMP ("bf-crypto-replay-" + (git rev-parse --short=12 HEAD))
if (Test-Path -LiteralPath $artifact) { throw "stale artifact root: $artifact" }
New-Item -ItemType Directory -Path "$artifact\dist" | Out-Null
$env:PIP_NO_INDEX = '1'
$env:PIP_DISABLE_PIP_VERSION_CHECK = '1'
python -m build --no-isolation --outdir "$artifact\dist"
$wheels = @(Get-ChildItem "$artifact\dist\*.whl")
$sdists = @(Get-ChildItem "$artifact\dist\*.tar.gz")
if ($wheels.Count -ne 1 -or $sdists.Count -ne 1) { throw 'unexpected artifact census' }
python scripts/verify_crypto_replay_artifacts.py --wheel $wheels[0].FullName --sdist $sdists[0].FullName
```

The verifier asserts rather than merely reporting:

- the wheel contains primary/final bundle JSON and `.sha256` files,
  `schema-lock.json`, the binary formula, and every schema named by the lock;
- exact archive-member recomputation of lock counts `8/13/27/1/48/49` and all
  primary/supporting/attachment/formula/final bundle digests;
- the wheel excludes tests, evidence, local fixture roots, payloads, terms,
  witnesses, `.env` names, fixture/receipt bytes, credential-shaped names, and
  the exact synthetic terms/payload sentinels;
- the sdist may contain source tests/docs but excludes generated fixture roots,
  every payload/terms/witness directory, `.env` names, secrets, and the exact
  generated sentinel payload/terms bytes;
- unconditional normalized `Requires-Dist` values are exactly
  `numpy>=1.24`, `pandas>=2.0`, and `scipy>=1.10`;
- `jsonschema>=4.23,<5` appears only with `extra == "test"` or
  `extra == "dev"`; and
- no provider/network/broker/wallet requirement appears.

- [ ] **Step 3: Prove installed-artifact import closure**

```powershell
$artifact = Join-Path $env:TEMP ("bf-crypto-replay-" + (git rev-parse --short=12 HEAD))
$wheels = @(Get-ChildItem "$artifact\dist\*.whl")
if ($wheels.Count -ne 1) { throw 'the verified wheel is not available' }
python -m venv "$artifact\venv"
& "$artifact\venv\Scripts\python" -m pip install --no-index --no-deps $wheels[0].FullName
& "$artifact\venv\Scripts\python" -I -c "import importlib,pkgutil,build_finance.crypto_replay as p; [importlib.import_module(m.name) for m in pkgutil.walk_packages(p.__path__,p.__name__+'.')]"
```

Expected: every replay submodule imports without optional numerical/test libraries and without importing forbidden legacy/network/provider modules.

- [ ] **Step 4: Add CI only for locally proven gates**

After the exact commands in Steps 2 and 3 pass locally, add this dedicated
Ubuntu/Python 3.12 job. It installs `build` plus the existing test surface,
builds exactly one artifact pair once, passes those exact paths between steps,
verifies the pair, and installs that same wheel into the clean import venv:

```yaml
crypto-replay-package:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: "3.12"
    - name: Install replay test and build dependencies
      run: |
        python -m pip install --upgrade pip
        python -m pip install build
        python -m pip install -e ".[all,test]"
    - name: Check generated resources and replay confinement
      run: |
        python -m build_finance.crypto_replay.schema_codegen --scope full --check
        python -m pytest -p no:cacheprovider tests/crypto_replay -q
    - name: Build exactly one artifact pair
      run: |
        mkdir -p .artifacts/crypto-replay/dist
        PIP_NO_INDEX=1 PIP_DISABLE_PIP_VERSION_CHECK=1 python -m build --no-isolation --outdir .artifacts/crypto-replay/dist
    - name: Freeze artifact paths
      id: replay_artifacts
      run: >-
        python -c "import os; from pathlib import Path; d=Path('.artifacts/crypto-replay/dist');
        w=list(d.glob('*.whl')); s=list(d.glob('*.tar.gz'));
        assert len(w)==len(s)==1, (w,s);
        open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8').write(f'wheel={w[0]}\nsdist={s[0]}\n')"
    - name: Verify the exact artifact pair
      run: >-
        python scripts/verify_crypto_replay_artifacts.py
        --wheel "${{ steps.replay_artifacts.outputs.wheel }}"
        --sdist "${{ steps.replay_artifacts.outputs.sdist }}"
    - name: Import the same wheel without dependencies
      run: |
        python -m venv .artifacts/crypto-replay/import-venv
        .artifacts/crypto-replay/import-venv/bin/python -m pip install --no-index --no-deps "${{ steps.replay_artifacts.outputs.wheel }}"
        .artifacts/crypto-replay/import-venv/bin/python -I -c "import importlib,pkgutil,build_finance.crypto_replay as p; [importlib.import_module(m.name) for m in pkgutil.walk_packages(p.__path__,p.__name__+'.')]"
```

Do not rebuild between verification and import, and do not broaden unrelated
release workflows.

- [ ] **Step 5: Run final branch verification**

```powershell
$base = '9c9f5c2f15ee037d450bacc3e6a8f8be704d507e'
$changed = @(git diff --name-only --diff-filter=ACMR "${base}...HEAD")
$trackedFiles = @($changed | Where-Object {
    $_ -and $_ -notmatch '(^|/)\.env($|\.)' -and (Test-Path -LiteralPath $_ -PathType Leaf)
})
$secretPatterns = @(
    'jup_[A-Za-z0-9]{20,}',
    'sk-[A-Za-z0-9_-]{20,}',
    '-----BEGIN [A-Z ]*PRIVATE KEY-----',
    '(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*["''][^"'']{12,}["'']'
)
$secretHits = @($trackedFiles | ForEach-Object {
    Select-String -LiteralPath $_ -Pattern $secretPatterns -AllMatches
})
if ($secretHits) {
    $secretHits | ForEach-Object { Write-Error "$($_.Path):$($_.LineNumber) credential-shaped content" }
    throw 'changed-file credential scan failed'
}
python -m build_finance.crypto_replay.schema_codegen --scope full --check
python -m pytest -p no:cacheprovider tests/crypto_replay -q
python -m pytest -p no:cacheprovider tests -q
python -m ruff check .
python -m ruff format --check .
python -m mypy
python -m pip check
git diff --check 9c9f5c2f15ee037d450bacc3e6a8f8be704d507e...HEAD
git status --short
```

The scan reads only changed/added tracked regular files and deliberately skips
every `.env`-named path; do not enumerate or open ignored environment files.
Step 2's archive verifier applies the equivalent high-confidence patterns and
sentinel checks to decompressed archive members. Record existing
whole-repository failures separately from replay-branch regressions. Fix only
failures introduced by this branch.

- [ ] **Step 6: Commit packaging and freeze the review candidate**

```powershell
git add docs/crypto-replay scripts/verify_crypto_replay_artifacts.py pyproject.toml .github/workflows/ci.yml tests/crypto_replay
git diff --cached --check
git commit -m "docs(crypto-replay): package offline T01-T03 evidence"
$candidate = git rev-parse HEAD
git update-ref refs/crypto-replay/review-candidate $candidate
git status --short
```

Expected: clean replay worktree. The private candidate ref persists the full
SHA across shell invocations but carries no approval meaning.

- [ ] **Step 7: Request independent review**

Resolve `$candidate = git rev-parse refs/crypto-replay/review-candidate`, then
use `superpowers:requesting-code-review` against
`9c9f5c2f15ee037d450bacc3e6a8f8be704d507e...$candidate`. Address only
correctness, determinism, security, packaging, evidence, and scope findings.
After any fix, repeat Steps 2–6 and obtain review of the new exact commit. Only
after the reviewer approves the exact full SHA, freeze it without recomputing:

```powershell
$candidate = git rev-parse refs/crypto-replay/review-candidate
$current = git rev-parse HEAD
if ($current -ne $candidate) { throw 'review candidate moved after review' }
git update-ref refs/crypto-replay/reviewed-t01-t03 $candidate
if ((git rev-parse refs/crypto-replay/reviewed-t01-t03) -ne $candidate) {
    throw 'reviewed replay ref was not frozen exactly'
}
```

- [ ] **Step 8: Merge the exact reviewed commit into the design branch**

```powershell
Set-Location C:\dev\worktrees\build-finance-live-paper-design
$designStatus = git status --porcelain
if ($designStatus) { throw 'design worktree is not clean before integration' }
if ((git branch --show-current) -ne 'design/live-data-paper-engine-20260713') {
    throw 'wrong design integration branch'
}
$designBase = git rev-parse refs/crypto-replay/design-doc-base
if ((git rev-parse HEAD) -ne $designBase) {
    throw 'design branch moved after its approved documents were frozen'
}
$reviewed = git rev-parse refs/crypto-replay/reviewed-t01-t03
$replayHead = git -C C:\dev\worktrees\build-finance-crypto-replay-t01-t03 rev-parse HEAD
if ($replayHead -ne $reviewed) { throw 'replay HEAD is not the reviewed commit' }
$replayStatus = git -C C:\dev\worktrees\build-finance-crypto-replay-t01-t03 status --porcelain
if ($replayStatus) { throw 'reviewed replay worktree is not clean' }
git merge --no-ff $reviewed -m "merge: integrate reviewed crypto replay T01-T03 prerequisite"
```

Expected: the design branch still equals its frozen approved-document commit,
the replay branch still equals the reviewer-approved ref, both worktrees are
clean, and the merge commit preserves design plus replay history. Resolve only
genuine doc/integration conflicts; do not squash away evidence lineage. If
either HEAD moved, stop and repeat the applicable review/freeze step rather
than recomputing a SHA at merge time.

- [ ] **Step 9: Verify the integrated tree, then stop**

```powershell
python -m build_finance.crypto_replay.schema_codegen --scope full --check
python -m pytest -p no:cacheprovider tests/crypto_replay -q
git log --oneline --decorate --graph --max-count=30
git status --short
```

Expected: replay gates pass from the integrated tree and the worktree is clean. Stop before T04. Do not push, publish, tag, call a provider, configure credentials, or implement the live/paper engine without the next approved plan.

---

## Completion Definition

- T01 remains durably GREEN and its sealed primary bundle is unchanged.
- T02 and T03 each have genuine RED-before-GREEN history and durable GREEN receipts bound to tested commits.
- All 27 attachment schemas, the binary formula, final bundle/digest/lock, no-follow source tree, resolving graph, local capture, pure parser, and admission logic exist and pass focused gates.
- Runtime confinement and actual archive contents are mechanically verified.
- P0 remains BLOCKED, P2 remains FAIL_ZERO_ADMITTED_FIXTURE, and no capability or profitability claim exceeds evidence.
- An independent reviewer approves the exact replay commit.
- The exact reviewed commit is merged into the design branch with history preserved.
- No T04+, provider, model, risk, paper order, broker, wallet, signer, real execution, publish, or push action occurs.

## Required Self-Review Before Execution

- Every task is T01–T03 prerequisite work or integration proof; later-engine work is absent.
- Commands name exact worktrees, files, tests, gates, and expected outcomes.
- No step depends on a secret, network call, provider endpoint, package-index install, or real dataset.
- RED and GREEN evidence ordering is explicit and cannot be satisfied by editing a receipt.
- Package and fresh-process checks inspect the artifact actually intended for integration.
- Integration is conditional on independent review and uses the exact reviewed commit.
- No unresolved planning markers or vague implementation steps remain.
