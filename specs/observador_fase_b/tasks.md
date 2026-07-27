# Tasks — Observador Fase B: Calidad del Rebote y Película Completa

Regla del repo: una task a la vez, test verde antes de [x]. Trazabilidad R↔test.
Todo número vive en config versionada (requirements R-principio); los tests
usan fixtures con umbrales locales, no literales del SDD.

- [x] T1. `src/observador/config/evolution_v1.yaml` + `config_loader.py`.
      Loader que carga cfg por activo; campos de diseño (R3/R5/R7/R10) sin
      valores máx. Test: loader devuelve cfg para EURUSD y XAUUSD; bump de
      `version` se refleja. (R3,R5,R7,R10)

- [x] T2. `store.py` EXTEND: tablas `episode_evolution`, `episode_summary`,
      `episode_version` (D1). Upsert idempotente por (episode_id,bar_index) y
      por episode_id. Test: esquema se crea; backfill no duplica filas.
      (R1,R2,R8,R10,R11)

- [x] T3. `evolution.py`: `EpisodeEvolutionWriter.record(bar_index, candle,
      state, vars)` con distance_pips/mfe/mae vivos; sin reloj de pared (ts y
      bar_index del evento). Test: secuencia sintética → mfe/mae correctos
      calculados a mano; bar_index relativo 0-based. (R1,R2,R12)

- [x] T4. Variables versionadas por barra (R3): escritura de `vars_json` +
      `vars_version` desde dict. Test: vars rondan y se leen con su version.
      (R3,R10)

- [x] T5. `evolution.py`: `CaptureMonitor` evalúa dimensiones configurables
      (D3); devuelve CAPTURE_FINISHED solo cuando TODAS reportan sin-cambio;
      NO por conteo fijo. Test: monitor sigue vivo con 1 dimensión cambiando;
      corta cuando todas quietas; umbrales por activo (fixture). (R5,R6,R7)

- [x] T6. Fin natural vs fin de captura (D4): writer cierra con finished=1 +
      end_reason+end_confidence ante estado de cierre real; con finished=0 +
      capture_limit_reached=1 ante CaptureMonitor. Test: ambos caminos; la
      diferencia semántica queda en la fila. (R4,R5)

- [x] T7. `summary.py`: `EpisodeSummary` computa quality/velocity/violence/
      curve_shape/symmetry/episode_type/duration_bars/mfe/mae (D5). Todas las
      fórmulas versionadas y recalculables. Test: snapshot de una traza
      sintética conocida coincide campo a campo. (R8,R10)

- [x] T8. `observer.py` MODIFICADO: tras RESOLUTION sigue alimentando el
      writer hasta fin natural o CaptureMonitor; agnóstico a vehículo (R9).
      Test: episodio sintético donde la traza sigue 20 barras tras RESOLUTION
      y cierra por CaptureMonitor (finished=0). (R9,R11,R12)

- [x] T9. Backfill idempotente 14 años (R11): re-correr EURUSD con Fase B
      activa sobre el store existente; episodios se completan con traza+
      summary, count_episodes() idéntico antes/después. Test (reducido):
      fuente sintética de N episodios, doble pasada, count estable. (R11)

- [x] T10. Candados + regresión: grep anti-bot (R13) limpio en
      `src/observador/`; `test_observador_no_wallclock.py` cubre Fase B;
      suite completa `tests/` sin nuevos rojos. Test: candado falla si alguien
      mete import de bot; wallclock test vigila archivos nuevos. (R12,R13)

Bitácora:
- Spec escrita 2026-07-27. Principio "SDD = comportamiento, no parámetros"
  acordado con el humano: cero literales numéricos en requirements/design;
  umbrales en config/evolution_v1.yaml versionado.
- Fin natural (mercado) separado de fin de captura (sistema) por mandato del
  humano: preserva la honestidad "el mercado terminó" vs "dejamos de observar".
- EpisodeVersion habilita recálculo de fórmulas sin re-reproducir 14 años.
