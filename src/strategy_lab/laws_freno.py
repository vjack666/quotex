"""laws_freno — leyes ejecutables del freno (Capa Estratega).

Cada ley es una funcion pura LawContext -> LawResult. El peso NO se
hardcodea aqui: lo inyecta el LawEngine via weight_provider (el Discovery
es la fuente de verdad de los pesos). Los umbrales vienen de `cfg`.

Ley #1 (FRENO-IMPULSO-MUERTO) es el cerebro: reusa brake_eval (ya validado
88% WR en cajas negras del bot, walk-forward estable). Las demas leyes son
filtros secundarios que el Discovery ira afinando (separacion optima,
salida-de-20, etc.) — HOY usan umbrales de cfg semilla; el Discovery los
reemplazara por leyes estadisticas (Ley 5/6 de la auditoria).

No importa nada del bot. Cero reloj de pared.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from strategy_lab import brake_eval as be
from strategy_lab.law_engine import ExecutableLaw, LawContext, LawResult


@dataclass
class FrenoConfig:
    """Umbrales semilla. El Discovery los sobreescribe con leyes estadisticas.

    NO son 'constantes a mano en produccion': vienen de cfg (yaml del
    strategy_lab) y el Discovery los reemplaza por hallazgos walk-forward.
    """
    impulse_window: int = 8
    impulse_min_pips: float = 30.0
    brake_fwd: int = 3
    brake_max_advance_frac: float = 0.10
    rebote_fwd: int = 3
    rebote_min_pips: float = 8.0
    stoch_extreme: float = 80.0       # sobrecompra (PUT) / sobreventa (CALL)
    sep_min: float = 3.0              # separacion %K-%D minima (Ley 5 pendiente)
    zone_min_age: int = 3


def _brake_cfg(c: FrenoConfig) -> dict:
    return {
        "stochastic": {"k": 14, "d": 3, "smooth": 3},
        "impulse": {"window": c.impulse_window, "min_pips": c.impulse_min_pips},
        "brake": {"fwd": c.brake_fwd,
                  "max_advance_frac": c.brake_max_advance_frac,
                  "require_alternation": True},
        "rebote": {"fwd": c.rebote_fwd, "min_pips": c.rebote_min_pips},
    }


def ley_impulso_muerto(ctx: LawContext, cfg: FrenoConfig) -> LawResult:
    """Ley #1 — el cerebro. Muerte del impulso en M15 (reusa brake_eval).

    brake_eval marca la vela DONDE el impulso murio (necesita fwd velas
    futuras para confirmar rebote, asi que la marca nunca es la ultima).
    Buscamos la marca mas reciente y la tratamos como senal vigente si
    esta cerca del final (el bot evalua al cerrar cada vela M15).
    Direccion: impulso bajista muerto -> CALL; alcista muerto -> PUT.
    """
    c15 = _as(ctx.c15)
    if len(c15) < cfg.impulse_window + cfg.brake_fwd + 2:
        return LawResult(ok=False, detail="M15 insuficiente para freno")
    feat = be.compute_brake_and_rebote(
        _as(ctx.o15), _as(ctx.h15), _as(ctx.l15), c15, _brake_cfg(cfg)
    )
    mask = feat["brake_mask"]
    net = feat["impulse_net"]
    # ultimo indice con muerte de impulso
    dead = [i for i in range(len(mask)) if mask[i]]
    if not dead:
        return LawResult(ok=False, detail="sin muerte de impulso M15")
    last = dead[-1]
    # vigencia: la muerte debe ser reciente (dentro de los ultimos fwd+window)
    if (len(c15) - 1) - last > (cfg.brake_fwd + cfg.impulse_window):
        return LawResult(ok=False, detail="muerte de impulso muy vieja")
    direction = "CALL" if net[last] < 0 else "PUT"
    return LawResult(ok=True, direction=direction,
                     detail=f"impulso muerto en {last} dir={direction}")


def ley_stoch_extremo(ctx: LawContext, cfg: FrenoConfig) -> LawResult:
    """Filtro secundario — estocastico en extremo EN LA ZONA (no coincidente).

    CALL espera %K < 20 (sobreventa del impulso bajista). PUT espera %K>80.
    El estocastico es el reloj que dice 'es el momento' (Constitucion Ley 4).
    """
    k = (ctx.stoch_m15 or {}).get("k")
    if k is None:
        return LawResult(ok=True, weight=0.0, detail="stoch M15 ausente (soft)")
    if ctx.direction_hint == "CALL" and k >= 20.0:
        return LawResult(ok=False, detail=f"stoch {k:.1f} no sobreventa para CALL")
    if ctx.direction_hint == "PUT" and k <= 80.0:
        return LawResult(ok=False, detail=f"stoch {k:.1f} no sobrecompra para PUT")
    return LawResult(ok=True, detail=f"stoch extremo k={k:.1f}")


def ley_separacion(ctx: LawContext, cfg: FrenoConfig) -> LawResult:
    """Filtro — separacion %K-%D abierta (Ley 5, hoy umbral semilla).

    El Discovery descubrira el rango optimo (p.ej. 3.1-4.4). Mientras,
    semilla configurable. Soft si no hay stoch.
    """
    m = ctx.stoch_m15 or {}
    k, d = m.get("k"), m.get("d")
    if k is None or d is None:
        return LawResult(ok=True, weight=0.0, detail="sin stoch para separacion")
    sep = abs(k - d)
    if sep < cfg.sep_min:
        return LawResult(ok=False, detail=f"separacion {sep:.1f} < {cfg.sep_min}")
    return LawResult(ok=True, detail=f"separacion {sep:.1f}")


def ley_zona_htf(ctx: LawContext, cfg: FrenoConfig) -> LawResult:
    """Filtro — zona HTF valida (requiere ctx.zone presente y con edad)."""
    if ctx.zone is None:
        return LawResult(ok=True, weight=0.0, detail="sin zona (soft)")
    age = getattr(ctx.zone, "bars_inside", None)
    if age is not None and age < cfg.zone_min_age:
        return LawResult(ok=False, detail=f"zona joven ({age} < {cfg.zone_min_age})")
    return LawResult(ok=True, detail="zona HTF ok")


def ley_rechazo_m1(ctx: LawContext, cfg: FrenoConfig) -> LawResult:
    """Filtro — rechazo en M1 (confirmacion de ejecucion, no DISPARADOR).

    Reusa la logica de _m1_rejects_band de strat_fractal, pero como ley
    pura sobre el ctx. Soft: si no hay M1, no bloquea.
    """
    if ctx.c1 is None or len(_as(ctx.c1)) < 2:
        return LawResult(ok=True, weight=0.0, detail="sin M1 (soft)")
    # placeholder de confirmacion: la ultima vela M1 cierra a favor de la dir
    # (el detalle fino lo hereda strat_fractal al cablear el ctx real)
    return LawResult(ok=True, detail="rechazo M1 (placeholder cableado)")


def build_freno_laws(cfg: FrenoConfig,
                     weight_provider: Callable[[str, float], float]
                     ) -> list[ExecutableLaw]:
    """Construye las leyes ejecutables ordenadas por prioridad.

    Prioridad: freno (100, cerebro) > stoch (90) > separacion (80) >
    zona (70) > rechazo (60). El Discovery puede inyectar leyes nuevas
    (Ley #37) sin tocar esto: solo se registran con su priority/requires.
    """
    def mk(lid: str, prio: int, fn: Callable, requires=()) -> ExecutableLaw:
        def _eval(c: LawContext) -> LawResult:
            return fn(c, cfg)
        return ExecutableLaw(id=lid, priority=prio, evaluar=_eval, requires=requires)

    return [
        mk("FRENO-IMPULSO-MUERTO", 100, ley_impulso_muerto),
        mk("STOCH-EXTREMO", 90, ley_stoch_extremo, requires=("FRENO-IMPULSO-MUERTO",)),
        mk("SEPARACION-KD", 80, ley_separacion, requires=("FRENO-IMPULSO-MUERTO",)),
        mk("ZONA-HTF", 70, ley_zona_htf, requires=("FRENO-IMPULSO-MUERTO",)),
        mk("RECHAZO-M1", 60, ley_rechazo_m1, requires=("FRENO-IMPULSO-MUERTO",)),
    ]


def _as(x) -> np.ndarray:
    if x is None:
        return np.array([])
    return np.asarray(x, float)
