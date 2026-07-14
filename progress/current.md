# Estado de sesión — lifecycle inteligente (Iniciar / resume / meta)

> Sesión: 2026-07-14 | Operador: Ruben | Agente: Grok

## Problema
Al pulsar **Iniciar** en el hub, el bot conectaba y se apagaba en ~4s.
Causa: `SessionManager` nacía en `STOPPED` y el loop hacía `break` sin escanear.
Además, `BotRunner.start()` intentaba `session_manager.start()` sobre un bot que
aún no existía (`self._bot` nunca se asignaba).

## Solución implementada
Lifecycle inteligente:

1. **Iniciar** → `bootstrap_for_run()` deja la sesión en `SCANNING`.
2. **Sesión incompleta** (wins/losses > 0 y no terminal) → **reanuda** contadores.
3. **Meta cumplida** (ITM / failed / timeout / exhausted) → `COMPLETED` y **para el scan**.
4. Siguiente **Iniciar** tras meta → ciclo **fresh**.
5. Al stop/salida → guarda Massaniello para poder reanudar.

## Archivos
- `src/session_manager.py` — `bootstrap_for_run`, terminal helpers, tick ampliado
- `src/consolidation_bot.py` — bootstrap al arrancar, bind_bot, save on exit
- `src/executor.py` — `session_completed` antes de resetear Massaniello
- `tests/test_session_lifecycle.py` — 12 tests nuevos

## Verificación
- `pytest tests/test_session_lifecycle.py` → 12 passed
- `pytest tests/` → **322 passed**
