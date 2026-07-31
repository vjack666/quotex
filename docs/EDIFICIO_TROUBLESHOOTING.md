# Edificio de Contratación — Troubleshooting

Bitácora de problemas reales, causa raíz y solución aplicada.

---

## 1. Hub con lock antiguo impide arrancar

- **Síntoma:** `Another QUOTEX webapp instance is already running (lock: ...\runtime\main.lock)`
- **Causa:** `stop_webapp.bat` no terminaba instancias previas; lockfile quedaba vivo por proceso Edge residual.
- **Solución:** usar lockfile como fuente de verdad; no matar PIDs directamente. Reiniciar con `stop_webapp.bat` y luego `app.py` en comandos separados.

## 2. Bot no inyectado en hub al inicio (`bot_no_edificio`)

- **Síntoma:** `/api/contract/execute` devolvía `bot_no_edificio` en el primer request.
- **Causa:** `_bot_ref=None` hasta un segundo request; race condition entre startup y primer request.
- **Solución:** fallback lazy en endpoints hacia `app._runner.bot`; mantener `set_bot()` como inyección principal.

## 3. `/api/contract/probe` cargaba pero daba 500

- **Síntoma:** traceback `NameError: name 'CONTRACT_DEFAULT_AMOUNT' is not defined`.
- **Causa:** patch anterior no persistió constantes en `hub/server.py`.
- **Solución:** definir `CONTRACT_DEFAULT_AMOUNT = 1.0` y `CONTRACT_DEFAULT_DURATION = 900` en módulo.

## 4. Proceso combinado `stop + start` moría con exit 127

- **Síntoma:** `cmd.exe /c stop_webapp.bat && sleep 2 && python app.py` fallaba.
- **Causa:** shell sin job control + lockfile; el `&&` no garantizaba estado limpio.
- **Solución:** separar stop y start en comandos distintos.

## 5. Código cacheado sin parches (`bot_no_edificio` repetido)

- **Síntoma:** error reaparecía aunque el código estaba corregido.
- **Causa:** proceso hub cargaba código viejo desde `__pycache__`.
- **Solución:** reinicio explícito con limpieza de `__pycache__` antes de relanzar.

## 6. Historial de contratados contaminado

- **Síntoma:** `contratados_recientes` acumulaba eventos de pruebas previas.
- **Solución:** método `reset_contratados_recientes()` + snapshot inicial en `data\logs\edificio_snapshot_<timestamp>.json`.

## 7. Caja negra no registraba eventos detallados

- **Síntoma:** logs existían pero sin contexto de edificio.
- **Solución:** auditoría confirmó DB y log activos; próximamente inyectar `black_box_cid` y detalle de piso/condiciones en cada `ContratadoEvent`.
