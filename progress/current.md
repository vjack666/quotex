# Estado de sesión — bankroll hub + resolve broker lag

> Sesión: 2026-07-14 | Operador: Ruben | Agente: Grok

## Hecho esta sesión

### 1. Lifecycle sesión (commit previo `a654fc0`)
- Iniciar → SCANNING; resume incompleta; stop al cumplir meta.

### 2. Log compacto
- `BOT_LOG_VERBOSE=1` para detalle por activo.
- Resúmenes de ciclo en INFO.

### 3. Bankroll Massaniello en hub (Operación)
- Card **Bankroll binarias**: capital, Ops/ITM, payout mín. %, próximo stake **en vivo**.
- Guardar bankroll → aplica a `config` + log de auditoría.
- Misma fórmula que `Desktop/massaniello` / `massaniello_engine`.
- Payout mín. = piso del **escáner** + fórmula de stake.
- Consola: sin bloque Massaniello duplicado.

### 4. Resolve broker lag
- No tratar `profitAmount==0` como LOSS.
- Más grace/timeout; UNRESOLVED en vez de LOSS forzado.
- Countdown se corta si la sesión ya terminó.

## Cómo usar bankroll
1. Bot detenido → editar capital / Ops / ITM / payout (stake se actualiza al tipear).
2. **Guardar bankroll** → log: `HUB config aplicada → Massaniello …`
3. **Iniciar**.

## Verificación
- pytest: 339+ passed (última corrida completa verde).
- Grafo: `graphify . --update --code-only` + `cluster-only` → **2434 nodos, 4949 edges, 152 comunidades**.
