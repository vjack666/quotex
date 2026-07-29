# Requirements — Contexto Geométrico M15 (Feature 29)

> Feature ID: 29 · status: spec_ready
> Depende de: 27 (memoria única), 28 (IA de Zonas)
> Aplica a: pares OTC (`*_otc`) — el bot opera OTC, NO majors.

## Contexto

El bot hoy solo mira el rango local de la zona (piso/techo de la consolidación
corta) + stoch M15 para decidir dirección. En EURJPY_otc (operación
`2247864af2e7b77e`) entró PUT en el PISO del rango con stoch sobrecompra +
cruce bajista, y perdió: la mecha tocó el piso pero el CUERPO no confirmó bajada
→ rebote alcista (bullish engulfing). Falló LEER LA DIRECCIÓN en el extremo, no
detectar el extremo.

El bot YA trae `candles_15m` (tf_sec=900) para stoch M15 y HTF gate, y YA tiene
`smc_analysis.detect_structure` (swings, FVG, bias, zones) — puro cálculo sin
reglas. Lo que falta: usar ~1 día de M15 (≈96 velas) para trazar los
soportes/resistencias REALES del día y cruzarlos con la memoria (IA de Zonas) y
la confirmación por cuerpo, como CONSENSO (sin veto duro, sin Bollinger).

## Requisitos funcionales

- **RG1 (contexto largo M15 OTC):** calcular swings/soportes/resistencias del
  día sobre ~96 velas M15 de cada par `_otc` (los mismos que ya opera el bot).
- **RG2 (cache):** el cálculo se hace UNA vez por asset por barra M15, no por
  candidato (costo: 1 scan / 15 min / asset, no por señal).
- **RG3 (sin reglas):** NO introducir "si swing low entonces compra". La
  geometría es SEÑAL DE CONTEXTO que la memoria lee, no un filtro duro. Cero
  tablas de decaimiento, cero roles fijos soporte/resistencia hardcoded.
- **RG4 (consenso):** la dirección en el extremo se decide por cruce de 3
  fuentes: (a) swing M15 del día, (b) zone_confidence de la IA de Zonas (memoria),
  (c) confirmación por CUERPO de vela en el extremo. Ninguna fuente es veto solo.
- **RG5 (memoria):** el contexto de swings M15 se guarda en
  `contexto_previo` del arco de experiencia (observation.py), para que las IAs
  aprendan "entré PUT en un swing low diario → LOSS".
- **RG6 (dirección en extremo):** exigir que la vela de entrada tenga CUERPO a
  favor en el extremo del rango/swing (no mecha sola). Si la mecha fue contra y
  el cuerpo no confirmó → no entra o invierte dirección.
- **RG7 (OTC-safe):** tolerar ruido de velas planas OTC (filtrar swings falsos
  por tamaño mínimo de cuerpo / número de toques), sin caer en majors.
- **RG8 (verificable):** tests deterministas con velas sintéticas (rango con
  soporte real tocado N veces) que demuestren que el consenso mejora la lectura
  de dirección vs stoch solo.

## No objetivos

- NO usar Bollinger para esto (mide estiramiento, no dirección en el extremo;
  en rango genera falsos toques).
- NO operar majors. NO añadir reglas de trading hardcoded.
- NO reemplazar la IA de Zonas (F28); esta feature la ALIMENTA con contexto.

## Trazabilidad

| Req | Cubre | Test |
|-----|-------|------|
| RG1 | contexto M15 OTC | test_market_geometry_ctx::test_swings_diarios |
| RG2 | cache por barra | test_market_geometry_ctx::test_cache_por_barra |
| RG3 | sin reglas | test_market_geometry_ctx::test_sin_reglas (solo señal) |
| RG4 | consenso 3 fuentes | test_market_geometry_ctx::test_consenso_direccion |
| RG5 | memoria contexto | test_observation::test_contexto_swings_guardado |
| RG6 | cuerpo en extremo | test_extreme_direction::test_cuerpo_confirma |
| RG7 | OTC-safe | test_market_geometry_ctx::test_filtra_swings_planos |
| RG8 | verificable | suite determinista |
