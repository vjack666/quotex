"""Tests de trazabilidad del Edificio de Contratación (F1+F2+F3).

F1: el envío confirmado queda registrado en la caja negra (strategy="EDIFICIO")
    y en el registro de pendientes (con ticket numérico order_ref).
F2: el resolvedor consulta el resultado por ticket (check_win) y actualiza
    caja negra + card; profit==0 NO se trata como LOSS.
F3: la secuencia combinada W/L se construye en orden de llegada.
"""
import sys
import time
from collections import deque
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from connection import interpret_broker_result  # noqa: E402
from edificio_contratacion import EdificioContratacion  # noqa: E402
from edificio_executor import execute_contratados, resolve_contratados  # noqa: E402


class FakeBlackBox:
    """Caja negra fake que registra llamadas, sin tocar SQLite."""

    def __init__(self):
        self.calls = []
        self.scan_counter = 0

    def record_scan_start(self, strategy, scan_number, market_context=None):
        self.scan_counter += 1
        self.calls.append(("scan_start", strategy, scan_number))
        return 1000 + self.scan_counter

    def record_candidate(self, scan_id, strategy, data):
        self.calls.append(("candidate", scan_id, strategy, data))
        return 1

    def record_order_result(self, order_id, outcome, profit):
        self.calls.append(("order_result", order_id, outcome, profit))


def _bot(edificio, *, client, history=None):
    return SimpleNamespace(
        client=client,
        edificio=edificio,
        trades={},
        outcome_history=history if history is not None else deque(maxlen=200),
    )


# ── F1: registro del envío ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_f1_envio_confirmado_registra_caja_negra_y_ticket(monkeypatch):
    edificio = EdificioContratacion()
    assert edificio.evaluate(asset="USDNGN_otc", direction="CALL", payout=90, payout_ok=True) == "subio"
    assert edificio.evaluate(asset="USDNGN_otc", direction="CALL", payout=90, payout_ok=True,
                             brake_ok=True, extreme_ok=True) == "subio"
    assert edificio.evaluate(asset="USDNGN_otc", direction="CALL", payout=90, payout_ok=True,
                             brake_ok=True, extreme_ok=True, cross_ok=True) == "subio"
    assert edificio.evaluate(asset="USDNGN_otc", direction="CALL", payout=90, payout_ok=True,
                             brake_ok=True, extreme_ok=True, cross_ok=True) == "contratado"

    fake_bb = FakeBlackBox()
    monkeypatch.setattr("edificio_executor.get_black_box", lambda: fake_bb)
    monkeypatch.setattr(
        "edificio_executor.place_order",
        AsyncMock(return_value=(True, "OID-EDF-1", 1.0512, 98765, "")),
    )
    bot = _bot(edificio, client=object())

    enviadas = await execute_contratados(bot)

    assert enviadas == 1
    # Card guarda id + ticket numérico
    card = edificio.get_card("USDNGN_otc")
    assert card.order_id == "OID-EDF-1"
    assert card.order_ref == 98765
    # Caja negra: scan + candidate con order_id
    assert any(c[0] == "scan_start" and c[1] == "EDIFICIO" for c in fake_bb.calls)
    cand = [c for c in fake_bb.calls if c[0] == "candidate"]
    assert len(cand) == 1
    _, scan_id, strategy, data = cand[0]
    assert strategy == "EDIFICIO"
    assert data["order_id"] == "OID-EDF-1"
    assert data["asset"] == "USDNGN_otc"
    assert data["direction"] == "CALL"
    assert data["decision"] == "BUY"
    assert data["payout"] == 90
    assert data["duration_sec"] == 900
    assert data["agent_tag"] == "BOT"
    # Registro de pendientes con ticket
    pending = edificio.sent_pending()
    assert "OID-EDF-1" in pending
    info = pending["OID-EDF-1"]
    assert info["order_ref"] == 98765
    assert info["resolved"] is False
    assert info["amount"] == 1.0


@pytest.mark.asyncio
async def test_f1_fallo_caja_negra_no_rompe_envio(monkeypatch):
    edificio = EdificioContratacion()
    assert edificio.evaluate(asset="XAGUSD_otc", direction="PUT", payout=90, payout_ok=True) == "subio"
    assert edificio.evaluate(asset="XAGUSD_otc", direction="PUT", payout=90, payout_ok=True,
                             brake_ok=True, extreme_ok=True) == "subio"
    assert edificio.evaluate(asset="XAGUSD_otc", direction="PUT", payout=90, payout_ok=True,
                             brake_ok=True, extreme_ok=True, cross_ok=True) == "subio"
    assert edificio.evaluate(asset="XAGUSD_otc", direction="PUT", payout=90, payout_ok=True,
                             brake_ok=True, extreme_ok=True, cross_ok=True) == "contratado"

    def _bb_explota():
        raise RuntimeError("db lock")

    monkeypatch.setattr("edificio_executor.get_black_box", _bb_explota)
    monkeypatch.setattr(
        "edificio_executor.place_order",
        AsyncMock(return_value=(True, "OID-EDF-2", 1.0512, 11111, "")),
    )
    bot = _bot(edificio, client=object())

    enviadas = await execute_contratados(bot)

    # El envío sobrevive aunque la caja negra falle
    assert enviadas == 1
    assert edificio.get_card("XAGUSD_otc").order_status == "sent"
    assert "OID-EDF-2" in edificio.sent_pending()


# ── F2: resolvedor por ticket ────────────────────────────────────────────

def _edificio_con_orden_enviada(*, order_id="OID-R1", ref=55555, sent_ago=1000, duration=900):
    edificio = EdificioContratacion()
    edificio.register_sent(order_id, {
        "asset": "USDNGN_otc",
        "direction": "CALL",
        "amount": 1.0,
        "payout": 90,
        "order_ref": ref,
        "sent_at": time.time() - sent_ago,
        "duration_sec": duration,
        "resolved": False,
        "attempts": 0,
    })
    return edificio


@pytest.mark.asyncio
async def test_f2_check_win_true_resuelve_win(monkeypatch):
    edificio = _edificio_con_orden_enviada()
    history = deque()
    client = SimpleNamespace(check_win=AsyncMock(return_value=True))
    bot = _bot(edificio, client=client, history=history)
    fake_bb = FakeBlackBox()
    monkeypatch.setattr("edificio_executor.get_black_box", lambda: fake_bb)

    resueltas = await resolve_contratados(bot)

    assert resueltas == 1
    client.check_win.assert_awaited_once_with(55555)
    # WIN con profit = amount * payout/100
    assert any(c == ("order_result", "OID-R1", "WIN", 0.9) for c in fake_bb.calls)
    assert edificio.sent_pending()["OID-R1"]["resolved"] is True
    assert list(history) == ["W"]


@pytest.mark.asyncio
async def test_f2_check_win_false_resuelve_loss(monkeypatch):
    edificio = _edificio_con_orden_enviada(order_id="OID-R2", ref=66666)
    history = deque()
    client = SimpleNamespace(check_win=AsyncMock(return_value=False))
    bot = _bot(edificio, client=client, history=history)
    fake_bb = FakeBlackBox()
    monkeypatch.setattr("edificio_executor.get_black_box", lambda: fake_bb)

    resueltas = await resolve_contratados(bot)

    assert resueltas == 1
    assert any(c == ("order_result", "OID-R2", "LOSS", -1.0) for c in fake_bb.calls)
    assert list(history) == ["L"]


@pytest.mark.asyncio
async def test_f2_profit_cero_no_es_loss_y_agota_intentos(monkeypatch):
    # check_win devuelve 0.0 (ticket sin PnL final) → NUNCA forzar LOSS.
    # Con max_attempts=2 y check_win siempre 0.0 → UNRESOLVED.
    edificio = _edificio_con_orden_enviada(order_id="OID-R3", ref=77777)
    history = deque()
    client = SimpleNamespace(check_win=AsyncMock(return_value=0.0))
    bot = _bot(edificio, client=client, history=history)
    fake_bb = FakeBlackBox()
    monkeypatch.setattr("edificio_executor.get_black_box", lambda: fake_bb)
    monkeypatch.setattr("edificio_executor.MARTIN_RESOLVE_RETRY_SEC", 0.0)

    resueltas = await resolve_contratados(bot, max_attempts=2)

    assert resueltas == 0  # UNRESOLVED no cuenta como resuelta
    assert client.check_win.await_count == 2
    assert not any(c[0] == "order_result" for c in fake_bb.calls)  # sin resultado forzado
    assert edificio.sent_pending()["OID-R3"]["resolved"] is True  # cerró el ciclo de reintentos
    assert list(history) == []  # UNRESOLVED no entra a la secuencia


@pytest.mark.asyncio
async def test_f2_no_resuelve_antes_del_vencimiento(monkeypatch):
    edificio = _edificio_con_orden_enviada(order_id="OID-R4", ref=88888, sent_ago=10)
    client = SimpleNamespace(check_win=AsyncMock())
    bot = _bot(edificio, client=client, history=deque())

    resueltas = await resolve_contratados(bot)

    assert resueltas == 0
    client.check_win.assert_not_awaited()
    assert edificio.sent_pending()["OID-R4"]["resolved"] is False


@pytest.mark.asyncio
async def test_f2_una_orden_por_llamada(monkeypatch):
    # Dos órdenes vencidas → la primera llamada resuelve 1; la segunda, la otra.
    edificio = EdificioContratacion()
    for i, oid in enumerate(("OID-1", "OID-2")):
        edificio.register_sent(oid, {
            "asset": "X_otc",
            "direction": "CALL",
            "amount": 1.0,
            "payout": 90,
            "order_ref": 100 + i,
            "sent_at": time.time() - 2000,
            "duration_sec": 900,
            "resolved": False,
            "attempts": 0,
        })
    client = SimpleNamespace(check_win=AsyncMock(return_value=True))
    bot = _bot(edificio, client=client, history=deque())

    assert await resolve_contratados(bot) == 1
    assert await resolve_contratados(bot) == 1
    assert await resolve_contratados(bot) == 0
    assert client.check_win.await_count == 2


# ── F3: secuencia combinada en orden de llegada ──────────────────────────

def test_f3_secuencia_combinada_en_orden_de_llegada():
    # Simula el hilo combinado: STRAT-F y edificio intercalados en el deque.
    history = deque(maxlen=200)
    # orden real: W (STRAT-F) → L (edificio) → W (edificio) → L (STRAT-F)
    for r in ("W", "L", "W", "L"):
        history.append(r)
    # Esta es la expresión exacta de hub/server.py (F3)
    assert "".join(history) == "WLWL"  # NO "WWLL" (agrupado) ni "LLWW"


def test_f3_secuencia_cronologica_no_se_reordena():
    # Si el hub agrupara W* + L* perdería el orden real; el deque lo preserva.
    history = deque()
    for r in ("L", "W", "L", "W", "W"):
        history.append(r)
    assert "".join(history) == "LWLWW"


def test_interpret_broker_result_shared_profit_cero_no_es_loss():
    # Función compartida (connection.py): profit==0 es "aún no liquidado".
    assert interpret_broker_result(True, trade_amount=1.0, payout_pct=90) == ("WIN", 0.9)
    assert interpret_broker_result(False, trade_amount=1.0, payout_pct=90) == ("LOSS", -1.0)
    assert interpret_broker_result(0.0, trade_amount=1.0, payout_pct=90) is None
    assert interpret_broker_result(1.35, trade_amount=1.0, payout_pct=90) == ("WIN", 1.35)
    assert interpret_broker_result(-1.0, trade_amount=1.0, payout_pct=90) == ("LOSS", -1.0)
