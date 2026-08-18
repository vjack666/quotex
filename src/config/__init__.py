"""Canonical configuration namespace.

The legacy ``config.py`` remains the compatibility source of truth while
settings are migrated by responsibility. New modules can depend on this
namespace without requiring a second configuration implementation.

Use the responsibility modules for new imports:
``config.trading``, ``config.risk``, ``config.execution`` and
``config.strategy``. They re-export existing values and do not redefine them.
"""
from config import *  # noqa: F401,F403
