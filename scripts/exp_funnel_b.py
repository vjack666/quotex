"""EXP-B — VARIANTE de la puerta P2→P3: retorno a extremo CONFIRMADO + K/D a favor.

NO modifica src/. Simula, sobre velas REALES M15 (y M5 sólo como contexto),
el mismo embudo P1→P2→P3 que el Edificio en modo 'return_to_extreme', pero
con dos reglas alternativas de promoción P2→P3:

  BASE  ('return_to_extreme'): el %K vuelve a tocar la línea de extremo de
        entrada (20 para CALL / 80 para PUT) habiendo salido antes de [20,80].
        Un solo tick en zona basta.

  VARIANTE B ('confirmado'): además exige
        1) CONFIRMACIÓN: la vela M15 SIGUIENTE también cierra con %K en la
           misma zona de extremo (no un tick aislado).
        2) K/D A FAVOR del trade: CALL → K subiendo (k > k_prev) y K >= D;
           PUT  → K bajando (k < k_prev) y K <= D.
        Como la confirmación necesita la vela siguiente, la promoción se
        resuelve con 1 vela de retardo (se registra en la vela de confirmación).

Ambas comparten: P1 (payout), P2 (freno confirmado + extremo + no sticky),
ley de permanencia EDIFICIO_P2_MAX_HOLD_VELAS velas, descarte por cruce
pegajoso. Reutiliza compute_stoch_full / derive_flags / is_sticky_cross de
scripts/audit_edificio_funnel.py.

Datos SOLO LECTURA:
    C:/Users/v_jac/Desktop/backtest quotex/datos de velas/data/EURUSD/M15

Uso:
    python scripts/exp_funnel_b.py [AÑO] [PAR]
Salida:
    reports/AUDITORIA_FUNNEL/exp_B_confirmado.md
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import pandas as pd

from audit_edificio_funnel import (  # noqa: E402
    EXT_ROOT,
    compute_stoch_full,
    derive_flags,
    is_sticky_cross,
    load_csv_year,
)

MAX_HOLD_VELAS = 8          # EDIFICIO_P2_MAX_HOLD_VELAS
STICKY_DESCARTE = 2.0       # EDIFICIO_DESCARTE_STICKY_THRESHOLD
BRAKE_RATIO = 0.7           # EDIFICIO_BRAKE_CONFIRM_RATIO


class Sim:
    """Máquina de estados mínima del embudo P1→P2→P3 (una sola tarjeta)."""

    def __init__(self, modo: str):
        self.modo = modo                # "base" | "B"
        self.piso = 1                   # P1: payout siempre OK en la auditoría
        self.extreme = None             # 20.0 / 80.0 de entrada a P2
        self.direction = None
        self.left_zone = False
        self.hold = 0
        self.pending_return = None      # vela índice del toque (variante B)
        self.entries = Counter()
        self.descartes = Counter()
        self.eventos = []               # filas para la tabla del reporte

    # ── helpers ──
    def _reset_p2(self):
        self.extreme = None
        self.direction = None
        self.left_zone = False
        self.hold = 0
        self.pending_return = None

    def _to_p3(self, i, ts, k, d, motivo):
        self.piso = 3
        self.entries[3] += 1
        self.eventos.append({
            "i": i, "ts": ts, "evento": "P2→P3", "dir": self.direction,
            "extremo": self.extreme, "k": round(float(k), 2),
            "d": round(float(d), 2), "motivo": motivo,
        })
        self._reset_p2()
        self.piso = 1  # ciclo cerrado: la tarjeta vuelve a competir desde P1

    def _descartar(self, i, ts, motivo):
        self.descartes[motivo] += 1
        self.eventos.append({
            "i": i, "ts": ts, "evento": "DESCARTE", "dir": self.direction,
            "extremo": self.extreme, "k": "", "d": "", "motivo": motivo,
        })
        self._reset_p2()
        self.piso = 1

    # ── un paso = una vela M15 cerrada ──
    def step(self, i, ts, k, d, k_prev, direction, cross_sticky,
             extreme_ok, brake_ok, k_next, k_next_prev):
        if self.piso == 1:
            # P1→P2: freno confirmado + extremo
            if brake_ok and extreme_ok and direction:
                if is_sticky_cross(k, d, STICKY_DESCARTE):
                    self.descartes["cruce pegajoso al entrar a P2 (|K-D|<2.0)"] += 1
                    return
                self.piso = 2
                self.entries[2] += 1
                self.direction = direction
                self.extreme = 20.0 if direction == "CALL" else 80.0
                self.left_zone = False
                self.hold = 0
                self.pending_return = None
            return

        # piso == 2
        self.hold += 1
        in_zone = 20.0 <= float(k) <= 80.0
        if not in_zone:
            self.left_zone = True

        toque = False
        if self.extreme == 20.0 and float(k) <= 20.0 and self.left_zone:
            toque = True
        if self.extreme == 80.0 and float(k) >= 80.0 and self.left_zone:
            toque = True

        if toque:
            if self.modo == "base":
                self._to_p3(i, ts, k, d, f"retorno a extremo {self.extreme:.0f}")
                return
            # ── VARIANTE B ──
            # 1) confirmación con la vela siguiente en la misma zona
            if k_next is None or pd.isna(k_next):
                self.descartes["sin vela siguiente para confirmar"] += 1
            else:
                conf = (self.extreme == 20.0 and float(k_next) <= 20.0) or \
                       (self.extreme == 80.0 and float(k_next) >= 80.0)
                if not conf:
                    self.descartes["retorno NO confirmado (tick aislado)"] += 1
                else:
                    # 2) K/D en dirección del trade, medido en la vela de confirmación
                    kd_ok = False
                    if self.direction == "CALL":
                        kd_ok = float(k_next) > float(k_next_prev) and float(k_next) >= float(d)
                    else:
                        kd_ok = float(k_next) < float(k_next_prev) and float(k_next) <= float(d)
                    if kd_ok:
                        self._to_p3(i + 1, ts, k_next, d,
                                    f"retorno CONFIRMADO a {self.extreme:.0f} + K/D a favor")
                        return
                    self.descartes["K/D en contra del trade"] += 1
            # el toque no promovió: sigue en P2 hasta agotar permanencia

        if self.hold >= MAX_HOLD_VELAS:
            self._descartar(i, ts, f"sin retorno válido en {MAX_HOLD_VELAS} velas M15")


def run(m15: pd.DataFrame, modo: str) -> Sim:
    sim = Sim(modo)
    n = len(m15)
    ks = m15["k"].tolist()
    ds = m15["d"].tolist()
    hi = m15["high"].tolist()
    lo = m15["low"].tolist()
    ts = m15["ts"].tolist()
    for i in range(1, n):
        k, d = ks[i], ds[i]
        if pd.isna(k) or pd.isna(d):
            continue
        k_prev, d_prev = ks[i - 1], ds[i - 1]
        flags = derive_flags(k, d, k_prev, d_prev)
        if flags is None:
            continue
        direction, _cross_ok, extreme_ok = flags
        cross_sticky = is_sticky_cross(k, d, 3.0)
        rng = hi[i] - lo[i]
        rng_prev = hi[i - 1] - lo[i - 1]
        brake_ok = rng_prev > 0 and rng < rng_prev * BRAKE_RATIO
        k_next = ks[i + 1] if i + 1 < n else None
        sim.step(i, ts[i], k, d, k_prev, direction, cross_sticky,
                 extreme_ok, brake_ok, k_next, k)
    return sim


def main() -> int:
    year = sys.argv[1] if len(sys.argv) > 1 else "2024"
    par = sys.argv[2] if len(sys.argv) > 2 else "EURUSD"

    m15 = load_csv_year(EXT_ROOT / par / "M15", year)
    ks, ds = compute_stoch_full(m15["high"].tolist(), m15["low"].tolist(),
                                m15["close"].tolist())
    m15["k"] = ks
    m15["d"] = ds
    print(f"[EXP-B] {par} {year}: M15={len(m15)} velas")

    base = run(m15, "base")
    varb = run(m15, "B")

    out_dir = ROOT / "reports" / "AUDITORIA_FUNNEL"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "exp_B_confirmado.md"

    def blk(s: Sim, nombre: str) -> str:
        t = [f"### {nombre}", "",
             f"- Entradas a P2: **{s.entries[2]}**",
             f"- Promociones P2→P3: **{s.entries[3]}**",
             f"- Tasa P2→P3: **{100.0 * s.entries[3] / max(1, s.entries[2]):.2f}%**",
             f"- Descartes totales: **{sum(s.descartes.values())}**", "",
             "| motivo de descarte | conteo |", "|---|---:|"]
        for m, c in s.descartes.most_common():
            t.append(f"| {m} | {c} |")
        return "\n".join(t) + "\n"

    lines = [
        f"# EXP-B — Puerta P2→P3 con retorno CONFIRMADO + K/D a favor ({par} {year})",
        "",
        "Simulación independiente (scripts/exp_funnel_b.py). **No se modificó `src/`.**",
        f"Datos M15 reales: `{EXT_ROOT / par / 'M15' / (year + '.csv')}` ({len(m15)} velas, solo lectura).",
        "",
        "## Reglas comparadas", "",
        "- **BASE (`return_to_extreme`)**: %K vuelve a tocar la línea de extremo de entrada (20 CALL / 80 PUT) habiendo salido antes de [20,80]. Un tick basta.",
        "- **VARIANTE B (`confirmado`)**: además (1) la vela M15 siguiente debe seguir en la misma zona extremo, y (2) K/D en dirección del trade (CALL: K subiendo y K≥D; PUT: K bajando y K≤D).",
        "",
        "Común a ambas: P1→P2 exige freno confirmado (rango < 0.7×rango previo) + extremo + no-sticky (|K−D|≥2.0); ley de permanencia de 8 velas M15.",
        "",
        "## Conteos del embudo", "",
        blk(base, "BASE — return_to_extreme"),
        blk(varb, "VARIANTE B — retorno confirmado + K/D a favor"),
        "## Comparativa", "",
        "| métrica | BASE | VARIANTE B | Δ |", "|---|---:|---:|---:|",
        f"| entradas P2 | {base.entries[2]} | {varb.entries[2]} | {varb.entries[2] - base.entries[2]} |",
        f"| promociones P3 | {base.entries[3]} | {varb.entries[3]} | {varb.entries[3] - base.entries[3]} |",
        f"| tasa P2→P3 | {100.0*base.entries[3]/max(1,base.entries[2]):.2f}% | {100.0*varb.entries[3]/max(1,varb.entries[2]):.2f}% | {100.0*varb.entries[3]/max(1,varb.entries[2]) - 100.0*base.entries[3]/max(1,base.entries[2]):+.2f} pp |",
        f"| descartes | {sum(base.descartes.values())} | {sum(varb.descartes.values())} | {sum(varb.descartes.values()) - sum(base.descartes.values())} |",
        "",
        "## Muestra de eventos (primeros 30 de la VARIANTE B)", "",
        "| # | fecha (UTC) | evento | dir | extremo | K | D | motivo |",
        "|---|---|---|---|---:|---:|---:|---|",
    ]
    for e in varb.eventos[:30]:
        lines.append(f"| {e['i']} | {e['ts']} | {e['evento']} | {e['dir']} | "
                     f"{e['extremo']} | {e['k']} | {e['d']} | {e['motivo']} |")

    ratio_b = varb.entries[3] / max(1, base.entries[3])
    veredicto = ("FLUYE MENOS" if varb.entries[3] < base.entries[3]
                 else ("FLUYE IGUAL" if varb.entries[3] == base.entries[3] else "FLUYE MÁS"))
    lines += [
        "", "## Veredicto honesto", "",
        f"La variante B **{veredicto}** que la base: {varb.entries[3]} promociones a P3 "
        f"frente a {base.entries[3]} ({ratio_b*100:.1f}% del flujo base).",
        "",
        "Razón mecánica: la base promueve con un **único toque** de %K en la línea de "
        "extremo, que es un evento frecuente porque el estocástico oscila con rapidez. "
        "La variante añade dos filtros en serie sobre ese mismo toque: la vela siguiente "
        "debe permanecer en la zona (elimina los toques-aguja de una sola vela) y K/D "
        "debe girar a favor del trade en esa vela de confirmación. Ambos filtros sólo "
        "pueden restar eventos, nunca añadirlos, y como el tiempo de espera sigue "
        "acotado por la ley de permanencia (8 velas), los toques no confirmados no "
        "obtienen segunda oportunidad dentro del mismo ciclo salvo que reaparezcan.",
        "",
        "Interpretación de embudo (no de win rate): el tapón P2→P3 se **estrecha**. "
        "Esta auditoría NO mide si los eventos supervivientes son mejores; sólo "
        "cuantifica el caudal. Para decidir si el filtro compensa hace falta un "
        "experimento de resultado, no de embudo.",
        "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")

    print(f"BASE : P2={base.entries[2]} P3={base.entries[3]} descartes={sum(base.descartes.values())}")
    print(f"VAR B: P2={varb.entries[2]} P3={varb.entries[3]} descartes={sum(varb.descartes.values())}")
    for m, c in varb.descartes.most_common():
        print(f"   {c:6d}  {m}")
    print(f"[MD] {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
