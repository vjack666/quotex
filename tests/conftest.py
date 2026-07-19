"""Fixtures compartidas para tests del bot."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Isolate tests from live hub bankroll (min_payout=90 etc.) BEFORE any config import.
os.environ.setdefault("QUOTEX_TEST_MODE", "1")

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
# Project root on path so `import hub` / `import app` work in lifecycle tests.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Mock pyquotex antes de importar módulos del bot (tests sin broker real).
if "pyquotex" not in sys.modules:
    _pyquotex = MagicMock()
    _stable = MagicMock()
    _stable.Quotex = MagicMock
    _pyquotex.stable_api = _stable
    sys.modules["pyquotex"] = _pyquotex
    sys.modules["pyquotex.stable_api"] = _stable