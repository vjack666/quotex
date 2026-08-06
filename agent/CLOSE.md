# CLOSE — Protocolo de Cierre de Sesión (apagar / "listo por hoy")

> Cuando el usuario diga **`listo por hoy`**, **`voy a apagar`**, **`cerrar
> sesión`**, **`terminamos`**, o cualquier frase equivalente, ejecutá este
> protocolo **exactamente** antes de soltar el control.
>
> Objetivo: que la PRÓXIMA sesión (cuando el usuario escriba `start`) arranque
> DESDE DONDE QUEDAMOS, no de cero. El agente no recuerda el chat entre
> sesiones; solo recuerda lo que está escrito en `/agent/*` y `progress/*`.

---

## Trigger

Frases que activan este protocolo (no hace falta que sea la única palabra):

```
listo por hoy
voy a apagar
voy a cerrar
cerrar sesión
terminamos
ya paro
apagar la compu
```

Ante cualquiera de esas, ejecutar el workflow completo abajo. No pedir
confirmación del usuario para CERRAR (ya dijo que se va); solo ejecutar y
entregar el resumen final.

---

## Close Workflow (ordenado)

### Phase A — Git: dejar el repo limpio y seguro

1. `git status` — ver qué quedó sin commitear.
2. **NO commitear trabajo ajeno.** Solo commitear lo de la sesión actual,
   archivo por archivo (nunca `git add -A` ciego). Si hay archivos sin
   staging que NO son de la sesión, dejarlos fuera y reportarlos.
3. Si hay cambios de la sesión sin commitear → `git add <solo lo mio>` +
   `git commit` con mensaje descriptivo. Regla §15: mostrar diff/hash.
4. **NO push sin OK del usuario.** Si la sesión terminó con un push ya
   autorizado, está bien. Si quedó pendiente push, NO lo hagas solo:
   reportarlo en el resumen y esperar OK la próxima vez.
5. `git log --oneline -1` — anotar el HEAD en el resumen.

### Phase B — Synthesizar estado de la sesión

6. En 5–8 líneas, resumir QUÉ se hizo hoy y QUÉ decisión se tomó.
   Incluir siempre:
   - Feature/objetivo trabajado y su estado (pending/spec_ready/in_progress/done).
   - Última decisión del usuario (aprobación, force-push, cambio de enfoque).
   - Próximo paso sugerido (la continuación lógica).

### Phase C — Actualizar memoria entre sesiones (OBLIGATORIO)

Escribir/actualizar estos archivos EN ESTE ORDEN (si no existen, crearlos):

| Orden | Archivo | Qué poner |
|-------|---------|-----------|
| 1 | `agent/HANDOFF.md` | El resumen de Phase B arriba. Es el PRIMER archivo que `start` lee. Debe decir dónde quedamos y qué hacer al volver. |
| 2 | `agent/PROJECT_STATE.md` | Milestone actual, estado de arquitectura, bloqueos. |
| 3 | `progress/current.md` | Estado de la sesión activa (formato corto, del SDD del harness). |
| 4 | `agent/TASKS.md` | Si cambió el estado de tareas (In Progress / Next / Completed). |
| 5 | `progress/history.md` | Append-only: pegar el resumen de la sesión al final (bitácora). |

Regla de oro: el próximo "yo" debe poder leer `HANDOFF.md` y saber el hilo
sin re-leer todo el repo.

### Phase D — Archivos clave para retomar

7. En `HANDOFF.md`, listar las rutas absolutas de los archivos que el próximo
   arranque debe leer primero (specs, Charter, scripts, módulos tocados).
   Ejemplo:
   - `docs/LAB_CHARTER.md` (principios inquebrantables)
   - `docs/specs.md` (ciclo de vida + checklist)
   - `specs/<feature>/` (requirements/design/tasks/review)
   - `scripts/lab_run.py`, `scripts/lab_ci.py`

### Phase E — Reglas que NO romper al retomar

8. En `HANDOFF.md`, recordar las reglas duras del proyecto:
   - Una feature a la vez. SDD obligatorio para features `sdd:true`.
   - No push sin OK. Commit = solo trabajo de la sesión.
   - El bot corre PRACTICE por defecto; NUNCA REAL sin OK explícito.
   - Datos REAL (EURUSD) = descubrimiento; OTC = validación final.
   - Trader-Humano revisa specs; usuario aprueba antes de implementar.

### Phase F — Resumen final (salida requerida)

9. Producir un **short close summary** para el usuario:

```
## Close Summary

**Branch:** <branch>
**Git HEAD:** <hash>
**Commits de la sesión:** <n | 0>
**Push:** <hecho | pendiente (esperar OK)>
**Archivos sin commitear:** <ninguno | lista breve de ajenos>

### Qué se hizo hoy
<3-5 bullets>

### Decisión tomada
<1 frase>

### Próximo paso sugerido
<1 frase accionable>

### Al retomar (start)
Leé agent/HANDOFF.md — dice dónde quedamos.
```

10. **Soltar el control.** No seguir trabajando. El usuario se va.

---

## Automatización futura (opcional)

Si más adelante se quiere, este protocolo puede dispararse solo al detectar
inactividad o comando de apagado del SO. Por ahora es manual: el usuario
dice la frase y el agente lo corre.

---

## Relación con START

| | START (`start`) | CLOSE (`listo por hoy`) |
|---|---|---|
| Cuándo | Al abrir | Al cerrar |
| Lee | `/agent/*` + `progress/*` | Escribe `/agent/*` + `progress/*` |
| Objetivo | Saber dónde quedamos | Dejar dicho dónde quedamos |
| Git | `pull` + `init.ps1` | commit sesión + NO push ciego |

Ambos mantienen el sistema de memoria entre máquinas sincronizado.
