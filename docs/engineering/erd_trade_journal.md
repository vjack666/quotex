# ERD — trade_journal.db (caja negra / diario de trading)

> Diagrama de entidad-relación de la base de datos del diario. DDL real en
> `src/trade_journal.py` (`_DDL`). Una BD por día en `data/db/`.

## Tablas

```
┌──────────────────────────────┐         ┌──────────────────────────────┐
│ candidates                   │         │ scan_sessions                │
├──────────────────────────────┤         ├──────────────────────────────┤
│ id                PK          │         │ id                PK          │
│ scanned_at        TEXT (ISO)  │         │ started_at       TEXT         │
│ asset             TEXT         │         │ ended_at         TEXT?        │
│ direction         call|put     │         │ total_assets     INTEGER      │
│ payout            INTEGER      │         │ total_candidates INTEGER      │
│ amount            REAL         │         │ total_accepted   INTEGER      │
│ stage             initial|...  │         │ dry_run          INTEGER      │
│ score             REAL         │         └──────────────────────────────┘
│ score_compression REAL         │
│ score_bounce      REAL         │         ┌──────────────────────────────┐
│ score_trend       REAL         │         │ shadow_decision_audit         │
│ score_payout      REAL         │         ├──────────────────────────────┤
│ reversal_pattern  TEXT         │         │ id                PK          │
│ reversal_strength REAL         │         │ candidate_id      FK→candidates│
│ zone_ceiling      REAL         │         │ asset             TEXT         │
│ zone_floor        REAL         │         │ strategy_origin   TEXT         │
│ zone_range_pct    REAL         │         │ old_decision      TEXT         │
│ zone_bars_inside  INTEGER      │         │ new_decision      TEXT         │
│ zone_age_min      REAL         │         │ new_category      TEXT         │
│ decision          ACCEPTED|... │         │ trade_outcome     WIN|LOSS|... │
│ reject_reason     TEXT?        │         │ error_text        TEXT?        │
│ order_id          TEXT?        │         │ context_hash      TEXT         │
│ outcome           WIN|LOSS|... │         └──────────────────────────────┘
│ profit            REAL         │
│ closed_at         TEXT?        │         ┌──────────────────────────────┐
│ strategy_origin   STRAT-A|F    │         │ expired_zones                 │
│ candles_json      TEXT (JSON)  │         ├──────────────────────────────┤
│ strategy_json     TEXT (JSON)  │         │ id                PK          │
│ entry_*, ticket_*  auditoría   │         │ asset             TEXT         │
└──────────────────────────────┘         │ expiry_reason     TIME_LIMIT|.. │
                                          │ ceiling/floor     REAL         │
                                          │ age_min           REAL         │
                                          │ break_body        REAL?        │
                                          └──────────────────────────────┘
```

## Relaciones

- `shadow_decision_audit.candidate_id` → `candidates.id` (1 auditoría : 1 candidato;
  una segunda opinión "caja negra" de la decisión tomada).
- `scan_sessions` es independiente: agrupa métricas de un ciclo de escaneo
  (cuántos pares, cuántos aceptados). No tiene FK a candidates.
- `expired_zones` es independiente: registra zonas de consolidación que expiraron
  o se rompieron (para aprender de fallas de contexto M15).
- `massaniello_state` (creada por `massaniello_persistence.py`) es independiente:
  estado de la gestión de riesgo; NO la borramos (ver ADR-003).

## Campos clave para STRAT-F

| Campo | Qué guarda |
|-------|-----------|
| `strategy_origin` | `'STRAT-F'` o `'STRAT-A'` (filtro del reporte) |
| `decision` | `ACCEPTED` | `REJECTED_STRAT_F` |
| `reject_reason` | texto del filtro que rechazó (R1/R2/R3/R4/R6) |
| `candles_json` | velas M1 usadas (últimas 20) para replay |
| `strategy_json` | contexto M15, evento M5, strength, y velas M15/M5/M1 para calibración |
| `outcome` | `WIN` / `LOSS` / `PENDING` / `DRY_RUN` (lo pone el broker post-trade) |

## Cómo consultar

```bash
# Diario + calibración STRAT-F
python -m trade_journal --strat-f
python -m src.calibration_report 90
```
