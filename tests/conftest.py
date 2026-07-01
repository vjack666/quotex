"""Fixtures compartidas para tests del bot."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Mock pyquotex antes de importar módulos del bot (tests sin broker real).
if "pyquotex" not in sys.modules:
    _pyquotex = MagicMock()
    _stable = MagicMock()
    _stable.Quotex = MagicMock
    _pyquotex.stable_api = _stable
    sys.modules["pyquotex"] = _pyquotex
    sys.modules["pyquotex.stable_api"] = _stable