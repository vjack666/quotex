# Design — hub_live_websocket

## Propósito
Definir las decisiones técnicas para implementar un dashboard en vivo basado en WebSocket que muestre en tiempo real el estado del bot de trading HFT para Quotex, sin bloquear el ciclo principal de trading.

## Arquitectura propuesta

El dashboard se implementará como un servidor WebSocket ligero integrado en el proyecto, usando:
- **FastAPI** para el marco web (altamente performante, fácil de usar, excelente soporte para WebSocket)
- **Uvicorn** como servidor ASGI para servir la aplicación
- Conexiones WebSocket para actualizaciones en tiempo real al frontend (navegador)
- Endpoint HTTP `/health` para monitoreo de vida
- Comunicación desde el bot principal al servidor de dashboard mediante eventos asíncronos (no bloqueantes)

Este enfoque permite:
- Baja latencia en actualizaciones
- Escalabilidad horizontal si se necesita en el futuro
- Integración limpia con el ciclo `asyncio` existente del bot
- Uso de dependencias externas ligeras y ampliamente adoptadas
- Modo de demostración con datos simulados

## Decisiones técnicas

### 1. Marco web: FastAPI + Uvicorn
- **¿Por qué?**
  - Muy popular en la comunidad Python para APIs y WebSockets
  - Basado en Starlette (asyncio-native) y Pydantic (validación de datos)
  - Excelente documentación y soporte
  - Permite definir endpoints WebSocket y HTTP en el mismo lugar
  - Uvicorn es rápido, ligero y fácil de embebider
- **Alternativas descartadas:**
  - `websockets` library + manual asyncio server: más trabajo manual, menos estructura
  - Django Channels: demasiado pesado para este uso
  - Flask + SocketIO: requiere más configuración, menos nativo en asyncio
  - HTTP polling (ej: `/api/events` cada segundo): ineficiente, genera tráfico innecesario
- **Conclusión:** FastAPI + Uvicorn ofrece el mejor equilibrio entre potencia, simplicidad y rendimiento.

### 2. Integración con el bot principal
- El servidor de dashboard se iniciará como una tarea `asyncio` dentro de `main.py` al arrancar el bot, usando:
  ```python
  import asyncio
  from hub.server import start_hub_server

  async def main():
      # ... inicialización normal del bot ...
      hub_task = asyncio.create_task(start_hub_server())
      # ... ciclo principal de trading ...
      await asyncio.gather(hub_task, trading_cycle_task())
  ```
- Esto asegura que:
  - El dashboard se levanta al iniciar el bot
  - Corre en el mismo loop de eventos (no crea hilos innecesarios)
  - Puede ser cancelado limpiamente al apagar el bot
  - No bloquea el ciclo principal (la tarea es de baja prioridad si no hay tráfico)

### 3. Comunicación bot → dashboard
- El bot principal no llama directamente al dashboard (para evitar acoplamiento y bloqueo).
- En su lugar, usa un **sistema de eventos asíncronos** mediante una cola (`asyncio.Queue`) o un `pub/sub` simple.
- El módulo `hub/events.py` definirá:
  - Clases de eventos: `SignalEvent`, `OrderEvent`, `CapitalEvent`, `HealthEvent`, etc.
  - Una función `publish_event(event)` que el bot puede llamar en cualquier momento
  - El servidor de dashboard se suscribe a esta cola y transmite los eventos por WebSocket
- Esto desacopla completamente el bot del dashboard: si el dashboard falla, el bot sigue funcionando.

### 4. Frontend (interfaz web)
- El dashboard servirá una página HTML simple en la ruta raíz (`/`) que:
  - Se conecta al WebSocket en `ws://localhost:8080/ws`
  - Muestra los datos en tiempo real en secciones claramente etiquetadas:
    - Señales recientes
    - Órdenes activas y recientes
    - Capital y estado de Massaniello
    - Salud del sistema (conexión, latencia, ciclos, errores)
    - Modo demo activado/desactivado
  - Permite pausar/reanudar la actualización de eventos (los eventos se bufferizan en el backend o se ignoran temporalmente)
  - Usa JavaScript vanilla (no se requieren frameworks como React o Vue para mantenerlo ligero)
  - Es responsivo y legible en móviles y escritorio
- El HTML se servirá como una cadena estática desde FastAPI (o desde un directorio `static/` si se prefiere separar recursos).

### 5. Modo de demostración
- Activado por variable de entorno: `HUB_DEMO_MODE=true`
- En modo demo:
  - El bot de trading puede no estar conectado al broker real (o puede estar en modo simulación)
  - El dashboard genera eventos simulados cada pocos segundos:
    - Señales aleatorias (símbolos OTC, direcciones, scores entre 60-90)
    - Órdenes simuladas con resultados aleatorios
    - Capital que aumenta o disminuye según resultados simulados
    - Salud del sistema: conexión simulada como "OK", latencia baja, ciclos incrementando
  - Esto permite probar el dashboard sin necesidad de conexión real al broker
  - Útil para desarrollo, pruebas y demostraciones

### 6. Manejo de errores y resiliencia
- Si el servidor de dashboard falla al iniciar, se registra el error pero el bot continúa (no es crítico para el trading)
- Las conexiones WebSocket se manejan con timeouts y reconexión automática desde el frontend
- Los eventos se bufferizan brevemente en el backend si no hay clientes conectados (opcional, para no perder datos)
- Se registran logs de actividad del hub en el sistema de logging existente (`loguru`)

### 7. Dependencias externas
- Se agregarán a `requirements.txt`:
  ```
  fastapi>=0.100.0
  uvicorn>=0.25.0
  ```
- Estas son ligeras, ampliamente usadas, y compatibles con el entorno actual (Python 3.10+)
- No entran en conflicto con dependencias existentes como `pyquotex`, `python-dotenv`, `pandas`, `loguru`

### 8. Seguridad y exposición
- El servidor de dashboard solo escucha en `localhost` (127.0.0.1) por defecto, no en todas las interfaces
- Se puede cambiar mediante variable de entorno `HUB_HOST=0.0.0.0` si se necesita acceso externo (no recomendado en producción sin autenticación)
- No se requiere autenticación para el modo demo o desarrollo local, pero se puede agregar en el futuro si se expone fuera de localhost

### 9. Estado inicial y reconexión
- Cuando un cliente se conecta por WebSocket, el servidor envía inmediatamente un mensaje de estado inicial:
  ```json
  {
    "type": "initial",
    "message": "esperando datos...",
    "demo_mode": true/false
  }
  ```
- Si el bot no ha enviado aún ningún evento, este mensaje se muestra hasta que llegue el primer evento real o simulado.
- Esto mejora la experiencia de usuario al evitar una pantalla vacía en frío.

### 10. Escalabilidad y mantenimiento
- El diseño es modular:
  - `hub/server.py`: servidor FastAPI + configuración de WebSocket y rutas HTTP
  - `hub/events.py`: definición de eventos y sistema de publicación/suscripción
  - `hub/__init__.py`: paquete (vacío o con metadatos)
- Fácil de extender en el futuro:
  - Agregar más tipos de eventos (por ejemplo, gráficos, alertas, configuración en tiempo real)
  - Agregar autenticación básica si se expone más allá de localhost
  - Agregar soporte para múltiples clientes simultáneos (ya lo soporta WebSocket nativo)

## Alternativas descartadas

| Alternativa | Motivo de rechazo |
|------------|-------------------|
| Usar solo `websockets` library + servidor asyncio manual | Requiere más código boilerplate, menos estructura para HTTP/WebSocket mixto, más propenso a errores |
| Django Channels | Muy pesado, sobrecargado para este uso, requiere configuración de ASGI, canales, etc. |
| Flask + SocketIO | Menos nativo en asyncio, requiere más dependencias, menos rendimiento en alto tráfico de WebSocket |
| HTTP polling (cliente hace `GET /api/events` cada segundo) | Ineficiente, genera tráfico innecesario, latencia alta, no cumple con requisito de actualización en tiempo real |
| Guardar estado en archivo y leerlo desde el frontend | Muy lento, riesgo de condiciones de carrera, no actualiza en tiempo real |
| Usar una solución externa como Grafana o Kibana | Sobrecargado, requiere infraestructura externa, no integrado, pierde la simplicidad y el control total |

## Tecnologías utilizadas

- **Backend:** Python 3.10+, FastAPI, Uvicorn
- **Frontend (embebido):** HTML5, CSS3, JavaScript vanilla (ES6+)
- **Comunicación:** WebSocket (RFC 6455), HTTP/1.1
- **Variables de entorno:** `HUB_PORT`, `HUB_DEMO_MODE`, `HUB_HOST` (opcional)
- **Logging:** `loguru` (ya usado en el proyecto)
- **Pruebas:** Se agregarán tests unitarios e de integración en `tests/test_hub_*`

## Próximos pasos (para el implementer)

1. Agregar `fastapi` y `uvicorn` a `requirements.txt`
2. Crear la estructura en `hub/`:
   - `hub/server.py`
   - `hub/events.py`
   - `hub/__init__.py`
   - (opcional) `hub/templates/index.html` o servir HTML como cadena desde `server.py`
3. Modificar `main.py` para iniciar el servidor de dashboard como tarea `asyncio`
4. Crear tests en `tests/test_hub_server.py`, `tests/test_hub_events.py`
5. Probar que:
   - El servidor se inicia en `http://localhost:8080`
   - Recibe eventos del bot y los transmite por WebSocket
   - Funciona en modo demo
   - No bloquea el bot principal
   - Se puede acceder desde el navegador
   - Se puede pausar/reanudar
6. Actualizar `progress/impl_hub_live_websocket.md` con trazabilidad R→test
7. Ejecutar `python -m pytest tests/ -v` y `.\\init.ps1` → ambos deben pasar
8. Someter a revisión del reviewer

## Verificación del reviewer

El reviewer verificará que:
- Las dependencias están en `requirements.txt`
- El servidor se inicia correctamente
- Los eventos del bot se transmiten por WebSocket
- El modo de demostración funciona
- El endpoint `/health` responde `{"status": "ok"}`
- No hay bloqueo del ciclo principal de trading
- Los tests pasan
- El trazabilidad R→test está documentada y verificada
- `.\\init.ps1` termina en verde

--- 

Este diseño cumple con todos los requisitos en `requirements.md` y sigue las convenciones del proyecto.