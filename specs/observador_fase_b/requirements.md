# Requirements — Observador Fase B: Calidad del Rebote y Película Completa

Feature: observador_fase_b
Capa: 2 (Observador). Consume Capa 0.5 (MarketFeed). NO decide, NO opera.
Hereda de Fase A (`observador_nucleo`) y la extiende: la Fase A guarda la
FOTO del episodio (MFE/MAE sueltos + clasificación); la Fase B guarda la
PELÍCULA (evolución barra a barra) y el resumen para consumo de IA.

Reutiliza (sin reimplementar):
- Store idempotente (R4.3 Fase A): re-correr no duplica.
- Candados anti-reloj (R5.2 Fase A) y anti-bot (R5.1 Fase A).
- Máquina de estados `transitions_v1` (Fase A) para la narrativa.

Documentos rectores: `docs/FILOSOFIA.md` (falsación; conceptos permanentes),
`docs/PTM_V3.md` (separación Mercado→Observador→Negocio),
`docs/CONSTITUCION_REBOTE.md` (LAB-001..005; Fase B hereda el combo
muerte-del-empuje + zona-grande ≈ 82%).

## Principio rector de este SDD (decisión 2026-07-27)

> EL SDD DEFINE COMPORTAMIENTO, NO PARÁMETROS.
> Los umbrales numéricos (barras de silencio, rango "plano", significancia
> mínima por activo, ventanas) viven en configuración VERSIONADA bajo
> `observador/config/` y son validados/afinados por el Atlas. Ningún número
> mágico se congela en este documento. Las fórmulas llevan `formula_version`
> y son recalculables sin re-reproducir 14 años.

---

## Requisitos funcionales

**R1 — Traza completa.** El Observador DEBE registrar, para cada episodio que
alcanza RESOLUTION, una traza de evolución barra a barra (`EpisodeEvolution`)
desde el inicio del episodio hasta su fin, a la resolución NATIVA del feed
(M1), independiente del timeframe en que se detectó. La traza se indexa por
número de barra relativo al inicio (0,1,2…), NUNCA por tiempo de pared.

**R2 — Contenido mínimo por barra.** Cada fila de la traza DEBE llevar, al
menos: `bar_index`, `ts`, `price`, `distance_pips` (distancia al origen del
episodio), `mfe` (máximo a favor acumulado), `mae` (máximo en contra
acumulado), y `state` (estado estructural del episodio en esa barra).

**R3 — Variables de mercado versionadas.** La traza DEBE poder llevar, por
barra, un conjunto CONFIGURABLE de variables de mercado (p.ej. continuidad,
presión, energía, volatilidad, spread). Cada variable lleva su
`formula_version`. Sus definiciones viven en config; NO en este SDD.

**R4 — Fin natural (prioridad absoluta).** Un episodio tiene exactamente UN
fin natural, decidido por el MERCADO mediante un evento estructural que
invalida la narrativa actual (p.ej. NEW_EXPANSION, NEW_PRESSURE,
OPPOSITE_STRUCTURE, CHAOS). El fin natural produce `end_reason` y
`end_confidence`.

**R5 — Fin de captura (separado del natural).** El sistema PUEDE detener la
captura antes del fin natural ÚNICAMENTE cuando hay evidencia suficiente de
que el episodio dejó de evolucionar (ya no aporta información nueva). Esto es
un FIN DE CAPTURA, NO un fin natural: `EpisodeSummary.finished = false`,
`capture_limit_reached = true`. Los criterios de "suficiente evidencia" son
CONFIGURABLES y versionados — jamás constantes fijas en este SDD.

**R6 — CaptureMonitor.** El mecanismo de fin de captura DEBE ser un
`CaptureMonitor` que, por barra, evalúa si el episodio sigue aportando
información a través de varias dimensiones (¿cambio estructural? ¿cambió la
presión? ¿la energía? ¿la dirección? ¿la volatilidad?). La captura termina
solo cuando TODAS las dimensiones reportan "sin cambio". No por conteo fijo de
barras.

**R7 — Significancia por activo.** Los umbrales de "sin cambio" / "plano"
DEBEN definirse POR INSTRUMENTO (EURUSD ≠ XAUUSD ≠ BTC ≠ Nasdaq) y residir en
config versionada. El SDD no nombra ningún valor.

**R8 — Snapshot final (`EpisodeSummary`).** Por episodio se DEBE persistir un
resumen: `quality`, `velocity`, `violence`, `curve_shape`
(convexa/cóncava/plana), `symmetry`, `episode_type` (Reversal/Continuation/
Chaos), `duration_bars`, `mfe`, `mae`, `end_reason`, `end_confidence`,
`finished`. Propósito: la IA/minería lee resúmenes sin recorrer millones de
puntos.

**R9 — Agnóstico al instrumento de negocio.** La Fase B DEBE ser
completamente agnóstica a cualquier vehículo de trading (binaria 5m/15m,
FX con TP, trailing stop). Solo describe la vida del episodio. La
interpretación contra un vehículo es responsabilidad de una CAPA DE NEGOCIO
separada (futura) que muestrea la traza al horizonte deseado — coherente con
PTM v3.

**R10 — Recalculabilidad (`EpisodeVersion`).** Toda fórmula de variable o
métrica de resumen DEBE llevar `formula_version` y ser recalculable de forma
independiente sobre los datos YA guardados, de modo que cambiar una definición
no exija re-reproducir 14 años.

**R11 — Idempotencia del poblamiento.** Re-correr el replay de 14 años con
Fase B activa NO debe duplicar episodios ni filas de traza (reusa la
idempotencia del store Fase A; backfill de episodios ya existentes).

**R12 — Sin reloj de pared.** El Observador Fase B NO debe usar `time.time()`
ni `datetime.now()`; solo `feed.now()` y timestamps de eventos (candado con
test adversarial reusado de Fase A).

**R13 — Sin dependencia del bot.** Fase B NO debe importar ni depender de
`scanner` / `strat_fractal` / nada del bot vivo (candado reusado de Fase A).

## Relación con Fase A
- `resolution_type` (Fase A) = clase narrativa del episodio.
- `end_reason` (Fase B) = evento de terminación REAL de la traza (puede
  diferir de `resolution_type`; p.ej. un episodio clasificado REBOUND cuya
  traza siguió viva y terminó por NEW_PRESSURE). Ambos se guardan.
- La traza de evolución se extiende DESDE el inicio del episodio HASTA el fin
  (natural o de captura), que puede exceder la ventana de 5 barras de
  TRANSITION de Fase A. El writer de traza sigue grabando tras RESOLUTION
  hasta que CaptureMonitor diga parar.
