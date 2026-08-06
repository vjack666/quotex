# Spec Driven Development (SDD)

> Este proyecto sigue un flujo Kiro-style: requirements → design → tasks → code.
> El código no se escribe hasta que el spec está aprobado por un humano.

## Estructura

Cada feature nueva (`"sdd": true` en `feature_list.json`) tiene una carpeta
dedicada en cuanto deja `pending`:

```
specs/<feature-name>/
├── requirements.md   # QUÉ se necesita (EARS notation)
├── design.md         # CÓMO se construirá (decisiones técnicas)
└── tasks.md          # PASOS concretos a implementar
```

El `feature-name` coincide con el campo `name` de `feature_list.json`.

## Estados de una feature

| Estado | Significado |
|---|---|
| `pending` | Sin spec. El `spec_author` es el primero en actuar. |
| `spec_ready` | Spec drafted. Esperando aprobación humana. NO se toca código. |
| `in_progress` | Spec aprobado. `implementer` trabajando. |
| `done` | Código verde, `reviewer` aprobó, sesión cerrada. |
| `blocked` | Atascado. Razón en `progress/current.md`. |

## La puerta de aprobación humana

El flujo automático se detiene **una vez**: cuando el `spec_author` termina
sus tres archivos, marca la feature como `spec_ready` y para. El humano
lee `specs/<feature>/` y dice "aprobado" (o pide cambios).

Solo entonces el `leader` transiciona `spec_ready → in_progress` y lanza
el `implementer`.

```
pending → [spec_author] → 🧑‍💼 trader_humano revisa specs → spec_ready → ⏸ HUMANO → in_progress → [implementer → reviewer] → done
```

> **Nota:** el agente trader-humano (`docs/agente-trader_humano.md`) no solo revisa
> el código final — participa en la **construcción** del spec. Ver sección
> siguiente.

## Participación del agente trader-humano en el SDD

El agente trader-humano (`docs/agente-trader_humano.md`) participa en la
**construcción** de los specs, no solo en la revisión del código terminado.
Su veredicto sobre los requirements/design/tasks es una puerta de calidad
adicional antes de marcar la feature como `spec_ready`.

### Cuándo interviene

Durante la fase `pending → spec_ready`, el `spec_author` NO marca
`spec_ready` hasta que el agente trader-humano haya revisado los tres
archivos del spec y emitido su dictamen. Esto evita que el laboratorio
búsque configuraciones a ciegas sobre un spec que el trader considera
conceptualmente mal planteado.

### Qué revisa el trader-humano

- **requirements.md**: ¿la hipótesis tiene sentido de trader? ¿la métrica de
  éxito (p.ej. EXP-039: `entrada_count>0` Y `noise_count=0`) es la correcta
  o está midiendo ruido en lugar de edge?
- **design.md**: ¿el embudo (funnel) de eventos planteado coincide con la
  realidad del mercado? ¿la secuencia de eventos propuesta es coherente?
- **tasks.md**: ¿los pasos del laboratorio realmente aislan la variable que
  el trader sospecha, o están mezclando cohortes (REAL vs OTC)?

### Dónde deja su dictamen

El trader-humano escribe su revisión en `specs/<feature>/trader_humano_review.md`
con esta estructura mínima:

```markdown
## Revisión trader-humano — <feature>

### Veredicto
APROBADO | CAMBIOS | RECHAZADO

### Dictamen (lenguaje trader)
<por qué la hipótesis/embudo/seguridad tiene o no sentido de mercado>

### Faltantes que exige el trader
<qué debe agregar el spec antes de aprobar>
```

El `spec_author` solo transiciona a `spec_ready` si el veredicto es
`APROBADO` (o si el humano genérico lo override explícitamente).

### Flujo resultante

```
pending
  → [spec_author redacta requirements/design/tasks]
  → 🧑‍💼 trader_humano revisa y dicta (trader_humano_review.md)
  → spec_ready  (solo si trader_humano = APROBADO)
  → ⏸ HUMANO (aprobación final)
  → in_progress → [implementer → reviewer] → done
```

## requirements.md — EARS estricto

Las requirements se redactan en **EARS** (Easy Approach to Requirements
Syntax). Cada requirement es un párrafo numerado con uno de estos cinco
patrones:

| Patrón | Plantilla |
|---|---|
| **Ubicuo** | `El sistema DEBE <acción>.` |
| **Evento** | `CUANDO <disparador>, el sistema DEBE <acción>.` |
| **Estado** | `MIENTRAS <estado>, el sistema DEBE <acción>.` |
| **Opcional** | `DONDE <feature opcional>, el sistema DEBE <acción>.` |
| **No deseado** | `SI <evento no deseado> ENTONCES el sistema DEBE <acción>.` |

Reglas duras:

- Cada requirement tiene un id estable: `R1`, `R2`, ...
- Cada requirement DEBE ser verificable por al menos un test concreto.
- No mezcles varios `DEBE` en un mismo requirement. Si hay más de uno, parte.
- No uses verbos blandos ("podría", "puede", "soporta"). Solo `DEBE` / `NO DEBE`.

Ejemplo:

```markdown
## R1
CUANDO el scanner ejecuta un ciclo completo, el sistema DEBE evaluar
todos los activos OTC abiertos con payout >= 80%.

## R2
SI la descarga de velas para un activo falla (timeout/error), ENTONCES
el sistema DEBE continuar con el siguiente activo sin detener el ciclo.
```

## design.md — decisiones técnicas

Captura **antes** de tocar código:

- Qué archivos se crean / modifican.
- Qué firmas nuevas aparecen (funciones, clases, comandos).
- Qué excepciones se reutilizan o se añaden.
- Qué alternativa se descartó y por qué (mínimo una).

NO es ingeniería desde primeros principios — apóyate en
`docs/architecture.md` y `docs/conventions.md`. El `design.md` documenta los
puntos donde tu feature roza la frontera de esas reglas.

## tasks.md — checklist ejecutable

Pasos discretos en orden, cada uno con checkbox. Cada task referencia al
menos un `R<n>` que cubre.

Ejemplo:

```markdown
- [ ] T1 — Añadir `detect_momentum` en `src/strat_momentum.py`. Cubre: R1, R3.
- [ ] T2 — Integrar nueva estrategia en el pipeline del scanner. Cubre: R1.
- [ ] T3 — Añadir `test_momentum_detect` en `tests/`. Cubre: R1, R2.
```

El `implementer` marca `[x]` cada task al completarla. El `reviewer`
rechaza si queda alguna `[ ]` sin justificación documentada.

## Trazabilidad (regla dura)

- Cada test en `tests/` debe poder mapearse a un `R<n>` de su spec.
- Cada `R<n>` debe tener al menos un test concreto.
- El `reviewer` comprueba esta correspondencia explícitamente y rechaza si falta.

El `implementer` documenta el mapa en `progress/impl_<name>.md`:

```markdown
## Trazabilidad
- R1 → `test_momentum_detect_bullish`
- R2 → `test_momentum_detect_bearish`
- R3 → `test_momentum_detect_no_signal`
```

## Cuándo NO aplica SDD

Las features con `"sdd": false` o sin el campo `sdd` NO tienen spec.
SDD solo se aplica hacia adelante.
