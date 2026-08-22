"""Offline live-paper G2 contract authority.

This package is intentionally separate from ``build_finance.crypto_replay``.
The package exposes only deterministic, in-memory evidence contracts and the
rooted normalization boundary. Later tasks own the paper kernel itself.
"""

from __future__ import annotations

from build_finance.live_paper.features import derive_feature_snapshot
from build_finance.live_paper.grouping import EventGroup, group_committed_events
from build_finance.live_paper.normalization import NormalizedCandidate, normalize_admitted_candidate
from build_finance.live_paper.profiles import PaperKernelProfiles
from build_finance.live_paper.resolver import EvidenceResolver
from build_finance.live_paper.run_input_builder import build_verified_run_inputs

__all__ = [
    "EvidenceResolver",
    "EventGroup",
    "NormalizedCandidate",
    "PaperKernelProfiles",
    "build_verified_run_inputs",
    "contracts",
    "content_ids",
    "derive_feature_snapshot",
    "group_committed_events",
    "normalize_admitted_candidate",
    "registry",
]
