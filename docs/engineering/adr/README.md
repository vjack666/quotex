# ADR — Índice

> Architecture Decision Records del proyecto QUOTEX / STRAT-F.
> Formato: contexto → decisión → consecuencias.

| # | Título | Estado |
|---|--------|--------|
| [001](001_evaluador_puro.md) | STRAT-F como evaluador puro (no opera) | Aceptado |
| [002](002_sqlite_diario.md) | Diario en SQLite local (trade_journal.db) | Aceptado |
| [003](003_no_borrar_hub_models.md) | No borrar `hub_models.py` al reemplazar el dashboard | Aceptado |

## Cómo proponer un ADR

1. Crear `NNN_titulo.md` siguiendo la plantilla de arriba.
2. RFC opcional en `docs/engineering/rfc/` si la decisión es debatible.
3. Una vez aceptado por el usuario, mover a "Aceptado" y citarlo en el código
   relevante (`# ver ADR-NNN`).
