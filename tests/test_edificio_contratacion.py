"""Tests del motor del Edificio de Contratación (src/edificio_contratacion.py)."""
import sys
import time
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from edificio_contratacion import (  # noqa: E402
    CONTRATADO,
    PISO_1,
    PISO_2,
    PISO_3,
    PISO_FUERA,
    BuildingCard,
    EdificioContratacion,
)


def _subir_a_p3(edificio: EdificioContratacion, asset: str = "A_otc", direction: str = "PUT") -> None:
    """Lleva un activo hasta P3 (sala de espera) pasando por P1 y P2.

    Usa la confirmación del freno por vela M15 cerrada y la ventana de
    separación K/D limpia cumplida para la puerta P2→P3.
    """
    # Semilla mínima para la secuencia: kd_distance debe existir antes de
    # cualquier sincronización con SequenceEngine.
    card = BuildingCard(
        asset=asset,
        direction=direction,
        payout=90,
        piso=PISO_FUERA,
        kd_distance=2.1,
    )
    edificio._cards[asset] = card
    assert edificio.evaluate(asset=asset, direction=direction, payout=90, payout_ok=True) == "subio"
    # Primer scan: detecta freno, queda en P1 esperando confirmación.
    assert edificio.evaluate(
        asset=asset, direction=direction, payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True,
    ) == "stay"
    card = edificio.get_card(asset)
    assert card is not None
    # Confirmación del freno por vela cerrada: simular vela M15 testigo.
    card.brake_at = 1.0
    card.brake_confirmed_at = 2.0
    card.brake_verdict = "CONFIRMED"
    card.brake_ratio = 0.50
    card.brake_witness_ts = 2.0
    card.piso = PISO_2
    card.p2_at = 2.0
    card.kd_distance = 2.1
    # Tercer scan: en P2, cruce limpio → inicia la espera de separación.
    assert edificio.evaluate(
        asset=asset, direction=direction, payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=True,
    ) == "stay"
    # Simular la ventana de separación K/D cumplida (>> EDIFICIO_SEPARATION_WAIT_SEC).
    card = edificio.get_card(asset)
    assert card is not None
    card.cross_separation_since = 1.0
    # Cuarto scan: separación confirmada → P3.
    assert edificio.evaluate(
        asset=asset, direction=direction, payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=True,
    ) == "subio"


def _llegar_a_contratado(edificio: EdificioContratacion, asset: str = "A_otc", direction: str = "PUT") -> None:
    """Lleva un activo hasta CONTRATADO, incluyendo delay de ejecución de 5 min."""
    import time as _time
    _subir_a_p3(edificio, asset, direction)
    # Primer evaluate en P3: marca entrada pendiente (delay 5 min).
    assert edificio.evaluate(
        asset=asset, direction=direction, payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=True,
    ) == "stay"
    # Simular paso de 5 min (delay de ejecución).
    card = edificio.get_card(asset)
    assert card is not None
    card.pending_since = _time.time() - 301
    # Sincronizar secuencia para que pase el gate antes de CONTRATADO.
    edificio._sync_sequence_card(asset, now_ts="2026-08-05T12:00:00Z")
    # Segundo evaluate: delay cumplido → CONTRATADO.
    assert edificio.evaluate(
        asset=asset, direction=direction, payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=True,
    ) == "contratado"


def test_activo_sube_hasta_contratado_y_encola_evento():
    edificio = EdificioContratacion()
    _subir_a_p3(edificio)
    # En P3, el primer cruce marca entrada pendiente (delay 5 min).
    assert edificio.evaluate(
        asset="A_otc", direction="PUT", payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=True,
    ) == "stay"
    # Simular paso de 5 min (delay de ejecución).
    card = edificio.get_card("A_otc")
    assert card is not None
    card.pending_since = time.time() - 301
    edificio._sync_sequence_card("A_otc", now_ts="2026-08-05T12:00:00Z")
    assert edificio.evaluate(
        asset="A_otc", direction="PUT", payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=True,
    ) == "contratado"

    card = edificio.get_card("A_otc")
    assert card.piso == CONTRATADO
    assert card.order_status == "pending"
    assert card.has_poi_p1 and card.has_poi_p2 and card.has_poi_p3

    events = edificio.pop_contratados()
    assert len(events) == 1
    assert events[0].asset == "A_otc"
    assert events[0].direction == "PUT"


def test_p1_espera_condiciones_sin_subir():
    edificio = EdificioContratacion()
    assert edificio.evaluate(asset="A_otc", direction="", payout=90, payout_ok=True) == "subio"
    # Sin brake ni extremo se queda en P1
    assert edificio.evaluate(asset="A_otc", direction="", payout=90, payout_ok=True) == "stay"
    assert edificio.get_card("A_otc").piso == PISO_1
    # brake solo no alcanza
    assert edificio.evaluate(
        asset="A_otc", direction="", payout=90, payout_ok=True, brake_ok=True,
    ) == "stay"
    assert edificio.get_card("A_otc").piso == PISO_1


def test_p2_necesita_cruce_para_subir_a_p3():
    edificio = EdificioContratacion()
    _subir_a_p3(edificio)
    edificio.pop_contratados()
    # Bajar manualmente a P2 simulando una card nueva que ya pasó P1+P2
    # y cuya separación K/D ya está confirmada.
    edificio._cards["A_otc"].piso = PISO_2
    edificio._cards["A_otc"].p2_at = 1.0
    edificio._cards["A_otc"].cross_separation_since = 1.0
    result = edificio.evaluate(
        asset="A_otc", direction="PUT", payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=True,
    )
    assert result == "subio"
    assert edificio.get_card("A_otc").piso == PISO_3


def test_p2_sin_cruce_limpio_no_subir_a_p3():
    edificio = EdificioContratacion()
    _subir_a_p3(edificio)
    # Bajar manualmente a P2
    edificio._cards["A_otc"].piso = PISO_2
    edificio._cards["A_otc"].p2_at = 1.0
    result = edificio.evaluate(
        asset="A_otc", direction="PUT", payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=False,
    )
    assert result == "stay"
    assert edificio.get_card("A_otc").piso == PISO_2


def test_p2_espera_separacion_y_se_reinicia():
    edificio = EdificioContratacion()
    _subir_a_p3(edificio)
    # Bajar manualmente a P2
    edificio._cards["A_otc"].piso = PISO_2
    edificio._cards["A_otc"].p2_at = 1.0
    card = edificio.get_card("A_otc")
    assert card.cross_separation_since is None
    # Primer cruce limpio: inicia la ventana de separación, NO sube aún.
    assert edificio.evaluate(
        asset="A_otc", direction="PUT", payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=True, cross_sticky=False,
    ) == "stay"
    assert card.cross_separation_since is not None
    assert card.piso == PISO_2
    # Si el cruce se pierde, la ventana se reinicia.
    assert edificio.evaluate(
        asset="A_otc", direction="PUT", payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=False, cross_sticky=False,
    ) == "stay"
    assert card.cross_separation_since is None
    # Un cruce sticky también reinicia la ventana.
    card.cross_separation_since = time.time() - 10
    assert edificio.evaluate(
        asset="A_otc", direction="PUT", payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=True, cross_sticky=True,
    ) == "stay"
    assert card.cross_separation_since is None
    # Cruce limpio de nuevo y ventana cumplida → P3.
    assert edificio.evaluate(
        asset="A_otc", direction="PUT", payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=True, cross_sticky=False,
    ) == "stay"
    assert card.cross_separation_since is not None
    card.cross_separation_since = time.time() - 901
    assert edificio.evaluate(
        asset="A_otc", direction="PUT", payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=True, cross_sticky=False,
    ) == "subio"
    assert card.piso == PISO_3
    assert card.cross_separation_since is None  # se limpia tras promover


def test_p2_sticky_espera_en_p2_y_no_subir_a_p3():
    edificio = EdificioContratacion()
    _subir_a_p3(edificio)
    # Bajar manualmente a P2
    edificio._cards["A_otc"].piso = PISO_2
    edificio._cards["A_otc"].p2_at = 1.0
    result = edificio.evaluate(
        asset="A_otc", direction="PUT", payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=False, cross_sticky=True,
    )
    assert result == "stay"
    assert edificio.get_card("A_otc").piso == PISO_2
    # Si luego se convierte en cross limpio, inicia la espera de separación.
    result2 = edificio.evaluate(
        asset="A_otc", direction="PUT", payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=True, cross_sticky=False,
    )
    assert result2 == "stay"
    assert edificio.get_card("A_otc").piso == PISO_2
    assert edificio.get_card("A_otc").cross_separation_since is not None
    # Tras la ventana de separación cumplida, sube a P3 en el mismo scan.
    card = edificio.get_card("A_otc")
    card.cross_separation_since = time.time() - 901
    result3 = edificio.evaluate(
        asset="A_otc", direction="PUT", payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=True, cross_sticky=False,
    )
    assert result3 == "subio"
    assert edificio.get_card("A_otc").piso == PISO_3


def test_expulsado_si_deja_de_pagar_en_piso_alto():
    edificio = EdificioContratacion()
    _subir_a_p3(edificio)
    assert edificio.evaluate(asset="A_otc", direction="PUT", payout=85, payout_ok=False) == "expulsado"
    assert edificio.get_card("A_otc").piso == 0


def test_requeue_devuelve_el_mismo_evento():
    edificio = EdificioContratacion()
    _llegar_a_contratado(edificio)
    events = edificio.pop_contratados()
    assert len(events) == 1
    edificio.requeue(events[0])
    again = edificio.pop_contratados()
    assert len(again) == 1
    assert again[0] is events[0]
    # requeue duplicado no duplica
    edificio.requeue(events[0])
    assert len(edificio.pop_contratados()) == 1


def test_get_state_expone_estado_de_orden():
    edificio = EdificioContratacion()
    _llegar_a_contratado(edificio)
    card = edificio.get_card("A_otc")
    card.order_status = "sent"
    card.order_id = "OID-123"
    state = edificio.get_state()
    card_state = state["cards"]["A_otc"]
    assert card_state["order_status"] == "sent"
    assert card_state["order_id"] == "OID-123"
    assert state["resumen"]["contratados"] == 1


def test_direction_se_fija_una_sola_vez():
    edificio = EdificioContratacion()
    edificio.evaluate(asset="A_otc", direction="", payout=90, payout_ok=True)
    edificio.evaluate(asset="A_otc", direction="CALL", payout=90, payout_ok=True)
    assert edificio.get_card("A_otc").direction == "CALL"


def test_card_no_contrata_sin_direction():
    edificio = EdificioContratacion()
    _subir_a_p3(edificio, direction="")
    edificio.get_card("A_otc").direction = None
    result = edificio.evaluate(
        asset="A_otc", direction="", payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=True,
    )
    assert result == "stay"
    assert edificio.get_card("A_otc").piso == PISO_3


def test_p3_filtra_vela_chica_y_no_contrata():
    edificio = EdificioContratacion()
    _subir_a_p3(edificio)
    # Vela 5m con body chico: body_pct=0.0167 (1.67%)
    vela_chica = {
        "name": "doji",
        "side": "bull",
        "body": 0.00001,
        "total_range": 0.0006,
        "body_pct": 0.0167,
        "open": 1.0,
        "close": 1.00001,
        "ts": 1785597900,
    }
    result = edificio.evaluate(
        asset="A_otc", direction="CALL", payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=True,
        close_candle_5m=vela_chica,
    )
    assert result == "stay"
    assert edificio.get_card("A_otc").piso == PISO_3


def test_p3_vela_grande_pasa_filtro_y_contrata():
    edificio = EdificioContratacion()
    _subir_a_p3(edificio)
    # Vela 5m con body grande: body=0.037, total_range=0.042 -> body_pct=0.881 (88.1%)
    vela_grande = {
        "name": "bullish_engulfing",
        "side": "bull",
        "body": 0.037,
        "total_range": 0.042,
        "body_pct": 0.881,
        "open": 290.942,
        "close": 290.979,
        "ts": 1785597900,
    }
    result = edificio.evaluate(
        asset="A_otc", direction="CALL", payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=True,
        close_candle_5m=vela_grande,
    )
    assert result == "stay"
    assert edificio.get_card("A_otc").piso == PISO_3
    assert edificio.get_card("A_otc").entry_pending is True
    # Simular delay de ejecución cumplido (5 min).
    card = edificio.get_card("A_otc")
    assert card is not None
    card.pending_since = time.time() - 301
    result2 = edificio.evaluate(
        asset="A_otc", direction="CALL", payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=True,
        close_candle_5m=vela_grande,
    )
    assert result2 == "contratado"
    assert edificio.get_card("A_otc").piso == CONTRATADO


def test_p3_cuerpo_pequeno_valida_entrada():
    edificio = EdificioContratacion()
    _subir_a_p3(edificio)
    # Doji con rechazo direccional CALL: cuerpo pequeño (body/range=0.27 <= 0.35)
    # y mecha INFERIOR dominante (0.0014 vs 0.0002 upper, ratio 7x >= 1.2).
    vela_do = {
        "name": "doji",
        "side": "doji",
        "body_pct": 0.02,
        "open": 1.0000,
        "high": 1.0008,
        "low": 0.9986,
        "close": 1.0006,
        "ts": 1785597900,
    }
    result = edificio.evaluate(
        asset="A_otc", direction="CALL", payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=True,
        close_candle_5m=vela_do,
    )
    assert result == "stay"
    card = edificio.get_card("A_otc")
    assert card.piso == PISO_3
    assert card.entry_pending is True  # cuerpo pequeño + rechazo CALL valida
    assert card.pattern_5m == "doji"


def test_p3_rechazo_direccional_misma_vela_no_valida_ambos():
    edificio = EdificioContratacion()
    _subir_a_p3(edificio)
    # La misma vela doji con mecha INFERIOR domina en CALL pero NO en PUT:
    # el rechazo es direccional (a diferencia del doji puro agnóstico).
    vela_do = {
        "name": "doji",
        "side": "doji",
        "body_pct": 0.02,
        "open": 1.0000,
        "high": 1.0008,
        "low": 0.9986,
        "close": 1.0006,
        "ts": 1785597900,
    }
    edificio.evaluate(
        asset="A_otc", direction="PUT", payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=True,
        close_candle_5m=vela_do,
    )
    card = edificio.get_card("A_otc")
    assert card.entry_pending is False  # mecha inferior no valida PUT


def test_p3_spooling_sin_wick_dominante_bloquea():
    edificio = EdificioContratacion()
    _subir_a_p3(edificio)
    card = edificio.get_card("A_otc")
    assert card.entry_pending is False
    # Spinning top: cuerpo pequeño (body/range=0.0273 <= 0.35) PERO mechas
    # casi iguales (upper 0.0114 vs lower 0.0100, ratio < 1.2) → sin rechazo
    # direccional → el gate AHORA BLOQUEA (restaura el filtro real en P3).
    vela_plana = {
        "name": "spinning_top",
        "side": "bull",
        "body_pct": 0.0273,
        "open": 1.0000,
        "high": 1.0120,
        "low": 0.9900,
        "close": 1.0006,
        "ts": 1785597900,
    }
    result = edificio.evaluate(
        asset="A_otc", direction="CALL", payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=True,
        close_candle_5m=vela_plana,
    )
    assert result == "stay"
    assert card.piso == PISO_3
    assert card.entry_pending is False  # no marcó entrada (sin wick dominante)


def test_post_brake_medicion_reintentable_cuando_llega_vela():
    edificio = EdificioContratacion()
    _subir_a_p3(edificio)
    card = edificio.get_card("A_otc")
    assert card.brake_confirmed_at is not None
    # En P2, sin vela post-freno en el snapshot → aún sin medición (reintenta).
    assert card.post_brake_body_ratio is None
    # Llega la vela M15 post-freno (ts > brake_confirmed_at): se mide en el
    # próximo ciclo aunque la promoción a P3 aún esté esperando separación.
    _now = time.time()
    velas = [
        {"ts": _now + 100, "open": 1.0, "high": 1.01, "low": 0.995, "close": 1.005},
        {"ts": _now + 200, "open": 1.0, "high": 1.02, "low": 0.99, "close": 1.015},
    ]
    result = edificio.evaluate(
        asset="A_otc", direction="PUT", payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=True,
        candles_15m=velas,
    )
    assert result == "stay"  # sigue en P3 (entrada marcada, esperando delay)
    assert card.piso == PISO_3
    assert card.post_brake_body_ratio is not None
    assert card.post_brake_measured_at == _now + 100


def test_p3_entry_pending_reset_al_bajar_a_p2_y_reingreso_despues():
    edificio = EdificioContratacion()
    _subir_a_p3(edificio)
    # Vela 5m con body grande para marcar entrada pendiente en P3.
    vela_grande = {
        "name": "bullish_engulfing",
        "side": "bull",
        "body": 0.037,
        "total_range": 0.042,
        "body_pct": 0.881,
        "open": 290.942,
        "close": 290.979,
        "ts": 1785597900,
    }
    result = edificio.evaluate(
        asset="A_otc", direction="CALL", payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=True,
        close_candle_5m=vela_grande,
    )
    assert result == "stay"
    assert edificio.get_card("A_otc").piso == PISO_3
    assert edificio.get_card("A_otc").entry_pending is True
    assert edificio.get_card("A_otc").pending_since is not None
    # Ahora pierde brake+extremo: baja a P1 y resetea pending.
    result2 = edificio.evaluate(
        asset="A_otc", direction="CALL", payout=90, payout_ok=True,
        brake_ok=False, extreme_ok=False, cross_ok=True,
    )
    assert result2 == "bajo"
    card = edificio.get_card("A_otc")
    assert card is not None
    assert card.piso == PISO_2
    assert card.entry_pending is False
    assert card.pending_since is None
    # Vuelve a cumplir brake+extremo en P2: espera separación K/D.
    result3 = edificio.evaluate(
        asset="A_otc", direction="CALL", payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=True,
    )
    assert result3 == "stay"
    assert edificio.get_card("A_otc").piso == PISO_2
    assert edificio.get_card("A_otc").entry_pending is False
    # Simular separación cumplida → promueve a P3.
    card3 = edificio.get_card("A_otc")
    assert card3 is not None
    card3.cross_separation_since = time.time() - 901
    result4 = edificio.evaluate(
        asset="A_otc", direction="CALL", payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=True,
    )
    assert result4 == "subio"
    # Reingreso a P3: en este ciclo NO marca entrada pendiente;
    # la 5m gate se evalúa en el próximo scan.
    result5 = edificio.evaluate(
        asset="A_otc", direction="CALL", payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=True,
        close_candle_5m=vela_grande,
    )
    assert result5 == "stay"
    assert edificio.get_card("A_otc").entry_pending is True
    assert edificio.get_card("A_otc").pending_since is not None


def test_p2_pierde_brake_extremo_y_vuelve_a_p1():
    edificio = EdificioContratacion()
    _subir_a_p3(edificio)
    edificio.pop_contratados()
    edificio._cards["A_otc"].piso = PISO_2
    edificio._cards["A_otc"].p2_at = 1.0
    edificio._cards["A_otc"].brake_at = 1.0
    edificio._cards["A_otc"].brake_confirmed_at = 2.0
    edificio._cards["A_otc"].brake_verdict = "CONFIRMED"
    edificio._cards["A_otc"].brake_ratio = 0.5
    edificio._cards["A_otc"].brake_witness_ts = 2.0
    result = edificio.evaluate(
        asset="A_otc", direction="PUT", payout=90, payout_ok=True,
        brake_ok=False, extreme_ok=False, cross_ok=False,
    )
    assert result == "bajo"
    card = edificio.get_card("A_otc")
    assert card is not None
    assert card.piso == PISO_1
    assert card.entry_pending is False
    assert card.pending_since is None
    assert card.piso == PISO_1
    assert card.brake_at is None
    assert card.brake_confirmed_at is None
    assert card.p2_at is None
    assert card.cross_separation_since is None
    assert card.entry_pending is False
    assert card.pending_since is None


def test_freno_es_tarjeta_de_acceso_a_p2_sin_extremo():
    """El freno (candidato + CONFIRMED con vela M15 cerrada) es la tarjeta de
    acceso a P2: el extremo NO es requisito de la puerta, se espera dentro de P2."""
    edificio = EdificioContratacion()
    assert edificio.evaluate(asset="A_otc", direction="PUT", payout=90, payout_ok=True) == "subio"
    # Candidato de freno arranca con SOLO brake_ok (sin extremo).
    assert edificio.evaluate(
        asset="A_otc", direction="PUT", payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=False,
    ) == "stay"
    card = edificio.get_card("A_otc")
    assert card is not None
    assert card.piso == PISO_1
    assert card.brake_at is not None
    # Confirmar el freno con vela M15 cerrada (ratio 0.5 < 0.7) → la tarjeta
    # de acceso se emite y la card queda en P2.
    card.brake_at = 1.0
    card.brake_confirmed_at = 2.0
    card.brake_verdict = "CONFIRMED"
    card.brake_ratio = 0.50
    card.brake_witness_ts = 2.0
    card.piso = PISO_2
    card.p2_at = 2.0
    # La permanencia en P2 exige extremo vigente: sin extremo baja a P1.
    assert edificio.evaluate(
        asset="A_otc", direction="PUT", payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=False,
    ) == "bajo"
    assert edificio.get_card("A_otc").piso == PISO_1


def test_p2_estadia_se_sostiene_con_tarjeta_y_extremo_vigente():
    """La estadía en P2 se sostiene con freno CONFIRMED + extremo vigente.
    El brake_ok instantáneo (vela en formación) NO revoca la tarjeta."""
    edificio = EdificioContratacion()
    _subir_a_p3(edificio)
    edificio.pop_contratados()
    # Bajar manualmente a P2 con la tarjeta emitida.
    edificio._cards["A_otc"].piso = PISO_2
    edificio._cards["A_otc"].p2_at = 1.0
    # brake_ok instantáneo False (vela en formación abrió amplia) pero
    # tarjeta CONFIRMED + extremo vigente → se queda en P2.
    result = edificio.evaluate(
        asset="A_otc", direction="PUT", payout=90, payout_ok=True,
        brake_ok=False, extreme_ok=True, cross_ok=False,
    )
    assert result == "stay"
    assert edificio.get_card("A_otc").piso == PISO_2
    # Pierde el extremo (contexto del cruce) → baja a P1.
    result2 = edificio.evaluate(
        asset="A_otc", direction="PUT", payout=90, payout_ok=True,
        brake_ok=False, extreme_ok=False, cross_ok=False,
    )
    assert result2 == "bajo"
    assert edificio.get_card("A_otc").piso == PISO_1


def test_p1_snapshot_guarda_velas_1m_reales():
    """Fix caja negra: las velas 1m pasadas al evaluate deben persistirse en
    el card (candles_1m_snap) y en el snapshot de PISO_1 — no salir vacías."""
    edificio = EdificioContratacion()
    velas_1m = [
        {"time": 1700000000 + i * 60, "open": 1.0 + i * 0.001,
         "high": 1.0 + i * 0.002, "low": 0.999, "close": 1.0 + i * 0.001,
         "ticks": 10}
        for i in range(10)
    ]
    result = edificio.evaluate(
        asset="VELA_otc", direction="PUT", payout=90, payout_ok=True,
        candles_1m=velas_1m,
    )
    assert result == "subio"
    card = edificio.get_card("VELA_otc")
    assert card is not None
    assert card.candles_1m_snap, "candles_1m_snap no debería quedar vacío"
    assert card.candles_1m_snap[-1]["time"] == velas_1m[-1]["time"]
    assert len(card.candles_1m_snap) == 10


def test_p1_sin_velas_1m_no_rompe_evaluate():
    """Sin velas 1m (feed viejo) el evaluate sigue funcionando y el card
    conserva una lista vacía — sin excepción (regresión del fix)."""
    edificio = EdificioContratacion()
    result = edificio.evaluate(
        asset="SINVELA_otc", direction="CALL", payout=90, payout_ok=True,
    )
    assert result == "subio"
    card = edificio.get_card("SINVELA_otc")
    assert card is not None
    assert card.candles_1m_snap == []

