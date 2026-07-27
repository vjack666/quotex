# Tasks — Discovery Engine (Minería de conocimiento del Atlas)

Regla del repo: una task a la vez, test verde antes de [x]. Sin literales
numéricos en código (principio Fase B): umbrales en config/discovery_v1.yaml.
Depende de Fase B poblada (backfill 14 años con trazas).

- [ ] T1. `src/discovery/config/discovery_v1.yaml` + `config_loader.py`.
      Campos: min_sample, p_cut, min_freq, max_depth, seed, split_year.
      Sin literales mágicos fijos (nombres/percentiles versionados). Test:
      loader devuelve cfg; seed/cut se reflejan.

- [ ] T2. `reader.py`: carga trazas+summary desde EpisodeStore; genera dicts
      por episodio; EXCLUYE variables de cierre del conjunto predictor (R8).
      Test: lee un store de fixture y entrega features válidos (sin end_reason
      como input). (R1,R8)

- [ ] T3. `space.py`: define espacio de features por barra + operadores +
      combinaciones acotadas por profundidad. Test: el espacio enumerado para
      un episodio fixture tiene las features esperadas y respeta max_depth.
      (R2)

- [ ] T4. `splitter.py`: walk-forward por año (entrenamiento/prueba). Test:
      episodios se particionan correctamente por ts_open; misma semilla =>
      mismo split. (R3,R10)

- [ ] T5. `falsifier.py`: n, tasa vs baseline, diferencia, p-valor por
      permutaciones. Test: ley real conocida pasa; ley falsa (ruido) se
      descarta; p se reproduce con semilla. (R4,R6)

- [ ] T6. `miner.py`: recorre el espacio, corre Splitter+Falsifier, acumula
      leyes que pasan, determinista. Test: sobre fixture pequeño descubre la
      ley "muerte del empuje" como candidata fuerte y la reporta. (R2,R5,R10)

- [ ] T7. `reporter.py`: emite LAB_0XX canónico (script + métricas legibles).
      Test: genera doc con los campos R7; la ley NO sobrescribe LAB-001.
      (R5,R7)

- [ ] T8. Candados + integración: grep anti-bot limpio en src/discovery/;
      test no_wallclock cubre discovery; pytest suite sin nuevos rojos.
      (R11)

- [ ] T9. Smoke end-to-end: corre el motor sobre la DB poblada (EURUSD 14y +
      universalidad) y reporta >=1 ley candidata con walk-forward y p<corte;
      guarda su LAB_0XX. (R3-R7)

Bitácora:
- Spec escrito 2026-07-27 por mandato de Rubén: tras congelar LAB-001 y
  completar Fase B, el Discovery Engine es el paso 3 antes del motor de
  trading. Invierte la pregunta: de "¿esto funciona?" a "¿qué funciona?".
- Acumula leyes, no las borra (ciencia). Mejora de LAB-001 => LAB-0XX nuevo.
- El Atlas (no el bot) es el activo estratégico del proyecto.
