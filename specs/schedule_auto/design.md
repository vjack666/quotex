# Design — schedule_auto

See also `progress/design_schedule_auto.md` (authoritative product design).

## Components

1. **UI** `hub/static/index.html` — replace cfg Operación fields; load/save; badge.
2. **Store** `src/hub_schedule_store.py` — load/save `data/hub_schedule.json`.
3. **Controller** `src/schedule_controller.py` — work/rest/consecutive/day counters.
4. **BotRunner** — wire config keys, duration_min→sec, arm on start, disarm on user stop, react to session terminal, expose schedule in get_status.
5. **app.py** — audit log keys for schedule; ensure start/stop hook controller.
6. **Tests** — store, duration mapping, controller transitions.

## Defaults

- schedule_mode: manual
- duration_min: 5
- max_consecutive_sessions: 3
- work_block_hours: 2.0
- rest_hours: 1.0
- max_sessions_per_day: 0
- session_max_min: 60 (existing)
