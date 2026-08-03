# TODOS — T2: Origen de la dirección (M1 vs M15) — 2026-08-03

> Lista de trabajo preparada por la ventana principal para decidir **quién elige
> la dirección del trade en el Edificio**. No es un bug: es una decisión de régimen.
> - Plan (`docs/EDIFICIO_CONTRATACION.md:26-28`): **M15 es el juez principal**; M1 es
>   solo contexto visual (Track B descartado el 30/07: filtrar por M1 = 0 entradas).
> - Código actual (`src/scanner.py:1475-1497`): la dirección se deriva PRIMERO desde
>   el estocástico M1 (K sube 3 velas → CALL, baja → PUT) y M15 solo como fallback.
> - La dirección manda sobre las puertas del piso: `cross_ok` y `extreme_ok` solo
>   valen si van a favor de la dirección (scanner.py:1500-1502).
> - Destinada a **Hermes (otra ventana)**. Tanda anterior archivada en
>   `progress/plan_completado/todos_auditoria_edificio_2026-08-03.md`.

---

## Reglas duras de esta tanda

- **Una tarea a la vez.** Tests verdes con cada cambio de código.
- Suite del edificio: `python -m pytest tests/test_edificio_contratacion.py tests/test_edificio_executor.py tests/test_edificio_trazabilidad.py` (47 tests hoy).
- Los 32 fallos preexistentes (STRAT-A, session_lifecycle, smart_order_place) NO son responsabilidad: no deben crecer, pero no los arregles.
- **NO tocar la decisión de dirección** — la Fase A es SOLO telemetría. La decisión se toma en la Fase C con datos y aprobación del usuario.
- **NO bumpear `EDIFICIO_RULE_VERSION`** en la Fase A (no cambia reglas de decisión, solo añade logging).
- Commits convencionales, mensajes claros. Sin atribución de IA.
- **Regla aprendida de la tanda anterior:** una tarea NO está done sin el test que la prueba, y la verificación se hace contra el código real (no contra claims). El CSV/DB de producción no se contamina con fixtures (usar `tmp_path`/monkeypatch).
- Si una tarea cambia reglas de decisión (Fase C aprobada) → bumpear `EDIFICIO_RULE_VERSION` en `src/config.py:80`.

---

## Fase A — Telemetría: registrar el origen de la dirección (code-change, NO toca la decisión)

### [ ] A1. Computar `direction_source` en el scanner
**Qué**: en `src/scanner.py` bloque 1475-1497, computar el origen de la dirección elegida:
- `"M1"` si la rama M1 (1476-1488) seteó la dirección.
- `"M15"` si la dirección salió del fallback M15 (1489-1497).
- `""` si no hay dirección.
**Pasos**:
1. Variable `_direction_source` seteada junto con `_direction`.
2. Agregarla al dict `flags_by_asset` (:1516-1530) junto a `"direction"`.
**Done**: `flags_by_asset[_sym]["direction_source"]` correcto en los 3 casos.

### [ ] A2. Columna `direction_source` en la caja negra
**Qué**: `src/black_box_recorder.py` — mismo patrón que `brake_verdict`:
1. Definición de columna `"direction_source": "TEXT"` (junto a :371-375).
2. Parseo `data.get("direction_source", None)` (patrón :411-430).
3. Agregar al INSERT de `scan_candidates` (:434-446).
**Done**: INSERT con la columna nueva; test de persistencia.

### [ ] A3. Cablear hasta `scan_candidates`
**Qué**: garantizar que `direction_source` viaja desde el scanner hasta el
`record_candidate` de la caja negra (misma ruta que `stoch_k`/`stoch_m15_full`,
incluido `_feed_edificio` scanner.py:3015-3048 si aplica).
**Done**: un candidato EDIFICIO registrado en la DB tiene `direction_source` poblado (verificación real contra la DB de tests, no contra mocks).

### [ ] A4. Tests
- Feed/scanner: M1 sube → `direction_source="M1"`; M1 plano + M15 decide → `"M15"`; sin dirección → `""`.
- Recorder: la columna se persiste y se lee bien.
**Done**: tests presentes + suite edificio verde (debe seguir 47 + nuevos).

### [ ] A5. Validación
1. Suite edificio verde.
2. `.\init.ps1` → los 32 fallos preexistentes NO crecen.
**Done**: evidencia escrita en este doc.

### [ ] A6. Commit
- `feat(edificio): telemetria direction_source en caja negra` (o similar, convencional).
- NO bumpear rule_version. NO tocar la decisión.
**Done**: commit + `git status` limpio.

---

## Fase B — Recolección de muestra (NO es tarea de Hermes; es del usuario)

- [ ] B1. Correr el bot en PRACTICE (demo) hasta tener **n≥30** candidatos con `direction_source="M1"` y **n≥30** con `"M15"` en `scan_candidates`.
- Estimar días según ritmo actual de señales; registrar fechas de inicio/fin en la Fase C.

---

## Fase C — Análisis y decisión (read-only → aprobación del usuario)

### [ ] C1. Query de WR por origen
- SQL a `scan_candidates` (strategy EDIFICIO, `direction_source NOT NULL`):
  WR por `direction_source` (M1 vs M15), separado CALL/PUT, con `order_result`.
- Reportar también el WR total de la ventana como referencia.
**Done**: números escritos en el reporte.

### [ ] C2. Aplicar regla de corte
- n≥30 por grupo. Si `|WR_M1 - WR_M15| ≥ 8pp` → hay señal → decidir.
- Si <8pp o muestra insuficiente → no hay señal: mantener estado actual y re-medir.
**Done**: veredicto con justificación numérica.

### [ ] C3. Recomendación escrita → ESPERAR al usuario
- Si M15 gana: recomendar alinear al plan (eliminar rama M1, scanner.py:1476-1488).
- Si M1 gana o empata: recomendar cerrar T2 como documentación (M1 se queda).
- **NO convertir en código sin aprobación explícita del usuario.**
**Done**: reporte entregado y esperando.

### [ ] C4. Solo si el usuario aprueba el cambio (alinear a M15)
- Eliminar rama M1 (1476-1488), bumpear `EDIFICIO_RULE_VERSION` en `src/config.py:80`,
  actualizar tests A1 (direction_source siempre "M15" salvo sin dirección), suite verde, commit.
**Done**: suite verde + commit + doc de auditoría actualizado.

---

## T3 — Pendiente referenciado (NO mezclar con esta tanda)

Cierre del experimento post-freno: `EDIFICIO_POST_BRAKE_MIN_RATIO = 0.0`
(`src/config.py:83`) mide `post_brake_body_ratio` pero no veta.
- Contar muestra por bucket (n≥30) y WR; fijar umbral y fecha de corte.
- Si `0.0` es óptimo → cerrar como documentación; si hay sesgo → code-change con aprobación.
- Se aborda DESPUÉS de cerrar T2 (una tarea a la vez).

---

## Orden de ejecución
A1 → A2 → A3 → A4 → A5 → A6 → (B1 = usuario deja correr demo) → C1 → C2 → C3 → ⏸ usuario → C4 (solo si aprueba).
