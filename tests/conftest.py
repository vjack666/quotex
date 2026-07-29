"""Pytest fixture: asegura que scripts/ sea importable como modulo.

El agente offline vive en scripts/agent_review.py y no es un paquete;
lo agregamos al sys.path para que `import agent_review` funcione en tests.
"""

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPTS = os.path.join(_ROOT, "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

_SRC = os.path.join(_ROOT, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
