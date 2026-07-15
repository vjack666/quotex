# Requirements — schedule_auto

## R1 — UI Consola renovada
WHEN the user opens Consola → Configuración del bot  
THE SYSTEM SHALL show: Modo (manual/auto_full), Expiración (min), Tiempo máx. sesión (min), Sesiones seguidas máx., Horas de trabajo seguido, Horas de descanso, Sesiones máx. por día (0=ilimitado).  
THE SYSTEM SHALL NOT show Monto base, Máx. loss, Max concurrent, Max daily trades, or STRAT-F Only.

## R2 — Expiración en minutos
WHEN the user saves Expiración (min)  
THE SYSTEM SHALL store `duration_min` and apply `duration_sec = duration_min * 60` (min 60s).

## R3 — Persistencia incógnitas
WHEN the user clicks Guardar  
THE SYSTEM SHALL persist schedule keys to `data/hub_schedule.json` and apply them to BotRunner/config.  
WHEN the hub restarts  
THE SYSTEM SHALL reload those keys.

## R4 — Modo manual
WHEN `schedule_mode` is `manual`  
THE SYSTEM SHALL keep current lifecycle (one Massaniello cycle → stop; no auto rest/resume).

## R5 — Bloque de trabajo
WHEN `schedule_mode` is `auto_full` and a work block is active  
THE SYSTEM SHALL stop the bot when `work_block_hours` elapses (no new entries; clean stop).

## R6 — Sesiones seguidas
WHEN `auto_full` completes Massaniello cycles  
THE SYSTEM SHALL count consecutive sessions; after `max_consecutive_sessions` it SHALL enter rest for `rest_hours` (bot stopped, hub alive).

## R7 — Descanso y reanudación
WHEN rest ends and mode is still `auto_full` and not user-disarmed  
THE SYSTEM SHALL auto-start a new work block / bot run.

## R8 — Stop usuario desarma
WHEN the user presses Detener  
THE SYSTEM SHALL cancel rest/resume timers and leave schedule disarmed until next Iniciar.

## R9 — Status visible
WHEN schedule is armed  
THE SYSTEM SHALL expose phase/counters via bot status for the UI badge.
