"""Verify the dedicated G2 paper-core artifact pair and import closure."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from email.parser import Parser
from pathlib import Path, PurePosixPath
from typing import Any

from verify_crypto_replay_artifacts import (
    ArchiveMembers,
    VerificationError,
    _read_sdist_members,
    _read_wheel_members,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "build_finance" / "live_paper" / "paper_core_manifest.json"
EXPECTED_REQUIREMENTS = frozenset({"numpy>=1.24", "pandas>=2.0", "scipy>=1.10"})
FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "alpaca",
    "binance",
    "ccxt",
    "coinbase",
    "ftplib",
    "http",
    "ibapi",
    "kraken",
    "requests",
    "socket",
    "ssl",
    "subprocess",
    "urllib",
    "wallet",
    "web3",
    "websocket",
    "websockets",
)
FORBIDDEN_BUILD_FINANCE_PREFIXES = (
    "build_finance.autotrader",
    "build_finance.broker",
    "build_finance.market_data",
)
FORBIDDEN_OS_CALLS = frozenset(
    {
        "environ",
        "execl",
        "execle",
        "execlp",
        "execlpe",
        "execv",
        "execve",
        "execvp",
        "execvpe",
        "getenv",
        "popen",
        "spawnl",
        "spawnle",
        "spawnlp",
        "spawnlpe",
        "spawnv",
        "spawnve",
        "spawnvp",
        "spawnvpe",
        "startfile",
        "system",
    }
)


@dataclass(frozen=True, slots=True)
class VerificationReport:
    """Machine-readable paper-core artifact verification result."""

    allowed_source_count: int
    import_closure: str
    manifest_sha256: str
    sdist: str
    sdist_member_count: int
    sdist_sha256: str
    wheel: str
    wheel_member_count: int
    wheel_sha256: str


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _load_expected_manifest() -> tuple[bytes, dict[str, Any], dict[str, str]]:
    payload = MANIFEST_PATH.read_bytes()
    if not payload.endswith(b"\n"):
        raise VerificationError("source paper-core manifest is not LF terminated")
    manifest = json.loads(payload)
    if not isinstance(manifest, dict) or _canonical_json_bytes(manifest) + b"\n" != payload:
        raise VerificationError("source paper-core manifest is not canonical JSON")
    unsigned = dict(manifest)
    claimed = unsigned.pop("manifest_sha256", None)
    if claimed != _sha256(_canonical_json_bytes(unsigned)):
        raise VerificationError("source paper-core manifest digest is invalid")
    rows = manifest.get("files")
    if not isinstance(rows, list):
        raise VerificationError("source paper-core manifest files is not a list")
    expected: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str) or not isinstance(row.get("sha256"), str):
            raise VerificationError("source paper-core manifest contains an invalid file row")
        path = row["path"]
        if path in expected:
            raise VerificationError(f"source paper-core manifest contains duplicate path: {path}")
        expected[path] = row["sha256"]
    expected["build_finance/live_paper/paper_core_manifest.json"] = _sha256(payload)
    return payload, manifest, expected


def _package_members(archive: ArchiveMembers) -> dict[str, bytes]:
    return {name: payload for name, payload in archive.members.items() if name.startswith("build_finance/")}


def _verify_exact_sources(archive: ArchiveMembers, expected: dict[str, str], manifest_payload: bytes) -> None:
    actual = _package_members(archive)
    if actual.keys() != expected.keys():
        raise VerificationError(
            f"{archive.label} package allowlist mismatch: "
            f"missing={sorted(expected.keys() - actual.keys())!r} extra={sorted(actual.keys() - expected.keys())!r}"
        )
    manifest_name = "build_finance/live_paper/paper_core_manifest.json"
    if actual[manifest_name] != manifest_payload:
        raise VerificationError(f"{archive.label} packaged manifest differs from reviewed source manifest")
    for name, expected_digest in expected.items():
        if _sha256(actual[name]) != expected_digest:
            raise VerificationError(f"{archive.label} source digest mismatch: {name}")


def _module_name(path: str) -> str:
    pure = PurePosixPath(path)
    parts = pure.with_suffix("").parts
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _is_forbidden_import(name: str) -> bool:
    prefixes = (*FORBIDDEN_IMPORT_PREFIXES, *FORBIDDEN_BUILD_FINANCE_PREFIXES)
    return any(name == prefix or name.startswith(f"{prefix}.") for prefix in prefixes)


def _verify_ast_closure(wheel: ArchiveMembers) -> None:
    sources = _package_members(wheel)
    python_sources = {name: payload for name, payload in sources.items() if name.endswith(".py")}
    modules = {_module_name(name) for name in python_sources}
    for name, payload in sorted(python_sources.items()):
        tree = ast.parse(payload, filename=name)
        for node in ast.walk(tree):
            imports: tuple[str, ...] = ()
            if isinstance(node, ast.Import):
                imports = tuple(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imports = (node.module,)
            for imported in imports:
                if _is_forbidden_import(imported):
                    raise VerificationError(f"wheel imports forbidden capability: {name}:{imported}")
                if imported.startswith("build_finance") and imported not in modules:
                    raise VerificationError(f"wheel internal import is outside allowlist: {name}:{imported}")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "os"
                    and node.func.attr in FORBIDDEN_OS_CALLS
                ):
                    raise VerificationError(f"wheel calls forbidden OS capability: {name}:os.{node.func.attr}")
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                if node.value.id == "os" and node.attr == "environ":
                    raise VerificationError(f"wheel reads process environment: {name}:os.environ")


def _verify_metadata(wheel: ArchiveMembers) -> None:
    candidates = [name for name in wheel.members if name.endswith(".dist-info/METADATA")]
    if len(candidates) != 1:
        raise VerificationError(f"wheel must contain exactly one METADATA member, found {candidates!r}")
    metadata = Parser().parsestr(wheel.members[candidates[0]].decode("utf-8", errors="strict"))
    if metadata.get("Name") != "build-finance-paper-core":
        raise VerificationError(f"unexpected paper-core distribution name: {metadata.get('Name')!r}")
    requires = metadata.get_all("Requires-Dist") or []
    unconditional = frozenset(
        re.sub(r"\s+", "", requirement).lower() for requirement in requires if ";" not in requirement
    )
    if unconditional != EXPECTED_REQUIREMENTS:
        raise VerificationError(f"unexpected paper-core runtime requirements: {sorted(unconditional)!r}")
    for requirement in requires:
        normalized = requirement.lower()
        if any(token in normalized for token in FORBIDDEN_IMPORT_PREFIXES):
            raise VerificationError(f"forbidden paper-core requirement: {requirement}")


def verify_artifacts(*, wheel: Path, sdist: Path) -> VerificationReport:
    """Assert exact package closure for one local paper-core artifact pair."""

    manifest_payload, manifest, expected = _load_expected_manifest()
    wheel_members = _read_wheel_members(wheel)
    sdist_members = _read_sdist_members(sdist)
    _verify_exact_sources(wheel_members, expected, manifest_payload)
    _verify_exact_sources(sdist_members, expected, manifest_payload)
    _verify_metadata(wheel_members)
    _verify_ast_closure(wheel_members)
    return VerificationReport(
        allowed_source_count=len(expected),
        import_closure="PASS",
        manifest_sha256=str(manifest["manifest_sha256"]),
        sdist=str(sdist),
        sdist_member_count=len(sdist_members.members),
        sdist_sha256=_sha256(sdist.read_bytes()),
        wheel=str(wheel),
        wheel_member_count=len(wheel_members.members),
        wheel_sha256=_sha256(wheel.read_bytes()),
    )


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", required=True, type=Path)
    parser.add_argument("--sdist", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        report = verify_artifacts(wheel=args.wheel, sdist=args.sdist)
    except (OSError, json.JSONDecodeError, SyntaxError, VerificationError) as error:
        print(f"live-paper artifact verification failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(asdict(report), separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
