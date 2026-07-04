# Design — strat_a_quality_filters

> Feature id=19. Fase SA-3 — filtros de calidad *reject-first* STRAT-A.
> Referencias: `docs/ROADMAP_STRAT_A.md` (SA-3), `src/config.py`,
> `src/strat_a.py`, `src/scanner.py`, `src/entry_scorer.py`.
> Depende de #18 (`strat_a_test_suite`, done).

---

## Objetivo

Endurecer los umbrales PLAN MAESTRO **solo para STRAT-A** sin alterar el
comportamiento global de STRAT-B, STRAT-MOMENTUM ni `MIN_PAYOUT`. Cada veto
debe ser observable en logs y cubierto por un test aislado.

| Filtro | Actual | Objetivo (#19) |
|--------|--------|----------------|
| Payout mínimo STRAT-A | 80% (`MIN_PAYOUT`) | **87%** (`STRAT_A_MIN_PAYOUT`) |
| Score mínimo STRAT-A | 65–68 adaptativo | **75 fijo** (`STRAT_A_MIN_SCORE`) |
| Edad zona rebote | 20 min (`ZONE_AGE_REBOUND_MIN`) | **30 min** (`STRAT_A_ZONE_MIN_AGE_REBOUND`) |
| Patrón 1m en rebote | penalización / espera | **obligatorio** — sin confirmación = sin señal |

**Fuera de alcance (#20):** HTF 15m, `zone_memory`, `entry_decision_engine`.

---

## Archivos a modificar

| Archivo | Cambio |
|---------|--------|
| `src/config.py` | Añadir `STRAT_A_MIN_PAYOUT`, `STRAT_A_MIN_SCORE`, `STRAT_A_ZONE_MIN_AGE_REBOUND` |
| `src/strat_a.py` | Importar constantes STRAT-A; usar `STRAT_A_ZONE_MIN_AGE_REBOUND` como default de `zone_age_rebound_min`; endurecer veto de patrón en rebotes; nuevo `skip_reason="pattern_missing"` |
| `src/scanner.py` | Filtro payout STRAT-A por activo; pasar `zone_age_rebound_min=STRAT_A_ZONE_MIN_AGE_REBOUND` a `evaluate_strat_a`; logs de veto unificados; score gate antes/de `select_best`; marcar origen STRAT-A en candidatos |
| `src/entry_scorer.py` | Extender `select_best` con umbral por estrategia **o** helper `effective_threshold(candidate, session_threshold)` consumido desde scanner |
| `tests/test_strat_a.py` | Tests unitarios R11, R12 (zona joven 30 min, patrón obligatorio) |
| `tests/test_scanner_strat_a.py` | Tests E2E R10, R13 (payout, select_best con umbral 75) |
| `progress/impl_strat_a_quality_filters.md` | Mapa trazabilidad R→test (implementer) |

**Sin cambios:** `executor.py` (umbral adaptativo global intacto), `connection.py`
(`get_open_assets` sigue con `MIN_PAYOUT`), HTF/zone_memory.

---

## Constantes nuevas (`config.py`)

```python
STRAT_A_MIN_PAYOUT = 87
STRAT_A_MIN_SCORE = 75
STRAT_A_ZONE_MIN_AGE_REBOUND = 30
```

- `ZONE_AGE_REBOUND_MIN = 20` se mantiene para compatibilidad y radar.
- `ZONE_AGE_BREAKOUT_MIN = 8` sin cambio.
- `ADAPTIVE_THRESHOLD_*` sin cambio (aplica a no-STRAT-A).

---

## Identificación de candidatos STRAT-A

Hoy STRAT-A no setea `_strategy_origin`; el executor asume `"STRAT-A"` por
defecto. Para el score gate se normaliza:

```python
def _is_strat_a_candidate(c: CandidateEntry) -> bool:
    origin = getattr(c, "_strategy_origin", "STRAT-A")
    return origin == "STRAT-A"
```

**Cambio en #19:** `_candidate_from_strat_a_evaluation` y candidatos de
`_process_pending_reversals` DEBEN asignar
`candidate._strategy_origin = "STRAT-A"` explícitamente.

STRAT-B y STRAT-MOMENTUM ya usan `"STRAT-B"` y `"STRAT-MOMENTUM"`.

---

## Filtro payout (R2)

**Ubicación:** `scanner._scan_phase_evaluate_assets`, al inicio del bucle por
activo STRAT-A (antes de `detect_consolidation` / `evaluate_strat_a`).

```python
if payout < STRAT_A_MIN_PAYOUT:
    log.info(
        "⛔ [STRAT-A] %s: payout=%d%% < %d%% — excluido del scan",
        sym, payout, STRAT_A_MIN_PAYOUT,
    )
    self.bot.stats["skipped"] = self.bot.stats.get("skipped", 0) + 1
    continue
```

- `get_open_assets(client, MIN_PAYOUT)` en `_scan_phase_prepare` **no cambia**
  (R9): activos 80–86% siguen disponibles para STRAT-B.
- Radar (`_radar_entry_from_evaluation`) DEBE usar `STRAT_A_MIN_PAYOUT` en lugar
  de `MIN_PAYOUT` cuando filtre por payout.

---

## Edad de zona rebote 30 min (R3)

Pasar explícitamente al evaluar:

```python
ev = evaluate_strat_a(
    ...,
    zone_age_rebound_min=STRAT_A_ZONE_MIN_AGE_REBOUND,
)
```

El log existente de `zone_too_young` en scanner se mantiene; el mensaje DEBE
mostrar el umbral efectivo (30).

---

## Patrón 1m obligatorio en rebotes (R4, R5)

### Comportamiento actual (gap)

- Rebotes sin `pattern_ok` ya devuelven `has_signal=False` en la mayoría de
  ramas.
- CALL sin patrón cae en `pattern_insufficient` sin `pending_reversal_hint`.
- PUT sin patrón encola `pending_reversals` (espera activa).
- `_compute_score_adjustments` aplica `weak_confirmation=-10` cuando
  `pattern_name=="none"` — relevante en **rupturas**, no debe permitir rebote
  con señal sin patrón.

### Endurecimiento propuesto

En `evaluate_strat_a`, bloque rebote, **antes** de evaluar `pattern_ok`:

```python
if pattern_name == "none":
    return StratAEvaluation(
        ...,
        skip_reason="pattern_missing",
        pending_reversal_hint=PendingReversalHint(...)  # solo si política PUT/CALL wait se mantiene
    )
```

**Política de pending_reversals:** se mantiene el encolado para PUT/CALL cuando
falta patrón o vela de rechazo (comportamiento #17/#18), pero:

1. `has_signal` permanece `False` en el ciclo actual (R4).
2. El scanner loguea veto explícito (R5) con prefijo `[STRAT-A]`.
3. `_process_pending_reversals` sigue exigiendo `confirms and strength >= req`
   antes de producir candidato (sin regresión R12 en #18).

### Logs de veto patrón (scanner)

Unificar en `_log_strat_a_pattern_veto(sym, ev)`:

| `skip_reason` | Mensaje mínimo |
|---------------|----------------|
| `pattern_missing` | `⛔ [STRAT-A] {sym}: rebote {side} — sin patrón 1m confirmado` |
| `pattern_insufficient` | `⛔ [STRAT-A] {sym}: rebote {side} — patrón 1m insuficiente ({name} {strength:.2f})` |
| `strict_pattern_veto` | mensaje existente + prefijo `[STRAT-A]` |

---

## Umbral fijo score 75 (R6, R7, R8)

### Problema

`select_best(candidates, threshold=session_threshold)` usa umbral adaptativo
(62–68). STRAT-A requiere **75 fijo** aunque la sesión esté en 65.

### Solución: umbral efectivo por candidato

Extender `select_best`:

```python
def select_best(
    candidates: List[CandidateEntry],
    max_entries: int = MAX_ENTRIES_CYCLE,
    threshold: int = SCORE_THRESHOLD,
    *,
    threshold_for: Callable[[CandidateEntry], int] | None = None,
) -> Tuple[List[CandidateEntry], List[CandidateEntry]]:
    def _thresh(c: CandidateEntry) -> int:
        if threshold_for is not None:
            return threshold_for(c)
        return threshold

    passed = [c for c in candidates if c.score >= _thresh(c)]
    failed = [c for c in candidates if c.score < _thresh(c)]
    ...
```

Scanner invoca:

```python
from config import STRAT_A_MIN_SCORE

def _score_threshold_for_candidate(c: CandidateEntry, session_threshold: int) -> int:
    if _is_strat_a_candidate(c):
        return STRAT_A_MIN_SCORE
    return session_threshold

selected, rejected = select_best(
    candidates,
    threshold=session_threshold,
    threshold_for=lambda c: _score_threshold_for_candidate(c, session_threshold),
)
```

Log previo al veto score (candidatos STRAT-A entre session_threshold y 75):

```python
"⛔ [STRAT-A] %s: score=%.1f < %d — veto calidad (umbral STRAT-A fijo)"
```

`FORCE_EXECUTE` en rupturas STRAT-A: si `score < STRAT_A_MIN_SCORE`, **no**
bypass del umbral 75 salvo que el humano apruebe excepción en spec futuro.
En #19: rupturas con `_force_execute` siguen sujetas a `STRAT_A_MIN_SCORE`
(reject-first consistente).

---

## Flujo post-cambio (pseudocódigo)

```python
# Por activo en evaluate STRAT-A
if payout < STRAT_A_MIN_PAYOUT:
    log + continue

ev = evaluate_strat_a(..., zone_age_rebound_min=STRAT_A_ZONE_MIN_AGE_REBOUND)

if not ev.has_signal:
    if ev.skip_reason in ("pattern_missing", "pattern_insufficient", "strict_pattern_veto"):
        _log_strat_a_pattern_veto(sym, ev)
    ...
    continue

candidate = _candidate_from_strat_a_evaluation(...)
candidate._strategy_origin = "STRAT-A"
score_candidate(candidate)
...

# Selección
selected, rejected = select_best(
    candidates,
    threshold=session_threshold,
    threshold_for=lambda c: STRAT_A_MIN_SCORE if _is_strat_a_candidate(c) else session_threshold,
)
```

---

## Alternativas descartadas

| Alternativa | Motivo de rechazo |
|-------------|-------------------|
| Subir `MIN_PAYOUT` global a 87 | Rompe STRAT-B/MOMENTUM y tests de conexión que usan payout 80+ |
| Reemplazar umbral adaptativo global por 75 | Demasiado restrictivo para STRAT-B; no está en acceptance |
| Integrar `entry_decision_engine` como único veto | HTF/zone_memory aún no cableados (#20); duplicaría lógica |
| Veto patrón solo en scanner (no en `evaluate_strat_a`) | Violaría capa Estrategias pura; tests unitarios de #18 perderían cobertura |
| Eliminar `pending_reversals` | Fuera de acceptance; rompe suite #18 y filosofía de espera activa |

---

## Trazabilidad tests previstos

| R | Test propuesto |
|---|----------------|
| R1 | `test_config_strat_a_quality_constants` |
| R2 | `test_strat_a_scan_excludes_low_payout_asset` |
| R3 | `test_evaluate_strat_a_rejects_rebound_zone_under_30min` |
| R4, R5 | `test_evaluate_strat_a_rebound_rejects_missing_pattern` |
| R6, R7 | `test_strat_a_select_best_uses_fixed_threshold_75` |
| R8 | `test_select_best_non_strat_a_keeps_session_threshold` |
| R9 | `test_get_open_assets_still_uses_min_payout_80` (o assert en test payout) |
| R14 | suite completa pytest |
| R16 | `init.ps1` |

---

## Verificación reviewer

1. Constantes presentes en `config.py` con valores exactos 87/75/30.
2. Activo payout 86%: sin candidato STRAT-A, con log de exclusión.
3. Rebote zona 25 min: `zone_too_young`, sin candidato.
4. Rebote sin patrón: `has_signal=False`, log con `patrón 1m`.
5. Candidato STRAT-A score 72: no en `selected` aunque `session_threshold=65`.
6. Candidato STRAT-B score 72 con `session_threshold=65`: puede estar en `selected`.
7. `init.ps1` verde; mapa en `progress/impl_strat_a_quality_filters.md`.