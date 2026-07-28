"""Candados del Discovery Engine (T9): anti-bot y anti-reloj de pared (R11, R9b).

Reusa el estándar del Observador: el paquete src/discovery/ NO debe importar nada
del bot (scanner/strat_fractal) y NO debe usar time.time()/datetime.now().
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys

DISCOVERY_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOT_MODULES = ("scanner", "strat_fractal", "consolidation_bot", "caffeine", "connection", "executor")
WALLCLOCK_CALLS = ("time.time", "datetime.now", "datetime.utcnow", "time.localtime", "time.gmtime")


def _py_files(root: str):
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if f.endswith(".py"):
                yield os.path.join(dirpath, f)


def test_discovery_no_bot_imports():
    """Grep anti-bot: src/discovery/ no importa módulos del bot (R11, R9b)."""
    # No dependemos de grep externo; parseamos imports con ast.
    offenses = []
    for path in _py_files(os.path.join(DISCOVERY_ROOT, "discovery")):
        tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, ast.Import):
                targets = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                targets = [node.module or ""]
            for t in targets:
                if any(b in t for b in BOT_MODULES) or t.startswith("bot."):
                    offenses.append((os.path.relpath(path), t))
    assert not offenses, f"Discovery importa módulos del bot: {offenses}"


def test_discovery_no_wallclock():
    """No debe haber llamadas a reloj de pared en src/discovery/ (R11)."""
    offenses = []
    for path in _py_files(os.path.join(DISCOVERY_ROOT, "discovery")):
        src = open(path, encoding="utf-8").read()
        tree = ast.parse(src, filename=path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                full = f"{getattr(node.func.value, 'id', '')}.{node.func.attr}"
                if any(w in full for w in WALLCLOCK_CALLS):
                    offenses.append((os.path.relpath(path), full))
    assert not offenses, f"Discovery usa reloj de pared: {offenses}"
