# Design — Capa de ALERTA TEMPRANA del SPIKE (cinemática del estocástico M15)

## Contexto
El spec `strat_f_spike_wyckoff_phase_a` ya promueve a SPIKE solo cuando R2 (cruce
M15 confirmado) + R2-bis (separación %K/%D adaptativa) + R3 (M5 alineado) + R3-bis
(M5 agotado) se cumplen juntos. Esa es una confirmación "dura" que llega tarde: el
cruce ya ocurrió y las líneas ya se abrieron. Esta capa NUEVA es un observador de
la *cinemática* del estocástico M15 que avisa "este par está a punto de cumplir
R2/R2-bis" unas velas antes, usando la misma inserción intravela (R10): la vela
M15 en curso + ventana M1 (lookback=15). No opera, no adelanta la entrada, no
toca la cadencia del scanner.

## Decisiones técnicas

### D-EA1 — Reutilizar las series ya expuestas (NO duplicar)
`stochastic_m15.compute_stoch(candles_15m)` ya devuelve `k_vals`/`d_vals` (series
de %K/%D). Esta capa se alimenta de esas series tal cual, evaluadas sobre
`candles_15m[-1]` (M15 abierta) + `candles_1m` (ventana intravela), exactamente
como hoy lo hace R2/R2-bis/R10. No se vuelve a calcular el estocástico; se
reusa. El helper vive en un módulo puro nuevo (p.ej. `stoch_early_alert.py`) para
que el spec vigente no se toque.

### D-EA2 — Puntaje combinado ADAPTATIVO (R-EA5), método concreto
Cada una de las 5 señales de R-EA4 se convierte en un sub-score en [0,1] usando un
referente RELATIVO al par, no un corte absoluto:
- **Pendiente** (`pend_k`, `pend_d`): sub-score = `|pendiente_actual| / max(|pendiente_historica_par|, ε)`.
  Cerca de 0 (aplanándose) da sub-score bajo, pero el aviso de alerta usa el
  *cambio de signo / caída relativa*, no el valor bruto: el sub-score de
  "aplanamiento" = `1 − (|pendiente_actual| / |pendiente_ref_par|)` cuando la
  pendiente cae respecto a su referente reciente del par.
- **Aceleración**: sub-score = `|aceleracion| / max(|aceleracion_ref_par|, ε)`,
  pero solo cuenta como alerta si la aceleración es de signo opuesto al impulso
  (ej. %K sube pero aceleración negativa = pierde fuerza).
- **Ángulo**: sub-score = `|angulo| / 90` (el ángulo ya es comparable entre pares
  por el arctan; 90° = vertical).
- **Proyección** (R-EA4.4 / R-EA6): sub-score = `1 − clamp(proyeccion_velas /
  ventana_proy_par, 0, 1)`. Cuanto menos velas faltan para tocar 20/80, más alto.
- **Convergencia** %K/%D: sub-score = velocidad de achique de `|%K−%D|` relativa a
  la velocidad histórica del par.
PESOS: **FIJOS en 1/5 cada uno para esta versión** (ver R-EA5). El ajuste de
pesos por "ratio de aciertos" de cada señal PARA ESE PAR queda **POSPUESTO**:
determinar si una alerta pasada "acertó" requiere vincularla con el resultado real
de la operación que vino después (el SPIKE confirmado con R2/R2-bis/R3/R3-bis y su
outcome), y ESA CONEXIÓN NO está diseñada aquí ni en el spec vigente. No se promete
peso adaptivo sin ese puente. Cuando se implemente vivirá en su propia fase.
UMBRAL de activación: **percentil 90 del rango histórico de puntajes del par** (decisión
del usuario). El bot mantiene en memoria (búfer de sesión, R-EA8) los últimos `N`
puntajes que ese par generó al pasar por zonas extremas similares. La alerta se
activa cuando el puntaje actual entra en el decil alto (>= percentil 90) de ese
rango propio. NO hay "60 de 100" universal. Sin historial suficiente (N < mínimo),
el umbral cae a un valor por defecto documentado y se marca `es_default=True`.

### D-EA3 — Ventana de proyección ADAPTATIVA (R-EA6), método concreto
El bot MIDE en el historial de ESE MISMO PAR cuántas velas tardó, en sus últimas
`M` ocasiones, en ir desde que %K tocó la zona extrema (20/80) hasta que el cruce
confirmado (R2) se dio. Esa duración histórica `T_par` es la REFERENCIA: la
ventana de proyección actual = `T_par` (anclada al ritmo del par). La proyección de
R-EA4.4 se interpreta contra `T_par`: "faltan X de las T_par velas típicas del
par". Sin historial (M insuficiente) → ventana = lookback=15 (coherente con R10) y
`marca es_default=True`. El historial se lee del MISMO búfer de sesión de R-EA8
(últimas veces que el par pasó por zona extrema), no de la base de datos.

### D-EA4 — Integración con `evaluate_strat_f` y el modo observación
Dentro de `evaluate_strat_f`, tras el cálculo de R2/R2-bis (y en paralelo, no en
lugar de), se invoca `compute_early_alert(k_vals, d_vals, direccion, buf_par)`.
Su salida (`EarlyAlertResult`: las 5 cantidades + puntaje + percentil + ventana +
es_default + activa: bool) se adjunta al `StratFEvaluation` en un campo
`early_alert` (nuevo, opcional, None cuando no aplica). NO cambia `has_signal`,
`entry_mode` ni `spike`. El scanner graba `early_alert` en `strategy_details` de
`scan_candidates` cuando `activa=True` (R-EA7/R-EA9). El modo observación del SPIKE
ya existente puede leer `early_alert` para enriquecer su desglose, pero la alerta
nunca lo hace operar.

### D-EA5 — Qué hace el sistema con la marca (R-EA7), sin ambigüedad
La marca es **puramente informativa**:
1. Se escribe en la caja negra (`early_alert` en `strategy_details`) para revisión
   humana y auditoría.
2. NO envía orden, NO cambia `has_signal`, NO promueve a SPIKE, NO altera el score
   de forma habilitante.
3. NO acelera el ciclo del scanner: el par se sigue evaluando en el ciclo normal
   del bot. El operador (o el modo observación) lo vigila de cerca en el siguiente
   ciclo normal; la cadencia no cambia.
Es un faro, no un gatillo. Queda explícito para que nadie lo use como disparador.

### D-EA6 — Búfer de sesión (R-EA8), sin I/O
El historial relativo del par vive en un `dict` en memoria keyed por símbolo, que
el bot alimenta con los puntajes que él mismo calcula en la sesión (últimas N
veces que el par pasó por zona extrema). No consulta BD ni red. Tamaño N relativo
(p.ej. últimas 50 ocasiones, o el que el rendimiento permita). Se descarta al
cerrar sesión. Si el símbolo no está en el búfer, la alerta usa valores por defecto
y marca `es_default=True`.

### D-EA7 — Persistencia del historial (R-EA11, ELEGIDA: ALT B)
El usuario eligió **ALT B**: archivo JSON liviano por símbolo en
`data/early_alert/<SYM>.json`. El búfer de D-EA6 se vuelca a disco y se recarga al
arrancar, así el referente del par sobrevive reinicios (arranca "caliente").
Método concreto de I/O (obligatorio):
- **Escritura atómica:** SIEMPRE escribir primero a `<SYM>.json.tmp` y luego
  `os.replace(tmp, final)` (renombrado atómico del SO). NUNCA escribir directo
  sobre el `.json` final: si el bot crashea a mitad de escritura, el archivo previo
  queda intacto y el corrupto queda solo como `.tmp` (se ignora al cargar).
- **Frecuencia:** volcar cada K alertas del par (p.ej. K=10) y al cerrar sesión; NO
  en cada ciclo (evitar saturar I/O de disco).
- **Carga:** al arrancar, si `<SYM>.json` existe y es JSON válido → reconstruye el
  búfer; si no existe o falla el parse → arranca vacío (`es_default=True`) y lo
  sobrescribe en el próximo volcado válido.
- **Ventana rodante:** el búfer guarda solo las últimas N ocasiones (p.ej. 50); al
  volcar se descartan las más viejas (anti-stale por cambio de régimen del par).
ALT C (DB del bot) queda como migración futura desde ALT B si se retoma el ajuste
de pesos por aciertos. El percentil 90 y la ventana adaptativa NO cambian.


## Riesgos y mitigaciones
- **Reproducir "entrar muy pronto" (pérdida de $1):** prohibido explícitamente en
  R-EA2 y testeado en R-EA10(a). La alerta no relaja R2/R2-bis/R3/R3-bis.
- **Números fijos disfrazados:** el UMBRAL se calcula del historial del par
  (percentil 90, D-EA2/D-EA3), no se inventa. Los PESOS son 1/5 fijos por esta
  versión (R-EA5 lo declara explícito, postergando el ajuste por aciertos); no hay
  peso fijo camuflado. Test R-EA10(c) verifica que señales débiles vs el
  par no activan.
- **Costo de cómputo:** el búfer es en memoria y las 5 cantidades son O(ventana)
  sobre series ya calculadas; costo despreciable frente al pipeline existente.
- **Falsas alarmas:** el percentil del par (no un corte universal) las acota; el
  modo observación existente sirve para medir la tasa de falsos positivos con
  datos reales antes de cualquier uso operativo.
- **Regresión:** los tests del spec vigente deben quedar verdes; esta capa es
  aditiva y no toca `strat_fractal` más allá de añadir el campo `early_alert`.
