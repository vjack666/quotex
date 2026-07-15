# Hub — Schedule / Auto Full (Consola)

> Fecha: 2026-07-14

## Propósito

Permitir recolección de datos overnight con un **modo automático** configurable
desde **Consola → Configuración del bot**, con el mismo patrón de *incógnitas*
que el bankroll: valores locales en el UI hasta **Guardar**.

## UI (Consola)

| Campo | Clave | Default |
|-------|-------|---------|
| Modo | `schedule_mode` | `manual` |
| Expiración (min) | `duration_min` → `duration_sec = min * 60` (piso 60s) | 5 |
| Tiempo máx. sesión (min) | `session_max_min` | 60 |
| Sesiones seguidas máx. | `max_consecutive_sessions` | 3 |
| Horas de trabajo seguido | `work_block_hours` | 2.0 |
| Horas de descanso | `rest_hours` | 1.0 |
| Sesiones máx. por día | `max_sessions_per_day` (0 = ilimitado) | 0 |

Eliminados del panel (siguen en defaults de código / bankroll): Monto base,
Máx. loss, Max concurrent, Max daily trades, STRAT-F Only.

Badge opcional en la barra de control: `Auto · trabajo 1/3` / `Auto · descanso m:ss`.

## Persistencia

Archivo: `data/hub_schedule.json` (`src/hub_schedule_store.py`).

- Load al arrancar `BotRunner`.
- Save en `POST /api/config` cuando vengan keys de schedule.
- Bankroll (`hub_bankroll.json`) se mantiene separado.

## Semántica

### Manual

Iniciar → un ciclo Massaniello → terminal → stop. Sin rest/resume automático.

### Automático full

1. Guardar config + **Iniciar** arma el scheduler.
2. Bloque de trabajo de `work_block_hours`.
3. Ciclos Massaniello encadenados mientras no se superen `max_consecutive_sessions`,
   el bloque de trabajo ni el tope diario.
4. Al vencer el bloque o el tope de consecutivas → **descanso** `rest_hours`
   (bot stopped, hub vivo).
5. Tras el descanso → auto-start de un nuevo bloque.
6. **Detener** del usuario desarma (cancela timers).

## Componentes

| Módulo | Rol |
|--------|-----|
| `src/hub_schedule_store.py` | load/save JSON |
| `src/schedule_controller.py` | fases idle/working/resting/disarmed |
| `BotRunner` (`consolidation_bot.py`) | arm/disarm, auto start/stop, `status.schedule` |
| `app.py` | audit log de keys schedule; stop UI = user stop |

## Logs

Prefijo `SCHEDULE`: work block, rest, auto-start cycle, work expired, day cap, user disarm.

## Fuera de alcance

- No apagar el proceso del hub.
- No cambiar Massaniello ni STRAT-F.
- No reintroducir monto base en Consola.
