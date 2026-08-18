"""Runtime configuration access facade.

Keep dynamic/hot-reloaded values behind a named boundary while the legacy
``config.py`` remains the compatibility source of truth.
"""
from config import *  # noqa: F401,F403
