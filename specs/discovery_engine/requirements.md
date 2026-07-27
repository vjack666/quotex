# Requirements — Discovery Engine (Minería de conocimiento del Atlas)

Feature: discovery_engine
Capa: 2.5 (sobre el Atlas / Observador Fase B). Lee episodios YA grabados
(trazas + summaries) y PROPONE leyes nuevas. NO decide, NO opera, NO toca
el feed. Es la inversión de la pregunta: en vez de "¿esto funciona?",
pregunta "Atlas, ¿qué funciona?".

Documentos rectores: `docs/FILOSOFIA.md` (falsación, acumular no borrar),
`docs/PTM_V3.md`, `docs/CONSTITUCION_REBOTE.md`, specs/observador_fase_b/.

## Principio rector (heredado de Fase B)
> EL SDD DEFINE COMPORTAMIENTO, NO PARÁMETROS. Los umbrales de significancia,
> cortes de rama, mínimos de muestra y definiciones de "ley candidata" viven
> en config versionada bajo `discovery/config/` y los valida el Atlas. Ningún
> literal numérico en este documento.

## Requisitos funcionales

**R1 — Entrada es el Atlas, no el mercado.** El motor DEBE leer desde
`EpisodeStore` (Fase A) y las tablas `episode_evolution` / `episode_summary`
(Fase B): trazas completas + snapshots. NUNCA consume feed en vivo ni
re-reproduce 14 años. (Eficiencia: el costo de cómputo ya se pagó al grabar.)

**R2 — Espacio de hipótesis abierto.** El motor DEBE poder explorar combinaciones
de variables ya grabadas (pressure/energy/continuity/volatility/spread por barra
+ campos del summary: quality, velocity, violence, curve_shape, symmetry,
duration_bars, mfe, mae, end_reason, finished) SIN que el humano las liste
una por una. Búsqueda automática sobre el espacio de features.

**R3 — Split temporal obligatorio.** Toda ley candidata DEBE validarse
walk-forward: se descubre en años de entrenamiento y se confirma en años
vírgenes. Una señal que no sobrevive el split se descarta (no se reporta como
ley). Hereda el estándar de LAB-001.

**R4 — Placebo / falsación.** Toda ley candidata DEBE compararse contra
barajados de desenlace (permutaciones) con p-valor. Solo se promueve si
p < umbral versionado. Hereda LAB-001.

**R5 — Reproducibilidad y versionado.** Cada ley descubierta DEBE guardarse
como experimento canónico (script + resultado) con su `discovery_version`,
al igual que los LAB manuales. Las leyes NO reemplazan LAB previos: se
ACUMULAN. Una mejora de una ley existente nace como nueva entrada
(LAB-0XX), nunca sobrescribe.

**R6 — Significancia mínima por muestra.** El motor NO DEBE reportar leyes con
muestra bajo el mínimo versionado, ni con frecuencia de señal no-tradeable
(umbral versionado; ej. señales/día mínimo por vehículo).

**R7 — Explicabilidad.** Toda ley promovida DEBE emitir: descripción legible
(variables + operadores), tamaño de efecto, intervalo, walk-forward por época,
p-valor, y frecuencia estimada. No se aceptan "cajas negras sin interpretar".

**R8 — Sin fuga de información (look-ahead).** El motor NO DEBE usar en el
descubrimiento ninguna variable calculada con conocimiento del desenlace
(end_reason, mfe/mae ya son del FUTURO del episodio). Explora solo features
disponibles AL MOMENTO de cada barra de la traza. (El summary es metadata de
cierre; usarlo como PREDICTOR está prohibido — es el desenlace.)

**R9 — Agnóstico al vehículo.** El motor descubre propiedades del episodio, no
de binarias/FX. La traducción a vehículo queda en la capa de Negocio (futura).

**R10 — Determinismo.** Misma entrada + misma config => mismas leyes. Semilla
de barajado versionada.

**R11 — Sin reloj de pared / sin bot.** No usa time.time()/datetime.now(); no
importa scanner/strat_fractal (candados reusados).

## Relación con el resto
- Consume la SALIDA de Fase B (películas + summaries). Depende de que el
  backfill de 14 años esté poblado.
- Las leyes que descubra alimentan (no reescriben) CONSTITUCION_REBOTE.md.
- Es el paso 3 del nuevo orden de Rubén: tras LAB-001 congelado y Fase B,
  antes del motor de trading.
