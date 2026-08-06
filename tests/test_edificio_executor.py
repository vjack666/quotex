"""Tests del ejecutor de contratados (src/edificio_executor.py).

Verifica que un activo CONTRATADO en el edificio termine en una orden real
al broker (socket único del bot), con reintentos y sin perder eventos.
"""
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from edificio_contratacion import CONTRATADO, PISO_2, ContratadoEvent, EdificioContratacion, BuildingCard  # noqa: E402
from edificio_executor import execute_contratados, is_sticky_cross, _infer_loss_reason, _append_order_audit  # noqa: E402


def _edificio_con_contratado(asset: str = "NZCADC_otc", direction: str = "PUT") -> EdificioContratacion:
    """Edificio con un activo ya en CONTRATADO y su evento en cola."""
    import time as _time
    edificio = EdificioContratacion()
    assert edificio.evaluate(asset=asset, direction=direction, payout=90, payout_ok=True) == "subio"
    assert edificio.evaluate(
        asset=asset, direction=direction, payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True,
    ) == "stay"
    card = edificio.get_card(asset)
    assert card is not None
    # Confirmación del freno por vela cerrada (deuda #1): campos explicitados.
    card.brake_at = 1.0
    card.brake_confirmed_at = 2.0
    card.brake_verdict = "CONFIRMED"
    card.brake_ratio = 0.50
    card.brake_witness_ts = 2.0
    card.piso = PISO_2
    card.p2_at = 2.0
    card.kd_distance = 2.1
    # Cruce limpio en P2: inicia la espera de separación (ventana 60s).
    assert edificio.evaluate(
        asset=asset, direction=direction, payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=True,
    ) == "stay"
    card = edificio.get_card(asset)
    assert card is not None
    card.cross_separation_since = _time.time() - 901
    assert edificio.evaluate(
        asset=asset, direction=direction, payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=True,
    ) == "subio"
    assert edificio.evaluate(
        asset=asset, direction=direction, payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=True,
    ) == "stay"
    card = edificio.get_card(asset)
    assert card is not None
    card.pending_since = _time.time() - 301
    assert edificio.evaluate(
        asset=asset, direction=direction, payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=True,
    ) == "contratado"
    return edificio


_UNSET = object()


def _bot(edificio: EdificioContratacion, *, client=_UNSET, trades=None) -> SimpleNamespace:
    """Bot fake: client por defecto es un objeto cualquiera; client=None explícito se respeta."""
    if client is _UNSET:
        client = object()
    return SimpleNamespace(
        client=client,
        edificio=edificio,
        trades=trades if trades is not None else {},
    )


@pytest.mark.asyncio
async def test_envia_orden_real_confirmada(monkeypatch):
    edificio = _edificio_con_contratado()
    bot = _bot(edificio)
    mock_order = AsyncMock(return_value=(True, "OID-77", 1.0512, 12345, ""))
    monkeypatch.setattr("edificio_executor.place_order", mock_order)

    enviadas = await execute_contratados(bot)

    assert enviadas == 1
    mock_order.assert_awaited_once()
    kwargs = mock_order.await_args.kwargs
    assert kwargs["asset"] == "NZCADC_otc"
    assert kwargs["direction"] == "PUT"
    assert kwargs["account_type"] == "PRACTICE"
    assert kwargs["amount"] == 1.0
    assert kwargs["duration"] == 900
    assert kwargs["dry_run"] is False
    # Card marcada como enviada para el hub
    card = edificio.get_card("NZCADC_otc")
    assert card.order_status == "sent"
    assert card.order_id == "OID-77"
    # Cola vacía
    assert edificio.pop_contratados() == []


@pytest.mark.asyncio
async def test_rechazo_del_broker_reencola_evento(monkeypatch):
    edificio = _edificio_con_contratado()
    bot = _bot(edificio)
    monkeypatch.setattr(
        "edificio_executor.place_order",
        AsyncMock(return_value=(False, "", 0.0, 0, "broker_rejected")),
    )

    enviadas = await execute_contratados(bot)

    assert enviadas == 0
    events = edificio.pop_contratados()
    assert len(events) == 1
    assert events[0].tries == 1
    assert events[0].order_status == ""


@pytest.mark.asyncio
async def test_descarta_evento_tras_max_tries(monkeypatch):
    edificio = _edificio_con_contratado()
    bot = _bot(edificio)
    monkeypatch.setattr(
        "edificio_executor.place_order",
        AsyncMock(return_value=(False, "", 0.0, 0, "broker_rejected")),
    )

    # Cada execute_contratados simula un ciclo de scan del bot.
    # max_tries=2 → intentos 1 y 2 re-encolan; el 3° supera el límite y descarta.
    for expected_in_queue in (1, 1, 0):
        assert await execute_contratados(bot, max_tries=2) == 0
        queued = edificio.pop_contratados()
        assert len(queued) == expected_in_queue
        for ev in queued:
            edificio.requeue(ev)

    assert edificio.get_card("NZCADC_otc").order_status == "failed"


@pytest.mark.asyncio
async def test_sin_client_reencola_sin_ejecutar(monkeypatch):
    edificio = _edificio_con_contratado()
    bot = _bot(edificio, client=None)
    mock_order = AsyncMock()
    monkeypatch.setattr("edificio_executor.place_order", mock_order)

    enviadas = await execute_contratados(bot)

    assert enviadas == 0
    mock_order.assert_not_awaited()
    assert len(edificio.pop_contratados()) == 1


@pytest.mark.asyncio
async def test_trades_abiertos_reencola_sin_ejecutar(monkeypatch):
    edificio = _edificio_con_contratado()
    bot = _bot(edificio, trades={"leg1": object()})
    mock_order = AsyncMock()
    monkeypatch.setattr("edificio_executor.place_order", mock_order)

    enviadas = await execute_contratados(bot)

    assert enviadas == 0
    mock_order.assert_not_awaited()
    assert len(edificio.pop_contratados()) == 1


@pytest.mark.asyncio
async def test_direction_invalida_descarta_sin_orden(monkeypatch):
    edificio = EdificioContratacion()
    edificio.evaluate(asset="X_otc", direction="", payout=90, payout_ok=True)
    edificio.get_card("X_otc").direction = "SELL"
    # Forzar piso CONTRATADO + evento manual
    card = edificio.get_card("X_otc")
    card.piso = CONTRATADO
    card.order_status = "pending"
    edificio._contratados.append(ContratadoEvent(
        asset="X_otc", direction="SELL", payout=90, score=0.0, card=card,
    ))
    bot = _bot(edificio)
    mock_order = AsyncMock()
    monkeypatch.setattr("edificio_executor.place_order", mock_order)

    enviadas = await execute_contratados(bot)

    assert enviadas == 0
    mock_order.assert_not_awaited()
    assert card.order_status == "failed"


@pytest.mark.asyncio
async def test_evento_expirado_no_envia_orden_y_vuelve_a_p3(monkeypatch):
    import time as _time

    edificio = _edificio_con_contratado()
    bot = _bot(edificio)
    mock_order = AsyncMock(return_value=(True, "OID-99", 1.05, 1, ""))
    monkeypatch.setattr("edificio_executor.place_order", mock_order)

    # El evento quedó esperando 5 minutos (ej. por un trade abierto)
    ev = edificio.pop_contratados()[0]
    ev.timestamp = _time.time() - 300
    edificio.requeue(ev)

    enviadas = await execute_contratados(bot, max_event_age_sec=120)

    assert enviadas == 0
    mock_order.assert_not_awaited()
    # El activo vuelve a la sala de espera, con sus POIs intactos
    card = edificio.get_card("NZCADC_otc")
    assert card.piso == 3
    assert card.order_status == ""
    assert card.has_poi_p1 and card.has_poi_p2 and card.has_poi_p3
    # La cola quedó vacía (el evento vencido no se re-encola)
    assert edificio.pop_contratados() == []


@pytest.mark.asyncio
async def test_evento_fresco_dentro_de_ventana_se_envia(monkeypatch):
    edificio = _edificio_con_contratado()
    bot = _bot(edificio)
    mock_order = AsyncMock(return_value=(True, "OID-88", 1.05, 1, ""))
    monkeypatch.setattr("edificio_executor.place_order", mock_order)

    enviadas = await execute_contratados(bot, max_event_age_sec=120)

    assert enviadas == 1
    mock_order.assert_awaited_once()


def test_is_sticky_cross():
    assert is_sticky_cross(50.0, 51.5, threshold=3.0) is True
    assert is_sticky_cross(50.0, 53.0, threshold=3.0) is False
    assert is_sticky_cross(50.0, 54.0, threshold=3.0) is False
    assert is_sticky_cross(None, 50.0, threshold=3.0) is False
    assert is_sticky_cross(50.0, None, threshold=3.0) is False


def test_infer_loss_reason_from_card():
    edificio = SimpleNamespace(
        get_card=lambda asset: BuildingCard(
            asset="X",
            direction="CALL",
            payout=90,
            payout_ok=True,
            brake_ok=True,
            extreme_ok=True,
            cross_ok=True,
            cross_sticky=False,
        )
    )
    card = edificio.get_card("X")
    card.body_5m = 0.05
    assert _infer_loss_reason(edificio, {"asset": "X"}) == "UNRESOLVED"


def test_infer_loss_reason_no_brake():
    card = BuildingCard(asset="X", direction="CALL", payout=90)
    card.brake_ok = False
    edificio = SimpleNamespace(get_card=lambda asset: card)
    assert _infer_loss_reason(edificio, {"asset": "X"}) == "NO_BRAKE"


def test_infer_loss_reason_no_payout():
    card = BuildingCard(asset="X", direction="CALL", payout=0)
    edificio = SimpleNamespace(get_card=lambda asset: card)
    assert _infer_loss_reason(edificio, {"asset": "X"}) == "NO_PAYOUT"


def test_infer_loss_reason_sticky_cross():
    card = BuildingCard(asset="X", direction="CALL", payout=90)
    card.payout_ok = True
    card.brake_ok = True
    card.extreme_ok = True
    card.cross_ok = True
    card.cross_sticky = True
    edificio = SimpleNamespace(get_card=lambda asset: card)
    assert _infer_loss_reason(edificio, {"asset": "X"}) == "STICKY_CROSS"


def test_infer_loss_reason_body_filter():
    card = BuildingCard(asset="X", direction="CALL", payout=90)
    card.payout_ok = True
    card.brake_ok = True
    card.extreme_ok = True
    card.cross_ok = True
    card.cross_sticky = False
    card.body_5m = 0.02
    edificio = SimpleNamespace(get_card=lambda asset: card)
    assert _infer_loss_reason(edificio, {"asset": "X"}) == "BODY_FILTER"


def test_infer_loss_reason_unresolved_when_card_missing():
    edificio = SimpleNamespace(get_card=lambda asset: None)
    assert _infer_loss_reason(edificio, {"asset": "Y"}) == "UNRESOLVED"


def test_append_order_audit_escribe_loss_reason_en_fila_loss(tmp_path, monkeypatch):
    """T1: el CSV de auditoría escribe loss_reason real solo en órdenes LOSS."""
    import csv as _csv

    from edificio_executor import _AUDIT_CSV_PATH

    csv_path = tmp_path / "edificio_order_audit.csv"
    monkeypatch.setattr("edificio_executor._AUDIT_CSV_PATH", csv_path)

    # Card nueva sin freno -> _infer_loss_reason devuelve "NO_BRAKE".
    card = BuildingCard(asset="X", direction="CALL", payout=90)
    edificio = SimpleNamespace(get_card=lambda asset: card)

    _append_order_audit(
        edificio,
        {"asset": "X", "sent_at": 1.0, "amount": 1.0, "duration_sec": 900,
         "order_id": "O-1", "order_ref": 42},
        "LOSS",
        -1.0,
    )
    _append_order_audit(
        edificio,
        {"asset": "X", "sent_at": 1.0, "amount": 1.0, "duration_sec": 900,
         "order_id": "O-2", "order_ref": 43},
        "WIN",
        0.9,
    )

    rows = list(_csv.DictReader(csv_path.open(encoding="utf-8")))
    assert len(rows) == 2
    loss_row = next(r for r in rows if r["outcome"] == "LOSS")
    win_row = next(r for r in rows if r["outcome"] == "WIN")
    assert loss_row["loss_reason"] == "NO_BRAKE"
    assert win_row["loss_reason"] == ""
