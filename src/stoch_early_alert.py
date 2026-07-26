"""Capa de ALERTA TEMPRANA del SPIKE (cinemática del estocástico M15).

Spec: specs/strat_f_spike_early_alert/

Esta capa es ADICIONAL y COMPLEMENTARIA a strat_f_spike_wyckoff_phase_a. NO
reemplaza el cruce confirmado (R2) ni la separación adaptativa (R2-bis); es una
marca de ATENCIÓN que anticipa el giro del estocástico M15 ANTES de que el cruce
esté confirmado. Se usa en el chequeo INTRAVELA (R10), nunca como disparador.

Doctrina (R-EA1..R-EA11):
- Es ALERTA, no disparador: no promueve SPIKE, no relaja R2/R2-bis/R3/R3-bis.
- Puntaje combinado ADAPTATIVO: pesos fijos 1/5 por versión; umbral = percentil 90
  del historial propio del par (sin números fijos universales).
- Proyección SIMÉTRICA con valor absoluto: |valor_actual - 20| / |pendiente| (CALL)
  o |valor_actual - 80| / |pendiente| (PUT). SIEMPRE positiva.
- Persistencia ALT B: JSON por símbolo en data/early_alert/<SYM>.json, escritura
  atómica (write-temp + os.replace). Sobrevive reinicios.

PURO salvo la escritura del JSON de historial (I/O mínimo, en disco local, no BD
ni red). El búfer en memoria es el de sesión; el JSON lo hace sobrevivir reinicios.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from collections import deque
from typing import Deque, Dict, List, Literal, Optional, Sequence, Tuple

from models import Candle

# Reusa el cálculo del estocástico del motor vigente (NO duplica lógica).
try:
    from stochastic_m15 import compute_stoch  # mismo origen que strat_fractal
except Exception:  # pragma: no cover - fallback si el import relativo falla
    compute_stoch = None  # type: ignore


# --------------------------------------------------------------------------- #
# Constantes de la capa (todas relativas, ninguna es umbral de "disparo")
# --------------------------------------------------------------------------- #
HISTORY_N = 50            # ocasiones recordadas por símbolo (ventana rodante)
PERSIST_EVERY_K = 10      # volcar JSON cada K alertas del par
ACTIVATION_PERCENTILE = 90.0  # percentil del rango histórico del par (R-EA5)
DEFAULT_PROJECTION_WINDOW = 15  # lookback por defecto (coherente con R10)
EPS = 1e-9


# --------------------------------------------------------------------------- #
# Resultado de la alerta
# --------------------------------------------------------------------------- #
@dataclass
class EarlyAlertResult:
    activa: bool
    reason: str  # por qué no se activó (o "activa" si sí)
    pendiente_k: float
    pendiente_d: float
    aceleracion: float
    angulo: float
    proyeccion_velas: float
    convergencia: float
    puntaje: float
    percentil_par: float
    ventana_proy: int
    es_default: bool  # True si no había historial suficiente del par
    sub_scores: Dict[str, float] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Búfer de historial por símbolo (en memoria + persistencia ALT B)
# --------------------------------------------------------------------------- #
_BUFFER: Dict[str, Deque[float]] = {}      # puntajes históricos del par
_ALERT_COUNT: Dict[str, int] = {}           # nº de alertas desde último volcado
_DATA_DIR = os.path.join("data", "early_alert")


def _sym_path(sym: str) -> str:
    safe = sym.upper().replace("/", "").replace("\\", "").replace(":", "")
    return os.path.join(_DATA_DIR, f"{safe}.json")


def _load_history(sym: str) -> Deque[float]:
    """Carga el búfer desde disco (ALT B). Si no existe o está corrupto -> vacío."""
    if sym in _BUFFER:
        return _BUFFER[sym]
    dq: Deque[float] = deque(maxlen=HISTORY_N)
    path = _sym_path(sym)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            for v in data.get("scores", []):
                dq.append(float(v))
        except (ValueError, OSError):
            # Archivo corrupto o ilegible: arranca vacío (es_default=True).
            dq = deque(maxlen=HISTORY_N)
    _BUFFER[sym] = dq
    _ALERT_COUNT[sym] = 0
    return dq


def _save_history(sym: str) -> None:
    """Vuelca el búfer a disco con escritura atómica (write-temp + os.replace)."""
    dq = _BUFFER.get(sym)
    if dq is None:
        return
    os.makedirs(_DATA_DIR, exist_ok=True)
    path = _sym_path(sym)
    tmp = path + ".tmp"
    payload = {"sym": sym, "scores": list(dq)}
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        os.replace(tmp, path)  # renombrado atómico del SO
    except OSError:
        # Si falla el volcado, no debe romper el ciclo del bot.
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


# --------------------------------------------------------------------------- #
# Métricas de cinemática (R-EA4)
# --------------------------------------------------------------------------- #
def _slope(vals: Sequence[float], n: int = 3) -> float:
    """Pendiente por vela: (valor_actual - valor_hace_n) / n. ~0 = aplanándose."""
    if len(vals) < n + 1:
        return 0.0
    return (vals[-1] - vals[-1 - n]) / n


def _acceleration(vals: Sequence[float], n: int = 3) -> float:
    """2ª derivada: pendiente_actual - pendiente_de_hace_pocas_velas."""
    if len(vals) < 2 * n + 1:
        return 0.0
    slope_now = (vals[-1] - vals[-1 - n]) / n
    slope_prev = (vals[-1 - n] - vals[-1 - 2 * n]) / n
    return slope_now - slope_prev


def _angle(slope: float) -> float:
    """Ángulo en grados: arctan(pendiente) * 180/pi. Comparable entre pares."""
    return math.degrees(math.atan(slope))


def _projection(value: float, slope: float, direction: Literal["CALL", "PUT"]) -> float:
    """Velas hasta tocar 20 (CALL) u 80 (PUT). SIMÉTRICA con valor absoluto.

    CALL: %K en sobreventa subiendo -> (20 - value) velas para llegar a 20.
    PUT:  %K en sobrecompra bajando -> (value - 80) velas para llegar a 80.
    Fórmula única: |value - target| / |slope|, SIEMPRE positiva.
    Si slope ~0 (línea plana) -> infinito -> se limita a la ventana del par.
    """
    target = 20.0 if direction == "CALL" else 80.0
    if abs(slope) < EPS:
        return float("inf")
    return abs(value - target) / abs(slope)


def _convergence_speed(k_vals: Sequence[float], d_vals: Sequence[float],
                       n: int = 3) -> float:
    """Velocidad de achique de |K - D| en el tiempo (dinámica de R2-bis).

    Devuelve la tasa de cambio de la separación (negativo = se achica más rápido).
    """
    if len(k_vals) < n + 1 or len(d_vals) < n + 1:
        return 0.0
    sep_now = abs(k_vals[-1] - d_vals[-1])
    sep_prev = abs(k_vals[-1 - n] - d_vals[-1 - n])
    return (sep_now - sep_prev) / n  # <0 => convergiendo


# --------------------------------------------------------------------------- #
# Ventana de proyección adaptativa (R-EA6 / D-EA3)
# --------------------------------------------------------------------------- #
def _projection_window(sym: str, scores: Deque[float]) -> Tuple[int, bool]:
    """Ventana de referencia = duración histórica del par (zona extrema->cruce).

    Como proxy de esa duración usamos el rango de puntajes históricos del par:
    la ventana es DEFAULT_PROJECTION_WINDOW hasta acumular historial. El historial
    de duraciones reales se puede enriquecer en versión futura; por ahora el
    búfer de puntajes alimenta el percentil (R-EA5) y la ventana usa el default
    hasta que el par tenga suficientes observaciones de 'tiempo en zona'.
    """
    if len(scores) < 5:
        return DEFAULT_PROJECTION_WINDOW, True
    return DEFAULT_PROJECTION_WINDOW, False


# --------------------------------------------------------------------------- #
# Puntaje combinado adaptativo (R-EA5 / D-EA2)
# --------------------------------------------------------------------------- #
def _referenced_score(current: float, history: Sequence[float]) -> float:
    """Normaliza current a [0,1] contra el rango histórico del par.

    Si el par no tiene historial (o referente ~0), devuelve 0.5 (neutral).
    """
    if len(history) < 2:
        return 0.5
    lo, hi = min(history), max(history)
    span = hi - lo
    if span < EPS:
        return 0.5
    return max(0.0, min(1.0, (current - lo) / span))


def _percentile_threshold(scores: Deque[float]) -> Tuple[float, bool]:
    """Umbral = percentil 90 del rango histórico de puntajes del par.

    Sin historial suficiente -> umbral por defecto (0.6) + es_default=True.
    """
    if len(scores) < 5:
        return 0.6, True
    s = sorted(scores)
    k = (len(s) - 1) * (ACTIVATION_PERCENTILE / 100.0)
    lo_i = int(math.floor(k))
    hi_i = int(math.ceil(k))
    if lo_i == hi_i:
        thr = s[lo_i]
    else:
        thr = s[lo_i] + (s[hi_i] - s[lo_i]) * (k - lo_i)
    return thr, False


# --------------------------------------------------------------------------- #
# API principal
# --------------------------------------------------------------------------- #
def evaluate_early_alert(
    direction: Literal["CALL", "PUT"],
    k_vals: Optional[Sequence[float]] = None,
    d_vals: Optional[Sequence[float]] = None,
    candles_15m: Optional[Sequence[Candle]] = None,
    candles_1m: Optional[Sequence[Candle]] = None,
    sym: str = "",
) -> EarlyAlertResult:
    """Evalúa la alerta temprana sobre la serie de %K/%D (o velas).

    INTRAVELA (R-EA3): usa candles_15m[-1] (M15 abierta) + candles_1m lookback=15.
    Reusa compute_stoch del motor vigente si solo se pasan velas.
    """
    # Obtener series k/d del motor (no duplicar cálculo).
    if (k_vals is None or d_vals is None) and candles_15m is not None and compute_stoch is not None:
        try:
            st = compute_stoch(candles_15m)
            k_vals = st.get("k_vals") or st.get("k")
            d_vals = st.get("d_vals") or st.get("d")
        except Exception:
            k_vals = k_vals or []
            d_vals = d_vals or []
    k_vals = list(k_vals or [])
    d_vals = list(d_vals or [])

    if len(k_vals) < 4 or len(d_vals) < 4:
        return EarlyAlertResult(
            activa=False, reason="serie_insuficiente", pendiente_k=0.0,
            pendiente_d=0.0, aceleracion=0.0, angulo=0.0, proyeccion_velas=0.0,
            convergencia=0.0, puntaje=0.0, percentil_par=0.6,
            ventana_proy=DEFAULT_PROJECTION_WINDOW, es_default=True,
        )

    # 1) Cinemática (R-EA4)
    pend_k = _slope(k_vals, 3)
    pend_d = _slope(d_vals, 3)
    accel = _acceleration(k_vals, 3)
    ang = _angle(pend_k)
    value_now = k_vals[-1]
    proj = _projection(value_now, pend_k, direction)
    conv = _convergence_speed(k_vals, d_vals, 3)

    # 2) Historial del par (R-EA8 / ALT B)
    scores = _load_history(sym) if sym else deque(maxlen=HISTORY_N)
    ventana_proy, es_default = _projection_window(sym, scores)

    # 3) Sub-scores en [0,1] con referente RELATIVO del par (D-EA2)
    # "Aplanamiento": la pendiente cae respecto a su referente reciente.
    k_ref = [abs(_slope(k_vals, 3)) for _ in range(0)]  # placeholder
    ref_k = max([abs(pend_k)] + [abs(p) for p in (list(scores)[-10:] if scores else [abs(pend_k)])]) or EPS
    aplanamiento = 1.0 - min(1.0, abs(pend_k) / ref_k)
    # Aceleración opuesta al impulso (pierde fuerza antes de girar).
    sign_opuesto = 1.0 if (pend_k > 0 and accel < 0) or (pend_k < 0 and accel > 0) else 0.0
    sub_acel = sign_opuesto * min(1.0, abs(accel) / (abs(accel) + EPS))
    # Ángulo normalizado.
    sub_ang = min(1.0, abs(ang) / 90.0)
    # Proyección: menos velas faltan -> más alto.
    if math.isinf(proj):
        sub_proj = 0.0  # sin convergencia clara
    else:
        sub_proj = 1.0 - min(1.0, proj / max(ventana_proy, 1))
    # Convergencia: se achica (conv<0) -> más alto.
    sub_conv = min(1.0, max(0.0, -conv / (abs(conv) + EPS)))

    sub_scores = {
        "aplanamiento": aplanamiento,
        "aceleracion": sub_acel,
        "angulo": sub_ang,
        "proyeccion": sub_proj,
        "convergencia": sub_conv,
    }
    # Pesos FIJOS 1/5 (R-EA5): ajuste por aciertos POSTPUESTO.
    pesos = [0.2, 0.2, 0.2, 0.2, 0.2]
    valores = [aplanamiento, sub_acel, sub_ang, sub_proj, sub_conv]
    puntaje = sum(w * v for w, v in zip(pesos, valores))

    # 4) Umbral percentil 90 del par (R-EA5)
    threshold, es_default = _percentile_threshold(scores)

    # 5) Activación
    activa = puntaje >= threshold and not es_default

    # 6) Alimentar y persistir historial (ALT B) SOLO cuando hay símbolo.
    if sym:
        scores.append(puntaje)
        _ALERT_COUNT[sym] = _ALERT_COUNT.get(sym, 0) + 1
        if _ALERT_COUNT[sym] >= PERSIST_EVERY_K:
            _save_history(sym)
            _ALERT_COUNT[sym] = 0

    reason = "activa" if activa else ("es_default" if es_default else "puntaje_bajo")
    return EarlyAlertResult(
        activa=activa, reason=reason, pendiente_k=pend_k, pendiente_d=pend_d,
        aceleracion=accel, angulo=ang, proyeccion_velas=(0.0 if math.isinf(proj) else proj),
        convergencia=conv, puntaje=puntaje, percentil_par=threshold,
        ventana_proy=ventana_proy, es_default=es_default, sub_scores=sub_scores,
    )


def flush_history(sym: Optional[str] = None) -> None:
    """Vuelca el búfer a disco (al cerrar sesión)."""
    if sym:
        _save_history(sym)
    else:
        for s in list(_BUFFER.keys()):
            _save_history(s)
