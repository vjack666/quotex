#!/usr/bin/env python
"""Pipeline auditor OFFLINE de rechazos de STRAT-F.

Investiga POR QUE el bot rechaza entradas y si los rechazos "zona muy joven"
luego se reusaron (maduraron) via la maturing_watchlist -> promocion
SHADOW_PROMOTED / ACCEPTED.

DISENO offline-first (Ruben 2026-07-25):
- La ETAPA de analisis NO necesita red: lee scan_candidates (candles/stoch ya
  guardados) y los CSV que se bajen a data/rechazos/.
- La ETAPA download (--mode download) es OPCIONAL y separada: requiere un
  cliente Quotex logueado (cuenta DEMO/PRACTICE). Usa
  connection.fetch_candles (NO se inventa API).

Etapas (--mode):
  extract  -> lee rechazos, agrupa por reject_reason, y CRUZA rechazo->promocion
              por (asset, direction, ventana +N min, y band EXACTO si existe).
  analyze  -> clasifica cada rechazo con el stoch guardado + precio posterior.
  download -> (opcional, red) baja histgrico +/- ventana a data/rechazos/CSV.
  report   -> genera data/rechazos/informe_audit.md (texto plano, legible).
  all      -> extract + analyze + report sobre datos locales (sin download).

Uso:
  .venv/Scripts/python.exe scripts/audit_rechazos.py --mode extract
  .venv/Scripts/python.exe scripts/audit_rechazos.py --db data/db/black_box_strat_2026-07-25.db --mode all
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sqlite3
from collections import defaultdict
from typing import Any, Optional

# --- constantes ------------------------------------------------------------
_BAND_DECIMALS = 5  # igual que maturing_watchlist.round_band
DEFAULT_WINDOW_MIN = 90       # ventana +N min para buscar la 2a oportunidad
FORWARD_PRICE_MIN = 180       # +3h para juzgar "precio a favor" (RECHAZO_MUYDURO)
YOUNG_REASON_HINTS = ("zona muy joven", "zone too young")

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_OUT_DIR = os.path.join(_ROOT, "data", "rechazos")


# --- helpers ---------------------------------------------------------------
def round_band(band: Optional[float]) -> Optional[float]:
    """Redondea el band a 5 decimales (misma clave que la watchlist)."""
    if band is None:
        return None
    try:
        return round(float(band), _BAND_DECIMALS)
    except (TypeError, ValueError):
        return None


def _latest_db() -> Optional[str]:
    """Devuelve la black_box_strat_*.db mas reciente en data/db."""
    cands = glob.glob(os.path.join(_ROOT, "data", "db", "black_box_strat*.db"))
    if not cands:
        return None
    return sorted(cands)[-1]


def _has_band_column(con: sqlite3.Connection) -> bool:
    cols = [r[1] for r in con.execute("PRAGMA table_info(scan_candidates)")]
    return "band" in cols


def _is_young(reason: Optional[str]) -> bool:
    r = (reason or "").lower()
    return any(h in r for h in YOUNG_REASON_HINTS)


def _load_rows(con: sqlite3.Connection, limit: Optional[int] = None) -> list[dict]:
    """Lee scan_candidates de STRAT-F como lista de dicts (con band si existe)."""
    has_band = _has_band_column(con)
    band_sql = "band" if has_band else "NULL AS band"
    sql = (
        f"SELECT id, ts, asset, direction, score, decision, reject_reason, "
        f"strategy_details, stoch_m15, stoch_m5, stoch_m1, candles_15m, {band_sql} "
        f"FROM scan_candidates WHERE strategy = 'STRAT-F' ORDER BY ts ASC"
    )
    if limit:
        sql += f" LIMIT {int(limit)}"
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(sql)]
    con.row_factory = None
    return rows


# --- ETAPA extract ---------------------------------------------------------
def stage_extract(rows: list[dict], window_min: int = DEFAULT_WINDOW_MIN) -> dict:
    """Agrupa rechazos por motivo y cruza rechazo->promocion.

    Cruce: para cada REJECTED_%, busca una promocion (SHADOW_PROMOTED/ACCEPTED)
    del MISMO asset+direction, con ts posterior dentro de +window_min, y — si
    ambos tienen band — con band EXACTO (round a 5 decimales). Cuenta esas
    'segundas oportunidades concretadas'.
    """
    rejects = [r for r in rows if (r["decision"] or "").startswith("REJECTED")]
    promos = [r for r in rows if r["decision"] in ("SHADOW_PROMOTED", "ACCEPTED")]

    # indice de promociones por (asset, direction)
    promo_idx: dict[tuple, list[dict]] = defaultdict(list)
    for p in promos:
        promo_idx[(p["asset"], (p["direction"] or "").upper())].append(p)

    by_reason: dict[str, dict] = defaultdict(
        lambda: {"total": 0, "matured": 0, "matured_exact_band": 0, "young": 0}
    )
    matched_ids: list[dict] = []
    win_sec = window_min * 60

    for rej in rejects:
        reason = rej["reject_reason"] or "(sin motivo)"
        slot = by_reason[reason]
        slot["total"] += 1
        young = _is_young(reason)
        if young:
            slot["young"] += 1
        key = (rej["asset"], (rej["direction"] or "").upper())
        rej_band = round_band(rej.get("band"))
        best = None
        for p in promo_idx.get(key, []):
            if p["ts"] <= rej["ts"]:
                continue
            if p["ts"] - rej["ts"] > win_sec:
                continue
            exact = False
            if rej_band is not None:
                p_band = round_band(p.get("band"))
                if p_band is not None and p_band == rej_band:
                    exact = True
                elif p_band is not None and p_band != rej_band:
                    # band presente en ambos pero distinto -> no es el mismo nivel
                    continue
            if best is None or p["ts"] < best[0]["ts"]:
                best = (p, exact)
        if best is not None:
            slot["matured"] += 1
            if best[1]:
                slot["matured_exact_band"] += 1
            matched_ids.append({
                "reject_id": rej["id"], "reason": reason,
                "asset": rej["asset"], "direction": rej["direction"],
                "promo_id": best[0]["id"], "promo_decision": best[0]["decision"],
                "exact_band": best[1],
            })

    return {
        "total_rejects": len(rejects),
        "total_promos": len(promos),
        "by_reason": dict(by_reason),
        "matched": matched_ids,
        "has_band": any(r.get("band") is not None for r in rows),
    }


# --- ETAPA analyze ---------------------------------------------------------
def _parse_json(s: Any) -> Any:
    if not s:
        return None
    if isinstance(s, (dict, list)):
        return s
    try:
        return json.loads(s)
    except (ValueError, TypeError):
        return None


def _price_favorable(candles_15m: list, direction: str, ref_close: Optional[float]) -> Optional[bool]:
    """¿El precio fue 'a favor' del rechazo en las velas posteriores guardadas?

    CALL -> favorable si algun high posterior supera ref_close.
    PUT  -> favorable si algun low posterior baja de ref_close.
    Retorna None si no hay datos suficientes (INCIERTO).
    """
    if not candles_15m or ref_close is None:
        return None
    d = (direction or "").upper()
    highs = [c.get("h") for c in candles_15m if isinstance(c, dict)]
    lows = [c.get("l") for c in candles_15m if isinstance(c, dict)]
    if d == "CALL":
        hs = [h for h in highs if h is not None]
        return (max(hs) > ref_close) if hs else None
    if d == "PUT":
        ls = [l for l in lows if l is not None]
        return (min(ls) < ref_close) if ls else None
    return None


def stage_analyze(rows: list[dict], extract_res: dict) -> dict:
    """Clasifica cada rechazo: CORRECTO | MUYDURO | INCIERTO.

    - RECHAZO_MUYDURO: NUNCA reusado (no maduro) Y el precio fue a favor en la
      ventana posterior (candles_15m guardadas). Candidato a suavizar el umbral.
    - RECHAZO_CORRECTO: maduro (2a oportunidad) O precio NO fue a favor.
    - INCIERTO: sin datos de precio posterior.
    """
    matured_ids = {m["reject_id"] for m in extract_res["matched"]}
    counts = {"CORRECTO": 0, "MUYDURO": 0, "INCIERTO": 0}
    detail: list[dict] = []

    for r in rows:
        if not (r["decision"] or "").startswith("REJECTED"):
            continue
        candles = _parse_json(r.get("candles_15m")) or []
        ref = None
        if candles and isinstance(candles[-1], dict):
            # las candles_15m guardadas son las previas al ts; ref = ultimo close
            ref = candles[-1].get("c")
        fav = _price_favorable(candles, r["direction"] or "", ref)
        reused = r["id"] in matured_ids
        if fav is None:
            cls = "INCIERTO"
        elif (not reused) and fav:
            cls = "MUYDURO"
        else:
            cls = "CORRECTO"
        counts[cls] += 1
        detail.append({
            "id": r["id"], "asset": r["asset"], "direction": r["direction"],
            "reason": r["reject_reason"], "reused": reused,
            "price_favorable": fav, "class": cls,
        })
    return {"counts": counts, "detail": detail}


# --- ETAPA download (opcional, red) ---------------------------------------
def stage_download(rows: list[dict], out_dir: str) -> dict:
    """Baja histrico +/- ventana para los activos rechazados via API demo.

    REQUIERE un cliente Quotex logueado. Se ejecuta SOLO si se llama
    explicitamente con --mode download. No se toca en modo 'all'.
    """
    import asyncio

    # imports perezosos: solo cuando de verdad hay red
    import sys
    sys.path.insert(0, os.path.join(_ROOT, "src"))
    from connection import fetch_candles  # noqa: E402
    from consolidation_bot import build_client  # type: ignore  # noqa: E402

    os.makedirs(out_dir, exist_ok=True)
    assets = sorted({r["asset"] for r in rows
                     if (r["decision"] or "").startswith("REJECTED")})

    async def _run():
        client = build_client(demo=True)
        await client.connect()
        saved = []
        for asset in assets:
            try:
                # 1 dia antes + margen: 24h*60/15 ~ 96 velas M15 + 12 (3h)
                candles = await fetch_candles(client, asset, 900, 120)
                path = os.path.join(out_dir, f"{asset.replace('/', '_')}_m15.csv")
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write("ts,open,high,low,close\n")
                    for c in candles:
                        fh.write(f"{c.ts},{c.open},{c.high},{c.low},{c.close}\n")
                saved.append(path)
            except Exception as exc:  # pragma: no cover - red
                print(f"[download] fallo {asset}: {exc}")
        return saved

    saved = asyncio.run(_run())
    return {"assets": assets, "saved": saved}


# --- ETAPA report ----------------------------------------------------------
def _threshold_suggestion(by_reason: dict) -> list[str]:
    """Sugerencias de umbrales con evidencia (dumi = espanol plano)."""
    out = []
    for reason, s in sorted(by_reason.items(), key=lambda x: -x[1]["total"]):
        if _is_young(reason) and s["total"] > 0:
            pct = 100.0 * s["matured"] / s["total"] if s["total"] else 0.0
            out.append(
                f"- 'zona muy joven': de {s['total']} rechazos, {s['matured']} "
                f"({pct:.0f}%) SI maduraron mas tarde. Si el % es alto, la barrera "
                f"de 3 velas M5 esta cortando entradas buenas: probar bajarla a 2 "
                f"velas M5 y medir winrate en DEMO antes de fijar."
            )
    if not out:
        out.append("- Sin senal fuerte para bajar umbrales: pocos rechazos maduraron.")
    return out


def stage_report(extract_res: dict, analyze_res: Optional[dict], out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "informe_audit.md")
    L: list[str] = []
    A = L.append

    A("AUDITORIA DE RECHAZOS - STRAT-F (offline)")
    A("=" * 50)
    A("")
    A(f"Total rechazos analizados : {extract_res['total_rejects']}")
    A(f"Total promociones (2a op) : {extract_res['total_promos']}")
    A(f"Columna 'band' disponible : {'SI' if extract_res['has_band'] else 'NO (datos viejos)'}")
    A("")
    A("POR MOTIVO DE RECHAZO")
    A("-" * 50)
    for reason, s in sorted(extract_res["by_reason"].items(), key=lambda x: -x[1]["total"]):
        pct = 100.0 * s["matured"] / s["total"] if s["total"] else 0.0
        A(f"* {reason}")
        A(f"    total={s['total']}  maduraron(2a op)={s['matured']} ({pct:.0f}%)"
          f"  con band EXACTO={s['matured_exact_band']}")
    A("")

    if analyze_res:
        c = analyze_res["counts"]
        A("CLASIFICACION (precio posterior guardado)")
        A("-" * 50)
        A(f"  RECHAZO_CORRECTO : {c['CORRECTO']}  (bien rechazado o ya reusado)")
        A(f"  RECHAZO_MUYDURO  : {c['MUYDURO']}   (nunca reusado + precio fue a favor -> suavizable)")
        A(f"  INCIERTO         : {c['INCIERTO']}  (sin datos de precio posterior; usar --download)")
        A("")

    A("EN PLANO (dumi): QUE SIGNIFICA")
    A("-" * 50)
    A("El bot rechaza cuando la zona (soporte/resistencia) es muy 'nueva': aun")
    A("no tiene suficientes velas M5 confirmandola. La maturing_watchlist guarda")
    A("esas zonas jovenes y, si maduran, las vuelve a intentar (SHADOW o LIVE).")
    A("Si muchos rechazos 'zona muy joven' terminan madurando Y el precio se")
    A("movio a favor, la barrera es demasiado dura y estamos dejando pasar")
    A("entradas buenas.")
    A("")
    A("SUGERENCIAS DE UMBRAL (con evidencia)")
    A("-" * 50)
    for line in _threshold_suggestion(extract_res["by_reason"]):
        A(line)
    A("")

    text = "\n".join(L)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return text


# --- CLI -------------------------------------------------------------------
def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Auditor OFFLINE de rechazos STRAT-F")
    ap.add_argument("--db", default=None, help="Ruta a la black_box_strat_*.db (default: mas reciente)")
    ap.add_argument("--mode", default="all",
                    choices=["extract", "download", "analyze", "report", "all"])
    ap.add_argument("--window-min", type=int, default=DEFAULT_WINDOW_MIN,
                    help="Ventana +N min para cruzar rechazo->promocion")
    ap.add_argument("--limit", type=int, default=None, help="Limitar filas leidas (debug)")
    ap.add_argument("--out", default=_OUT_DIR, help="Directorio de salida")
    args = ap.parse_args(argv)

    db = args.db or _latest_db()
    if not db or not os.path.exists(db):
        print(f"[ERROR] No se encontro DB: {db}")
        return 2
    print(f"[audit] DB: {db}  mode={args.mode}")

    con = sqlite3.connect(db)
    try:
        rows = _load_rows(con, limit=args.limit)
    finally:
        con.close()
    print(f"[audit] filas STRAT-F leidas: {len(rows)}")

    if args.mode == "download":
        res = stage_download(rows, args.out)
        print(f"[download] activos={len(res['assets'])} guardados={len(res['saved'])}")
        return 0

    extract_res = stage_extract(rows, window_min=args.window_min)
    print(f"[extract] rechazos={extract_res['total_rejects']} "
          f"promos={extract_res['total_promos']} "
          f"motivos={len(extract_res['by_reason'])}")
    for reason, s in sorted(extract_res["by_reason"].items(), key=lambda x: -x[1]["total"])[:8]:
        print(f"  - {reason}: total={s['total']} maduraron={s['matured']} "
              f"(exact_band={s['matured_exact_band']})")

    if args.mode == "extract":
        return 0

    analyze_res = stage_analyze(rows, extract_res)
    print(f"[analyze] {analyze_res['counts']}")

    if args.mode == "analyze":
        return 0

    text = stage_report(extract_res, analyze_res, args.out)
    print(f"[report] escrito en {os.path.join(args.out, 'informe_audit.md')}")
    if args.mode in ("report", "all"):
        print("\n" + text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
