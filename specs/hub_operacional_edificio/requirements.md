# Requirements — hub_operacional_edificio (Feature 41)

Este SPEC cumple el Laboratory Charter (docs/LAB_CHARTER.md). No modifica ninguno de sus principios. Subordinado a AGENTS.md y docs/specs.md.

El objetivo es cerrar el ciclo operativo del Edificio de Contratación: las herramientas de la fábrica (feature 40) ya están enchufadas como gate; ahora deben producir señales reales a la cuenta, con Massaniello desde el inicio, caja negra recolectando velas 1m sin borrado, y un hub verificado físicamente.

## R1 — Acceso directo al hub
El sistema DEBE proveer un acceso directo de Windows `QUOTEX Web App.lnk` que lance `python app.py` (el launcher del hub) y abra el dashboard en el navegador por defecto.

## R2 — Envío de señales a la cuenta (modo seguro por defecto)
CUANDO el Edificio alcanza un evento CONTRATADO, el sistema DEBE enviar la orden al broker vía `edificio_executor.execute_contratados` usando `account_type = PRACTICE` (demo) por defecto.
SI el operador provee credenciales válidas en `.env` Y activa explícitamente el flag `EDIFICIO_ACCOUNT_TYPE=REAL`, ENTONCES el sistema DEBE enviar a cuenta real. El sistema NO DEBE enviar a cuenta REAL sin ambas condiciones.

## R3 — Conmutación de cuenta sin tocar credenciales
El sistema DEBE leer `account_type` desde `config.EDIFICIO_ACCOUNT_TYPE` en tiempo de arranque y exponerlo en el hub (`/api/state` y panel de config), de forma que el cambio demo/real NO requiera editar código ni credenciales por parte del agente.

## R4 — Massaniello activo desde el inicio
CUANDO el bot arranca, el sistema DEBE inicializar el gestor Massaniello (`bot.massaniello`) y aplicar la forma de bankroll inmediatamente, antes de la primera operación. El monto de cada orden del Edificio DEBE derivarse de `massaniello.next_stake(...)`.

## R5 — Massaniello gobierna el monto del Edificio
CUANDO `edificio_executor` envía una orden, el sistema DEBE usar el stake calculado por Massaniello (no un monto fijo), salvo que `STAKE_MODE=fixed` esté activo desde el hub.

## R6 — Caja negra recolecta velas 1m en cada operación
CUANDO el Edificio registra un candidato aceptado o una orden enviada, el sistema DEBE guardar el snapshot de velas de 1m (contexto previo + post-cierre) en `black_box_recorder`, enriquecido con `stoch_m1`.

## R7 — Caja negra recolecta velas 1m al llegar a piso 1
CUANDO un activo ingresa a PISO_1 (Recepción) del Edificio, el sistema DEBE registrar el snapshot de velas 1m de ese instante como línea base de trazabilidad.

## R8 — Sin borrado de velas (retención infinita en crudo)
El sistema NO DEBE eliminar ningún archivo de base de datos de caja negra por antigüedad. El parámetro `RETENTION_DAYS` de `BlackBoxRecorder` DEBE ser 0 (sin caducidad). El sistema DEBE ofrecer solo exportación a `exports/black_box/` como mecanismo de archivo, nunca borrado automático.

## R9 — Caja negra recolecta el máximo de datos 1m posible
El sistema DEBE extender el snapshot de velas 1m a la mayor ventana disponible del buffer del bot (mínimo 60 velas previas) y mantener la captura post-cierre hasta la resolución de la orden, para acumular el máximo de muestras de mercado.

## R10 — Mejora del hub (+110%)
El sistema DEBE mejorar el dashboard `hub/static/index.html` y `hub/server.py` para exponer claramente: estado de cuenta (demo/real), masa Massaniello en vivo, secuencia W/L, última orden, y panel de caja negra. La mejora DEBE medirse como +110% respecto al baseline (más KPIs, más controles, menos pasos para operar).

## R11 — Eliminación de redundancia
El sistema NO DEBE mantener módulos, endpoints o controles de UI que sean duplicados o huérfanos (p.ej. paneles STRAT-F muertos si el Edificio es la única estrategia viva). El implementer DEBE eliminar lo redundante y documentarlo en `progress/impl_hub_operacional.md`.

## R12 — Verificación física de cada control del hub
El sistema DEBE verificar mediante navegador (browser-driven) que cada botón y cada opción de menú desplegable del hub funciona de verdad (no adornos): start, stop, reconnect, force-kill, shutdown, cada tab, cada `<select>` y cada botón de config. Cualquier control que no responda DEBE ser reparado o eliminado. La verificación DEBE documentarse con capturas/evidencia en `reports/hub_verificacion/`.

## R13 — Trazabilidad de herramientas en la señal
CUANDO el Edificio emite una señal CONTRATADO, el sistema DEBE incluir en la orden y en la caja negra la trazabilidad de la herramienta que la originó (feature 40: audit_decision → EXP-XXX), cumpliendo el Charter Art. 10 (dominio fijo).

## R14 — Tests verdes para código nuevo
El implementer DEBE añadir tests en `tests/` que cubran: enchufe de cuenta (R2/R3), init temprano de Massaniello (R4), derivación de monto (R5), grabación 1m sin borrado (R6/R7/R8/R9), y wiring de cada botón del hub (R12). El reviewer DEBE rechazar si falta trazabilidad R<n> → test.
