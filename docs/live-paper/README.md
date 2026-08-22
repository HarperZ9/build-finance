# Build Finance G2 paper core

This gate packages the deterministic Build Finance live-paper kernel as a dedicated
offline artifact named `build-finance-paper-core`. The builder copies only the
per-file allowlist sealed in `build_finance/live_paper/paper_core_manifest.json`
into a clean staging tree. The verifier rejects extra package members, missing or
changed sources, unresolved internal imports, network/process capabilities, and
unexpected runtime dependencies.

Build and inspect locally:

```powershell
python scripts/build_paper_core_artifacts.py --out-dir .artifacts/paper-core/dist
python scripts/verify_crypto_replay_artifacts.py --wheel <wheel> --sdist <sdist>
python scripts/verify_live_paper_artifacts.py --wheel <wheel> --sdist <sdist>
```

The artifact is synthetic/offline paper evidence only. It has no external data,
credential, account, transaction signing, live order, publication, or profitability
claim. Live sensors, process isolation, models, and real-capital execution remain
outside G2 and require separately authorized milestones.
