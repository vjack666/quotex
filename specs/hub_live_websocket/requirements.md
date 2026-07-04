# Requirements — hub_live_websocket

## Propósito
Un dashboard en vivo que muestre en tiempo real el estado del bot de trading HFT para Quotex, incluyendo señales, rechazos, capital, órdenes, rendimiento y salud del sistema, usando WebSocket para actualizaciones eficientes sin polling.

## Requisitos (formato EARS)

1. <system shall> proporcionar un servidor WebSocket accesible en `http://localhost:8080` por defecto, configurable mediante la variable de entorno `HUB_PORT`.
2. WHEN el bot se inicia, <system shall> levantar el servidor de dashboard en segundo plano sin bloquear el ciclo principal de trading.
3. WHEN el bot envía un evento de señal detectada, <system shall> transmitirlo en tiempo real a todos los clientes conectados con: símbolo, dirección (CALL/PUT), estrategia, score, payout, timestamp y razón de rechazo si aplica.
4. WHEN el bot envía un evento de orden enviada, <system shall> transmitirlo en tiempo real con: símbolo, dirección, stake, resultado (pendiente/ganado/perdido), hora de entrada y hora de salida esperada.
5. WHEN el bot actualiza el capital disponible o la racha de Massaniello, <system shall> transmitir el capital actual, operaciones realizadas, ITM actuales y progreso hacia la meta (3/5).
6. <system shall> transmitir un panel de salud del sistema que incluya: estado de conexión al broker, latencia promedio de velas, número de ciclos completados, errores recientes en el último minuto y estado de los módulos clave (scanner, estrategias, executor).
7. WHEN se establece una conexión WebSocket nueva, <system shall> enviar un estado inicial de "esperando datos..." hasta que llegue el primer evento del bot.
8. <system shall> permitir al usuario pausar/reanudar la visualización de eventos en tiempo real desde la interfaz sin detener el bot ni perder eventos (estos se bufferizan brevemente o se muestran al reanudar).
9. <system shall> incluir un modo de demostración que pueda funcionar con datos simulados o históricos si no hay conexión activa al broker (activado por variable de entorno `HUB_DEMO_MODE=true`).
10. <system shall> usar tecnologías ligeras y compatibles con el entorno actual: se permitirá el uso de `FastAPI` y `Uvicorn` como dependencias externas si se agregan a `requirements.txt`.
11. <system shall> no bloquear ni ralentizar el bot principal; el servidor de dashboard debe correr en una tarea `asyncio` de baja prioridad o en un hilo separado con uso mínimo de CPU.
12. <system shall> salir con código de estado 0 al terminar correctamente.
13. WHEN se proporciona la bandera `--help` o `-h`, <system shall> mostrar un mensaje de ayuda y salir.
14. <system shall> incluir un endpoint de salud HTTP (`/health`) que devuelva `{"status": "ok"}` si el servidor está activo.
15. <system shall> garantizar que los mensajes WebSocket se entreguen en orden y sin duplicados bajo condiciones normales de red.