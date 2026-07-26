# Tasks — Capa de ALERTA TEMPRANA del SPIKE (cinemática del estocástico M15)

> Implementación tras aprobación SDD. Orden sugerido. Cada task marca `[x]` al cerrar.
> Regla de oro: esta capa es ADITIVA. NO se toca la lógica de promoción a SPIKE de
> `strat_f_spike_wyckoff_phase_a`. NO se modifican sus requirements/design/tasks.

## T-EA1 — Módulo puro `stoch_early_alert.py` (R-EA4)
- [ ] Crear `src/stoch_early_alert.py` (evaluador puro, sin I/O).
- [ ] Función `compute_early_alert(k_vals, d_vals, direction, buf_par)` que devuelva
  `EarlyAlertResult` con: `pendiente_k`, `pendiente_d`, `aceleracion`, `angulo`,
  `proyeccion_velas`, `convergencia`, `puntaje`, `percentil_par`, `ventana_proy`,
  `es_default`, `activa`.
- [ ] Pendiente (R-EA4.1): `(valor_actual − valor_hace_N) / N` para %K y %D, con N
  dado por el búfer del par (R-EA6 / D-EA3).
- [ ] Aceleración (R-EA4.2): `pendiente_actual − pendiente_de_hace_P` velas.
- [ ] Ángulo (R-EA4.3): `arctan(pendiente) × 180/π` para %K (y %D).
- [ ] Proyección (R-EA4.4): `(valor_actual − 20) / pendiente_actual` (CALL) o
  `(80 − valor_actual) / |pendiente_actual|` (PUT). Tratar como probabilidad.
- [ ] Convergencia (R-EA4.5): tasa de achique de `|%K−%D|` en el tiempo.
- [ ] Test unitario: las 5 cantidades se calculan y son finitas/positivas en un
  caso sintético claro (R-EA10(b)).

## T-EA2 — Puntaje combinado adaptativo (R-EA5 / D-EA2)
- [ ] Normalizar cada señal a sub-score en [0,1] con referente RELATIVO al par
  (no corte absoluto): pendiente caída vs referente, aceleración opuesta al
  impulso, ángulo/90, proyección vs ventana_par, convergencia vs histórico.
- [ ] Pesos FIJOS 1/5 para esta versión (R-EA5): el ajuste por "ratio de aciertos"
  queda POSTPUESTO (requiere vincular cada alerta con el outcome real de la
  operación, conexión no diseñada). NO implementar pesos adaptivos ahora.
- [ ] Umbral = percentil 90 del rango histórico de puntajes del par (decil alto del
  búfer de sesión). Sin historial → valor por defecto + `es_default=True`.
- [ ] `activa = puntaje >= percentil_par`.
- [ ] Test (R-EA10(c)): señales débiles vs historial del par → NO activa; señales
  fuertes (decil alto) → SÍ activa.

## T-EA3 — Ventana de proyección adaptativa (R-EA6 / D-EA3)
- [ ] Medir en el búfer del par la duración histórica `T_par` (zona extrema →
  cruce confirmado) en sus últimas M ocasiones.
- [ ] Ventana de proyección actual = `T_par`; proyección interpretada contra él.
- [ ] Sin historial (M insuficiente) → ventana = lookback=15, `es_default=True`.
- [ ] Test (R-EA10(d)): con historial refleja duración histórica; sin historial
  usa 15 y marca `es_default=True`.

## T-EA4 — Búfer persistente por símbolo (R-EA8 / D-EA6 / R-EA11 / D-EA7, ALT B)
- [ ] Estructura en memoria `dict[sym] -> deque` de últimos puntajes/duraciones
  del par al pasar por zona extrema (ventana rodante, ~50 ocasiones).
- [ ] El bot alimenta el búfer con los puntajes que él mismo calcula en la sesión.
- [ ] **ALT B ELEGIDA (R-EA11):** persistencia en `data/early_alert/<SYM>.json`.
- [ ] Escritura atómica: escribir a `<SYM>.json.tmp` y `os.replace` al final; NUNCA
  escritura directa sobre el `.json` (anti-corrupción por crash). Test: simular
  crash a mitad de escritura deja el `.json` previo intacto.
- [ ] Frecuencia de volcado: cada K=10 alertas del par y al cerrar sesión; no en
  cada ciclo.
- [ ] Carga al arrancar: si `<SYM>.json` existe y es JSON válido → reconstruye el
  búfer; si no existe o corrupto → arranca vacío (`es_default=True`).
- [ ] Test: búfer vacío → `es_default=True`; tras acumular N y volcar, el archivo
  existe y al recargar reproduce el percentil/ventana del par (no es_default).

## T-EA5 — Integración en `evaluate_strat_f` (R-EA3 / D-EA4 / D-EA1)
- [ ] Añadir campo `early_alert: Optional[EarlyAlertResult] = None` a
  `StratFEvaluation` (NO cambia `has_signal`/`entry_mode`/`spike`).
- [ ] En `evaluate_strat_f`, tras R2/R2-bis, invocar `compute_early_alert(...)` con
  las `k_vals`/`d_vals` de `compute_stoch`, evaluado sobre `candles_15m[-1]` (M15
  abierta) + `candles_1m` (lookback=15). Resultado en `early_alert`.
- [ ] NO promover a SPIKE por `early_alert`: la promoción sigue exigiendo
  R2+R2-bis+R3+R3-bis juntos.
- [ ] Test (R-EA10(a)): alerta presente PERO sin cruce confirmado → `has_signal`
  sigue False / `entry_mode` sigue REBOUND (R-EA1/R-EA2).

## T-EA6 — Caja negra trazable (R-EA7 / R-EA9 / D-EA5)
- [ ] En `scanner.py`, al armar `strategy_details`, incluir `early_alert` de
  `f_eval` cuando `activa=True` (pendiente_k/d, aceleracion, angulo,
  proyeccion_velas, convergencia, puntaje, percentil_par, ventana_proy, es_default).
- [ ] Confirmar que NO se altera `has_signal` ni se envía orden por la alerta.
- [ ] Test (R-EA10(e)): alerta generada se registra en caja negra y NO altera
  `has_signal`.
- [ ] Test (R-EA10(b2)): proyección CALL simétrica — %K CALL ya por encima de 20 y
  BAJANDO (valor_actual=24, pendiente=−2):
  - fórmula VIEJA (sin abs): `(24 − 20) / (−2)` = −2.0 (el bug, "−2 velas").
  - fórmula NUEVA (con abs): `|24 − 20| / |−2|` = 2.0 (positivo, correcto).
  El test DEBE verificar `proyeccion_velas == 2.0` (no 4.0, no −2.0). Ídem PUT con
  %K por encima de 80 y subiendo. Cubre la corrección del bug de fórmula sin valor
  absoluto.

## T-EA7 — INTRAVELA (R-EA3 / R-EA10(f))
- [ ] Confirmar que la alerta se evalúa sobre la M15 abierta + M1 lookback=15, no
  solo al cierre. Reusar el mismo mecanismo de R10 del spec vigente.
- [ ] Test (R-EA10(f)): inyectar M15 abierta + 15 velas M1 donde la cinemática
  anticipa el giro, y confirmar que `early_alert.activa=True` se detecta ANTES de
  cerrar la M15.

## T-EA8 — Regresión y nuevos tests (R-EA10)
- [ ] Ejecutar `pytest tests/test_strat_f_spike.py tests/test_strat_f_spike_wyckoff.py tests/test_stoch_exhaustion.py tests/test_stochastic_zones.py tests/test_stochastic_m15.py -m "not slow"` → TODO VERDE.
- [ ] Añadir `tests/test_stoch_early_alert.py` cubriendo (a)-(f) de R-EA10.
- [ ] Verificar que el spec vigente no perdió señales REBOUND/SPIKE por efecto
  colateral de añadir el campo `early_alert`.

## T-EA9 — Verificación final y cierre SDD
- [ ] `init.ps1` en verde (o equivalente pytest del proyecto).
- [ ] Actualizar `progress/current.md` con el resumen.
- [ ] Marcar la feature nueva `done` en `feature_list.json` (tras aprobar reviewer).
- [ ] Commit con `git add` de archivos ESPECÍFICOS (regla: nunca -A). Los specs
  nuevos en `specs/strat_f_spike_early_alert/` + `src/stoch_early_alert.py` +
  `src/strat_fractal.py` (solo el campo) + `src/scanner.py` (solo strategy_details)
  + `tests/test_stoch_early_alert.py`.
