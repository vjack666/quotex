"""Compatibility facade for the canonical scanner pipeline.

The implementation now lives in ``scan_pipeline.scanner``. Keep this module
as a stable import path while downstream consumers are migrated.
"""
from scan_pipeline.scanner import *  # noqa: F401,F403
