# Design — strat_a_evaluate

> Feature id=17. Fase SA-1 — arquitectura STRAT-A.
> Referencias: `docs/architecture.md` (capa Estrategias sin I/O),
> `src/strat_b.py` (`evaluate_strat_b`), `src/scanner.py` líneas 746–1217.

---

## Objetivo

Concentrar la **lógica de señal STRAT-A** en `evaluate_strat_a()` y dejar en
`scanner.py` solo orquestación: fetch de velas, estado del bot, side-effects de
ruptura (journal/snapshot), mutación de `pending_reversals` y construcción de
`CandidateEntry`.

---

## Archivos a modificar

| Archivo | Cambio |
|---------|--------|
| `src/strat_a.py` | Añadir dataclasses `StratAEvaluation`, `PendingReversalHint`, `ScoreAdjustments`; función `evaluate_strat_a()`; helper interno `_resolve_entry_direction()` si hace falta |
| `src/scanner.py` | Reemplazar bloque inline STRAT-A (~470 líneas) por delegación ≤150 líneas; posible helper privado `_build_strat_a_candidate()` |
| `tests/test_strat_a.py` | ≥8 tests nuevos para `evaluate_strat_a` |
| `progress/impl_strat_a_evaluate.md` | Mapa trazabilidad R→test (lo crea el implementer) |

**Sin cambios en esta feature:** `config.py` (umbrales actuales), `executor.py`,
`_process_pending_reversals` (permanece en scanner; #18 ampliará tests E2E).

---

## Tipos nuevos (strat_a.py)

```python
@dataclass
class PendingReversalHint:
    """Pista para que scanner encole espera activa; sin mutación en strat_a."""
    proposed_direction: str
    entry_mode: str
    conflicting_pattern: str
    update_existing: bool = True


@dataclass
class ScoreAdjustments:
    reversal_bonus: float = 0.0
    reversal_penalty: float = 0.0
    weak_confirmation: float = 0.0
    breakout_bonus: float = 0.0
    order_block: float = 0.0
    ma_filter: float = 0.0


@dataclass
class StratAEvaluation:
    has_signal: bool
    direction: str | None = None
    entry_mode: str = "none"       # rebound_ceiling | rebound_floor | breakout_above | breakout_below | none
    stage: str = "initial"         # initial | breakout
    zone: ConsolidationZone | None = None
    pattern_name: str = "none"
    strength: float = 0.0
    confirms: bool = False
    rejection_ok: bool = False
    skip_reason: str | None = None
    breakout_strength_ok: bool = False
    skip_zone_age_check: bool = False
    pending_reversal_hint: PendingReversalHint | None = None
    score_adjustments: ScoreAdjustments = field(default_factory=ScoreAdjustments)
    ob_info: str = ""
    ma_info: str = ""
    force_execute: bool = False
```

`skip_reason` usa strings estables para logs/tests:

| Valor | Significado |
|-------|-------------|
| `no_direction` | Precio en mitad de rango |
| `zone_too_young` | Edad < `ZONE_AGE_*_MIN` |
| `rejection_candle_fail` | Vela 1m no confirma rebote |
| `pattern_insufficient` | Patrón débil o contradictorio |
| `put_pattern_blacklisted` | Patrón en `PATTERN_PUT_BLACKLIST` |
| `strict_pattern_veto` | `STRICT_PATTERN_CHECK` descartó antes de score |
| `h1_conflict` | Tendencia H1 contradice dirección |

---

## Firma propuesta

```python
def evaluate_strat_a(
    *,
    candles_5m: list[Candle],
    candles_1m: list[Candle],
    zone: ConsolidationZone,
    blocks: dict[str, list[OrderBlock]],
    ma_state: MAState | None,
    price: float | None = None,
    dynamic_touch_tolerance: float | None = None,
    h1_trend: str = "neutral",
    h1_confirm_enabled: bool = H1_CONFIRM_ENABLED,
    strict_pattern_check: bool = STRICT_PATTERN_CHECK,
    force_execute_strong_breakout: bool = FORCE_EXECUTE_STRONG_BREAKOUT,
    zone_age_rebound_min: int = ZONE_AGE_REBOUND_MIN,
    zone_age_breakout_min: int = ZONE_AGE_BREAKOUT_MIN,
    pattern_signal: CandleSignal | None = None,
) -> StratAEvaluation:
```

**Notas de diseño:**

- `price` por defecto = `candles_5m[-1].close`.
- `dynamic_touch_tolerance` por defecto = tercer valor de `compute_dynamic_range(candles_5m)`.
- `pattern_signal` opcional: si el scanner ya llamó `detect_reversal_pattern`, lo
  pasa para evitar acoplar `candle_patterns` dentro de `strat_a`; si es `None`,
  `evaluate_strat_a` importa `detect_reversal_pattern` (módulo puro, sin I/O).
- `h1_trend` lo calcula el scanner con `infer_h1_trend(h1_candles)` **después** de
  fetch H1; `evaluate_strat_a` solo aplica el veto (R11).

---

## División de responsabilidades

### Permanece en `scanner.py` (orquestación + I/O)

| Responsabilidad | Motivo |
|-----------------|--------|
| `len(candles) < MIN_CONSOLIDATION_BARS + 2` guard | Pre-filtro antes de evaluate |
| `detect_consolidation` + merge `bot.zones[sym].detected_at` | Estado transversal del bot |
| Expiración `MAX_CONSOLIDATION_MIN` + journal `TIME_LIMIT` | Side-effect BD |
| Guardias de precio contaminado (`last_known_price`) | Estado del bot |
| `await fetch_candles_with_retry` velas OB 3m | I/O red |
| `detect_order_blocks`, `compute_ma_state` | Puede invocarse en scanner; resultados pasados a evaluate |
| Fetch velas H1 + `infer_h1_trend` | I/O red (R12) |
| Mutar `pending_reversals` según `pending_reversal_hint` | Estado mutable del bot (R13) |
| Journal `log_expired_zone` + snapshot en `BROKEN_ABOVE/BELOW` | Side-effects de ruptura |
| `CandidateEntry` + `score_candidate` + aplicar `score_adjustments` | Capa análisis/ejecución |
| Stats (`skipped`, `rejected_young_zone`, `filtered_sensor`) | Telemetría del ciclo |
| `_process_pending_reversals` | Flujo async separado; fuera de #17 |

### Se mueve a `evaluate_strat_a()` (lógica pura)

| Lógica actual (scanner ~852–1198) | Destino |
|-----------------------------------|---------|
| `price_at_ceiling/floor`, `broke_above/below`, `is_high_volume_break` | `_resolve_entry_direction` |
| Chequeo edad zona + `skip_zone_age_check` | evaluate |
| Validación rebote: `validate_rejection_candle`, fuerza, blacklist, STRICT | evaluate |
| Decisión `pending_reversal_hint` (sin crear `PendingReversal`) | evaluate |
| Veto H1 cuando `h1_confirm_enabled` | evaluate |
| Bonus/penalty patrón 1m, breakout, `score_order_blocks`, `score_ma` | evaluate → `ScoreAdjustments` |
| `force_execute` flag | evaluate |

---

## Flujo scanner post-refactor (pseudocódigo)

```python
# --- STRAT-A orquestación (objetivo ≤150 líneas) ---
if len(candles) < MIN_CONSOLIDATION_BARS + 2:
    continue

dynamic_max_range, _, dynamic_touch_tolerance = compute_dynamic_range(candles)
zone = detect_consolidation(candles, max_range_pct=dynamic_max_range)
if zone is None:
    self.bot.zones.pop(sym, None)
    continue
zone = self._merge_zone_state(sym, zone, candles, payout)  # TIME_LIMIT, detected_at
if zone is None:
    continue
if not self._price_sanity_ok(sym, zone, candles[-1].close):
    continue

candles_ob, ob_tf_label = await self._fetch_ob_candles(sym, candles)
blocks = detect_order_blocks(candles_ob)
ma_state = self._compute_ma_state(sym, candles)

h1_candles = await fetch_candles_with_retry(...)  # siempre fetch (comportamiento actual)
h1_trend = infer_h1_trend(h1_candles)

ev = evaluate_strat_a(
    candles_5m=candles,
    candles_1m=candles_1m,
    zone=zone,
    blocks=blocks,
    ma_state=ma_state,
    dynamic_touch_tolerance=dynamic_touch_tolerance,
    h1_trend=h1_trend,
)

if ev.pending_reversal_hint:
    self._apply_pending_reversal_hint(sym, zone, payout, ev.pending_reversal_hint)
if not ev.has_signal:
    self._bump_strat_a_skip_stats(ev.skip_reason)
    continue

if ev.entry_mode.startswith("breakout"):
    await self._handle_breakout_side_effects(sym, zone, candles, candles_1m, payout, ev)

candidate = self._candidate_from_strat_a_evaluation(sym, payout, candles, h1_candles, ev, ...)
score_candidate(candidate)
self._apply_score_adjustments(candidate, ev.score_adjustments)
candidates.append(candidate)
```

El helper `_merge_zone_state` absorbe líneas 759–788 actuales para mantener el
bloque principal bajo 150 líneas.

---

## Patrón de referencia: evaluate_strat_b

`evaluate_strat_b` devuelve `dict | None` y el scanner interpreta el dict. Para
STRAT-A el resultado es más rico (rebotes con espera, rupturas, score mods), por
eso se usa dataclass tipado en lugar de dict genérico.

**Alternativa descartada:** devolver `CandidateEntry` directamente desde
`evaluate_strat_a`. Rechazada porque mezclaría capa Estrategias con modelo de
ejecución/scoring (`entry_scorer.CandidateEntry`) y obligaría a `strat_a` a
conocer atributos dinámicos `_amount`, `_stage`, etc.

---

## H1: scanner fetch, evaluate veto

| Capa | Rol |
|------|-----|
| `scanner.py` | `await fetch_candles_with_retry(H1)` — I/O |
| `strat_a.infer_h1_trend` | Cálculo puro (ya existe); invocado en scanner |
| `evaluate_strat_a` | Recibe `h1_trend: str`; si `h1_confirm_enabled` y conflicto → `skip_reason="h1_conflict"` |

Comportamiento idéntico al actual: H1 se fetchea siempre (líneas 1092–1113); solo
se filtra cuando `H1_CONFIRM_ENABLED=True`.

---

## pending_reversals

`evaluate_strat_a` **nunca** escribe en `bot.pending_reversals`. Emite
`PendingReversalHint` con los mismos criterios que hoy crean `PendingReversal`:

- Vela 1m no confirma rebote
- Patrón PUT en blacklist
- Patrón insuficiente / contradictorio (salvo `STRICT_PATTERN_CHECK` hard veto)
- PUT sin patrón suficiente

El scanner traduce el hint a:

```python
PendingReversal(
    asset=sym,
    zone=zone,
    proposed_direction=hint.proposed_direction,
    conflicting_pattern=hint.conflicting_pattern,
    detected_at=datetime.now(tz=BROKER_TZ),
    entry_mode=hint.entry_mode,
    payout=payout,
)
```

`_process_pending_reversals` no se refactoriza en #17; #18 añadirá tests E2E.

---

## Regresión y verificación

1. Tests existentes en `test_strat_a.py` siguen verdes (R12 arquitectura).
2. Tests existentes `test_scanner.py` sin cambios de comportamiento.
3. Comparación manual de logs en dry-run: mismos mensajes de skip/ruptura/rebote.
4. Conteo de líneas: bloque STRAT-A en `scan_all` entre comentario
   `# STRAT-A requiere historial` y `candidates.append` ≤150 líneas
   (excluyendo helpers privados nuevos en la clase `Scanner`).

---

## Fuera de alcance (#17)

- Endurecer umbrales PLAN MAESTRO (#19).
- Cablear `HTFScanner` / `zone_memory` (#20).
- Prefetch paralelo OB (#21).
- Refactor de `_process_pending_reversals` para usar `evaluate_strat_a`.
- Validación demo en vivo (#22).