# Tasks — Discovery Engine (Minería de conocimiento del Atlas)

Regla del repo: una task a la vez, test verde antes de [x]. Sin literales
numéricos en código (principio Fase B): umbrales en config/discovery_v1.yaml.
Depende de Fase B poblada (backfill 14 años con trazas).

- [ ] T1. `src/discovery/config/discovery_v1.yaml` + `config_loader.py`.
      Campos: min_sample, p_cut, min_freq, max_depth, seed, split_year,
      markets (forex/otc). Sin literales mágicos fijos (nombres/percentiles
      versionados). Test: loader devuelve cfg; seed/cut/se reflejan.

- [ ] T2. `reader.py`: carga trazas+summary desde EpisodeStore; genera dicts
      por episodio; EXCLUYE variables de cierre del conjunto predictor (R8);
      MARCA cada episodio con su MERCADO (forex/otc) según fuente (R9b).
      Test: lee un store de fixture y entrega features válidos (sin end_reason
      como input) y mercado etiquetado. (R1,R8,R9b)

- [ ] T3. `space.py`: define espacio de features por barra + operadores +
      combinaciones acotadas por profundidad. Test: el espacio enumerado para
      un episodio fixture tiene las features esperadas y respeta max_depth.
      (R2)

- [ ] T4. `splitter.py`: walk-forward por año (entrenamiento/prueba) y
      PARTICIONA por MERCADO cuando hay >1 (R9b). Test: episodios se
      particionan correctamente por ts_open y por mercado; misma semilla =>
      mismo split. (R3,R9b,R10)

- [ ] T5. `falsifier.py`: n, tasa vs baseline, diferencia, p-valor por
      permutaciones, POR MERCADO (R9b). Test: ley real conocida pasa; ley
      falsa (ruido) se descarta; p se reproduce con semilla. (R4,R6,R9b)

- [ ] T6. `miner.py`: recorre el espacio, corre Splitter+Falsifier, acumula
      leyes que pasan, determinista. Test: sobre fixture pequeño descubre la
      ley "muerte del empuje" como candidata fuerte y la reporta etiquetada
      por mercado. (R2,R5,R10,R9b)

- [ ] T7. `law_store.py`: escribe Leyes #N en tabla `leyes` de la Memoria con
      id, name, conditions, probability, confidence, markets, timeframes,
      cases_studied, discovery_version, script_ref. Test: inserta y lee por
      id; acumula sin sobrescribir. (R12)

- [ ] T8. `reporter.py`: emite LAB_0XX canónico (script + métricas legibles)
      Y registro en `leyes`. Test: genera doc con los campos R7 + mercados
      validados; la ley NO sobrescribe LAB-001. (R5,R7,R12)

- [ ] T9. Candados + integración: grep anti-bot limpio en src/discovery/;
      test no_wallclock cubre discovery; grep unidireccional Memoria→bot
      ausente; pytest suite sin nuevos rojos. (R11,R9b)

- [ ] T10. Smoke end-to-end: corre el motor sobre la DB poblada (EURUSD 14y)
      y emite >=1 Ley #N con walk-forward, p<corte y MERCADO etiquetado;
      guarda su LAB_0XX y su registro en `leyes`. (R3-R7,R12,R9b)

Bitácora:
- Spec escrito 2026-07-27 por mandato de Rubén: tras congelar LAB-001 y
  completar Fase B, el Discovery Engine es el paso 3 antes del motor de
  trading. Invierte la pregunta: de "¿esto funciona?" a "¿qué funciona?".
- ACTUALIZADO 2026-07-27 con dos aportes de Rubén: (1) arquitectura de 4 capas
  (Laboratorio→Memoria→Estrategas): el motor EMITE LEYES #N como objeto de la
  Memoria del Mercado, no texto suelto (R12, law_store, D6/D7); el scanner
  futuro consulta por id con sí/no. (2) NOTA forex/OTC: el Atlas es solo forex;
  el bot opera forex+OTC; el motor etiqueta leyes POR MERCADO y NO promueve
  ley de forex en OTC sin validación (R9b). Mientras no haya datos OTC, el
  scanner queda en modo desconocido para OTC (candado de no operar ley no
  validada).
- Acumula leyes, no las borra (ciencia). Mejora de LAB-001 => LAB-0XX nuevo.
- El Atlas (no el bot) es el activo estratégico del proyecto.
