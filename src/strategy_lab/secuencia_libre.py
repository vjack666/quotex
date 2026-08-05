"""Motor de Secuencia Libre — Edificio de Contratación (LAB-SEC).

Diferencia CLAVE con backtest_edificio.py:
  - NO impone el orden freno -> cruce -> martillo.
  - Detecta cada evento de forma INDEPENDIENTE y registra el ORDEN REAL.
  - Invalidación estructural (zona muerta 20-80), no timeout arbitrario.
  - win = cierre de la vela de entrada vs su apertura (binaria pura, sin TP).

Leyes aplicadas (MOTOR_SECUENCIAS_LEY_MAESTRA):
  Ley 1  causalidad: solo datos hasta t.
  Ley 2  eventos persisten como estado hasta invalidación.
  Ley 6  invalidación predefinida: zona muerta.
  Ley 8  trazabilidad: cada expediente guarda su firma y timestamps.
  Ley 10 fase, no señal.
  Ley 11 embudo antes que winrate.
  Ley 12 etiqueta separada de la decisión.

Definiciones congeladas ANTES de correr (Ruben, 2026-08-05):
  expiry            = 1 vela M15 (15 min)
  win               = vela verde para CALL / roja para PUT
  zona_muerta       = ambas líneas K y D dentro de (20, 80)
  zona_media        = |K-50| < 10 -> peor escenario, se marca
  nacimiento        = freno en POI (brake_transition)
  atencion          = el cruce K/D eleva la atención, no la crea
  timeout           = NO existe; muere por estructura
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from strategy_lab.compute_features import (
    SMC_ROOT,
    build_feature_frame,
    load_htf,
    load_m15,
)

# --- Constantes congeladas (Ley 6: definidas ANTES de correr) ---
OVERSOLD = 20.0
OVERBOUGHT = 80.0
MID_ZONE_HALF_WIDTH = 10.0  # |K-50| < 10 => zona media (peor escenario)
MIN_SEPARATION = 2.0        # separación K/D para cruce "limpio"
EXPIRY_CANDLES = 1          # 15 min
MAX_LIFE_CANDLES = 480      # tope de seguridad (5 días), NO criterio de estrategia

DEFAULT_PAIRS = [
    "EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY",
]

EVENT_NAMES = ("freno", "extremo", "cruce", "separacion", "martillo")


@dataclass
class Expediente:
    """Una hipótesis viva. Nace con el freno, acumula evidencia, muere por estructura."""

    asset: str
    birth_idx: int
    direction: str          # CALL / PUT
    birth_time: Any
    # evento -> índice de vela en que ocurrió por primera vez
    events: dict[str, int] = field(default_factory=dict)
    # contexto capturado en el nacimiento (causal, Ley 1)
    ctx: dict[str, float] = field(default_factory=dict)
    death_idx: int | None = None
    death_reason: str = ""

    @property
    def alive(self) -> bool:
        return self.death_idx is None

    def firma(self) -> str:
        """Orden REAL en que ocurrieron los eventos. Esta es la gramática a descubrir."""
        got = [(idx, name) for name, idx in self.events.items()]
        got.sort()
        return ">".join(name for _, name in got)

    def completa(self) -> bool:
        """Secuencia completa = freno + cruce + martillo (en cualquier orden)."""
        return {"freno", "cruce", "martillo"}.issubset(self.events)


def _detect_events_at(
    i: int,
    direction: str,
    k: np.ndarray,
    d: np.ndarray,
    kd_dist: np.ndarray,
    hammer: np.ndarray,
    inv_hammer: np.ndarray,
    brake_transition: np.ndarray,
) -> set[str]:
    """Qué eventos nacen en la vela i, para una dirección dada. Ley 4: condición cumplida."""
    out: set[str] = set()
    if not (np.isfinite(k[i]) and np.isfinite(d[i])):
        return out

    if brake_transition[i]:
        out.add("freno")

    # extremo: el estocástico está en la zona que da sentido al giro
    if direction == "CALL" and k[i] <= OVERSOLD:
        out.add("extremo")
    if direction == "PUT" and k[i] >= OVERBOUGHT:
        out.add("extremo")

    # cruce K/D a favor de la dirección (usa i-1: causal)
    if i >= 1 and np.isfinite(k[i - 1]) and np.isfinite(d[i - 1]):
        if direction == "CALL" and k[i - 1] <= d[i - 1] and k[i] > d[i]:
            out.add("cruce")
        if direction == "PUT" and k[i - 1] >= d[i - 1] and k[i] < d[i]:
            out.add("cruce")

    # separación suficiente entre líneas
    if np.isfinite(kd_dist[i]) and kd_dist[i] >= MIN_SEPARATION:
        out.add("separacion")

    # vela de confirmación
    valid = inv_hammer[i] if direction == "CALL" else hammer[i]
    if bool(valid):
        out.add("martillo")

    return out


def _zona_muerta(ki: float, di: float) -> bool:
    """Ley 6 — invalidación: ambas líneas volvieron al centro del rango."""
    if not (np.isfinite(ki) and np.isfinite(di)):
        return False
    return (OVERSOLD < ki < OVERBOUGHT) and (OVERSOLD < di < OVERBOUGHT)


def run_secuencia_libre(
    pairs: list[str] | None = None,
    root: Path = SMC_ROOT,
    expiry: int = EXPIRY_CANDLES,
    verbose: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Recorre las velas y construye expedientes sin imponer orden de eventos.

    Devuelve (expedientes, embudo).
    """
    pairs = list(pairs or DEFAULT_PAIRS)
    rows: list[dict[str, Any]] = []
    funnel: list[dict[str, Any]] = []

    for asset in pairs:
        try:
            df = build_feature_frame(load_m15(asset, root), load_htf(asset, root))
        except Exception as exc:  # datos faltantes
            if verbose:
                print(f"[warn] {asset}: {exc}")
            continue
        if df.empty:
            continue

        o = df["open"].values.astype(float)
        c = df["close"].values.astype(float)
        k = df["k"].values.astype(float)
        d = df["d"].values.astype(float)
        kd_dist = df["kd_dist"].values.astype(float)
        hammer = np.asarray(df["hammer_15m"].values)
        inv_hammer = np.asarray(df["hammer_inv_15m"].values)
        brake_transition = df["brake_transition"].values.astype(bool)
        impulse_net = df["impulse_net"].values.astype(float)
        body_n = df["body_n"].values.astype(float)
        brake_ratio = df["brake_ratio"].values.astype(float)
        rvol = df["rvol"].values.astype(float)
        trend = df["trend"].values.astype(float)
        htf_bias = df["htf_bias"].values.astype(float)
        times = df["time"].values

        n = len(c)
        vivos: list[Expediente] = []
        cerrados: list[Expediente] = []
        nacidos = 0

        for i in range(20, n - expiry - 1):
            # --- 1. Nacimiento: SOLO el freno abre expediente (Ruben) ---
            if brake_transition[i] and np.isfinite(k[i]) and np.isfinite(d[i]):
                direction = "CALL" if impulse_net[i] < 0 else "PUT"
                exp = Expediente(
                    asset=asset,
                    birth_idx=i,
                    direction=direction,
                    birth_time=times[i],
                    ctx={
                        "body_n": float(body_n[i]) if np.isfinite(body_n[i]) else 0.0,
                        "brake_ratio": float(brake_ratio[i]) if np.isfinite(brake_ratio[i]) else 1.0,
                        "rvol": float(rvol[i]) if np.isfinite(rvol[i]) else 1.0,
                        "trend": float(trend[i]) if np.isfinite(trend[i]) else 0.0,
                        "htf_bias": float(htf_bias[i]) if np.isfinite(htf_bias[i]) else 0.0,
                        "k_birth": float(k[i]),
                        "d_birth": float(d[i]),
                        "hour": float(pd.Timestamp(times[i]).hour),
                    },
                )
                exp.events["freno"] = i
                vivos.append(exp)
                nacidos += 1

            if not vivos:
                continue

            # --- 2. Acumular evidencia + invalidar (Ley 2 + Ley 6) ---
            aun_vivos: list[Expediente] = []
            for exp in vivos:
                nuevos = _detect_events_at(
                    i, exp.direction, k, d, kd_dist, hammer, inv_hammer, brake_transition
                )
                for ev in nuevos:
                    if ev not in exp.events:
                        exp.events[ev] = i

                # invalidación estructural: zona muerta (solo después del nacimiento)
                if i > exp.birth_idx and _zona_muerta(k[i], d[i]):
                    exp.death_idx = i
                    exp.death_reason = "zona_muerta"
                    cerrados.append(exp)
                    continue

                if i - exp.birth_idx > MAX_LIFE_CANDLES:
                    exp.death_idx = i
                    exp.death_reason = "max_life"
                    cerrados.append(exp)
                    continue

                # secuencia completa -> se contrata y se cierra
                if exp.completa():
                    exp.death_idx = i
                    exp.death_reason = "completa"
                    cerrados.append(exp)
                    continue

                aun_vivos.append(exp)
            vivos = aun_vivos

        # los que quedaron vivos al final del dataset
        for exp in vivos:
            exp.death_idx = n - 1
            exp.death_reason = "fin_datos"
            cerrados.append(exp)

        # --- 3. Etiquetar (Ley 12: la etiqueta NO alimentó ninguna decisión) ---
        for exp in cerrados:
            entry_idx = None
            win = None
            if exp.death_reason == "completa":
                entry_idx = exp.death_idx + 1  # entra en la vela siguiente al cierre
                if entry_idx is not None and int(entry_idx) + expiry - 1 < n:
                    close_idx = entry_idx + expiry - 1
                    # binaria pura: verde para CALL, roja para PUT
                    verde = c[close_idx] > o[entry_idx]
                    win = int(verde if exp.direction == "CALL" else (not verde))
                else:
                    entry_idx = None

            rows.append({
                "asset": asset,
                "birth_idx": exp.birth_idx,
                "birth_time": exp.birth_time,
                "direction": exp.direction,
                "firma": exp.firma(),
                "n_eventos": len(exp.events),
                "completa": int(exp.completa()),
                "death_reason": exp.death_reason,
                "vida_velas": (exp.death_idx or exp.birth_idx) - exp.birth_idx,
                "entry_idx": entry_idx if entry_idx is not None else -1,
                "win": win if win is not None else -1,
                **{f"idx_{ev}": exp.events.get(ev, -1) for ev in EVENT_NAMES},
                **{f"lag_{ev}": (exp.events[ev] - exp.birth_idx) if ev in exp.events else -1
                   for ev in EVENT_NAMES},
                **exp.ctx,
            })

        funnel.append({
            "asset": asset,
            "nacidos": nacidos,
            "cerrados": len(cerrados),
            "completas": sum(1 for e in cerrados if e.completa()),
            "muertos_zona_muerta": sum(1 for e in cerrados if e.death_reason == "zona_muerta"),
        })
        if verbose:
            f = funnel[-1]
            print(f"  {asset}: nacidos={f['nacidos']} completas={f['completas']} "
                  f"zona_muerta={f['muertos_zona_muerta']}")

    return pd.DataFrame(rows), pd.DataFrame(funnel)
