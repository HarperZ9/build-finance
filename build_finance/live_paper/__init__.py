"""Offline live-paper G2 contract authority.

This package is intentionally separate from ``build_finance.crypto_replay``.
Task 2 owns only the evidence contracts and local content-ID registry; kernel,
normalization, feature, algorithm, fusion, risk, fill, and ledger behavior are
implemented by later tasks.
"""

from __future__ import annotations

__all__ = ["contracts", "content_ids", "registry"]
