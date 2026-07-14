# API Spec — HUB STRAT-F (hub/server.py)

> Contrato de la API del dashboard. Servidor FastAPI + WebSocket. Arranca
> desde `consolidation_bot` / `main.py`. Si FastAPI no está en el venv, el
> panel cae al modo terminal (`main.py --hub-readonly`).

- **Host:** `127.0.0.1` (o el configurado)
- **Puerto:** resuelto automáticamente (ver `_resolve_port`)
- **Formato:** JSON

## Endpoints

### GET `/health`
Heartbeat del servidor.

**Response 200**
```json
{ "status": "ok", "clients": 0, "scanner": true, "timestamp": 1718000000.0 }
```

### GET `/api/state`
Snapshot completo del HUB (estado legacy de Masaniello + `strat_f`).

**Response 200**
```json
{
  "status": "ok",
  "strat_f": {
    "total_assets": 14,
    "accepted":   [ { "asset": "USDPKR_otc", "direction": "call",
                      "strength": 70, "payout": 92, "ctx": "range",
                      "event": "fractal_down" } ],
    "rejected":   [ { "asset": "BNBUSD_otc", "payout": 92,
                      "skip_reason": "M1 no rechaza la banda (cierra fuera)" } ],
    "metrics":    { "accepted": 1, "rejected": 13, "accept_rate_pct": 7.1 }
  }
  /* + campos legacy de Masaniello si el bot corre */
}
```

### GET `/api/strat_f`
Solo el estado STRAT-F (atajo para el panel nuevo).

**Response 200** (`_panel` inicializado)
```json
{
  "total_assets": 14,
  "accepted":  [ { "asset": "USDPKR_otc", "direction": "call",
                   "strength": 70, "payout": 92, "ctx": "range",
                   "event": "fractal_down" } ],
  "rejected":  [ { "asset": "BNBUSD_otc", "payout": 92,
                   "skip_reason": "M1 no rechaza la banda (cierra fuera)" } ],
  "metrics":   { "accepted": 1, "rejected": 13, "accept_rate_pct": 7.1 }
}
```
**Response 200** (`_panel` es None)
```json
{ "status": "waiting" }
```

### GET `/`
Sirve `hub/static/index.html` (panel web STRAT-F + bankroll Massaniello).

### GET `/api/config` · POST `/api/config` (app.py)
Config del `BotRunner`. **POST solo con bot detenido.**

Campos Massaniello / riesgo (también desde card **Bankroll binarias** en Operación):

| Campo | Tipo | Efecto |
|-------|------|--------|
| `massaniello_virtual_capital` | float | Capital de riesgo (no el balance completo de cuenta) |
| `massaniello_ops` | int | Operaciones de la secuencia Massaniello |
| `massaniello_wins` | int | ITM objetivo |
| `min_payout` | int | Piso de payout del **escáner** y de la fórmula de stake (alinea `MIN_PAYOUT`, `STRAT_A_MIN_PAYOUT`, `STRAT_F_MIN_PAYOUT`) |

Al guardar, `app.py` deja traza en log:
`HUB config aplicada → Massaniello N ops / M ITM | capital=$… | min_payout=…%`.

### GET `/api/massaniello/preview` (app.py)
Preview de próximo stake con la misma fórmula que `massaniello_engine.calculate_stake`.

**Query (opcionales, para tipado en vivo sin Guardar):**
`capital`, `ops`, `itm`, `payout`, `form=1`

**Response 200 (ejemplo)**
```json
{
  "assigned_capital": 30.0,
  "account_balance": 144.54,
  "operations": 5,
  "expected_wins": 3,
  "payout_pct": 92,
  "next_stake": 10.83,
  "status": "Te quedan 2 OTM",
  "can_enter": true,
  "source": "form"
}
```

El panel Operación también calcula el stake **en el navegador** (misma fórmula) para feedback instantáneo al cambiar Ops/ITM/capital/payout.

### GET `/`
Sirve `hub/static/index.html` (panel web STRAT-F).

### WS `/ws`
Canal de actualización en vivo. El servidor empuja:

- `{"type": "init", "data": <snapshot>, "timestamp": ...}` al conectar.
- `{"type": "pong", "timestamp": ...}` respuesta a `ping` del cliente.
- `{"type": "ping", "timestamp": ...}` heart-beat cada 45s si el cliente calla.

El cliente puede enviar `"ping"` para mantener viva la conexión.

## Modelo de datos (StratFHubState)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `total_assets` | int | pares evaluados en el ciclo |
| `accepted[]` | StratFRow | señales que pasaron todos los filtros |
| `rejected[]` | StratFReject | señales descartadas con su razón |
| `metrics` | dict | accepted / rejected / accept_rate_pct |

**StratFRow:** `asset, direction (call|put), strength (0-100), payout (%), ctx, event`
**StratFReject:** `asset, payout (%), skip_reason`

## Notas

- `strat_f` se alimenta vía `hub.strat_f_panel.StratFPanel.record_strat_f`,
  llamado por `scanner._scan_phase_evaluate_assets` al final de cada ciclo.
- El WebSocket empuja el snapshot legacy + `strat_f`; el `index.html` nuevo
  solo pinta la sección `strat_f`.
