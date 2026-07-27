# Tasks — Strategy Lab (Laboratorio de estrategias)

Regla del repo: una task a la vez, test verde antes de [x]. Sin literales
numéricos en código (principio Fase B): umbrales en config/strategy_lab_v1.yaml.
Depende de Fase B poblada (Atlas) y de Discovery Engine emitiendo Leyes #N.

- [ ] T1. `src/strategy_lab/config/strategy_lab_v1.yaml` + `config_loader.py`.
      Campos: min_contribution, p_cut, min_sample, max_depth, seed, split_year.
      Sin literales mágicos fijos. Test: loader devuelve cfg; seed/cut se reflejan.

- [ ] T2. `strategy_parser.py`: descompone estrategia propuesta en pasos; cada
      paso es predicado o referencia a Law #N; valida que la ley exista en la
      Memoria (lectura). Test: parsea fixture y RECHAZA referencia inexistente.
      (SL-R2,R12)

- [ ] T3. `variant_searcher.py`: orden/inclusión/umbrales acotados, determinista.
      Test: enumera variantes de un fixture y respeta max_depth/semilla; no
      inventa pasos fuera de la propuesta. (SL-R3,R10,R13)

- [ ] T4. `backtester.py`: mide edge walk-forward sobre Atlas reusando splitter.
      Test: variante conocida da edge esperado; variante ruido da ~baseline. (SL-R4)

- [ ] T5. `ablator.py` + `falsifier.py`: importancia por ablation, p-valor por
      permutación. Test: paso clave tiene alta importancia y p<corte; paso
      inútil se marca para eliminar. (SL-R5,R6,R7)

- [ ] T6. `orderer.py`: compara secuencias alternativas (A/B/C). Test: ordena y
      reporta la de mayor edge walk-forward. (SL-R8)

- [ ] T7. `optimizer.py`: orquesta parse→search→backtest→ablation→elimina→ordena.
      Test: sobre fixture pequeño devuelve estrategia óptima que ELIMINA paso
      inútil y ORDENA por importancia. (SL-R3..R9,R13)

- [ ] T8. `strategy_store.py`: emite estrategia optimizada como objeto + doc.
      Test: objeto tiene pasos/importancia/contribución/edge; NO escribe leyes.
      (SL-R9,R12)

- [ ] T9. Candados + integración: grep anti-bot limpio en src/strategy_lab/;
      test no_wallclock cubre strategy_lab; grep unidireccional Memoria→strategy_lab
      ausente; pytest suite sin nuevos rojos. (SL-R11,R12)

- [ ] T10. Smoke E2E: corre sobre estrategia propuesta fixture + DB poblada y
      devuelve estrategia optimizada con pasos ordenados, importancia por paso y
      edge walk-forward. (SL-R2..R9)

Bitácora:
- Spec propuesto 2026-07-27 por Rubén tras validar Discovery Engine: crear un
  SEGUNDO laboratorio (Strategy Lab) que perfecciona la estrategia propuesta en
  vez de inventar. Separado de Discovery (que descubre leyes del mercado).
- Misión: tomar estrategia de Rubén, descomponer en pasos, probar miles de
  variantes, eliminar pasos inútiles, ordenar por importancia estadística,
  devolver versión óptima basada en evidencia.
- La geometría óptima del estocástico (Ley #34 tipo) la descubre Discovery
  (descompone indicador en variables, R2 ampliado); Strategy Lab la CONSUME como
  paso y mide su contribución. El orden óptimo (A/B/C) también se descubre.
- Mantiene separación de 6 responsabilidades: Laboratorio observa, Discovery
  descubre, Memoria recuerda, Strategy Lab perfecciona, Scanner consulta,
  Estrategia decide.
