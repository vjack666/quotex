"""Tests del motor del Edificio de Contratación (src/edificio_contratacion.py)."""
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from edificio_contratacion import (  # noqa: E402
    CONTRATADO,
    PISO_1,
    PISO_2,
    PISO_3,
    BuildingCard,
    EdificioContratacion,
)


def _subir_a_p3(edificio: EdificioContratacion, asset: str = "A_otc", direction: str = "PUT") -> None:
    """Lleva un activo hasta P3 (sala de espera) pasando por P1 y P2."""
    assert edificio.evaluate(asset=asset, direction=direction, payout=90, payout_ok=True) == "subio"
    assert edificio.evaluate(
        asset=asset, direction=direction, payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True,
    ) == "subio"
    assert edificio.evaluate(
        asset=asset, direction=direction, payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=True,
    ) == "subio"


def test_activo_sube_hasta_contratado_y_encola_evento():
    edificio = EdificioContratacion()
    _subir_a_p3(edificio)
    # El cruce ya ocurrió al subir; un nuevo scan con cruce + extremo contrata.
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
    edificio._cards["A_otc"].piso = PISO_2
    edificio._cards["A_otc"].p2_at = 1.0
    result = edificio.evaluate(
        asset="A_otc", direction="PUT", payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=True,
    )
    assert result == "subio"
    assert edificio.get_card("A_otc").piso == PISO_3


def test_expulsado_si_deja_de_pagar_en_piso_alto():
    edificio = EdificioContratacion()
    _subir_a_p3(edificio)
    assert edificio.evaluate(asset="A_otc", direction="PUT", payout=85, payout_ok=False) == "expulsado"
    assert edificio.get_card("A_otc").piso == 0


def test_requeue_devuelve_el_mismo_evento():
    edificio = EdificioContratacion()
    _subir_a_p3(edificio)
    edificio.evaluate(
        asset="A_otc", direction="PUT", payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=True,
    )
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
    _subir_a_p3(edificio)
    edificio.evaluate(
        asset="A_otc", direction="PUT", payout=90, payout_ok=True,
        brake_ok=True, extreme_ok=True, cross_ok=True,
    )
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
