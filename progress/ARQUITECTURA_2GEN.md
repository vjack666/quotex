# ARQUITECTURA 2ª GENERACIÓN — Memoria del proyecto (separada de la memoria de SMC)

> Archivo de memoria APARTE para el proyecto QUOTEX 2ª gen (observador/laboratorio/atlas).
> NO modifica la memoria del agente ni nada de SMC-SYSTEMS. Creado 2026-07-27.

## Decisión de arquitectura (Ruben, 2026-07-27)
El descubrimiento más importante del laboratorio NO es una estrategia nueva: es un
CAMBIO DE ARQUITECTURA. Flujo anterior: Datos → Scanner → Señal → Operación.
Flujo nuevo (4 capas, como un investigador humano):

  Datos → Scanner científico → Memoria del Mercado → Estrategia → Operación

### Capa 1 — LABORATORIO = el científico
- Misión: DESCRUBIR. Hace millones de pruebas, propone hipótesis, valida, genera estadísticas.
- NO opera. NUNCA. NO genera código.
- Emite LEYES (#N) como CONOCIMIENTO: nombre, condiciones, probabilidad, confianza,
  mercados, timeframes, casos estudiados.
- Ejemplo Ley #17: "Muerte progresiva del empuje" — Prob 74.2%, Confianza Alta,
  Mercados EURUSD/GBPUSD, TF M1-M5, Casos 218.541.

### Capa 2 — SCANNER = el observador en vivo
- Misión: RECONOCER en tiempo real las leyes descubiertas por el laboratorio.
- NO dice "Compra". Dice: "La probabilidad de muerte del impulso acaba de aumentar"
  o "¿Estoy viendo exactamente el mismo comportamiento que en 18.000 casos históricos?".
- Pregunta a la Memoria: "¿Estoy viendo la Ley #17?" → Sí / No.
- Ya NO busca "ICT" ni "fractales" como fuente de verdad.

### Capa 3 — MEMORIA DEL MERCADO = el cerebro
- Vive el conocimiento PERMANENTE.
- No solo FVG/OB: guarda EPISODIOS (Atlas) + TABLA DE LEYES (#N).
- Ejemplo episodio: #52341 | Expansión fuerte | Agotamiento lento | Rebote 73% |
  Duración 19 velas | Contexto HTF | Resultado final.
- Con miles/millones de episodios + leyes vivas.

### Capa 4 — ESTRATEGIAS = los tomadores de decisiones
- Ya NO detectan el mercado. Solo hacen PREGUNTAS a la Memoria:
  "Muéstrame episodios parecidos" / "¿Cuál fue el resultado histórico cuando ocurrió esto?".
- La estrategia DECIDE con ese conocimiento.

## Ventaja clave (por qué vale la pena)
Hoy: si descubres una ley nueva, tienes que modificar el scanner (y 20 estrategias).
Con esta arquitectura: Laboratorio descubre ley → la guarda en Memoria → el scanner
aprende a reconocerla (por ID #N) → TODAS las estrategias la usan automáticamente.
NO hay que reescribir nada del scanner.

## "¿Podemos usar el laboratorio para corregir el setup?" → SÍ
El laboratorio reemplaza heurísticas REFUTADAS del scanner por LEYES VALIDADAS:
- ICT/FVG como fuente de verdad → REFUTADO (auditoría: WR base STRAT-F ~55%, AUC 0.477 = ruido).
- "El precio pierde presión y gira" → INCORRECTO: es MUERTE TOTAL del empuje (LAB-001).
- "Consume la zona antes de girar" → REFUTADO (LAB-003): el giro es EN el borde.
El setup se corrige mediante la Memoria (leyes validadas reemplazan heurísticas),
NO reescribiendo el scanner. Esa es la gracia.

## Mapeo a lo ya construido (no hay que reescribir)
- Observador (Fase A+B, 89.8k ep filmados, 2.82M filas traza) = Capa 2 en vivo
  (cuando se conecte LiveFeed real de Quotex).
- Atlas (episodes_eurusd_full.db) = parte de Capa 3 (episodios).
- Discovery Engine (specced, NO implementado) = genera las Leyes #N → tabla `leyes` de Capa 3.
- Estrategias (entry_decision_engine.py, entry_scorer.py del bot) = Capa 4 (preguntan a Memoria).

## Eslabones QUE FALTAN (roadmap de implementación)
A) Discovery Engine real → emite Ley #1 (muerte del empuje, 89.8k ep) como primer
   objeto en tabla `leyes`. CREA la Memoria como tabla de leyes, no solo episodios.
B) LiveFeed real conectado a pyquotex (hoy es stub) → Observador mira Quotex en vivo.
C) Puente scanner→Memoria: scanner pregunta "¿Ley #N?" sí/no; Memoria contesta prob
   actual. UNIDIRECCIONAL: scanner importa Memoria; Memoria NO importa scanner.
D) Candado sagrado: el laboratorio/observador/memoria NUNCA importan el bot (scanner/
   strat_fractal). Solo el bot los importa a ellos.

## Orden acordado (Ruben aprobó "continúa con todas las fases")
1. Discovery Engine (emite Leyes #N → Memoria). [spec listo, código pendiente]
2. LiveFeed real (P3).
3. Puente scanner→Memoria.
4. Setup del bot queda igual pero alimentado por leyes, no por heurísticas refutadas.
TODO SIN tocar la lógica de operación del bot (candado sagrado).

## NOTA CRÍTICA — Forex vs OTC (Ruben, 2026-07-27)
El laboratorio y el Atlas están entrenados SOLO con datos de FOREX (+ oro) prestados
de Dukascopy (SMC-SYSTEMS/data/raw). Verificado: los 42 parquets son EURUSD, GBPUSD,
XAUUSD, etc. — CERO archivos `_otc`. Pero el bot OPERA forex Y OTC (`*_otc` en
config.py / connection.py). HAY UN VACÍO: las Leyes #N descubiertas en forex NO están
validadas en OTC.

¿Por qué importa?
- OTC (Quotex) tiene spreads/falsa liquidez/distorsiones de market-maker que el forex
  interbancario (Dukascopy) NO tiene. La "muerte del empuje 72-77%" de forex puede
  NO replicarse igual en OTC. Aplicar leyes de forex a OTC sin validar = riesgo.

Opciones (qué podemos hacer en este caso):
1) BUSCAR datos OTC históricos (Dukascopy NO los tiene). Fuentes posibles:
   - Grabarlos nosotros desde Quotex en vivo (el LiveFeed real del bot ya los trae;
     hay que guardarlos, no solo operar). Es lento (se acumulan con el tiempo).
   - Proveedores OTC (ej. HistData no tiene OTC; algunos brokers dan histórico de
     opciones binarias, pero es escaso/ de pago).
2) CORRER el laboratorio en paralelo sobre OTC apenas tengamos datos (mismo motor,
   otro `asset`/fuente). El Discovery Engine ya es feed-agnostic: le das parquet OTC
   y emite Leyes #N_Otc. Se comparan con las de forex (universalidad OTC).
3) PUENTE cauteloso: mientras no haya datos OTC, las leyes de forex se usan en el
   scanner SOLO para activos forex; para OTC el scanner queda en "modo desconocido"
   (no aplica ley no validada). El scanner pregunta "¿Ley #1 validada en este
   mercado?" y la Memoria contesta sí/no por mercado. Esto preserva el candado de
   no operar sobre ley no validada.
4) VALIDACIÓN cruzada: cuando haya OTC, correr universalidad_lab.py sobre OTC y ver
   si la muerte del empuje da % similar. Si sí → la Ley #1 es universal (forex+OTC).
   Si no → nace Ley #1_OTC aparte (acumula, no borra).

Decisión pendiente: elegir fuente de datos OTC (opción 1) antes de pretender que el
setup OTC use las leyes. El laboratorio ya está listo para recibirlos; solo falta
el DATA. Mientras tanto: candado de que el scanner NO aplique leyes de forex a OTC
sin validación (opción 3).

## Estado al 2026-07-27 (verificado)
- LAB-001 CONGELADO (ley histórica, no editable; mejoras = LAB-0XX).
- Universalidad 9 pares: muerte 72-77%, zona grande 34-38% → comportamiento, no activo.
- Fase B: 89,832 episodios filmados barra a barra, 2.82M filas evolution, 58 tests verdes.
- Auditoría TEORIA_VS_EVIDENCIA.md: veredictos por afirmación (VALIDADA/REFUTADA/PENDIENTE).
- Discovery Engine: spec escrito (Capa 2.5), sin literales (comportamiento no parámetros).
- feature_list.json: observador_fase_b=done, discovery_engine=spec_ready.

## REFINAMIENTO DE DISEÑO (Ruben, 2026-07-27, durante review del SDD)
Cambio de paradigma: el Laboratorio respondía "¿mi hipótesis funciona?"; el
Discovery Engine responde "Mercado, ¿qué leyes escondes?". El motor BUSCA,
no confirma. Eso cambia todo el enfoque.

### Pipeline de la arquitectura (5 responsabilidades separadas)
  Laboratorio → Atlas (episodios) → Discovery Engine → Memoria (Leyes #N)
  → Scanner → Estrategia → Bot
- El SCANNER deja de ser "inteligente": es un CONSULTOR. Detecta un episodio y
  pregunta a la Memoria; la Memoria contesta "93% parecido a Ley #17, validada
  en Forex, NO en OTC" y el scanner decide NO aplicarla. Toda la estadística
  vive en la Memoria, no en el scanner.
- R12 es clave: la ley dejó de ser DOCUMENTO (LAB_001.md) y pasó a ser OBJETO
  (id, nombre, variables, condiciones, probabilidad, confianza, mercados,
  timeframes, casos, discovery_version). Conocimiento para máquinas: verdadera
  base de conocimiento.

### 5 refinamientos acordados (integrados en el SDD)
1) FUENTE, no solo MERCADO (extiende R9b): etiquetar la ley por FUENTE concreta
   (Dukascopy, Quotex OTC, Broker X, IC Markets). Dos brokers OTC pueden diferir.
   La ley queda validada para la fuente donde se demostró, no para "OTC" genérico.
2) CICLO DE VIDA de la ley (R13): estados EXPERIMENTAL → VALIDADA → FUERTE →
   UNIVERSAL → OBSOLETA. El mercado cambia; la ley cambia de estado, NUNCA se
   borra. Conserva todo el historial científico (grado de evidencia).
3) GRAFO de conocimiento (R14): la Memoria admite RELACIONES entre leyes
   (refuerza / contradice / requiere). El scanner pregunta "¿qué leyes apoyan
   esta situación?" en vez de "¿existe Ley #17?". La Memoria es un grafo, no
   solo una tabla. Modelo: tabla de aristas ley→ley con tipo y fuerza.
4) El candado forex/OTC se mantiene y se extiende con Fuente (punto 1).
5) Separación de responsabilidades como valor central: Laboratorio observa,
   Discovery descubre, Memoria recuerda, Scanner consulta, Estrategia decide.
   Cada pieza evoluciona sin romper las demás; múltiples estrategias consultan
   la MISMA Memoria (como científicos consultando la misma biblioteca).
