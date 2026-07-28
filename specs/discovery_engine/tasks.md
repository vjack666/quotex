# Tasks — Discovery Engine (Minería de conocimiento del Atlas)

Regla del repo: una task a la vez, test verde antes de [x]. Sin literales
numéricos en código (principio Fase B): umbrales en config/discovery_v1.yaml.
Depende de Fase B poblada (backfill 14 años con trazas).

- [x] T1. `src/discovery/config/discovery_v1.yaml` + `config_loader.py`.
      Campos: min_sample, p_cut, min_freq, max_depth, seed, split_year,
      sources (Dukascopy/Quotex OTC/Broker X/...). Sin literales mágicos
      fijos (nombres/percentiles versionados). Test: loader devuelve cfg;
      seed/cut/sources se reflejan.

- [x] T2. `reader.py`: carga trazas+summary desde EpisodeStore; genera dicts
      por episodio; EXCLUYE variables de cierre del conjunto predictor (R8);
      MARCA cada episodio con su MERCADO y FUENTE según proveedor (R9b).
      Test: lee un store de fixture y entrega features válidos (sin end_reason
      como input) y mercado/fuente etiquetados. (R1,R8,R9b)

- [x] T3. `space.py`: define espacio de features por barra + operadores +
      combinaciones acotadas por profundidad. Test: el espacio enumerado para
      un episodio fixture tiene las features esperadas y respeta max_depth. (R2)

- [x] T4. `splitter.py`: walk-forward por año (entrenamiento/prueba) y
      PARTICIONA por FUENTE cuando hay >1 (R9b). Test: episodios se
      particionan correctamente por ts_open y por fuente; misma semilla =>
      mismo split. (R3,R9b,R10)

- [x] T5. `falsifier.py`: n, tasa vs baseline, diferencia, p-valor por
      permutaciones, POR FUENTE (R9b). Test: ley real conocida pasa; ley
      falsa (ruido) se descarta; p se reproduce con semilla. (R4,R6,R9b)

- [x] T6. `miner.py`: recorre el espacio, corre Splitter+Falsifier, acumula
      leyes que pasan, determina `state=EXPERIMENTAL` (R13), determinista.
      Test: sobre fixture pequeño descubre la ley "curva_plana_revierte" como
      candidata fuerte y la reporta etiquetada por fuente. (R2,R5,R10,R9b,R13)
      NOTA: la candidata "muerte del empuje" (DEAD_PUSH) NO existe en el
      vocabulario del Atlas actual (PTM v3 usa QUIET/EXPANSION/PRESSURE/BRAKE/
      TRANSITION/RESOLUTION). La primera ley genuine descubierta en datos es
      curve_shape (ver T10). La "muerte del empuje" de Rubén requiere el
      estocástico, que NO está en el Atlas -> queda para el Strategy Lab.

- [x] T7. `law_store.py`: escribe Leyes #N en tabla `leyes` con id, name,
      conditions, probability, confidence, markets, sources, timeframes,
      cases_studied, state, discovery_version, script_ref. Test: inserta y lee
      por id; acumula sin sobrescribir; state por defecto EXPERIMENTAL. (R12,R9b,R13)

- [x] T8. `reporter.py`: emite LAB_0XX canónico (script + métricas legibles)
      Y registro en `leyes` con state y fuentes. Test: genera doc con los
      campos R7 + mercados/fuentes validados + state; la ley NO sobrescribe
      LAB-001. (R5,R7,R12,R13,R9b)

- [x] T9. Candados + integración: grep anti-bot limpio en src/discovery/;
      test no_wallclock cubre discovery; grep unidireccional Memoria→bot
      ausente; pytest suite sin nuevos rojos. (R11,R9b)

- [x] T10. Smoke end-to-end: corre el motor sobre la DB poblada (EURUSD 14y)
      y emite >=1 Ley #N con walk-forward, p<corte y FUENTE etiquetada;
      guarda su LAB_0XX y su registro en `leyes`. (R3-R7,R12,R9b,R13)
      RESULTADO REAL (2026-07-27): 2 Leyes #N emitidas sobre EURUSD M1
      (60k episodios, 2012-2020):
        #1 curva_plana_revierte  prob=0.902  state=EXPERIMENTAL  forex/Dukascopy
        #2 curva_concava_reviere_parcial  prob=0.654  EXPERIMENTAL  forex/Dukascopy
      Variable objetivo = reversal (distance_pips final < 0, baseline ~49%).
      curve_shape=='flat' predice reversal 90% vs baseline 49% (p<0.05).

- [x] T11. `law_relations.py` + `relation_miner.py`: grafo de relaciones
      ley→ley (refuerza/contradice/requiere, strength, version). Test: inserta
      y lee aristas; relation_miner propone una relación válida entre dos leyes
      fixture y el scanner puede consultar "leyes que apoyan #N". (R14)

- [x] T12. `reporter.py`/lifecycle: transiciones de estado (EXPERIMENTAL →
      VALIDADA → FUERTE → UNIVERSAL → OBSOLETA) registradas con version+motivo;
      una ley OBSOLETA NO se borra. Test: transición de estado persiste; ley
      obsoleta sigue consultable. (R13)

Bitácora:
- Spec escrito 2026-07-27 por mandato de Rubén: tras congelar LAB-001 y
  completar Fase B, el Discovery Engine es el paso 3 antes del motor de
  trading. Invierte la pregunta: de "¿esto funciona?" a "¿qué funciona?".
- ACTUALIZADO 2026-07-27 (review de Rubén, 2 pasadas):
  (a) arquitectura de 4 capas: el motor EMITE LEYES #N como OBJETO de la
      Memoria (R12), no documento; el scanner futuro consulta por id sí/no.
  (b) R9b: candado forex/OTC extendido a FUENTE concreta (Dukascopy, Quotex
      OTC, Broker X...); dos brokers OTC pueden diferir; la ley se valida por
      fuente, no por "OTC" genérico.
  (c) R13: ciclo de vida de la ley (EXPERIMENTAL→VALIDADA→FUERTE→UNIVERSAL→
      OBSOLETA); nunca se borra, solo cambia de estado.
  (d) R14: grafo de conocimiento — relaciones entre leyes (refuerza/contradice/
      requiere); el scanner pregunta "¿qué leyes apoyan esto?" no solo "¿existe
      #N?".
  (e) pipeline explícito de 5 responsabilidades: Laboratorio observa, Discovery
      descubre, Memoria recuerda, Scanner consulta, Estrategia decide.
- Acumula leyes, no las borra (ciencia). Mejora de LAB-001 => LAB-0XX nuevo.
- El Atlas (no el bot) es el activo estratégico del proyecto.
- IMPLEMENTADO 2026-07-27: 3 agentes en paralelo (A=T1/T2/T3, B=T4/T5/T7/T11,
  C=T6/T8/T12) + ensamblaje y smoke E2E por el coordinator. 30 tests verdes.
  La primera Ley #N genuine del Atlas es sobre curve_shape (no sobre "muerte
  del empuje", que requiere el estocástico no presente en el Atlas).
