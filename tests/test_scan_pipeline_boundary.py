"""Boundary tests for the scanner package refactor."""
from scan_pipeline import AssetScanner, ScanCycleContext, ScanResult
from scan_pipeline.prefetch import ScanCycleData


def test_scanner_has_canonical_pipeline_owner():
    assert AssetScanner.__module__ == "scan_pipeline.scanner"


def test_scan_result_is_pipeline_contract():
    result = ScanResult()
    assert result.candidates == []
    assert result.stats_delta == {}
    assert result.diagnostics == {}


def test_scan_cycle_context_is_dependency_light():
    context = ScanCycleContext()
    assert context.symbols == []
    assert context.candles == {}
    assert context.secondary == {}
    assert context.diagnostics == {}
    assert context.runtime is None


def test_prefetch_api_is_available_from_pipeline():
    assert ScanCycleData is not None
