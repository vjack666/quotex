# Protocolo de validación live — Config secuencia Edificio

**Config bajo prueba**:
- `kd_distance >= 2.0`
- `dwell_cerebro = 1`
- `cross_limpieza_ok = True`

**Objetivo**:
- Medir cuántos `CONTRATADO` reales se bloquean por secuencia.
- Medir cuántos llegan a `ENTRADA` y se convierten en orden enviada.
- Confirmar que la tasa de `ENTRADA` no cae a 0 como en la base vieja.

**Duración**:
- Mínimo 30 minutos de captura limpia con bot corriendo.
- Si en ese lapso no aparece al menos 1 evento en `CEREBRO` con `kd_distance` real, extender a 1 hora.

**Métricas**:
- `entrada_count`: órdenes efectivamente enviadas desde `ENTRADA`.
- `reject_reception_count`: bloqueos en recepción por secuencia.
- `reject_cerebro_count`: bloqueos en cerebro por `kd_distance` o dwell.
- `noise_count`: eventos que entran sin cumplir la secuencia.

**Criterio de éxito**:
- `entrada_count > 0`
- `noise_count = 0`

**Criterio de fracaso**:
- `entrada_count = 0` luego de la ventana completa → reevaluar dataset o condiciones de captura.
- `noise_count > 0` → endurecer `edificio_executor.py` para consultar `SequenceEngine` antes de enviar.

**Siguiente acción automática**:
- Registrar resultados en `src/strategy_lab/results/exp039_live_validation.json`.
- Actualizar bitácora con conclusión.
