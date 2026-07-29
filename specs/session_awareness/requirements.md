# Requirements — session_awareness

> **Feature ID:** 21
> **Status:** spec_ready
> **Depends on:** None

---

## R1 — Session Detection

CUANDO el bot está operando,
EL sistema DEBE detectar la sesión de trading actual basándose en la hora UTC:
- Asian: 00:00 - 08:00 UTC
- London: 08:00 - 16:00 UTC
- New York: 16:00 - 21:00 UTC
- Off-hours: 21:00 - 00:00 UTC

---

## R2 — Session Configuration

EL sistema DEBE tener configuración por sesión en `config.py`:
```python
SESSION_CONFIG = {
    "asian": {"min_score": 65, "enabled": True},
    "london": {"min_score": 60, "enabled": True},
    "new_york": {"min_score": 55, "enabled": True},
    "off_hours": {"min_score": 75, "enabled": False},
}
```

---

## R3 — Score Threshold Adjustment

CUANDO el scanner evalúa un candidato,
EL sistema DEBE usar el `min_score` de la sesión actual en vez del global `STRAT_F_MIN_SCORE`.

---

## R4 — Off-Hours Block

CUANDO la sesión es "off_hours" y `SESSION_OFF_HOURS_ENABLED = False`,
EL sistema DEBE bloquear todas las entradas y loggear:
`[SESSION] Off-hours activo — entradas bloqueadas hasta London open`

---

## R5 — Session Logging

CUANDO inicia un ciclo de scan,
EL sistema DEBE loggear:
`[SESSION] London activo (08:00-16:00 UTC) | min_score=60`

---

## R6 — Session Transition

CUANDO la sesión cambia (ej: asian → london),
EL sistema DEBE loggear el cambio:
`[SESSION] Transición: asian → london (08:00 UTC)`

---

## R7 — Configuration Override

CUANDO `SESSION_AWARENESS_ENABLED = False`,
EL sistema DEBE ignorar toda configuración de sesión y usar el comportamiento actual (global min_score).

---

## R8 — Tests

Los tests DEBEN cubrir:
- Detección correcta de cada sesión (asian, london, ny, off)
- Score threshold adjust por sesión
- Off-hours blocking
- Session transition logging
- Disabled session awareness (fallback global)
- Edge cases: exact hour boundaries (08:00, 16:00, 21:00)
