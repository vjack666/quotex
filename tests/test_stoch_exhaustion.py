"""Tests de agotamiento verdadero del estocástico M15 (V3) — ZONA ADAPTATIVA.

Cubre la regla completa: ZONA + CRUCE CONFIRMADO (>=1 vela M15) + VELA DE
AGOTAMIENTO en la franja de la zona. Doble camino de confirmacion:
  (A) RUPTURA: vela de indecision en la franja de la zona.
  (B) ATRAPADO: estocastico atrapado varias velas en el extremo sin salir.
La zona es adaptativa (% del precio), NO pips fijos -> funciona en cualquier
par (AUDUSD o USDPKR).
"""
from dataclasses import dataclass

import pytest

from stochastic_m15 import compute_stoch
from stoch_exhaustion import (
    ExhaustResult,
    adaptive_zone,
    classify_exhaustion_candle,
    evaluate_exhaustion,
)
from models import Candle


@dataclass
class _C:
    o: float
    h: float
    l: float
    c: float

    @property
    def open(self):
        return self.o

    @property
    def high(self):
        return self.h

    @property
    def low(self):
        return self.l

    @property
    def close(self):
        return self.c


def _c(o, h, l, c):
    return _C(o, h, l, c)


# --- clasificacion de vela de agotamiento --------------------------------


def test_doji_indecision():
    c = _c(1.0000, 1.0004, 0.9996, 1.0001)
    assert classify_exhaustion_candle(c, "CALL") == "doji"
    assert classify_exhaustion_candle(c, "PUT") == "doji"


def test_martillo_call_inferior_wick():
    c = _c(1.0000, 1.00035, 0.99935, 1.0003)
    assert classify_exhaustion_candle(c, "CALL") == "martillo"


def test_estrellafugaz_put_upper_wick():
    c = _c(1.0005, 1.0040, 1.0003, 1.0006)
    assert classify_exhaustion_candle(c, "PUT") == "estrellafugaz"


def test_vela_normal_no_exhaust():
    c = _c(1.0000, 1.0030, 0.9995, 1.0028)
    assert classify_exhaustion_candle(c, "PUT") is None
    assert classify_exhaustion_candle(c, "CALL") is None


# --- zona adaptativa (sin pips fijos) ------------------------------------


def test_adaptive_zone_pct_not_pips():
    candles = [_c(1.0 + i * 0.0005, 1.0 + i * 0.0005 + 0.0002, 1.0 + i * 0.0005 - 0.0002, 1.0 + i * 0.0005)
               for i in range(20)]
    lo, hi = adaptive_zone(candles, frac=0.5, lookback=20)
    assert lo < hi
    # el ancho es un % del precio (3-7‰ aqui), nunca pips absolutos fijos
    pct = (hi - lo) / ((hi + lo) / 2)
    assert 0.003 <= pct <= 0.007


# --- regla completa: evaluate_exhaustion ---------------------------------


def test_fuera_de_zona_extrema_espera():
    ex = evaluate_exhaustion(k=55.0, d=50.0, direction="PUT",
                             k_vals=[50.0, 55.0], d_vals=[50.0, 50.0])
    assert ex.action == "EXHAUST_WAIT"
    assert ex.in_extreme_zone is False


def test_zona_extrema_sin_cruce_confirmado_espera():
    # PUT en Z5 (sobrecompra) PERO sin cruce bajista -> espera (caso AUDUSD id 142)
    ex = evaluate_exhaustion(
        k=94.5, d=83.9, direction="PUT",
        k_vals=[80.0, 90.0, 100.0, 94.5],
        d_vals=[83.0, 83.5, 83.9, 83.9],
    )
    assert ex.action == "EXHAUST_WAIT"
    assert ex.in_extreme_zone is True
    assert ex.cross_confirmed is False


def _crossed_series_put():
    """Serie donde %K cruza a la baja hace 1 vela M15.
    k: 60 -> 95 -> 90 -> 88 ; d: 72 -> 85 -> 98 -> 70
    idx2: k0=95>=d0=85 y k1=90<d1=98 -> CRUCE BAJISTA, cross_ago=1."""
    k = [60.0, 95.0, 90.0, 88.0]
    d = [72.0, 85.0, 98.0, 70.0]
    return k, d


def test_cruce_confirmado_sin_vela_espera():
    k, d = _crossed_series_put()
    ex = evaluate_exhaustion(
        k=88.0, d=70.0, direction="PUT",
        k_vals=k, d_vals=d,
        candles_15m=[_c(1.0000, 1.0030, 1.0001, 1.0028)],
        zone_lo=0.9997, zone_hi=1.0003,
    )
    assert ex.cross_confirmed is True
    assert ex.action == "EXHAUST_WAIT"
    assert ex.exhaustion_candle is None


def test_cruce_confirmado_estrellafugaz_confirmado():
    k, d = _crossed_series_put()
    ex = evaluate_exhaustion(
        k=88.0, d=70.0, direction="PUT",
        k_vals=k, d_vals=d,
        candles_15m=[_c(1.0005, 1.0040, 1.0003, 1.0006)],
        zone_lo=1.0037, zone_hi=1.0043,  # franja resistencia alrededor 1.0040
    )
    assert ex.action == "EXHAUST_CONFIRMED"
    assert ex.path == "ruptura"
    assert ex.exhaustion_candle in ("martillo", "estrellafugaz")
    assert ex.cross_ago is not None and ex.cross_ago >= 1


def test_call_sobreventa_martillo_soporte():
    k = [20.0, 18.0, 25.0, 30.0]   # idx2: 18<=22 y 25>21 -> alcista, ago=1
    d = [22.0, 22.0, 21.0, 24.0]
    ex = evaluate_exhaustion(
        k=15.0, d=30.0, direction="CALL",
        k_vals=k, d_vals=d,
        candles_15m=[_c(1.0000, 1.00035, 0.99935, 1.0003)],
        zone_lo=0.99905, zone_hi=0.99965,  # franja soporte alrededor 0.99935
    )
    assert ex.action == "EXHAUST_CONFIRMED"
    assert ex.exhaustion_candle == "martillo"


def test_camino_atrapado_en_extremo():
    """Tu regla USDPKR: muchos cruces DENTRO de 80-100 pero el %K nunca
    baja de la linea 80 -> agotamiento en sobrecompra (no falsa reversión)."""
    # cruce bajista confirmado hace >=1 (idx1), luego 5 velas atrapadas >=80
    k = [95.0, 85.0, 82.0, 85.0, 90.0, 92.0]
    d = [90.0, 88.0, 80.0, 82.0, 86.0, 88.0]
    ex = evaluate_exhaustion(
        k=92.0, d=88.0, direction="PUT",
        k_vals=k, d_vals=d,
        candles_15m=[_c(1.0000, 1.0030, 1.0001, 1.0028)],  # vela normal, no rechazo
        zone_lo=0.9997, zone_hi=1.0003,
        trap_window=5,
    )
    assert ex.action == "EXHAUST_CONFIRMED"
    assert ex.path == "atrapado"


def test_no_atrapado_si_sale_del_extremo():
    """Si el %K baja de 80 (sale del extremo), no es 'atrapado'."""
    k = [82.0, 85.0, 90.0, 95.0, 60.0, 55.0]  # ultimas 2 salen de 80
    d = [80.0, 82.0, 86.0, 90.0, 70.0, 65.0]
    ex = evaluate_exhaustion(
        k=55.0, d=65.0, direction="PUT",
        k_vals=k, d_vals=d,
        candles_15m=[_c(1.0, 1.003, 0.999, 1.002)],
        zone_lo=0.9997, zone_hi=1.0003,
        trap_window=5,
    )
    # k=55 ya no esta en sobrecompra -> fuera de zona (no atrapado)
    assert ex.action == "EXHAUST_WAIT"


# --- integracion con compute_stoch (cross_ago expuesto) -------------------


def test_compute_stoch_expone_cross_ago_y_series():
    closes = [1.0 + i * 0.001 for i in range(20)]
    highs = [c + 0.002 for c in closes]
    lows = [c - 0.002 for c in closes]
    closes[-1] = closes[-2] + 0.010
    highs[-1] = closes[-1] + 0.001
    lows[-1] = closes[-1] - 0.001
    cls = [_c(o, h, l, c) for o, h, l, c in zip(closes, highs, lows, closes)]
    st = compute_stoch(cls, direction="PUT")
    assert "cross_ago" in st
    assert "k_vals" in st and "d_vals" in st
    assert st["estado"] in ("SOBRECOMPRA", "SOBREVENTA", "NEUTRO")


def test_cross_ago_no_rompe_si_d_mas_corta_que_k():
    """Regresion: pyquotex devuelve %D mas corta que %K."""
    k = [95, 96, 97, 96.5, 95, 93, 90, 88, 85, 82]
    d = [94, 95, 96, 95.5, 94.5, 93.5, 92]
    ex = evaluate_exhaustion(k=k[-1], d=d[-1], k_vals=k, d_vals=d,
                              direction="PUT", zone_lo=0.999, zone_hi=1.001)
    assert ex.action in ("EXHAUST_CONFIRMED", "EXHAUST_WAIT")
    assert ex.cross_ago is not None


def test_m5_contra_bloquea_put():
    """Regla del usuario: M15 y M5 deben ir en la direccion de la entrada.
    PUT confirmado en M15 PERO M5 alcista (inclinado arriba) -> WAIT (m5_contra)."""
    k, d = _crossed_series_put()
    ex = evaluate_exhaustion(
        k=88.0, d=70.0, direction="PUT",
        k_vals=k, d_vals=d,
        candles_15m=[_c(1.0005, 1.0040, 1.0003, 1.0006)],
        zone_lo=1.0037, zone_hi=1.0043,
        stoch_m5={"k": 60.0, "d": 55.0, "cruce": "alcista"},  # M5 apunta ARRIBA
    )
    assert ex.action == "EXHAUST_WAIT"
    assert ex.reason == "m5_contra"


def test_m5_ali_neado_permite_put():
    """M5 bajista (alineado con PUT) -> CONFIRMADO si hay vela de rechazo."""
    k, d = _crossed_series_put()
    ex = evaluate_exhaustion(
        k=88.0, d=70.0, direction="PUT",
        k_vals=k, d_vals=d,
        candles_15m=[_c(1.0005, 1.0040, 1.0003, 1.0006)],
        zone_lo=1.0037, zone_hi=1.0043,
        stoch_m5={"k": 40.0, "d": 55.0, "cruce": "bajista"},  # M5 abajo
    )
    assert ex.action == "EXHAUST_CONFIRMED"
    assert ex.path == "ruptura"

    m1 = [
        _c(0.70080, 0.70090, 0.70070, 0.70085),
        _c(0.70085, 0.70145, 0.70080, 0.70095),  # shooting star: mecha sup 0.70145
        _c(0.70095, 0.70100, 0.70060, 0.70065),
    ]
    k_vals = [88, 92, 96, 90, 92, 94]
    d_vals = [86, 90, 94, 93, 91, 92]
    ex = evaluate_exhaustion(
        k=94.0, d=92.0, k_vals=k_vals, d_vals=d_vals,
        direction="PUT", candles_15m=m1,
        zone_lo=0.70115, zone_hi=0.70175, lookback=15,
    )
    assert ex.action == "EXHAUST_CONFIRMED"
    assert ex.exhaustion_candle in ("estrellafugaz", "martillo")


# --- R7: zone_strength como FUENTE PRINCIPAL de la banda -------------

def test_zone_strength_primario_ensancha_banda():
    """R7: cuando hay zone_strength, manda sobre adaptive_zone.
    Fuerza alta (0.90) => banda permisiva => la vela 'casi' en la zona
    cuenta como rechazo (CONFIRMADO). Sin zone_strength (fallback) la
    misma vela queda fuera de banda => WAIT."""
    k = [95.0, 85.0, 82.0, 88.0]
    d = [90.0, 88.0, 80.0, 84.0]
    # vela con mecha sup 1.0045, zonas 1.0037..1.0043
    # banda base (ZS=None) ~0.00018 => zh+band=1.004488 < 1.0045 => fuera
    # banda con ZS=0.90 (x1.4) ~0.000252 => zh+band=1.004552 >= 1.0045 => dentro
    candle = _c(1.0005, 1.0045, 1.0003, 1.0006)
    # SIN zone_strength: banda base angosta => fuera => WAIT
    ex_fb = evaluate_exhaustion(
        k=88.0, d=84.0, k_vals=k, d_vals=d, direction="PUT",
        candles_15m=[candle], zone_lo=1.0037, zone_hi=1.0043,
        zone_strength=None,
    )
    # CON zone_strength alto: banda ensanchada => dentro => CONFIRMADO
    ex_zs = evaluate_exhaustion(
        k=88.0, d=84.0, k_vals=k, d_vals=d, direction="PUT",
        candles_15m=[candle], zone_lo=1.0037, zone_hi=1.0043,
        zone_strength=0.90,
    )
    assert ex_fb.action == "EXHAUST_WAIT"
    assert ex_zs.action == "EXHAUST_CONFIRMED"


def test_zone_strength_debil_rechaza():
    """R7 endurecido: fuerza < 0.20 (línea inexistente) => zona no fiable
    => EXHAUST_WAIT (zona_debil), aunque hubiera vela de rechazo."""
    k = [95.0, 85.0, 82.0, 88.0]
    d = [90.0, 88.0, 80.0, 84.0]
    ex = evaluate_exhaustion(
        k=88.0, d=84.0, k_vals=k, d_vals=d, direction="PUT",
        candles_15m=[_c(1.0005, 1.0040, 1.0003, 1.0006)],
        zone_lo=1.0037, zone_hi=1.0043,
        zone_strength=0.10,  # línea imaginaria inexistente
    )
    assert ex.action == "EXHAUST_WAIT"
    assert ex.reason.startswith("zona_debil")
