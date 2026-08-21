"""T03 crypto-replay confinement tests for offline-only imports and calls."""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

PACKAGE_ROOT = Path("build_finance") / "crypto_replay"
PACKAGE_PREFIX = "build_finance.crypto_replay"
FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "alpaca",
    "alpaca_trade_api",
    "anchorpy",
    "base58",
    "binance",
    "ccxt",
    "cffi",
    "coinbase",
    "ctypes",
    "ftplib",
    "http",
    "ibapi",
    "jupiter",
    "kraken",
    "native",
    "okx",
    "requests",
    "solders",
    "solana",
    "socket",
    "ssl",
    "urllib",
    "wallet",
    "web3",
    "websocket",
    "websockets",
)
FORBIDDEN_BUILD_FINANCE_IMPORTS = (
    "build_finance.autotrader",
    "build_finance.broker",
    "build_finance.market_data",
)
FORBIDDEN_CALLS = (
    ("builtins", "__import__"),
    ("builtins", "compile"),
    ("builtins", "eval"),
    ("builtins", "exec"),
    ("importlib", "__import__"),
    ("importlib", "import_module"),
    ("os", "execl"),
    ("os", "execle"),
    ("os", "execlp"),
    ("os", "execlpe"),
    ("os", "execv"),
    ("os", "execve"),
    ("os", "execvp"),
    ("os", "execvpe"),
    ("os", "popen"),
    ("os", "spawnl"),
    ("os", "spawnle"),
    ("os", "spawnlp"),
    ("os", "spawnlpe"),
    ("os", "spawnv"),
    ("os", "spawnve"),
    ("os", "spawnvp"),
    ("os", "spawnvpe"),
    ("os", "startfile"),
    ("os", "system"),
    ("runpy", "run_module"),
    ("runpy", "run_path"),
    ("subprocess", "Popen"),
    ("subprocess", "call"),
    ("subprocess", "check_call"),
    ("subprocess", "check_output"),
    ("subprocess", "run"),
)


def _runtime_module_paths() -> dict[str, Path]:
    return {
        _module_name(path): path
        for path in sorted(PACKAGE_ROOT.glob("*.py"), key=lambda item: item.as_posix().encode("utf-8"))
    }


def _module_name(path: Path) -> str:
    return f"{PACKAGE_PREFIX}.{path.stem}" if path.name != "__init__.py" else PACKAGE_PREFIX


def _imported_modules(tree: ast.AST) -> tuple[str, ...]:
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return tuple(modules)


def _import_aliases(tree: ast.AST) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                aliases[alias.asname or alias.name.split(".", 1)[0]] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    return aliases


def _call_path(node: ast.Call, aliases: dict[str, str]) -> tuple[str | None, str | None]:
    if isinstance(node.func, ast.Name):
        resolved = aliases.get(node.func.id)
        if resolved is None:
            return "builtins", node.func.id
        module, _, function = resolved.rpartition(".")
        return module or resolved, function or None
    parts: list[str] = []
    current: ast.AST = node.func
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        root = aliases.get(current.id, current.id)
        path = ".".join((root, *reversed(parts)))
        module, _, function = path.rpartition(".")
        return module or path, function or None
    return None, None


def _reachable_runtime_modules() -> tuple[tuple[str, Path], ...]:
    paths = _runtime_module_paths()
    pending = [PACKAGE_PREFIX]
    seen: set[str] = set()
    while pending:
        module = pending.pop()
        if module in seen or module not in paths:
            continue
        seen.add(module)
        tree = ast.parse(paths[module].read_bytes(), filename=str(paths[module]))
        for imported in _imported_modules(tree):
            if imported == PACKAGE_PREFIX or imported.startswith(f"{PACKAGE_PREFIX}."):
                pending.append(imported)
    return tuple((module, paths[module]) for module in sorted(seen, key=lambda value: value.encode("utf-8")))


def _is_forbidden_module(module: str) -> bool:
    return module in FORBIDDEN_BUILD_FINANCE_IMPORTS or any(
        module == prefix or module.startswith(f"{prefix}.") for prefix in FORBIDDEN_IMPORT_PREFIXES
    )


def test_crypto_replay_runtime_ast_denies_direct_and_transitive_forbidden_capabilities() -> None:
    failures: list[str] = []
    for module, path in _reachable_runtime_modules():
        tree = ast.parse(path.read_bytes(), filename=str(path))
        aliases = _import_aliases(tree)
        for imported in _imported_modules(tree):
            if _is_forbidden_module(imported):
                failures.append(f"{module}:{imported}")
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _call_path(node, aliases) in FORBIDDEN_CALLS:
                call_module, call_name = _call_path(node, aliases)
                failures.append(f"{module}:{call_module}.{call_name}")
    assert failures == []


def test_clean_process_imports_crypto_replay_without_transitive_live_or_external_dependencies() -> None:
    script = f"""
import importlib
import json
import pkgutil
import sys

baseline_modules = set(sys.modules)
import build_finance.crypto_replay as package

modules = [package.__name__]
modules.extend(info.name for info in pkgutil.walk_packages(package.__path__, package.__name__ + "."))
for name in sorted(modules):
    importlib.import_module(name)
forbidden_prefixes = {FORBIDDEN_IMPORT_PREFIXES!r}
forbidden_exact = {FORBIDDEN_BUILD_FINANCE_IMPORTS!r}
forbidden = sorted(
    name for name in sys.modules
    if name not in baseline_modules
    and (name in forbidden_exact or any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden_prefixes))
)
print(json.dumps({{"forbidden": forbidden, "modules": sorted(modules)}}, sort_keys=True))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        text=True,
        capture_output=True,
    )
    result = json.loads(completed.stdout)
    assert result["forbidden"] == []
    assert "build_finance.crypto_replay.admission" in result["modules"]
    assert "build_finance.crypto_replay.jupiter_fixture" in result["modules"]
    assert "build_finance.crypto_replay.local_fixture" in result["modules"]
