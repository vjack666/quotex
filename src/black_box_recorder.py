"""
BLACK BOX RECORDER - Captura completa de estrategias A, B, C
============================================================

Sistema exhaustivo que registra CADA escaneo, decisión y resultado:
- Todo lo que ve cada estrategia
- Todas las métricas calculadas
- Razones de aceptación/rechazo
- Snapshots de velas
- Histórico completo para análisis posterior

Almacenamiento: SQLite + JSON exports
"""

import json
import sqlite3
import os
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

log = logging.getLogger("black_box_recorder")

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_DIR = DATA_DIR / "db"
EXPORTS_DIR = DATA_DIR / "exports" / "black_box"
LOGS_DIR = DATA_DIR / "logs" / "black_box"

for d in [DB_DIR, EXPORTS_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

TODAY = datetime.now().strftime("%Y-%m-%d")
BLACK_BOX_DB = DB_DIR / f"black_box_strat_{TODAY}.db"
BLACK_BOX_LOG = LOGS_DIR / f"black_box_{TODAY}.jsonl"


# ─────────────────────────────────────────────────────────────────────────────
#  DDL - SCHEMA COMPLETO
# ─────────────────────────────────────────────────────────────────────────────

_DDL_SCANS = """
CREATE TABLE IF NOT EXISTS scans (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              REAL NOT NULL,
    ts_iso          TEXT NOT NULL,
    strategy        TEXT NOT NULL,          -- A | B | C
    scan_number     INTEGER,
    total_candidates INTEGER DEFAULT 0,
    
    -- Contexto de mercado
    market_state    TEXT,                   -- trending | consolidating | ranging
    volatility_atr  REAL,
    
    -- Resultado del escaneo
    found_count     INTEGER DEFAULT 0,      -- candidatos encontrados
    accepted_count  INTEGER DEFAULT 0,
    rejected_count  INTEGER DEFAULT 0,
    
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scan_candidates (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id         INTEGER NOT NULL,
    ts              REAL NOT NULL,
    strategy        TEXT NOT NULL,          -- A | B | C
    
    -- Identificación
    asset           TEXT NOT NULL,
    direction       TEXT NOT NULL,          -- call | put
    
    -- Scores y métricas
    score           REAL,
    confidence      REAL,
    payout          INTEGER,
    
    -- Decisión
    decision        TEXT NOT NULL,          -- ACCEPTED | REJECTED_SCORE | etc
    decision_reason TEXT,
    reject_reason   TEXT,
    
    -- Detalles específicos por estrategia
    strategy_details TEXT,                  -- JSON con detalles específicos
    
    -- Velas snapshot (JSON)
    candles_1m      TEXT,                   -- últimas 5 velas 1m
    candles_5m      TEXT,                   -- últimas 3 velas 5m
    candles_15m     TEXT,                   -- últimas velas 15m (contexto estocástico)
    candles_post    TEXT,                   -- 3-5 velas 1m post-cierre (post-mortem)
    
    -- Resultado (si fue aceptado)
    order_id        TEXT,
    order_result    TEXT,                   -- WIN | LOSS | PENDING | EXPIRED
    profit          REAL,
    entry_price     REAL,                   -- open 1m al entrar
    exit_price      REAL,                   -- precio al expiry
    masaniello_snapshot TEXT,               -- JSON con estado Masaniello al cerrar
    
    -- Contexto estocástico M15 y sesión
    session_id      TEXT,                   -- ciclo Massaniello
    stoch_m15       TEXT,                   -- JSON {k, d, estado, cruce, divergencia}
    stoch_contradicts INTEGER DEFAULT 0,    -- 1 si el estocástico va contra la dirección
    
    -- Post-mortem automático
    loss_reason     TEXT,                   -- por qué perdió (ANTES vs resultado)
    improvement_hint TEXT,                  -- sugerencia de calibración derivada de datos
    extreme_read    INTEGER DEFAULT 0,      -- 1 si la señal pasó por el extreme-read gate (STRAT-F)

    -- Order expiry used for multi-duration A/B data collection
    duration_sec    INTEGER,
    
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY(scan_id) REFERENCES scans(id)
);

CREATE TABLE IF NOT EXISTS strategy_metrics (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              REAL NOT NULL,
    strategy        TEXT NOT NULL,          -- A | B | C
    
    -- Acumulado
    total_scans     INTEGER DEFAULT 0,
    total_candidates INTEGER DEFAULT 0,
    total_accepted  INTEGER DEFAULT 0,
    
    -- Performance
    wins            INTEGER DEFAULT 0,
    losses          INTEGER DEFAULT 0,
    pending         INTEGER DEFAULT 0,
    win_rate        REAL,
    pnl             REAL,
    
    -- Últimos valores
    last_decision   TEXT,
    last_asset      TEXT,
    
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS phase_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              REAL NOT NULL,
    ts_iso          TEXT NOT NULL,
    strategy        TEXT NOT NULL,
    asset           TEXT,
    
    phase           TEXT NOT NULL,          -- signal_detected | scored | filtered | accepted | rejected
    message         TEXT,
    
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS maintenance_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              REAL NOT NULL,
    ts_iso          TEXT NOT NULL,
    category        TEXT NOT NULL,          -- HTF_LIBRARY | VIP_LIBRARY | SPIKE_FILTER | etc
    subtype         TEXT NOT NULL,          -- REFRESH | ENTER | EXIT | PURGE | SUMMARY
    asset           TEXT,
    severity        TEXT DEFAULT 'INFO',
    payload_json    TEXT,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


# ─────────────────────────────────────────────────────────────────────────────
#  BLACK BOX RECORDER CLASS
# ─────────────────────────────────────────────────────────────────────────────

class BlackBoxRecorder:
    """Registra TODA la actividad de las estrategias."""
    
    RETENTION_DAYS = 30  # Caducidad: 1 mes

    def __init__(self):
        self.db_path = BLACK_BOX_DB
        self.log_path = BLACK_BOX_LOG
        self._init_db()
        self._cleanup_old_files()
    
    def _init_db(self) -> None:
        """Crea tablas si no existen."""
        try:
            con = sqlite3.connect(self.db_path)
            con.executescript(_DDL_SCANS)
            # Migración ligera para DBs existentes del día.
            cols = [
                str(row[1]).lower()
                for row in con.execute("PRAGMA table_info(scan_candidates)").fetchall()
            ]
            if "masaniello_snapshot" not in cols:
                con.execute("ALTER TABLE scan_candidates ADD COLUMN masaniello_snapshot TEXT")
            # Migración caja negra STRAT-F + estocástico M15 (idempotente)
            _NEW_COLS = [
                "candles_15m", "candles_post", "entry_price", "exit_price",
                "session_id", "stoch_m15", "stoch_contradicts",
                "loss_reason", "improvement_hint", "duration_sec",
                "stoch_m5", "filter_funnel",
            ]
            existing = set(cols)
            for col in _NEW_COLS:
                if col not in existing:
                    if col == "stoch_contradicts":
                        _ctype = "INTEGER DEFAULT 0"
                    elif col == "duration_sec":
                        _ctype = "INTEGER"
                    else:
                        _ctype = "TEXT"
                    con.execute(f"ALTER TABLE scan_candidates ADD COLUMN {col} {_ctype}")
            maintenance_cols = [
                str(row[1]).lower()
                for row in con.execute("PRAGMA table_info(maintenance_log)").fetchall()
            ]
            if not maintenance_cols:
                con.execute(
                    """
                    CREATE TABLE IF NOT EXISTS maintenance_log (
                        id              INTEGER PRIMARY KEY AUTOINCREMENT,
                        ts              REAL NOT NULL,
                        ts_iso          TEXT NOT NULL,
                        category        TEXT NOT NULL,
                        subtype         TEXT NOT NULL,
                        asset           TEXT,
                        severity        TEXT DEFAULT 'INFO',
                        payload_json    TEXT,
                        created_at      TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            con.commit()
            con.close()
        except Exception as e:
            print(f"❌ Error inicializando DB: {e}")

    def _cleanup_old_files(self) -> None:
        """Elimina archivos DB y JSONL de caja negra con más de RETENTION_DAYS."""
        try:
            cutoff = datetime.now() - timedelta(days=self.RETENTION_DAYS)
            cutoff_str = cutoff.strftime("%Y-%m-%d")
            removed = 0
            for folder in [DB_DIR, LOGS_DIR]:
                if not hasattr(folder, "exists") or not folder.exists():
                    continue
                for f in folder.iterdir():
                    if not f.is_file():
                        continue
                    import re
                    match = re.search(r"(\d{4}-\d{2}-\d{2})", f.name)
                    if not match:
                        continue
                    date_str = match.group(1)
                    if date_str < cutoff_str:
                        try:
                            f.unlink()
                            removed += 1
                        except Exception:
                            pass
            if removed:
                log.info("🧹 Caja negra: %d archivos antiguos eliminados (>%d días)", removed, self.RETENTION_DAYS)
        except Exception:
            pass  # Silently skip cleanup in test environments
    
    def record_scan_start(
        self,
        strategy: str,
        scan_number: int,
        market_context: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Registra el inicio de un escaneo. Retorna scan_id."""
        ts = datetime.now(timezone.utc).timestamp()
        ts_iso = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

        market_state = market_context.get("market_state", "unknown") if market_context else "unknown"
        volatility = market_context.get("volatility_atr", 0.0) if market_context else 0.0

        con = sqlite3.connect(self.db_path)
        cur = con.cursor()
        cur.execute('''
            INSERT INTO scans (ts, ts_iso, strategy, scan_number, market_state, volatility_atr)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (ts, ts_iso, strategy, scan_number, market_state, volatility))
        con.commit()
        scan_id = int(cur.lastrowid or 0)
        con.close()

        # Log a JSONL
        self._log_jsonl({
            "event": "scan_start",
            "ts": ts,
            "ts_iso": ts_iso,
            "strategy": strategy,
            "scan_number": scan_number,
            "market_state": market_state,
            "volatility": volatility,
        })

        return scan_id
    
    def record_candidate(self, scan_id: int, strategy: str, data: Dict[str, Any]) -> int:
        """Registra un candidato escaneado y retorna su id."""
        ts = datetime.now(timezone.utc).timestamp()
        
        con = sqlite3.connect(self.db_path)
        cur = con.cursor()
        
        # Extraer campos
        asset = data.get("asset", "")
        direction = data.get("direction", "")
        score = data.get("score", 0.0)
        confidence = data.get("confidence", 0.0)
        payout = data.get("payout", 0)
        decision = data.get("decision", "")
        decision_reason = data.get("decision_reason", "")
        reject_reason = data.get("reject_reason", "")
        order_id = data.get("order_id", None)  # ← Use None instead of ""
        
        # Detalles específicos por estrategia (JSON)
        strategy_details = json.dumps(data.get("strategy_details", {}), ensure_ascii=False)
        
        # Velas (JSON)
        candles_1m = json.dumps(data.get("candles_1m", []), ensure_ascii=False) if data.get("candles_1m") else None
        candles_5m = json.dumps(data.get("candles_5m", []), ensure_ascii=False) if data.get("candles_5m") else None
        candles_15m = json.dumps(data.get("candles_15m", []), ensure_ascii=False) if data.get("candles_15m") else None
        session_id = data.get("session_id", None)
        stoch_m15 = json.dumps(data.get("stoch_m15", {}), ensure_ascii=False) if data.get("stoch_m15") else None
        stoch_m5 = json.dumps(data.get("stoch_m5", {}), ensure_ascii=False) if data.get("stoch_m5") else None
        filter_funnel = json.dumps(data.get("filter_funnel", []), ensure_ascii=False) if data.get("filter_funnel") else None
        duration_sec = data.get("duration_sec", None)
        if duration_sec is not None:
            duration_sec = int(duration_sec)
        extreme_read = int(data.get("extreme_read", 0) or 0)

        cur.execute('''
            INSERT INTO scan_candidates 
            (scan_id, ts, strategy, asset, direction, score, confidence, payout,
             decision, decision_reason, reject_reason, strategy_details, candles_1m, candles_5m,
             candles_15m, session_id, stoch_m15, stoch_m5, filter_funnel, order_id, duration_sec,
             extreme_read)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            scan_id, ts, strategy, asset, direction, score, confidence, payout,
            decision, decision_reason, reject_reason, strategy_details, candles_1m, candles_5m,
            candles_15m, session_id, stoch_m15, stoch_m5, filter_funnel, order_id, duration_sec,
            extreme_read
        ))
        candidate_id = int(cur.lastrowid or 0)
        con.commit()
        con.close()
        
        # Log a JSONL
        self._log_jsonl({
            "event": "candidate_recorded",
            "ts": ts,
            "strategy": strategy,
            "asset": asset,
            "direction": direction,
            "score": score,
            "confidence": confidence,
            "decision": decision,
        })
        return candidate_id

    def update_candidate(
        self,
        candidate_id: int,
        *,
        decision: Optional[str] = None,
        decision_reason: Optional[str] = None,
        reject_reason: Optional[str] = None,
        order_id: Optional[str] = None,
        order_result: Optional[str] = None,
        profit: Optional[float] = None,
        entry_price: Optional[float] = None,
        exit_price: Optional[float] = None,
        candles_post: Optional[list] = None,
        stoch_m15: Optional[Dict[str, Any] | str] = None,
        stoch_contradicts: Optional[int] = None,
        loss_reason: Optional[str] = None,
        improvement_hint: Optional[str] = None,
        masaniello_snapshot: Optional[Dict[str, Any] | str] = None,
        duration_sec: Optional[int] = None,
    ) -> None:
        """Actualiza un candidato existente con estado posterior al escaneo."""
        if candidate_id <= 0:
            return

        fields: list[str] = []
        values: list[Any] = []
        if decision is not None:
            fields.append("decision = ?")
            values.append(decision)
        if decision_reason is not None:
            fields.append("decision_reason = ?")
            values.append(decision_reason)
        if reject_reason is not None:
            fields.append("reject_reason = ?")
            values.append(reject_reason)
        if duration_sec is not None:
            fields.append("duration_sec = ?")
            values.append(int(duration_sec))
        if order_id is not None:
            fields.append("order_id = ?")
            values.append(order_id)
        if order_result is not None:
            fields.append("order_result = ?")
            values.append(order_result)
        if profit is not None:
            fields.append("profit = ?")
            values.append(profit)
        if entry_price is not None:
            fields.append("entry_price = ?")
            values.append(entry_price)
        if exit_price is not None:
            fields.append("exit_price = ?")
            values.append(exit_price)
        if candles_post is not None:
            fields.append("candles_post = ?")
            values.append(json.dumps(candles_post, ensure_ascii=False) if candles_post else None)
        if stoch_m15 is not None:
            fields.append("stoch_m15 = ?")
            values.append(json.dumps(stoch_m15, ensure_ascii=False) if isinstance(stoch_m15, dict) else stoch_m15)
        if stoch_contradicts is not None:
            fields.append("stoch_contradicts = ?")
            values.append(int(stoch_contradicts))
        if loss_reason is not None:
            fields.append("loss_reason = ?")
            values.append(loss_reason)
        if improvement_hint is not None:
            fields.append("improvement_hint = ?")
            values.append(improvement_hint)
        if masaniello_snapshot is not None:
            fields.append("masaniello_snapshot = ?")
            if isinstance(masaniello_snapshot, str):
                values.append(masaniello_snapshot)
            else:
                values.append(json.dumps(masaniello_snapshot, ensure_ascii=False))
        if not fields:
            return

        fields.append("updated_at = ?")
        values.append(datetime.now(timezone.utc).isoformat())
        values.append(candidate_id)

        con = sqlite3.connect(self.db_path)
        cur = con.cursor()
        cur.execute(
            f"UPDATE scan_candidates SET {', '.join(fields)} WHERE id = ?",
            values,
        )
        con.commit()
        con.close()

    def resolve_candidate_for_asset(
        self,
        asset: str,
        outcome: str,
        profit: float,
        *,
        entry_price: Optional[float] = None,
        exit_price: Optional[float] = None,
        candles_post: Optional[list] = None,
        stoch_m15: Optional[Any] = None,
        loss_reason: Optional[str] = None,
        improvement_hint: Optional[str] = None,
    ) -> Optional[int]:
        """Cierra el candidato STRAT-F más reciente de `asset` sin resultado.

        Usado por el post-mortem (Fase 4): busca el último candidato de ese
        asset con order_result NULL y lo actualiza con el resultado real +
        contexto post-cierre. Idempotente: si no hay pendiente, no hace nada.
        Retorna el candidate_id actualizado o None.
        """
        con = sqlite3.connect(self.db_path)
        cur = con.cursor()
        row = cur.execute(
            """
            SELECT id FROM scan_candidates
            WHERE asset = ? AND strategy = 'STRAT-F' AND order_result IS NULL
            ORDER BY id DESC LIMIT 1
            """,
            (asset,),
        ).fetchone()
        if not row:
            con.close()
            return None
        cid = int(row[0])

        fields = ["order_result = ?", "profit = ?"]
        values: list[Any] = [outcome, profit]
        if entry_price is not None:
            fields.append("entry_price = ?")
            values.append(entry_price)
        if exit_price is not None:
            fields.append("exit_price = ?")
            values.append(exit_price)
        if candles_post is not None:
            fields.append("candles_post = ?")
            values.append(json.dumps(candles_post, ensure_ascii=False) if candles_post else None)
        if stoch_m15 is not None:
            fields.append("stoch_m15 = ?")
            values.append(json.dumps(stoch_m15, ensure_ascii=False) if isinstance(stoch_m15, dict) else stoch_m15)
        if loss_reason is not None:
            fields.append("loss_reason = ?")
            values.append(loss_reason)
        if improvement_hint is not None:
            fields.append("improvement_hint = ?")
            values.append(improvement_hint)
        fields.append("updated_at = ?")
        values.append(datetime.now(timezone.utc).isoformat())
        values.append(cid)

        cur.execute(
            f"UPDATE scan_candidates SET {', '.join(fields)} WHERE id = ?",
            values,
        )
        con.commit()
        con.close()
        return cid

    def resolve_candidate_by_id(
        self,
        candidate_id: int,
        outcome: str,
        profit: float,
        *,
        entry_price: Optional[float] = None,
        exit_price: Optional[float] = None,
        candles_post: Optional[list] = None,
        stoch_m15: Optional[Any] = None,
        loss_reason: Optional[str] = None,
        improvement_hint: Optional[str] = None,
    ) -> Optional[int]:
        """Cierra un candidato por id exacto (resolución preferida de Fase 4)."""
        con = sqlite3.connect(self.db_path)
        cur = con.cursor()
        row = cur.execute("SELECT id FROM scan_candidates WHERE id = ?", (candidate_id,)).fetchone()
        if not row:
            con.close()
            return None
        fields = ["order_result = ?", "profit = ?"]
        values: list[Any] = [outcome, profit]
        if entry_price is not None:
            fields.append("entry_price = ?")
            values.append(entry_price)
        if exit_price is not None:
            fields.append("exit_price = ?")
            values.append(exit_price)
        if candles_post is not None:
            fields.append("candles_post = ?")
            values.append(json.dumps(candles_post, ensure_ascii=False) if candles_post else None)
        if stoch_m15 is not None:
            fields.append("stoch_m15 = ?")
            values.append(json.dumps(stoch_m15, ensure_ascii=False) if isinstance(stoch_m15, dict) else stoch_m15)
        if loss_reason is not None:
            fields.append("loss_reason = ?")
            values.append(loss_reason)
        if improvement_hint is not None:
            fields.append("improvement_hint = ?")
            values.append(improvement_hint)
        fields.append("updated_at = ?")
        values.append(datetime.now(timezone.utc).isoformat())
        values.append(candidate_id)
        cur.execute(
            f"UPDATE scan_candidates SET {', '.join(fields)} WHERE id = ?",
            values,
        )
        con.commit()
        con.close()
        return candidate_id

    def get_candidate_by_id(self, candidate_id: int) -> Optional[Dict[str, Any]]:
        """Recupera las velas ANTES + stoch de un candidato por id exacto."""
        con = sqlite3.connect(self.db_path)
        cur = con.cursor()
        row = cur.execute(
            """
            SELECT id, candles_1m, stoch_m15, direction
            FROM scan_candidates WHERE id = ?
            """,
            (candidate_id,),
        ).fetchone()
        con.close()
        if not row:
            return None
        return {
            "id": int(row[0]),
            "candles_1m": json.loads(row[1]) if row[1] else [],
            "stoch_m15": json.loads(row[2]) if row[2] else None,
            "direction": row[3] or "",
        }

    def clone_candidate_for_duration(
        self,
        source_id: int,
        duration_sec: int,
    ) -> int:
        """Clone a scan_candidate row with a new duration_sec (multi-duration A/B).

        Returns new candidate id, or 0 on failure / missing source.
        """
        if source_id <= 0:
            return 0
        con = sqlite3.connect(self.db_path)
        cur = con.cursor()
        cur.execute("SELECT * FROM scan_candidates WHERE id = ?", (source_id,))
        row = cur.fetchone()
        if not row:
            con.close()
            return 0
        col_names = [d[0] for d in cur.description]
        data = dict(zip(col_names, row))
        data.pop("id", None)
        data["duration_sec"] = int(duration_sec)
        data["order_id"] = None
        data["order_result"] = None
        data["profit"] = None
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        # Keep decision ACCEPTED / PENDING for the cloned leg.
        cols = list(data.keys())
        placeholders = ", ".join("?" for _ in cols)
        col_sql = ", ".join(cols)
        cur.execute(
            f"INSERT INTO scan_candidates ({col_sql}) VALUES ({placeholders})",
            [data[c] for c in cols],
        )
        new_id = int(cur.lastrowid or 0)
        con.commit()
        con.close()
        return new_id

    def get_pending_candidate_before(self, asset: str) -> Optional[Dict[str, Any]]:
        """Recupera las velas ANTES + stoch del candidato STRAT-F pendiente de `asset`."""
        con = sqlite3.connect(self.db_path)
        cur = con.cursor()
        row = cur.execute(
            """
            SELECT id, candles_1m, stoch_m15, direction
            FROM scan_candidates
            WHERE asset = ? AND strategy = 'STRAT-F' AND order_result IS NULL
            ORDER BY id DESC LIMIT 1
            """,
            (asset,),
        ).fetchone()
        con.close()
        if not row:
            return None
        return {
            "id": int(row[0]),
            "candles_1m": json.loads(row[1]) if row[1] else [],
            "stoch_m15": json.loads(row[2]) if row[2] else None,
            "direction": row[3] or "",
        }

    def record_order_result(self, order_id: str, outcome: str, profit: float) -> None:
        """Actualiza resultado de una orden."""
        ts = datetime.now(timezone.utc).timestamp()
        ts_iso = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        
        con = sqlite3.connect(self.db_path)
        cur = con.cursor()
        cur.execute('''
            UPDATE scan_candidates
            SET order_result = ?, profit = ?, updated_at = ?
            WHERE order_id = ?
        ''', (outcome, profit, ts_iso, order_id))
        con.commit()
        con.close()
        
        self._log_jsonl({
            "event": "order_result",
            "ts": ts,
            "order_id": order_id,
            "outcome": outcome,
            "profit": profit,
        })
    
    def record_phase(self, strategy: str, phase: str, message: str = "", asset: str = "") -> None:
        """Registra una fase de procesamiento."""
        try:
            ts = datetime.now(timezone.utc).timestamp()
            ts_iso = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

            con = sqlite3.connect(self.db_path)
            cur = con.cursor()
            cur.execute(
                '''
                INSERT INTO phase_log (ts, ts_iso, strategy, asset, phase, message)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (ts, ts_iso, str(strategy), str(asset or ""), str(phase), str(message or "")),
            )
            con.commit()
            con.close()

            self._log_jsonl({
                "event": "phase",
                "ts": ts,
                "ts_iso": ts_iso,
                "strategy": strategy,
                "asset": asset,
                "phase": phase,
                "message": message,
            })
        except Exception as exc:
            log.debug("Black box record_phase error: %s", exc)

    def record_maintenance_event(
        self,
        category: str,
        subtype: str,
        *,
        asset: str = "",
        severity: str = "INFO",
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Registra eventos de mantenimiento / salud del sistema en la caja negra."""
        try:
            ts = datetime.now(timezone.utc).timestamp()
            ts_iso = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
            payload_json = json.dumps(payload or {}, ensure_ascii=False)

            con = sqlite3.connect(self.db_path)
            cur = con.cursor()
            cur.execute(
                '''
                INSERT INTO maintenance_log (ts, ts_iso, category, subtype, asset, severity, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (ts, ts_iso, str(category), str(subtype), str(asset or ""), str(severity or "INFO"), payload_json),
            )
            con.commit()
            con.close()

            self._log_jsonl({
                "event": "maintenance",
                "ts": ts,
                "ts_iso": ts_iso,
                "category": category,
                "subtype": subtype,
                "asset": asset,
                "severity": severity,
                "payload": payload or {},
            })
        except Exception as exc:
            log.debug("Black box record_maintenance_event error: %s", exc)
    
    def update_scan_results(self, scan_id: int, found: int, accepted: int, rejected: int) -> None:
        """Actualiza conteo final del escaneo."""
        con = sqlite3.connect(self.db_path)
        cur = con.cursor()
        cur.execute('''
            UPDATE scans
            SET found_count = ?, accepted_count = ?, rejected_count = ?
            WHERE id = ?
        ''', (found, accepted, rejected, scan_id))
        con.commit()
        con.close()
    
    def update_strategy_metrics(self, strategy: str, metrics: Dict[str, Any]) -> None:
        """Actualiza métricas agregadas de la estrategia."""
        ts = datetime.now(timezone.utc).timestamp()
        
        con = sqlite3.connect(self.db_path)
        cur = con.cursor()
        cur.execute('''
            INSERT INTO strategy_metrics 
            (ts, strategy, total_scans, total_candidates, total_accepted, wins, losses, pending, win_rate, pnl, last_decision, last_asset)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            ts, strategy,
            metrics.get("total_scans", 0),
            metrics.get("total_candidates", 0),
            metrics.get("total_accepted", 0),
            metrics.get("wins", 0),
            metrics.get("losses", 0),
            metrics.get("pending", 0),
            metrics.get("win_rate", 0.0),
            metrics.get("pnl", 0.0),
            metrics.get("last_decision", ""),
            metrics.get("last_asset", ""),
        ))
        con.commit()
        con.close()
    
    def _log_jsonl(self, record: Dict[str, Any]) -> None:
        """Escribe evento a JSONL."""
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"⚠️ Error escribiendo JSONL: {e}")
    
    def get_trades(self, limit: int = 100, date_from: Optional[str] = None) -> list[dict]:
        """Retrieve closed trades from the black box DB.

        Args:
            limit: Max number of trades to return (default 100)
            date_from: Optional ISO date string to filter from (e.g. "2024-01-15")

        Returns:
            List of trade dicts ordered by most recent first.
        """
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        cur = con.cursor()

        query = """
            SELECT id, asset, direction, score, payout, order_result, profit,
                   entry_price, exit_price, ts, created_at
            FROM scan_candidates
            WHERE order_result IS NOT NULL
        """
        params: list[Any] = []

        if date_from:
            # created_at is stored as ISO text like "2024-01-15 10:30:00"
            query += " AND created_at >= ?"
            params.append(date_from + " 00:00:00")

        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        rows = cur.execute(query, params).fetchall()
        con.close()

        trades = []
        for row in rows:
            trades.append({
                "id": int(row["id"]),
                "asset": row["asset"] or "",
                "direction": (row["direction"] or "").upper(),
                "score": float(row["score"]) if row["score"] is not None else None,
                "payout": int(row["payout"]) if row["payout"] is not None else None,
                "result": row["order_result"] or "",
                "profit": float(row["profit"]) if row["profit"] is not None else 0.0,
                "entry_price": float(row["entry_price"]) if row["entry_price"] is not None else None,
                "exit_price": float(row["exit_price"]) if row["exit_price"] is not None else None,
                "ts": float(row["ts"]) if row["ts"] is not None else None,
                "created_at": row["created_at"] or "",
            })
        return trades

    def clear_trades(self) -> int:
        """Delete all trade records from the DB (JSONL files remain intact).

        Returns:
            Number of records deleted.
        """
        con = sqlite3.connect(self.db_path)
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM scan_candidates WHERE order_result IS NOT NULL")
        count = int(cur.fetchone()[0])
        cur.execute("DELETE FROM scan_candidates WHERE order_result IS NOT NULL")
        con.commit()
        con.close()
        log.info("🧹 Black box: %d trade records cleared (JSONL files preserved)", count)
        return count

    def get_session_summary(self) -> dict[str, Any]:
        """Get current session stats from the black box.

        Returns:
            Dict with session statistics.
        """
        con = sqlite3.connect(self.db_path)
        cur = con.cursor()

        # Today's trades
        today = datetime.now().strftime("%Y-%m-%d")
        row = cur.execute(
            """
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN order_result='WIN' THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN order_result='LOSS' THEN 1 ELSE 0 END) as losses,
                   COALESCE(SUM(profit), 0) as pnl
            FROM scan_candidates
            WHERE order_result IS NOT NULL AND created_at >= ?
            """,
            (today + " 00:00:00",),
        ).fetchone()

        total = int(row[0]) if row[0] else 0
        wins = int(row[1]) if row[1] else 0
        losses = int(row[2]) if row[2] else 0
        pnl = float(row[3]) if row[3] else 0.0
        win_rate = (wins / total * 100) if total > 0 else 0.0

        # Last trade
        last = cur.execute(
            """
            SELECT asset, direction, order_result, profit, created_at
            FROM scan_candidates
            WHERE order_result IS NOT NULL
            ORDER BY id DESC LIMIT 1
            """,
        ).fetchone()

        last_trade = None
        if last:
            last_trade = {
                "asset": last[0] or "",
                "direction": (last[1] or "").upper(),
                "result": last[2] or "",
                "profit": float(last[3]) if last[3] else 0.0,
                "created_at": last[4] or "",
            }

        con.close()

        return {
            "today_total": total,
            "today_wins": wins,
            "today_losses": losses,
            "today_pnl": round(pnl, 2),
            "today_win_rate": round(win_rate, 1),
            "last_trade": last_trade,
        }

    def export_summary(self) -> Dict[str, Any]:
        """Genera resumen del día."""
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        
        # Scans por estrategia
        cur.execute('''
            SELECT strategy, COUNT(*) as count, SUM(found_count) as found, 
                   SUM(accepted_count) as accepted
            FROM scans
            GROUP BY strategy
        ''')
        scans = {row["strategy"]: dict(row) for row in cur.fetchall()}
        
        # Performance por estrategia
        cur.execute('''
            SELECT strategy, COUNT(*) as total_trades, 
                   SUM(CASE WHEN order_result = 'WIN' THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN order_result = 'LOSS' THEN 1 ELSE 0 END) as losses,
                   ROUND(SUM(profit), 2) as pnl
            FROM scan_candidates
            WHERE order_result IS NOT NULL
            GROUP BY strategy
        ''')
        performance = {row["strategy"]: dict(row) for row in cur.fetchall()}
        
        con.close()
        
        return {
            "date": TODAY,
            "scans_by_strategy": scans,
            "performance_by_strategy": performance,
        }


# ─────────────────────────────────────────────────────────────────────────────
#  SINGLETON INSTANCE
# ─────────────────────────────────────────────────────────────────────────────

_recorder = None

def get_black_box() -> BlackBoxRecorder:
    """Obtiene instancia singleton del recorder."""
    global _recorder
    if _recorder is None:
        _recorder = BlackBoxRecorder()
    return _recorder


# ─────────────────────────────────────────────────────────────────────────────
#  USO SIMPLE
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Ejemplo de uso
    recorder = get_black_box()
    
    # Registrar escaneo
    scan_id = recorder.record_scan_start("A", 1, {"market_state": "consolidating", "volatility_atr": 0.0015})
    
    # Registrar candidato
    recorder.record_candidate(scan_id, "A", {
        "asset": "EURUSD_OTC",
        "direction": "call",
        "score": 65.3,
        "confidence": 0.82,
        "payout": 82,
        "decision": "ACCEPTED",
        "decision_reason": "Strong rebound signal",
        "strategy_details": {"zone": [1.0950, 1.0980], "pattern": "spring"},
    })
    
    # Actualizar resultados
    recorder.update_scan_results(scan_id, found=5, accepted=1, rejected=4)
    
    # Exportar resumen
    summary = recorder.export_summary()
    print("\n📊 BLACK BOX SUMMARY")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    
    print(f"\n✅ Datos guardados en:")
    print(f"   DB:   {BLACK_BOX_DB}")
    print(f"   JSONL: {BLACK_BOX_LOG}")
