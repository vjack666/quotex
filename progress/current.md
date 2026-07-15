# Estado de sesión — schedule_auto

> Sesión: 2026-07-14 | Agente: implementer

## Feature en curso
`schedule_auto` (in_progress) — lista para review. **No marcar done.**

## Hecho
- T1–T6 implementados y tests de feature verdes (13).
- T7: suite amplio sin contaminación de bankroll → 355 passed / 2 fail preexistentes.
- Resumen: `progress/impl_schedule_auto.md`

## Cómo usar esta noche
1. Bankroll (Operación) → Guardar.
2. Consola: **Automático full** + horas trabajo/descanso → **Guardar**.
3. **Iniciar**. **Detener** desarma el auto.
4. Badge: `Auto · trabajo n/m` o `Auto · descanso m:ss`.

## Notas reviewer
- Feature tests 13 green; no marcar `done` aún.
- `hub_bankroll.json` (min_payout=90) contamina `config` en import de pytest.
- feature id=7: se agregó `name` faltante.
