"""Tests del watchdog: lógica de decisión (no toca el bot real).

Verifica las funciones puras que deciden si reiniciar:
- recent_connection_lost(): detecta "Connection to remote host was lost" reciente.
- api_alive(): True si la API responde 200, False si falla.
"""
import importlib
import os
import sys
import tempfile
from unittest import mock

import pytest

# watchdog_bot vive en scripts/, no en la raíz del repo.
_SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)
import watchdog_bot as wd


def _write_log(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def test_recent_connection_lost_true(monkeypatch, tmp_path):
    log = tmp_path / "bot.log"
    # Línea de caída con timestamp de hoy (mismo día => reciente).
    from datetime import datetime
    ts = datetime.now().strftime("%H:%M:%S")
    _write_log(str(log), f"{ts} [ERROR] Connection to remote host was lost.\n")
    monkeypatch.setattr(wd, "LOG_PATH", str(log))
    assert wd.recent_connection_lost() is True


def test_recent_connection_lost_false_without_marker(monkeypatch, tmp_path):
    log = tmp_path / "bot.log"
    _write_log(str(log), "14:25:00 [INFO] SCAN #1 | 15 activos\n")
    monkeypatch.setattr(wd, "LOG_PATH", str(log))
    assert wd.recent_connection_lost() is False


def test_api_alive_true(monkeypatch):
    ctx = mock.Mock()
    ctx.status = 200
    monkeypatch.setattr(wd.urllib.request, "urlopen", lambda *a, **k: ctx)
    assert wd.api_alive() is True


def test_api_alive_false_on_error(monkeypatch):
    def _boom(*a, **k):
        raise OSError("no route")
    monkeypatch.setattr(wd.urllib.request, "urlopen", _boom)
    assert wd.api_alive() is False


def test_main_does_not_restart_when_healthy(monkeypatch, tmp_path, capsys):
    log = tmp_path / "bot.log"
    _write_log(str(log), "14:25:00 [INFO] SCAN #1 | 15 activos\n")
    monkeypatch.setattr(wd, "LOG_PATH", str(log))
    monkeypatch.setattr(wd, "api_alive", lambda: True)
    monkeypatch.setattr(wd, "proc_alive", lambda: True)
    monkeypatch.setattr(wd, "recent_connection_lost", lambda: False)
    restart_called = {"n": 0}

    def _fake_restart(reason):
        restart_called["n"] += 1

    monkeypatch.setattr(wd, "restart", _fake_restart)
    wd.main()
    assert restart_called["n"] == 0
    assert "bot sano" in capsys.readouterr().out
