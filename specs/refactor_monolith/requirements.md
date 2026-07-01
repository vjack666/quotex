# Requirements — refactor_monolith

> Feature id=1. Extraer módulos del monolito `consolidation_bot.py` según
> `docs/architecture.md`. Cada `R<n>` es verificable por un test concreto.

## R1
El sistema DEBE mantener `src/consolidation_bot.py` con un máximo de 500 líneas
de código fuente (conteo de líneas físicas del archivo, incluyendo docstrings
y comentarios).

## R2
El sistema DEBE exponer el módulo `src/connection.py` con las funciones públicas
`connect_with_retry`, `fetch_candles`, `fetch_candles_with_retry`,
`get_open_assets`, `place_order` y `looks_like_connection_issue`.

## R3
El sistema DEBE exponer el módulo `src/scanner.py` con una clase o función pública
que orqueste el escaneo de activos (`scan_all` o equivalente) delegando la descarga
de velas a `connection.py` y la evaluación de señales a `strat_a.py` / `strat_b.py`.

## R4
El sistema DEBE exponer el módulo `src/executor.py` con la lógica de ejecución
de órdenes, resolución de trades, gestión de ciclo/martingala y selección final
de candidatos (integración con `entry_scorer`).

## R5
El sistema DEBE exponer el módulo `src/strat_a.py` con la lógica pura de
consolidación (detección de zona, ruptura, volumen, helpers de techo/piso)
sin importar `pyquotex` ni realizar I/O de red.

## R6
El sistema DEBE exponer el módulo `src/strat_b.py` con la lógica pura de
Spring/Upthrust (Wyckoff) sin importar `pyquotex` ni realizar I/O de red.

## R7
CUANDO `main.py` arranca en modo dry-run con `--once`, el sistema DEBE completar
un ciclo de escaneo sin excepciones no manejadas, importando explícitamente
`connection`, `scanner` y `executor` además del facade `consolidation_bot`.

## R8
El sistema DEBE incluir `tests/test_connection.py` con tests que verifiquen
`looks_like_connection_issue`, `fetch_candles` y `connect_with_retry` usando
mocks (sin broker real).

## R9
El sistema DEBE incluir `tests/test_scanner.py` con tests que verifiquen el
flujo de escaneo sobre activos y velas sintéticas/mockeadas (sin broker real).

## R10
El sistema DEBE incluir `tests/test_executor.py` con tests que verifiquen
envío de órdenes en dry-run, resolución de trades y límites de capital usando
mocks (sin broker real).

## R11
CUANDO se ejecuta `.\init.ps1`, el sistema DEBE terminar con código de salida 0
(todos los tests en verde y validación de `feature_list.json` correcta).

## R12
SI un módulo de estrategia (`strat_a.py`, `strat_b.py`) recibe velas como entrada,
ENTONCES el sistema DEBE devolver señales o `None`/`False` sin efectos secundarios
de red, archivos ni base de datos.

## R13
CUANDO `main.py` aplica configuración en tiempo de ejecución (`_apply_runtime_config`),
el sistema DEBE seguir pudiendo mutar los parámetros operativos expuestos hoy por
`consolidation_bot` (payout mínimo, ciclo, STRAT-B, etc.) sin romper el arranque.

## R14
El sistema DEBE preservar el comportamiento observable del bot monolítico actual:
mismos puntos de entrada CLI (`--live`, `--real`, `--loop`, `--greylist`) y misma
firma pública de `consolidation_bot.main(dry_run, real_account, loop_forever, ...)`.