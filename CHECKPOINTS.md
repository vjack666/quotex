# CHECKPOINTS — Evaluación del estado final

> En sistemas multi-agente no se evalúa el camino, se evalúa el destino.
> Estos son los checkpoints objetivos que un juez (humano o IA) puede usar
> para decidir si el proyecto está sano.
>
> **Última evaluación:** 2026-07-04 (22/22 features done)

## C1 — El arnés está completo

- [x] Existen los 4 archivos base: `AGENTS.md`, `init.ps1`, `feature_list.json`, `progress/current.md`.
- [x] Existen los 3 docs: `docs/architecture.md`, `docs/conventions.md`, `docs/verification.md`.
- [x] Existe `docs/ROADMAP.md` con fases y progreso actualizado.
- [x] `.\init.ps1` termina con exit code 0.

## C2 — El estado es coherente

- [x] Como mucho una feature en `in_progress` en `feature_list.json`.
- [x] Toda feature `done` tiene tests asociados que pasan.
- [x] `progress/current.md` está vacío o describe la sesión activa (no contiene basura de sesiones anteriores).

## C3 — El código respeta la arquitectura

- [x] `src/` está dividido en módulos según `docs/architecture.md` (no monolito; facade ≤500 líneas).
- [x] Gestión de riesgo activa es Massaniello (`massaniello_risk.py`), no martingala en runtime.
- [x] No hay dependencias externas sin declarar en `requirements.txt`.
- [ ] No hay `print()` sueltos para debug, ni TODOs sin contexto (revisar periódicamente).

## C4 — La verificación es real

- [x] `tests/` tiene tests para módulos principales (251 tests passing).
- [x] Los tests no dependen del broker (usan mocks en `conftest.py`).
- [x] `python -m pytest tests/ -v` muestra todos los tests verdes.

## C5 — La sesión se cerró bien

- [x] `progress/history.md` tiene entradas por sesiones completadas.
- [x] Todas las 22 features reflejadas como `done` en `feature_list.json`.
- [ ] Validación live del sistema completo en PRACTICE pendiente.

## C6 — Spec Driven Development

- [x] Features `done` tienen carpeta `specs/<name>/` con requirements, design, tasks.
- [x] `requirements.md` usa EARS estricto (ver `docs/specs.md`).
- [x] Features `done` tienen todas sus tasks marcadas `[x]` en `tasks.md`.
- [x] Cada `R<n>` de features `done` cubierto por al menos un test en `tests/`.
