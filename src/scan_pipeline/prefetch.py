"""Canonical scanner prefetch API.

The implementation remains in ``data.scan_prefetch`` during migration. This
module provides the stable pipeline boundary without changing behavior.
"""
from data.scan_prefetch import (
    ScanCycleData,
    decrement_failed_assets,
    filter_scan_assets,
    prefetch_historical_m15_initial,
    prefetch_primary_candles,
    prefetch_strat_a_secondary,
    symbols_needing_strat_a_prefetch,
)

__all__ = [
    "ScanCycleData",
    "decrement_failed_assets",
    "filter_scan_assets",
    "prefetch_historical_m15_initial",
    "prefetch_primary_candles",
    "prefetch_strat_a_secondary",
    "symbols_needing_strat_a_prefetch",
]
