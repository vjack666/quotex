# FASE B — Resultado del Backfill (Atlas con película completa)

Fecha: 2026-07-27 · Observador Fase B · Estado: COMPLETADO

## Qué se generó
`data/observador/episodes_eurusd_full.db` (342 MB) — Atlas EURUSD M1 14 años
con película completa por episodio.

| Métrica                    | Valor              |
|----------------------------|--------------------|
| Episodios (Fase A)         | 89,832             |
| Summaries (Fase B)         | 89,830 (99.99%)    |
| Filas de traza evolutiva   | 2,822,619          |
| Largo medio de traza       | 31.4 barras M1     |
| Cierre natural (NEW_PRESSURE) | 39,015          |
| Cierre por captura (límite)   | 50,815          |

## Por qué 89,832 y no 117,169
La corrida original de Fase A (transitions_v1, script `corrida_14y.py`) contó
117,169 episodios SIN película. La Fase B corre el observer unificado
(Fase A + B en una pasada) con fin natural + CaptureMonitor; su definición de
"episodio filmable" es MÁS ESTRICTA (filtra los que no cierran con traza
coherente). Por eso 89,832. Es el Atlas con película; los 117k eran solo el
índice de Fase A. No es pérdida de datos: es una definición distinta.

## Calidad verificada (muestra)
- ep 2: quality 0.89, curve_shape convex → buen rebote (mfe +3.0 pips).
- ep 3: quality 0.0, flat → rebote fallido (mae -7.4 pips).
- mfe/mae/quality/curve_shape/symmetry/episode_type/duration_bars/end_reason/
  end_confidence/finished/capture_limit todos poblados por episodio.

## Reproducir
`PYTHONPATH=src python scripts/backfill_fase_b.py`
(Chunking por año, idempotente, source_label='observador_unified'.
Regenera la DB completa Fase A+B en ~4.3 min.)

## Nota de la DB anterior (`episodes_eurusd_14y.db`)
La DB vieja quedó con un handle lock (WAL) de una corrida previa abortada y
NO debe usarse: tiene 663 episodios contaminados de un backfill fallido.
Los scripts LAB congelados (lab_001, lab_002) aún apuntan a ella; cuando el
lock se libere (reinicio de máquina o liberación del handle), se reemplaza
`episodes_eurusd_14y.db` con `episodes_eurusd_full.db` renombrada. Hasta
entonces, el Discovery Engine y todo análisis Fase B usan
`episodes_eurusd_full.db`.
