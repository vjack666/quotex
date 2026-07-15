# Design — Schedule / Auto Full (Consola)

> Fecha: 2026-07-14 | Estado: implementar

## Objetivo

Dejar el bot en la noche recolectando datos con un **modo automático**
configurable desde **Consola**, con el mismo patrón de *incógnitas* que el
bankroll: el UI muestra valores locales hasta **Guardar**, y ahí el servidor
aplica y persiste.

## UI (reemplazo del bloque Operación)

| Antes | Después | Clave servidor |
|-------|---------|----------------|
| Expiry (segundos) | **Expiración (min)** | `duration_min` → `duration_sec = min * 60` |
| Monto base | *Eliminado* (Bankroll en Operación) | — |
| Máx. loss seguidos | **Sesiones seguidas máx.** | `max_consecutive_sessions` |
| Max concurrent trades | *Eliminado* (Massaniello opera 1 a la vez) | — |
| Max daily trades | **Horas de trabajo seguido** | `work_block_hours` |
| STRAT-F Only | *Eliminado* (código sigue en default actual) | — |
| *(nuevo)* | **Horas de descanso** | `rest_hours` |
| *(nuevo)* | **Modo** Manual / Automático full | `schedule_mode` |
| Tiempo máx. sesión (min) | Se mantiene (tope de un ciclo Massaniello) | `session_max_min` |
| *(nuevo, opcional)* | **Sesiones máx. por día** (0 = sin tope) | `max_sessions_per_day` |

Defaults sensatos para noche:

- `duration_min` = 5 → 300 s  
- `max_consecutive_sessions` = 3  
- `work_block_hours` = 2  
- `rest_hours` = 1  
- `schedule_mode` = `manual`  
- `max_sessions_per_day` = 0 (ilimitado)  
- `session_max_min` = 60  

## Semántica

### Manual (default)

Comportamiento actual: Iniciar → un ciclo Massaniello → terminal → stop + modal.
No reinicia solo. No aplica rest programado.

### Automático full

1. Usuario **Guarda** config y pulsa **Iniciar** (arma el scheduler).
2. Arranca un **bloque de trabajo** de `work_block_hours`.
3. Corre ciclos Massaniello uno tras otro (tras terminal → reset limpio → re-scan)
   mientras:
   - no se superen `max_consecutive_sessions` en el bloque, y
   - no se agote el bloque de trabajo, y
   - no se alcance `max_sessions_per_day` (si > 0).
4. **Tope de trabajo:** si pasan `work_block_hours` sin que el ciclo actual
   cumpla meta Massaniello (o en general al vencer el bloque), el bot **se
   detiene** de forma limpia (deja de escanear / no nuevas entradas; resuelve
   trade abierto si hay).
5. Entra **descanso** `rest_hours`: hub sigue vivo, bot en stopped, no scan.
6. Tras el descanso, si el modo sigue en `auto_full` y no se desarmó, **re-Inicia**
   solo (nuevo bloque de trabajo).
7. Usuario puede **Detener** en cualquier momento → desarma auto (cancela
   timers de rest/resume).

## Persistencia (incógnitas)

Archivo: `data/hub_schedule.json` (análogo a `hub_bankroll.json`).

Keys:

```json
{
  "schedule_mode": "manual",
  "duration_min": 5,
  "max_consecutive_sessions": 3,
  "work_block_hours": 2,
  "rest_hours": 1,
  "max_sessions_per_day": 0,
  "session_max_min": 60
}
```

- Load al arrancar `BotRunner`.
- Save en `POST /api/config` cuando vengan esas keys.
- `duration_sec` derivado al aplicar: `max(60, duration_min * 60)`.

## Arquitectura

```
hub/static index.html  →  POST /api/config
                              ↓
                     BotRunner.update_config
                              ↓
              config.DURATION_SEC + schedule fields
                              ↓
                   ScheduleController (nuevo)
                    ├─ on session terminal → next cycle or rest
                    ├─ work block timer → stop + rest
                    └─ rest timer → start again
```

### Módulo nuevo: `src/schedule_controller.py`

- Estado: `idle | working | resting | disarmed`
- Contadores: consecutive sessions, sessions today (reset medianoche local),
  work_block_started_at, rest_until
- API usada por BotRunner / app:
  - `arm_from_config(cfg)`
  - `on_bot_started()`
  - `on_session_terminal(summary)`
  - `on_user_stop()` → disarmed
  - `tick()` o tasks asyncio internas
- Logs claros: `SCHEDULE work block 2.0h`, `SCHEDULE rest 1.0h until …`,
  `SCHEDULE auto-start cycle 2/3`, `SCHEDULE work block expired — stop`.

### Integración BotRunner

- Al `start()`: si `schedule_mode=auto_full`, armar controller.
- Al `stop()` por usuario: disarm.
- Al terminal Massaniello (evento ya existente `session_complete`):
  controller decide next vs rest.
- Auto-restart: llamar el mismo path que `/api/bot/start` internamente
  (no depender del browser).

### Status API

`GET /api/bot/status` (o config) expone:

```json
{
  "schedule": {
    "mode": "auto_full",
    "phase": "resting",
    "consecutive": 2,
    "max_consecutive": 3,
    "work_block_remaining_sec": 0,
    "rest_remaining_sec": 2400,
    "sessions_today": 5
  }
}
```

UI: badge en Consola o barra superior opcional (`Auto · descanso 0:40`).

## Fuera de alcance

- No apagar el proceso Python del hub (solo bot stopped = “apagado” de trading).
- No cambiar Massaniello ni STRAT-F.
- No reintroducir monto base en Consola.

## Tests

- Mapeo duration_min → duration_sec
- Persist load/save schedule
- Controller: after N consecutive → rest; work block expiry → stop; user stop → disarm
- UI fields no envían massaniello/payout ni strat_f_only

## Verificación manual

1. Guardar: 5 min exp, 2 sesiones seguidas, 2h trabajo, 1h descanso, auto.
2. Iniciar; al completar 1 ciclo, debe arrancar el 2º sin modal “atasque”.
3. Tras 2º ciclo → rest (status resting).
4. Detener manual desarma.
