# Estado de sesión

<!-- Plantilla — la sesión 2026-07-31 (purga: solo Edificio) está en progress/history.md -->

## 2026-08-02 — Protocolo de inicio, espera post-freno y poblado de loss_reason

### Qué se hizo
- **Protocolo de inicio**: agregó carga garantizada de `C:\Users\v_jac\.hermes.md` y `docs/engineering.md` desde el primer mensaje.
- **Espera post-freno matemática**: agregó medición de `body/range` de la primera vela M15 post-freno sin bloquear entradas, lista para experimento demo.
- **Poblado de `loss_reason`**: en `LOSS` se infiere y graba la causa (`NO_BRAKE`, `NO_CROSS`, `STICKY_CROSS`, etc.) para diagnóstico real.

### Cambios
- `C:\Users\v_jac\.hermes.md`: Protocolo de Inicio + verificación de comprensión + tono conversacional.
- `C:\Users\v_jac\Desktop\QUOTEX\docs\engineering.md`: nuevo archivo con filosofía de ingeniería.
- `C:\Users\v_jac\Desktop\QUOTEX\AGENTS.md`: flujo `start` carga identidad y método antes de actuar.
- `src/config.py`: agrega `EDIFICIO_POST_BRAKE_MIN_RATIO = 0.0`, bump `EDIFICIO_RULE_VERSION` a `2026-08-02b`.
- `src/edificio_contratacion.py`: agrega `body_5m` en `BuildingCard`, método `_measure_post_brake()`, y campos de experimento.
- `src/edificio_executor.py`: graba campos de experimento en black box y pobla `loss_reason` en `LOSS`.
- `src/black_box_recorder.py`: migra columnas `post_brake_body_ratio`, `post_brake_would_pass`, `post_brake_measured_at`.
- `tests/test_edificio_executor.py`: 6 tests nuevos para `_infer_loss_reason`.

### Verificación
- `pytest tests/test_edificio_contratacion.py tests/test_edificio_executor.py -q`: 27 passed.
- `.\init.ps1`: detecta 32 failures preexistentes fuera del paquete edificio; documentado como ruido conocido.

### Próximo paso
- Correr demo en `PRACTICE` y usar `data/db/black_box_strat_YYYY-MM-DD.db` para definir el corte óptimo de `EDIFICIO_POST_BRAKE_MIN_RATIO`.
- Una vez definido, activar el gate en `evaluate()` para subir de P2 a P3 solo si `post_brake_body_ratio >= EDIFICIO_POST_BRAKE_MIN_RATIO`.

### Pendiente
- Ninguno para demo de Edificio.

---

## 2026-08-02 (segunda pasada) — Investigación: por qué no pasa ningún par (demo cerrada)

### Qué se hizo
- Demo en PRACTICE cerrada por el usuario (~11:20): ningún par avanzaba de P2.
- Diagnóstico con caja negra + logs → **causa raíz identificada; no hace falta recolectar más datos para el porqué**.

### Causa raíz (regresión lógica, no mercado ni datos)
- Commit `7f20cc6` (2026-08-01 19:29, "espera post-freno, eliminar sticky, delay ejecución") dejó la puerta P2→P3 autocontradictoria: exige `cross_ok and not cross_sticky`, pero el cruce y el sticky se computan en el **mismo scan** (`scanner.py:1497-1500`): al detectarse el cruce K≈D → `is_sticky_cross` (|K−D|<3.0) es **siempre True** → ningún cruce limpio existe → nadie sube a P3.
- Evidencia: 08-01 con reglas viejas = **66 órdenes reales** (10:20–19:00); desde el deploy del código nuevo (08-01 19:30) = **0 órdenes** (~16 h de runtime). Hoy solo `ETHUSD_otc` llegó a P2 (11:16:31) y quedó en "sticky" hasta el cierre de la demo.
- Demoras extra que hacen casi imposible el flujo en demo corta: confirmación del freno **15 min sin titilar** (`brake_at + 900s`, cualquier flicker resetea) + delay de **5 min** en P3 (`entry_pending`).

### Hallazgo del experimento post-freno
- `post_brake_body_ratio`: **0 registros** en los JSONL y DBs — la medición NO se está poblando (falta wiring en el flujo scanner→edificio; `_measure_post_brake` no produce datos). El experimento de la mañana no recolectó nada.
- Las DBs `black_box_strat_2026-07-31.db` / `_08-01.db` SÍ tienen contexto de órdenes reales (backfill) → se puede validar la regla post-brake **offline** antes de volver a medir en vivo.

### Estado
- Freno NO superado: paquete de código del freno (`config.py`, `edificio_contratacion.py`, `edificio_executor.py`, `black_box_recorder.py`, `tests/test_edificio_*`) **sin commitear a propósito** hasta resolver la puerta P2→P3.
- Commiteado: protocolo de inicio (`.hermes.md` + `docs/engineering.md`), watchdog webapp, estado de sesión.

### Próximo paso
- Decidir el fix de la puerta sticky (volver a `cross_ok or cross_sticky`, histeresis post-cruce, o ajustar `EDIFICIO_STICKY_THRESHOLD`) para que los pares vuelvan a subir a P3 → CONTRATADO.
