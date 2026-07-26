# Requirements — Capa de ALERTA TEMPRANA del SPIKE (cinemática del estocástico M15)

> Feature: `strat_f_spike_early_alert` (capa ADICIONAL y COMPLEMENTARIA al spec
> `strat_f_spike_wyckoff_phase_a`). NO reemplaza, NO modifica, NO debilita
> ningún requirement de ese spec. Es una señal de ATENCIÓN que anticipa el giro
> del estocástico M15 ANTES de que el cruce confirmado (R2) y la separación
> adaptativa (R2-bis) se cumplan.
>
> Relación con el spec vigente: esta capa se alimenta de las MISMAS series
> `k_vals`/`d_vals` que `stochastic_m15.compute_stoch` ya expone hoy para R2/R2-bis,
> y se evalúa en el MISMO punto de inserción intravela (R10): la vela M15 EN
> CURSO usando la ventana M1 (lookback=15). Su salida es una MARCA, no una señal
> de entrada.

## R-EA1 — Naturaleza de la capa: ALERTA, no disparador
EL sistema DEBE tratar la salida de esta capa como una **marca de atención
puramente informativa**. La capa NO DEBE, bajo ninguna circunstancia, promover
una entrada SPIKE por sí sola, ni habilitar `entry_mode="SPIKE"`, ni forzar
`has_signal=True`. La promoción a SPIKE sigue exigiendo que R2 (cruce M15
confirmado) + R2-bis (separación %K/%D adaptativa) + R3 (M5 alineado) + R3-bis
(M5 agotado) se cumplan JUNTOS en el mismo instante, exactamente como rige en
`strat_f_spike_wyckoff_phase_a`. Esta capa solo AVISA que esos requisitos están
por cumplirse.

## R-EA2 — Prohibición explícita de "entrar más temprano"
EL sistema DEBE prohibir que la marca de alerta se use para saltarse la espera
de confirmación real del spec vigente. En particular, la alerta NO DEBE:
(a) reducir o anular el requisito `cross_ago >= 1` de R2;
(b) relajar el umbral de separación adaptativa de R2-bis;
(c) sustituir la alineación M5 (R3) ni el agotamiento M5 (R3-bis).
Esta prohibición existe para evitar reproducir la pérdida de $1 (M15 decía
"baja" pero M5 subía): la alerta anticipa, pero la CONFIRMACIÓN de R2/R2-bis/R3/
R3-bis es lo único que habilita operar. El código DEBE llevar un comentario que
lo recuerde y un test que verifique que, con alerta presente pero SIN cruce
confirmado, el SPIKE no se promueve.

## R-EA3 — Uso principal: chequeo INTRAVELA (R10 del spec vigente)
CUANDO el scanner evalúa STRAT-F en su ciclo normal (que ya trae `candles_1m`),
el sistema DEBE evaluar esta capa de alerta sobre la **vela M15 en curso** usando
las velas M1 de su ventana (lookback=15), igual que el spec vigente lo hace para
R2/R2-bis/R10. La alerta debe poder detectarse ANTES de que la vela M15 cierre,
no solo al cierre. El mecanismo es DENTRO de `evaluate_strat_f` (o un helper que
éste invoca), alimentado por las `k_vals`/`d_vals` de `compute_stoch`, evaluado
sobre `candles_15m[-1]` (M15 abierta) + `candles_1m` (ventana).

## R-EA4 — Cinemática del estocástico M15 (las 5 piezas matemáticas)
CUANDO el sistema evalúa la alerta, DEBE computar estas 5 cantidades a partir de
las series `k_vals`/`d_vals` (y sus equivalentes para %D), NUNCA como umbrales de
puntos fijos — todas relativas/adaptativas (misma doctrina anti-umbral-fijo del
spec vigente para la zona de precio y la separación %K/%D):
1. **PENDIENTE** de %K y %D por vela: `(valor_actual − valor_hace_N) / N`, con N
   ventana relativa al par (ver R-EA6). Si la pendiente se acerca a cero, la
   línea se está aplanando (primera señal de agotamiento de impulso).
2. **ACELERACIÓN** (segunda derivada): `pendiente_actual − pendiente_de_hace_P`
   velas. Si %K sigue subiendo pero su pendiente está bajando, pierde fuerza
   ANTES de girar — es la señal de alerta temprana real.
3. **ÁNGULO** en vez de pendiente cruda: `arctan(pendiente) × 180/π`. Vuelve la
   medida COMPARABLE entre pares sin importar su escala (coherente con la
   doctrina de "todo adaptativo/relativo" ya vigente).
4. **PROYECCIÓN** de velas hasta tocar la línea 20/80: `|valor_actual − 20| /
   |pendiente_actual|` para CALL (o `|valor_actual − 80| / |pendiente_actual|`
   para PUT). AMBAS fórmulas usan valor absoluto para que el resultado sea
   SIEMPRE un número de velas POSITIVO (no existen "−3 velas"). La simetría es
   obligatoria: la fórmula de CALL NO debe usar `valor_actual − 20` sin valor
   absoluto (daría negativo cuando %K ya sobrepasó 20, caso real en cruces que
   rebotan). Es una **PROBABILIDAD**, no certeza ni confirmación dura; el diseño
   DEBE tratarla siempre como estimación, nunca como gatillo. Si la pendiente es
   ~0 (línea plana) la proyección tiende a infinito → el sistema la limita a la
   ventana de proyección del par (R-EA6) y la marca como "sin convergencia clara".
5. **VELOCIDAD DE CONVERGENCIA** %K/%D: cómo cambia la separación `|%K−%D|` en el
   tiempo (no solo su valor actual, sino si se achica cada vez más rápido). Es
   la dinámica de R2-bis, mirada en movimiento, no como valor umbral.

## R-EA5 — Activación por PUNTAJE COMBINADO (adaptativo, no números fijos)
CUANDO el sistema combina las 5 señales de R-EA4, DEBE usar un **puntaje
combinado** donde cada señal aporta puntos y, si el total supera un umbral, se
prende la alerta. PERO ni los PESOS de cada señal ni el UMBRAL de activación
pueden ser números universales fijos (eso violaría la doctrina del spec). Ambos
DEBEN calcularse de forma RELATIVA comparando el puntaje actual contra el rango
de puntajes que ESE MISMO PAR tuvo en sus últimas N veces que pasó por una zona
extrema similar (su propio historial reciente). Método concreto (ver design D-EA2):
- Cada señal se normaliza a un score en [0,1] usando un referente relativo del
  par (no un corte absoluto).
- **PESOS FIJOS POR AHORA (1/5 cada uno):** el spec DECLARA EXPLÍCITAMENTE que el
  ajuste de pesos por "ratio de aciertos" de cada señal PARA ESE PAR queda
  **POSPUESTO para una versión futura**. En esta versión los pesos son SIEMPRE
  iguales (1/5) para las 5 señales. La razón: determinar si una alerta pasada
  "acertó" requiere vincular cada alerta con el resultado REAL de la operación que
  vino después (el SPIKE que se confirmó con R2/R2-bis/R3/R3-bis y su outcome
  ganó/perdió), y ESA CONEXIÓN NO ESTÁ DISEÑADA en este spec (ni en el vigente).
  Prometer pesos adaptivos por aciertos sin ese puente sería dejar la promesa a
  medias. Cuando se implemente, vivirá en su propia fase con su propia tarea; no
  se introduce aquí.
- El umbral de activación es un **percentil** del rango histórico de puntajes del
  par (percentil 90 por decisión del usuario: el par activa cuando su puntaje
  entra en el decil alto de sus propias veces previas), NO un "60 de 100" universal.
El sistema NO DEBE activar la alerta por acumulación de señales si el puntaje no
supera ese percentil relativo al par.

## R-EA6 — Ventana de proyección ADAPTATIVA (sin número fijo de velas)
CUANDO el sistema calcula la proyección de R-EA4.4, DEBE determinar la ventana de
anticipación (cuántas velas de aviso tiene sentido) de forma ADAPTATIVA al par,
sin fijar un número universal. Método concreto (ver design D-EA3):
- El sistema MIDE, en el historial de ESE MISMO PAR, cuánto tardó en completar el
  recorrido desde la zona extrema (20/80) hasta el cruce confirmado (%K cruza %D
  con cross_ago>=1) en sus últimas M ocasiones.
- Esa duración histórica se usa como REFERENCIA para la ventana de proyección
  actual: la alerta avisa con una anticipación anclada al ritmo propio del par,
  no a un "3 velas" universal.
- Si el par no tiene historial suficiente, el sistema usa la ventana intravela
  por defecto (lookback=15 de M1, coherente con R10) y lo marca como "ventana por
  defecto, sin historial".

## R-EA7 — Qué hace el sistema con la marca de alerta (REQUIREMENT CONCRETO)
CUANDO la alerta se genera (puntaje supera el percentil del par, R-EA5), el
sistema DEBE:
(a) **Registrarla en la caja negra** como campo de auditoría puramente
    informativo (`early_alert` con las 5 cantidades de R-EA4, el puntaje, el
    percentil y la ventana de proyección de R-EA6) en `scan_candidates` /
    `strategy_details`, con `agent_tag` respetado.
(b) **NO disparar ninguna acción del bot**: la alerta NO envía orden, NO cambia
    `has_signal`, NO promueve a SPIKE, NO modifica el score de entrada de forma
    que lo habilite.
(c) **NO hacer que el scanner evalúe el par con más frecuencia**: el ciclo de scan
    no se acelera por la alerta; se sigue evaluando en el ciclo normal del bot.
    La alerta es puramente INFORMATIVA para revisión humana y para que el
    operador (o el modo observación del SPIKE ya existente) vigile ese par de
    cerca en el siguiente ciclo normal, sin cambiar la cadencia del scanner.
El sistema DEBE tratar la alerta como un faro, no como un gatillo.

## R-EA8 — Sin I/O en el evaluador puro
EL sistema DEBE mantener la evaluación de la alerta como cálculo puro (sin red):
recibe `k_vals`/`d_vals` (ya disponibles de `compute_stoch`) y, para el
historial relativo del par, usa un búfer en memoria de los últimos puntajes
propios del par (no consulta la base de datos ni la red en cada ciclo; el búfer
se alimenta de los propios cálculos previos del bot en la sesión). El tamaño del
búfer es relativo (ver design D-EA2) y se descarta con la sesión.

## R-EA9 — Trazabilidad en la caja negra
CUANDO la alerta se genera, el sistema DEBE registrar en `scan_candidates` el
bloque `early_alert` con: `pendiente_k`, `pendiente_d`, `aceleracion`, `angulo`,
`proyeccion_velas`, `convergencia`, `puntaje`, `percentil_par`, `ventana_proy`,
`es_default` (sin historial), para auditoría post-mortem. El `agent_tag`
(BOT/WATCHDOG/HUMAN) se respeta sin cambios.

## R-EA10 — Tests de regresión y nuevos casos
EL sistema DEBE mantener verdes los tests del spec vigente
(`test_strat_f_spike.py`, `test_strat_f_spike_wyckoff.py`, `test_stoch_exhaustion.py`)
y AÑADIR tests que cubran:
(a) Con alerta presente PERO sin cruce M15 confirmado → el SPIKE NO se promueve
    (R-EA1/R-EA2): `has_signal` sigue False / `entry_mode` sigue REBOUND.
(b) Las 5 cantidades de R-EA4 se calculan y están en el rango esperado (pendiente
    finita, ángulo en grados, proyección positiva hacia la línea 20/80).
(b2) **Proyección CALL simétrica (corrección de bug):** con %K de CALL YA por
    encima de 20 y BAJANDO, p.ej. `valor_actual=24`, `pendiente_actual=-2`:
    - fórmula VIEJA (sin valor absoluto): `(24 − 20) / (−2)` = `4 / −2` = **−2.0**
      (el bug: "−2 velas" no tiene sentido).
    - fórmula NUEVA (con valor absoluto): `|24 − 20| / |−2|` = `4 / 2` = **2.0**
      (positivo, correcto).
    El test DEBE verificar `proyeccion_velas == 2.0` (no 4.0, no −2.0). Ídem PUT
    con %K por encima de 80 y subiendo: `|valor_actual − 80| / |pendiente|`.
(c) Puntaje combinado: con señales débiles (puntaje bajo vs historial del par) →
    NO se activa la alerta; con señales fuertes (puntaje en decil alto del par) →
    SÍ se activa.
(d) Ventana de proyección adaptativa: con historial del par, la ventana refleja la
    duración histórica; sin historial, usa lookback=15 y marca `es_default=True`.
(e) La alerta generada se registra en la caja negra (`early_alert` presente) y NO
    altera `has_signal` (R-EA7).
(f) INTRAVELA (R-EA3): la alerta se detecta sobre la M15 abierta + M1 lookback=15,
    no solo al cierre.

## R-EA11 — Persistencia del historial del par (ELEGIDA: ALT B)
El historial relativo del par (búfer de sesión de R-EA8) alimenta el umbral de
percentil (R-EA5) y la ventana de proyección (R-EA6). El usuario ELIGIÓ **ALT B
(archivo JSON liviano por símbolo en disco)** como mecanismo de persistencia.
Esto sobrevive reinicios del bot sin la pesadez de acoplarse a la base de datos
grande, y es migrable a ALT C en el futuro si se retoma el ajuste de pesos por
aciertos. Alternativas consideradas (para contexto):

- **ALT A — Solo en memoria:** el búfer vive en RAM y se descarta al cerrar.
  *Ventaja:* cero I/O. *Desventaja:* al reiniciar el par arranca en `es_default`
  (umbral por defecto, ventana=15) y, como las señales SPIKE son raras, casi
  siempre operaría en modo default — justo lo que se quiso evitar.
- **ALT B (ELEGIDA) — Archivo JSON liviano por símbolo:** al cerrar (o cada K
  alertas) se vuelca el búfer de ese par a `data/early_alert/<SYM>.json`; al
  arrancar se recarga.
  *Ventaja:* el referente del par sobrevive reinicios; arranca "caliente" con su
  percentil y ventana reales desde la primera vela. Archivo pequeño, portable, sin
  DB.
  *Desventaja:* hay I/O de disco (poco, pero en el ciclo); riesgo de JSON corrupto
  si el bot muere a mitad de escritura (mitigar con write-temp + rename atómico);
  el histórico puede volverse stale si el régimen del par cambia (mitigar con
  TTL/ventana rodante).
- **ALT C — Base de datos existente del bot:** tabla `early_alert_history` keyed
  por símbolo en la DB del bot.
  *Ventaja:* centralizado, sobrevive reinicios, alimenta futuro ajuste por aciertos
  leyendo el outcome real. *Desventaja:* acopla a la capa de persistencia, requiere
  esquema/migración, más pesado que JSON para un búfer pequeño y rodante. Se deja
  como migración futura desde ALT B.

Comportamiento de ALT B (obligatorio en la implementación):
- Ruta: `data/early_alert/<SYM>.json` (SYM en mayúsculas, sin barras).
- Escritura: SIEMPRE write-temp (`<SYM>.json.tmp`) + `os.replace` atómico; NUNCA
  escritura directa sobre el archivo final (evita JSON corrupto si hay crash).
- Frecuencia de volcado: cada K alertas del par (p.ej. K=10) y al cerrar sesión;
  no en cada ciclo (no saturar I/O).
- Carga: al arrancar, si el archivo existe y es JSON válido, se reconstruye el
  búfer; si no existe o está corrupto, se arranca vacío (`es_default=True`) y se
  sobrescribe en el próximo volcado válido.
- TTL/ventana rodante: el búfer recuerda solo las últimas N ocasiones (p.ej. 50);
  se descartan las más viejas al volcar, para no volverse stale.
El umbral de percentil 90 (R-EA5) y la ventana adaptativa (R-EA6) NO cambian por
ALT B: solo cambia que el historial se carga desde disco en vez de solo RAM.
