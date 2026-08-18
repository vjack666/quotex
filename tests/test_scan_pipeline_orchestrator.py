"""Boundary tests for the canonical scanner orchestrator."""
import asyncio
import sys
import types


def test_scanner_orchestrator_import_is_lazy(monkeypatch):
    calls = []
    fake_scanner = types.ModuleType("scan_pipeline.scanner")

    class FakeScanner:
        def __init__(self, bot, executor):
            calls.append((bot, executor))

        async def scan(self, *args, **kwargs):
            return (args, kwargs)

    fake_scanner.AssetScanner = FakeScanner
    monkeypatch.setitem(sys.modules, "scan_pipeline.scanner", fake_scanner)

    from scan_pipeline.orchestrator import ScannerOrchestrator

    orchestrator = ScannerOrchestrator("bot", "executor")
    assert calls == [("bot", "executor")]
    assert asyncio.run(orchestrator.scan("asset", limit=1)) == (("asset",), {"limit": 1})
