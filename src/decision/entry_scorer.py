"""Public decision-domain facade for the entry scorer.

The implementation remains in ``src/entry_scorer.py`` during the migration.
Keeping this facade lets new code depend on the domain-oriented package while
legacy consumers continue importing the original module until the dependency
migration is complete.
"""

from entry_scorer import *  # noqa: F401,F403
