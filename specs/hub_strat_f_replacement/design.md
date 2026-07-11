# Design — Reemplazo del HUB por panel STRAT-F

## Principio de reemplazo seguro

El skill `quotex-bot-strategy` documenta las lecciones mortales de este repo:
1. **Nunca borrar a lo loco** — el commit 340597f rompió 21/40 tests por grep defectuoso.
2. **Placeholders de log_stats** — al borrar Strategy B, `log_stats()` seguía con
   `[B]:%dW/%dL` esperando args que ya no existían → TypeError al cerrar.
3. **Método sin `self`** — `_serialize_candles` sin self explotó en vivo.

Por eso el reemplazo se hace en **3 fases**: (A) crear lo nuevo en paralelo,
(B) cablear y verificar con tests verdes, (C) borrar lo viejo SOLO tras pytest verde.

## Archivos

### Nuevos (paralelo, sin tocar lo viejo al inicio)
- `hub/strat_f_state.py` — `StratFRow`, `StratFReject`, `StratFHubState`.
  Una sola fuente de verdad del panel.
- `hub/hub_scanner.py` — SE REESCRIBE `HubScanner` para usar
  `StratFHubState` y exponer `record_strat_f(snapshot)` + `get_state()`.
  Se conserva el nombre de clase para no romper `server.py` (que llama
  `HubScanner()` e `init(scanner)`).
- `hub/render.py` — usa **Rich** (estándar de dashboards de terminal en
  Python, según búsqueda web). Panel a color: barras verdes/rojas, tabla de
  aceptadas, lista de rechazos con razón.
- `hub/parser.py` — YA EXISTE; se mantiene (lee log del diag STRAT-F).
- `tests/test_hub_strat_f.py` — tests del nuevo modelo + render + parser.

### Modificados
- `hub_models.py` — se ELIMINAN `CandidateData`, `HubState`, `MasanielloState`,
  `GaleState`, `VipWindowData`, `HubScanSnapshot`, `CandleSnapshot` (eran de
  STRAT-A). Se dejan solo los imports que use el nuevo hub. **OJO**: `vip_library.py`
  importa `VipWindowData` de aquí → se ajusta o se deja la clase si la usa
  el bot en vivo (ver riesgo R1 abajo).
- `hub/__init__.py` — se actualizan los exports al nuevo modelo.
- `server.py` — `_build_snapshot()` serializa `StratFHubState` (mínimo cambio:
  lee `state.accepted`/`state.rejected`). `static/index.html` se reescribe.
- `consolidation_bot.py` — en `_scan_phase_evaluate_assets`, tras evaluar
  STRAT-F, llamar `hub.record_strat_f(snapshot)` (construye el snapshot desde
  `f_eval` + `candidates`). **Cuidado con `log_stats`**: grepear por
  `Masaniello`/`Gale`/`[A]:`/`[B]:` para no dejar placeholder colgado.
- `scanner.py` — en el bloque STRAT-F, además del log `[STRAT-F] skip:`,
  acumular fila en `self._strat_f_batch` y al final del ciclo llamar
  `self.bot._hub_scanner.record_strat_f(...)`.

### Eliminados (SOLO tras pytest verde)
- `hub/static/index.html` viejo (reemplazado).
- Los modelos STRAT-A de `hub_models.py` (si no los usa el bot en vivo).
- Las llamadas `record_scan_cycle`/`record_entry`/`update_masaniello_state` de
  `consolidation_bot.py` (si STRAT-A/Masaniello siguen vivos en el bot,
  SE CONSERVAN y el hub solo ignora esos campos).

## Formato de datos (StratFHubState)

```python
@dataclass
class StratFRow:
    asset: str
    direction: str        # call | put
    strength: int          # 0-100
    payout: int           # %
    ctx: str              # range | uptrend | downtrend | broken
    event: str            # fractal_up | fractal_down | none

@dataclass
class StratFReject:
    asset: str
    payout: int
    skip_reason: str      # legible, p.ej. "M1 no rebota (cierra fuera)"

@dataclass
class StratFHubState:
    accepted: list[StratFRow] = []
    rejected: list[StratFReject] = []
    total_assets: int = 0
    filtered_count: int = 0
    cycle: int = 0
    timestamp: float = 0.0
```

## Por qué Rich (decisión de diseño)

Búsqueda web: Rich/Textual es el stack estándar para dashboards de terminal en
Python (Live display, color, tablas, sin dependencias raras). El ASCII plano que
hice ayer funciona pero es frágil y poco "competente". Rich da:
- Color semántico (verde=aceptada, rojo=rechazada) — refuerza tu principio.
- Barras de progreso para el % de aceptación.
- Tabla alineada para las aceptadas.
- `rich.Live` para refresco en tiempo real si se corre el bot en vivo.

Si Rich no está instalado en el venv, `render.py` tiene fallback a texto plano
(import opcional: `try: import rich ... except: _plain_render`).

## Panel web (server.py + index.html)

`server.py` ya tiene FastAPI+WS sirviendo `static/index.html`. Solo cambiamos:
- `_build_snapshot()` → serializa `StratFHubState` (ya tiene `_serialize`).
- `index.html` → JS que pinta dos listas (aceptadas verdes / rechazadas rojas)
  y un contador con barras, consumiendo el WS `state_update`.

Esto reutiliza toda la infra de `server.py` (polling, broadcast, puerto) sin
rewrite. Si FastAPI no está, `main.py` ya cae al panel de terminal (graceful).

## Riesgos y mitigaciones

- **R1 — `vip_library.py` importa `VipWindowData` de `hub_models`.**
  Mitigación: grep previo; si lo usa, dejar esa clase o moverla a su propio
  módulo. No borrar a ciegas (lección 340597f).
- **R2 — `consolidation_bot.py` alimenta hub con STRAT-A hoy.**
  Mitigación: ADD `record_strat_f`, no borrar lo de STRAT-A a menos que el bot
  ya no los use. Verificar con grep que el bot siga llamando Masaniello.
- **R3 — `log_stats` placeholder.** Mitigación: grep `[A]:`/`[B]:`/`Masaniello`
  antes y después; correr 1 ciclo read-only para ver STATS sin crash.
- **R4 — Rich puede no estar en venv.** Mitigación: import opcional + fallback.
