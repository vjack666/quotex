# Design — Experience Engine (Market Memory)

> **Feature ID:** 27
> **Architecture layer:** Knowledge / Memory (observación + memoria única)
> **Principio:** el mercado se EXPERIMENTA, no se memoriza. Una única fuente de
> experiencias, IAs que solo leen y reaccionan. CERO reglas de detección.

---

## Posición en el flujo (del concepto)

```
Mercado
   │
   ▼
Observación  →  captura el arco de experiencia (sin juicio)
   │
   ▼
Experience Engine  →  adquiere y DISTRIBUYE
   │
   ├── IA Entradas (F18, ya existe)
   ├── IA Zonas (futuro)
   ├── IA Patrones (futuro)
   ├── IA Tendencias (futuro)
   ├── IA Riesgo (futuro)
   ├── IA Volatilidad (futuro)
   └── IA futura
```

---

## Unidad de información: arco de experiencia

El capturador NO guarda "un soporte". Guarda un arco:

```
contexto_previo  →  evento  →  evolución  →  resultado  →  consecuencias
```

- **contexto_previo**: estado del mercado ANTES (estructura, zonas vivas sin
  etiquetar, estocástico, horario, correlación con otros activos, volatilidad).
- **evento**: lo que ocurrió (reacción en un nivel, ruptura, entrada del scanner).
- **evolución**: cómo se desarrolló después (pips recorridos, invalidación de
  estructura, tiempo, qué hizo un activo correlacionado).
- **resultado**: desenlace medible (WIN/LOSS, pips netos, estructura rota o no).
- **consecuencias**: efectos de segundo orden (patrón emergente, sesgo de sesión,
  reacción de activo correlacionado).

El arco se reconstruye íntegro desde la memoria (R2). No es una foto.

---

## Módulos (a crear / extender)

| Módulo | Rol |
|--------|-----|
| `src/experience_engine.py` | Observación + adquisición del arco + memoria única + distribución a IAs. NUEVO. |
| `src/experience_schema.py` | Definición del arco (dataclass `MarketExperience`) sin I/O. NUEVO. |
| `data/market_memory/` | Almacenamiento de la memoria única (append-only, particionado por mes). NUEVO. |
| `src/entry_scorer.py` / `src/ml_scorer.py` (F18) | Se vuelven lectores del engine (R6). EXTENDIDO. |
| `src/zone_memory.py` | SE MARCA OBSOLETO (anti-patrón R9: rol hardcoded + decaimiento). No se borra hasta migrar F18. |

---

## Captura sin juicio (R7, R9)

La Observación registra contexto + evolución TAL CUAL. NO etiqueta "soporte" /
"resistencia" / "FVG válido" en captura. La etiqueta la produce el modelo (IA de
Zonas futura), no el capturador. Esto es lo que mata `zone_memory._classify_role`
y `_DECAY_TABLE`: eran juicio en la captura.

---

## Memoria única, sin silos (R3)

TODAS las experiencias en UNA fuente. No `reaction_zones`, no `expired_zones` con
reglas de rol. Una IA de Zonas futura aprende "qué perfiles de arco terminan en
rebote" leyendo la MISMA memoria que la IA de Entradas. El schema de captura no
cambia para acomodar IAs nuevas (R8).

---

## Modo activo (R5)

El engine, al adquirir una experiencia, busca en la memoria arcos similares (por
perfil de contexto/evento, no por regla) y los distribuye a las IAs conectadas.
Cada IA responde con Confidence Score / distribución. El engine empuja; las IAs no
van a buscar (diferencia con el modo pasivo actual de F18).

---

## Contrato de las IAs (R4)

1. Solo leen la memoria.
2. No escriben en ella ni la modifican.
3. Publican salida (Confidence Score) hacia afuera.
F18 migra de "infiere al scorear" a "recibe experiencia del engine y emite score".

---

## Reutilización de datos ya existentes

No hay que recolectar desde cero para el MVP:
- `scan_candidates` ya guarda `candles_1m/5m/15m` + `stoch_m15/m5/m1` + `direction`
  + `payout` + `duration_sec` + `asset`.
- `black_box` / `trade_journal` ya guardan `WIN`/`LOSS` + pips.
El MVP del engine puede sembrar la memoria RE-leyendo esos datos ya persistidos
(OFFLINE, sin tocar el bot), construyendo arcos de experiencia desde trades
resueltos. Es la validación temprana de que los datos alcanzan.

---

## Alternativas descartadas

1. **Tablas por detector (`reaction_zones`, `expired_zones`):** descartadas — son
   silos con reglas hardcoded (R3, R9).
2. **Decaimiento por heurística (`_DECAY_TABLE`):** descartado — el modelo debe
   descubrir la relevancia temporal, no el capturador (R7).
3. **Snapshots fotográficos:** descartados — la unidad es el arco, no la foto (R2).
4. **Un Zone Model separado:** descartado — rompe la memoria única; las IAs leen
   la misma fuente (concepto §5).
5. **Reglas de detección (3 toques, FVG, OB):** descartadas explícitamente (R9).
