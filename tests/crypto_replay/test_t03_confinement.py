"""T03 crypto-replay confinement tests for offline-only imports and calls."""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path


PACKAGE_ROOT = Path("build_finance") / "crypto_replay"
FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "cffi",
    "ctypes",
    "ftplib",
    "http",
    "requests",
    "socket",
    "ssl",
    "urllib",
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
    ("builtins", "eval"),
    ("builtins", "exec"),
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
    ("subprocess", "Popen"),
    ("subprocess", "call"),
    ("subprocess", "check_call"),
    ("subprocess", "check_output"),
    ("subprocess", "run"),
)


def _runtime_modules() -> tuple[Path, ...]:
    return tuple(sorted(PACKAGE_ROOT.glob("*.py"), key=lambda path: path.as_posix().encode("utf-8")))


def _imported_modules(tree: ast.AST) -> tuple[str, ...]:
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return tuple(modules)


def _call_name(node: ast.Call) -> tuple[str | None, str | None]:
    if isinstance(node.func, ast.Name):
        return "builtins", node.func.id
    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
        return node.func.value.id, node.func.attr
    return None, None


def test_crypto_replay_runtime_ast_denies_network_process_native_ffi_and_dynamic_execution() -> None:
    failures: list[str] = []
    for path in _runtime_modules():
        tree = ast.parse(path.read_bytes(), filename=str(path))
        for module in _imported_modules(tree):
            if module.startswith(FORBIDDEN_IMPORT_PREFIXES) or module in FORBIDDEN_BUILD_FINANCE_IMPORTS:
                failures.append(f"{path}:{module}")
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _call_name(node) in FORBIDDEN_CALLS:
                failures.append(f"{path}:{_call_name(node)[0]}.{_call_name(node)[1]}")
    assert failures == []


def test_clean_process_imports_crypto_replay_without_live_trading_dependencies() -> None:
    script = """
import importlib
import json
import pkgutil
import sys

import build_finance.crypto_replay as package

modules = [package.__name__]
modules.extend(info.name for info in pkgutil.walk_packages(package.__path__, package.__name__ + "."))
for name in sorted(modules):
    importlib.import_module(name)
forbidden = sorted(
    name for name in sys.modules
    if name in {"build_finance.autotrader", "build_finance.broker", "build_finance.market_data"}
)
print(json.dumps({"forbidden": forbidden, "modules": sorted(modules)}, sort_keys=True))
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
