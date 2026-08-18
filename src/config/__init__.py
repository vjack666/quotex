"""Canonical configuration namespace.

The legacy ``config.py`` remains the compatibility source of truth while
settings are migrated by responsibility. New modules can depend on this
namespace without requiring a second configuration implementation.
"""
from config import *  # noqa: F401,F403
