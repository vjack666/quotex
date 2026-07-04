# Requirements — Telegram Alerts

## R1 — Módulo alerter
El sistema DEBE incluir un módulo `src/alerter.py` con una clase `TelegramAlerter`
que pueda enviar mensajes a un chat de Telegram vía Bot API.

## R2 — Configuración por entorno
El sistema DEBE leer `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` de las variables
de entorno. SI alguna de las dos está vacía o ausente, ENTONCES el alerter DEBE
no-operar silenciosamente sin lanzar errores.

## R3 — Sin dependencias externas nuevas
El alerter DEBE usar `requests.post` (ya instalado) para comunicarse con la
Telegram Bot API. NO DEBE añadir dependencias nuevas al proyecto.

## R4 — Evento sesion_cumplida
CUANDO `MassanielloRiskManager.register_win()` detecta que la sesión está completa
(`is_session_complete()`), el sistema DEBE enviar una alerta `alert_session_complete`.

## R5 — Evento racha_perdidas
CUANDO `MassanielloRiskManager.register_loss()` detecta que la sesión ha fallado
(`is_session_failed()`), el sistema DEBE enviar una alerta `alert_losing_streak`.

## R6 — Evento conexion_caida
CUANDO el bucle principal de `ConsolidationBot` no puede establecer conexión
(`ensure_connection()` retorna `False`), el sistema DEBE enviar una alerta
`alert_connection_lost`. El alerter DEBE tener un cooldown mínimo de 5 minutos
para este evento para evitar spam.

## R7 — Evento stop_loss
CUANDO `TradeExecutor.refresh_balance_and_risk()` activa el stop-loss de sesión
(`session_stop_hit = True`), el sistema DEBE enviar una alerta `alert_stop_loss`.

## R8 — Tests con mock
El sistema DEBE incluir tests en `tests/test_alerter.py` que usen
`unittest.mock.patch` para simular `requests.post` y no dependan de Telegram real.
DEBE haber al menos 6 tests.

## R9 — Formato de mensajes
Los mensajes DEBEN usar `parse_mode=HTML` e incluir emoji identificador del evento
y etiquetas `<b>` para los títulos.

## R10 — Cooldown anti-spam
El alerter DEBE implementar un cooldown configurable por tipo de evento para
evitar mensajes duplicados en ráfagas cortas. El cooldown por defecto DEBE ser
de 60 segundos, y de 300 segundos para `alert_connection_lost`.
