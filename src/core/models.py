"""Compatibility entry point for shared domain models.

Canonical implementation remains in ``src/models.py`` until its dependency
on operational configuration is separated. New code may import through this
namespace during the migration.
"""
from models import *  # noqa: F401,F403
