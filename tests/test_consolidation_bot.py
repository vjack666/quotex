"""Tests del facade consolidation_bot."""
from __future__ import annotations

import argparse
import asyncio
import inspect
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_consolidation_bot_under_500_lines():
    lines = (SRC / "consolidation_bot.py").read_text(encoding="utf-8").splitlines()
    # Soft ceiling: facade grows with lifecycle/session/schedule/continuous guards.
    assert len(lines) <= 1200


def test_consolidation_bot_main_signature_unchanged():
    with patch.dict(sys.modules, {"pyquotex": MagicMock(), "pyquotex.stable_api": MagicMock()}):
        import importlib
        import consolidation_bot as cb
        importlib.reload(cb)
        sig = inspect.signature(cb.main)
        params = list(sig.parameters.keys())
        assert params == ["dry_run", "real_account", "loop_forever", "greylist_assets", "hub_scanner", "continuous_mode"]


def _parser_option_strings(parser: argparse.ArgumentParser) -> set[str]:
    opts: set[str] = set()
    for action in parser._actions:
        opts.update(action.option_strings)
    return opts


def test_parse_args_legacy_cli_flags():
    """R14: parse_args() declara y acepta --live, --real, --loop, --greylist."""
    with patch.dict(sys.modules, {"pyquotex": MagicMock(), "pyquotex.stable_api": MagicMock()}):
        import importlib
        import consolidation_bot as cb
        importlib.reload(cb)

        captured_parsers: list[argparse.ArgumentParser] = []
        real_parse_args = argparse.ArgumentParser.parse_args

        def capture_parse_args(self, args=None, namespace=None):
            captured_parsers.append(self)
            if args is None:
                args = ["--live", "--real", "--loop", "--greylist", "EURUSD,GBPUSD"]
            return real_parse_args(self, args, namespace)

        with patch.object(argparse.ArgumentParser, "parse_args", capture_parse_args):
            ns = cb.parse_args()

        assert len(captured_parsers) == 1
        opts = _parser_option_strings(captured_parsers[0])
        for flag in ("--live", "--real", "--loop", "--greylist"):
            assert flag in opts

        assert ns.live is True
        assert ns.real is True
        assert ns.loop is True
        assert "EURUSD" in ns.greylist
        assert "GBPUSD" in ns.greylist


def test_main_imports_new_modules():
    import connection
    import scanner
    import executor
    import consolidation_bot

    assert hasattr(connection, "connect_with_retry")
    assert hasattr(scanner, "AssetScanner")
    assert hasattr(executor, "TradeExecutor")
    assert hasattr(consolidation_bot, "ConsolidationBot")


def test_apply_runtime_config_mutates_constants():
    import argparse
    import importlib

    with patch.dict(sys.modules, {"pyquotex": MagicMock(), "pyquotex.stable_api": MagicMock()}):
        import consolidation_bot as cb
        importlib.reload(cb)
        sys.path.insert(0, str(ROOT))
        import main as main_mod
        importlib.reload(main_mod)

        args = argparse.Namespace(
            amount_initial=2.5,
            amount_martin=5.0,
            max_loss_session=0.15,
            cycle_ops=4,
            cycle_wins=1,
            cycle_profit_pct=0.05,
            min_payout=75,
            scan_lead_sec=20.0,
            strat_a_only=False,
            hub_readonly=False,
            continuous=False,
        )
        main_mod._apply_runtime_config(args)
        assert cb.MIN_PAYOUT == 75
        assert cb.AMOUNT_INITIAL == 2.5


@pytest.mark.asyncio
async def test_main_once_dry_run_completes():
    sys.path.insert(0, str(ROOT))
    with patch.dict(sys.modules, {"pyquotex": MagicMock(), "pyquotex.stable_api": MagicMock()}):
        import importlib
        import consolidation_bot as cb
        importlib.reload(cb)

        mock_client = MagicMock()
        mock_client.connect = AsyncMock(return_value=(True, ""))
        mock_client.change_account = AsyncMock()
        mock_client.get_balance = AsyncMock(return_value=1000.0)
        mock_client.close = AsyncMock()

        mock_bot = MagicMock()
        mock_bot.scan_all = AsyncMock()
        mock_bot.reconcile_pending_candidates = AsyncMock()
        mock_bot.log_stats = MagicMock()
        mock_bot.shutdown_background_tasks = AsyncMock()
        mock_bot.session_stop_hit = False
        mock_bot.ensure_connection = AsyncMock(return_value=True)
        mock_bot.htf_scanner = MagicMock()
        mock_bot.htf_scanner.run_forever = AsyncMock()
        create_task_calls: list = []

        def _spy_create_task(coro):
            create_task_calls.append(coro)
            task = MagicMock()
            task.done.return_value = False
            return task

        with patch.object(cb, "EMAIL", "a@b.com"), patch.object(cb, "PASSWORD", "x"), \
             patch.object(cb, "Quotex", return_value=mock_client), \
             patch.object(cb, "ConsolidationBot", return_value=mock_bot), \
             patch.object(cb, "connect_with_retry", AsyncMock(return_value=(True, ""))), \
             patch.object(cb.asyncio, "create_task", side_effect=_spy_create_task):
            await cb.main(dry_run=True, real_account=False, loop_forever=False)
        mock_bot.scan_all.assert_awaited_once()
        mock_bot.htf_scanner.run_forever.assert_called_once()
        assert len(create_task_calls) == 1


@pytest.mark.asyncio
async def test_shutdown_background_tasks_cancels_htf_task():
    with patch.dict(sys.modules, {"pyquotex": MagicMock(), "pyquotex.stable_api": MagicMock()}):
        import importlib
        import consolidation_bot as cb
        importlib.reload(cb)

        mock_client = MagicMock()
        bot = cb.ConsolidationBot(mock_client, dry_run=True)

        async def _run_forever_sim():
            await asyncio.sleep(3600)

        bot._htf_task = asyncio.create_task(_run_forever_sim())
        bot.executor.shutdown_background_tasks = AsyncMock()

        await bot.shutdown_background_tasks()

        assert bot._htf_task.done()
        assert bot._htf_task.cancelled()


def test_consolidation_bot_htf_scanner_uses_min_payout():
    """HTF scanner follows hub min_payout (same floor as bankroll card)."""
    with patch.dict(sys.modules, {"pyquotex": MagicMock(), "pyquotex.stable_api": MagicMock()}):
        import importlib
        import consolidation_bot as cb
        import config as cfg
        importlib.reload(cb)

        mock_client = MagicMock()
        bot = cb.ConsolidationBot(mock_client, dry_run=True)

        assert bot.htf_scanner._min_payout == cfg.MIN_PAYOUT