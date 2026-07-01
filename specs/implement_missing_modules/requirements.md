# Requirements — implement_missing_modules

> Feature id=2. Crear módulos SMC y `filter_and_sell_otc` referenciados en README y
> roadmap pero ausentes en `src/`. Fuente de verdad SMC:
> `C:\Users\v_jac\Desktop\QUOTEX\src\smc_analysis.py` y `smc_decision_engine.py`.
> Cada `R<n>` es verificable por un test concreto.

---

## smc_analysis.py — análisis estructural puro

## R1
El sistema DEBE exponer `src/smc_analysis.py` con la función pública `detect_swings`
que detecte swing highs y swing lows mediante el método zigzag (vecindad configurable
por parámetro `strength`).

## R2
El sistema DEBE exponer en `src/smc_analysis.py` la función pública `detect_fvg` que
identifique Fair Value Gaps alcistas y bajistas en secuencias de al menos 3 velas,
filtrando gaps cuyo tamaño relativo sea menor que `min_size_pct`.

## R3
El sistema DEBE exponer en `src/smc_analysis.py` la función pública `detect_structure`
que devuelva un `StructureResult` con bias, swings, eventos BOS/CHoCH, FVG y zonas.

## R4
CUANDO `detect_structure` evalúa una zona de oferta/demanda sin un FVG adyacente de
polaridad coincidente dentro de la ventana configurada, el sistema DEBE excluir esa
zona del resultado (no aparece en `StructureResult.zones`).

## R5
CUANDO la secuencia de velas tiene menos de `2 * swing_strength + 2` elementos,
el sistema DEBE devolver `StructureResult` con `bias=NEUTRAL` y listas vacías de
swings, eventos, FVG y zonas.

## R6
El módulo `src/smc_analysis.py` NO DEBE importar `pyquotex` ni realizar I/O de red,
archivos ni base de datos.

---

## smc_decision_engine.py — Ley de Dictadura HTF

## R7
El sistema DEBE exponer `src/smc_decision_engine.py` con la clase pública
`SMCDecisionEngine` que acepte velas H4 (o equivalente), M15 y M1 y exponga el
método `decide()` devolviendo un `Decision`.

## R8
CUANDO el bias H4 es `NEUTRAL`, el sistema DEBE devolver `Decision.signal=WAIT` con
razón que indique espera de alineación con H4.

## R9
CUANDO el bias H4 es `BEARISH` y el bias M15 difiere de H4, el sistema DEBE
devolver `Decision.signal=WAIT` (sin señal de compra).

## R10
CUANDO el bias H4 es `BULLISH`, M15 coincide con H4, existe zona de demanda con FVG
en M15 y el último evento M1 es `BOS_UP`, el sistema DEBE devolver
`Decision.signal=BUY`.

## R11
CUANDO el bias H4 es `BEARISH`, M15 coincide con H4, existe zona de oferta con FVG
en M15 y el último evento M1 es `BOS_DOWN`, el sistema DEBE devolver
`Decision.signal=SELL`.

## R12
CUANDO H4 y M15 están alineados pero el último evento M1 es un CHoCH en dirección
opuesta al bias H4, el sistema DEBE devolver `Decision.signal=WAIT` y la razón DEBE
identificar el movimiento como trampa de liquidez (retroceso hacia zona).

## R13
El módulo `src/smc_decision_engine.py` NO DEBE importar `pyquotex` ni realizar I/O
de red, archivos ni base de datos.

---

## smc_auto_trader.py — trader asíncrono SMC

## R14
El sistema DEBE exponer `src/smc_auto_trader.py` con una función o clase pública que
orqueste un ciclo SMC: conectar al broker vía `connection.py`, descargar velas
multi-timeframe, ejecutar `SMCDecisionEngine.decide()` y actuar según la señal.

## R15
CUANDO `SMCDecisionEngine.decide()` devuelve `Signal.BUY` o `Signal.SELL` y
`dry_run=False`, el sistema DEBE enviar una orden al broker mediante
`connection.place_order` con dirección `call` (BUY) o `put` (SELL).

## R16
CUANDO `SMCDecisionEngine.decide()` devuelve `Signal.WAIT`, el sistema DEBE omitir
el envío de órdenes en ese ciclo.

## R17
CUANDO la descarga de velas H4 falla o devuelve datos insuficientes, el sistema
DEBE reintentar con velas H1 como marco macro equivalente antes de abortar el ciclo.

## R18
CUANDO `dry_run=True`, el sistema DEBE completar el ciclo de análisis sin enviar
órdenes reales al broker (delegando en el modo dry-run de `connection.place_order`).

---

## filter_and_sell_otc.py — filtro por payout y venta OTC

## R19
El sistema DEBE exponer `src/filter_and_sell_otc.py` con una función o clase pública
que obtenga activos OTC abiertos mediante `connection.get_open_assets`.

## R20
CUANDO existen activos OTC con `payout >= min_payout`, el sistema DEBE seleccionar
el activo de mayor payout y enviar una orden `put` (venta) por el monto y duración
configurados.

## R21
CUANDO ningún activo OTC abierto cumple `payout >= min_payout`, el sistema DEBE
finalizar el ciclo sin enviar órdenes e informar ausencia de candidatos.

## R22
CUANDO `dry_run=True`, el sistema DEBE ejecutar el escaneo y la selección de activo
sin enviar órdenes reales al broker.

---

## Tests y verificación del harness

## R23
El sistema DEBE incluir `tests/test_smc_analysis.py` con tests unitarios sobre velas
sintéticas que cubran detección de swings, FVG, exclusión de zonas sin FVG y caso de
datos insuficientes (sin broker real).

## R24
El sistema DEBE incluir `tests/test_smc_decision_engine.py` con tests unitarios que
cubran señales WAIT (H4 neutral, conflicto M15, trampa CHoCH) y señales BUY/SELL en
cascada alineada (sin broker real).

## R25
El sistema DEBE incluir `tests/test_smc_auto_trader.py` y `tests/test_filter_and_sell_otc.py`
con mocks de `connection` y `Quotex` verificando envío dry-run, omisión en WAIT y
manejo de ausencia de candidatos (sin broker real).

## R26
CUANDO se ejecuta `.\init.ps1`, el sistema DEBE terminar con código de salida 0
(todos los tests en verde y validación de `feature_list.json` correcta).

## R27
El sistema NO DEBE recrear ni modificar `src/config.py` como parte de la entrega de
módulos; las constantes SMC y filter-sell nuevas DEBE añadirlas al `config.py`
existente o definirlas con valores por defecto en los módulos nuevos sin duplicar el
archivo de configuración.