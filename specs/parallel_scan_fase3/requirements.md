# Requirements — parallel_scan_fase3

> Ejes: EJE A (parallelizar FASE 3 del scanner con ProcessPool) solamente.
> EJE B (event-driven por cierre de vela) QUEDA FUERA de este cambio.
> Objetivo: liberar el loop asyncio/WS durante la evaluación de activos,
> usando el 50% de los núcleos de la máquina (10 de 20 en la PC de Ruben).

## R1
MIENTRAS el scanner ejecuta `_scan_phase_evaluate_assets`, el sistema DEBE
evaluar los activos del ciclo usando un `ProcessPoolExecutor` global con
`max(1, cpu_count() // 2)` workers, en lugar de un bucle `for` serial en el
loop principal.

## R2
CUANDO el bot inicia, el sistema DEBE crear el `ProcessPoolExecutor` una sola
vez (global, reusado entre ciclos) y cerrarlo en el shutdown del bot.

## R3
CUANDO la evaluación paralela termina, el sistema DEBE devolver la misma lista
de `CandidateEntry` (mismo scoring, mismas estrategias) que la evaluación
serial actual, para que `_scan_phase_select_execute` opere al mejor candidato
sin cambios de comportamiento.

## R4
MIENTRAS la evaluación paralela corre, el sistema NO DEBE bloquear el loop
asyncio principal (el WS de Quotex debe seguir siendo atendido).

## R5
SI la evaluación de un activo falla dentro de un worker (excepción), ENTONCES
el sistema DEBE capturar el error, registrarlo y continuar con los demás
activos (igual que hoy el `for` serial que hace `continue` en reject/error),
sin abortar el ciclo.

## R6
DONDE el entorno no soporte `ProcessPoolExecutor` (p. ej. test mode / sin
pickling de los datos de vela), el sistema DEBE degradar a la evaluación
serial actual sin romper el scan.

## R7
CUANDO el cambio está activo, el sistema DEBE poder medir (benchmark local)
que el tiempo de evaluación paralela es menor que el serial, y que el loop WS
no está idle bloqueado durante la evaluación.

## R8 (opcional, FUERA DEL CORE)
DONDE el usuario habilite "adaptación de setup", el sistema PUEDE ajustar
umbrales de score/timeframe según el mercado. Esta fase es posterior y NO se
implementa en parallel_scan_fase3.
