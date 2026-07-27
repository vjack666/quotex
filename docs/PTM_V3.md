# PTM v3 — Pressure Transition Model (CONGELADO 2026-07-27)

Estado: CONGELADO. Cambios = nueva versión mayor (PTM v4) con migración
justificada por evidencia del Atlas. Ver docs/FILOSOFIA.md para las razones.

Este documento define el MODELO DE DATOS del Observador (Capa 2).
No define código, ni tablas SQL concretas, ni implementación: define
CONCEPTOS y sus relaciones. La implementación que lo materialice debe
poder responder siempre: "¿esto describe el mercado o cómo lo medimos?"

---

## Unidad atómica: PressureEpisode

La unidad de observación NO es el scan ni la señal: es el EPISODIO —
la historia completa de un activo desde que deja de ser aburrido hasta
que su desenlace queda resuelto.

Regla estadística de oro (lección de la falsación del criterio (a)):
1 episodio = 1 observación. Jamás contar scans ni filas.

### Ciclo de vida (estados)

QUIET → EXPANSION → PRESSURE → BRAKE → TRANSITION → RESOLUTION
(+ ABORTED en cualquier punto: las no-historias son el grupo de control)

- El episodio nace cuando el mercado SALE DE QUIET (definición de
  "aburrido" por-activo y versionada), no cuando ya hay impulso:
  empezar tarde pierde media historia.
- El Observador vigila TODOS los activos del feed, no "candidatos".
  Esto elimina el sesgo de muestreo de la primera generación.
- Historial completo de transiciones de estado con timestamp = la
  narrativa cronológica del episodio.

### Bloques del episodio

1. PressureCurve — EL PROTAGONISTA FÍSICO
   Serie temporal de presión 0-1 (una medición por minuto).
   Impulso y freno NO son entidades separadas: el impulso es la fase
   alta y sostenida de la curva; el freno es su derivada negativa
   sostenida; la transición es cuando la derivada del bando contrario
   se vuelve positiva. Impulse/Brake son VISTAS calculadas, no tablas.

2. Participants — EL PORQUÉ
   seller_pressure, buyer_pressure, initiative (quién empuja),
   absorption (quién aguanta sin ceder), dominance.
   Se INFIEREN de velas/ticks (sin order flow real): nacen con
   confidence estructuralmente bajo y fórmulas versionadas. El modelo
   habla el idioma de compradores/vendedores aunque hoy se vean borrosos;
   cuando exista mejor instrumento, el bloque solo mejora su medición.

3. Energy — EXPERIMENTAL
   "¿Cuánto combustible le queda al movimiento?" (rápido≠con energía).
   Proxies candidatos: recorrido acumulado vs recorrido típico diario,
   tramos sin descanso, comparación con impulsos históricos del activo.
   El Atlas decide qué proxy asciende. Si ninguno discrimina, el bloque
   se vacía sin romper nada.

4. AttentionZone — CONCEPTO, no implementación
   zone_type abierto: 'fractal_band' (hoy), 'vwap', 'order_block',
   'pivot', ... con payload propio por tipo. La zona produce ATENCIÓN,
   nunca entradas. Guarda: banda, origen, edad, toques históricos y su
   desenlace (eficacia de la pared), serie de distancia precio-banda,
   tiempo dentro de la zona.

5. Transition — EL OBJETO DE ESTUDIO
   ts_inicio (primer síntoma), ts_confirmación (primer cierre contrario),
   duración, secuencia observada (qué apareció y en qué orden:
   achique → mechas → cierre contrario), completitud 0-5,
   ¿hubo pelea? (alternancia, solapamiento de rangos),
   transition_type: EXHAUSTION | COMPRESSION | ABSORPTION | CAPITULATION
   | FAKE_BREAK | CONTINUATION | UNKNOWN (todos nacen UNKNOWN; las
   familias las descubre el Atlas por clustering, no se presumen),
   score de transición (solo se GRABA; su poder predictivo se descubre,
   no se presume — no repetir el pecado del score viejo).

6. Timing — CONCEPTO de sincronía ("¿es ahora?")
   Juicio 0-1 + confidence + versión. Las lecturas de instrumentos van
   en instrument_readings(episode_id, ts, instrument, payload JSON):
   'stoch_full_14_3_3' hoy (pendiente, aceleración, ángulo, proyección,
   separación K-D — cinemática ya implementada en stoch_early_alert.py);
   mañana delta de volumen o velocidad de ticks SIN tocar el modelo.
   Test: si el estocástico muere, se modifica CERO tablas.

7. Expectations — EL CIENTÍFICO APUESTA POR ESCRITO
   En cada transición de estado el Observador registra su distribución
   esperada (p.ej. 70% transition / 25% continuation / 5% unknown),
   versionada. El delta esperado-vs-realidad es LA métrica de
   calibración del sistema. No decide: registra lo que esperaba.

8. Resolution — FÍSICA DEL DESENLACE (mercado puro, sin negocio)
   REBOUND | CONTINUATION | CHAOS | NEUTRALIZATION | FAILURE
   + curvas MFE/MAE continuas en ambas direcciones
   + duración y amplitud del rebote (¿murió a los 4 min? ¿vivió 15?)
   + velas completas de los 20-30 min posteriores
   + resolution_reason: REBOUND_FULL | REBOUND_SHORT (falla de
     sincronización) | NO_REBOUND (falla de tesis) | CONTINUATION_THROUGH
     | CHOPPY. Distinguir falla de reloj vs falla de teoría.

9. Narrative — TEXTO AUTO-GENERADO
   Al cerrar el episodio, texto en español plantillado desde los datos
   (nunca inventado): "Venía cayendo con 7 velas continuas, frenó 3
   minutos, aparecieron compradores en la zona, rebotó 11 minutos."
   Usos: Atlas legible/etiquetable por el humano; futuro: búsqueda
   semántica de episodios parecidos.

10. Snapshot de MarketMemory al nacer
    "BTC ya falló 2 rebotes en esta zona hace 1h y 2h."
    La historia empieza antes del episodio.

11. Etiqueta humana (opcional)
    "Hubiera entrado / no me gusta / por qué" — el campo donde vive el
    edge discrecional del trader. El Atlas de 100-200 ejemplos se
    etiqueta aquí.

---

## Objetos independientes

### MarketMemory (por activo)
Intentos de rebote recientes con desenlace, zonas testeadas hoy y qué
pasó, régimen del día. Vive fuera de los episodios; ellos la snapshotean.

### experimental_features (el purgatorio)
Tabla aparte, JSON, con fecha de ingreso. Ascenso al núcleo SOLO con
evidencia del Atlas (tribunal de falsación completo). Descenso simétrico
si deja de discriminar. El núcleo se mantiene pequeño (regla anti-monstruo).

### instrument_readings (catálogo de instrumentos)
Cualquier indicador es una fila más, nunca una tabla más.

---

## Estructura universal de todo valor medido

Metric {
  raw_value          — lo que midió el instrumento
  normalized_value   — comparable entre activos (ATR, rangos propios)
  confidence         — 0-1, ¿qué tan bien pude medir esto?
  formula_version    — con qué reglas se calculó
}
Ningún número desnudo en todo el modelo. Los índices compuestos son
recalculables desde los crudos (Principio 5).

## Contrato de calidad de datos (entrada)
El Observador solo consume velas VERIFICADAS (guard anti-velas-cruzadas).
Huecos y resampleos quedan estampados en el confidence del tramo.
La lección más cara de la primera generación fue que el instrumento
mentía; este modelo nace con detector de mentiras incluido.

---

## Capa de negocio (FUERA del Observador)

BusinessOutcome: traduce Resolution a economía — "¿ganaba una binaria de
15 min?" (multi-horizonte 600/750/900/1200/1800s), payout, stake, profit,
link a trade_journal (ground truth del broker). Mañana: "¿ganaba un futuro
con stop X?". El Observador jamás conoce estos conceptos.

Test de portabilidad permanente: cambiar de broker/instrumento financiero
debe reescribir <5% del Observador.

## Relación con STRAT-F
STRAT-F (primera generación) sigue corriendo como baseline y recolector.
Cada episodio graba qué habría dicho STRAT-F (aceptado/rechazado/razón):
comparación motor nuevo vs viejo, gratis, desde el día uno.
