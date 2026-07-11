# ADR-002 — Diario en SQLite local (trade_journal.db)

- **Estado:** Aceptado
- **Fecha:** 2026-07-11

## Contexto

Necesitamos registrar CADA decisión del bot (aceptada/rechazada) con su razón,
velas y resultado, para calibración y diario de trading. Opciones: Postgres,
 SQLite, CSV plano, JSON lines.

## Decisión

Usar **SQLite local** (`data/db/trade_journal-YYYY-MM-DD.db`, un archivo por
día). Módulo `src/trade_journal.py` con `Journal`.

## Consecuencias

- ✅ Cero infraestructura: el bot corre en la máquina de Ruben sin servidor.
- ✅ Transaccional y consultable con SQL.
- ✅ `query_strat_f()` / `print_strat_f_report()` / `calibration_report.py`
  leen directo.
- ✅ Reproducible: `candles_json` + `strategy_json` guardan las velas.
- ⚠️ Un archivo por día: consultas multi-día deben unir BDs (el reporte recibe
  `days=N` y busca en la BD del día; para rango largo hay que iterar archivos).
- ⚠️ No concurrente: un solo proceso escribe. Suficiente para el bot.
