# Auditoría — La secuencia del Edificio en tres documentos

> **Objetivo**: comparar cómo `docs/EDIFICIO_CONTRATACION.md`, `docs/agente-trader_humano.md` y
> `docs/EDIFICIO_AUDIT_FLOW_2026-08-01.md` definen la secuencia de pisos del Edificio de
> Contratación, listar las contradicciones y decidir la versión canónica a implementar.
>
> **Regla**: no se modifica código aquí; este documento es el entregable del punto 1 de la
> tarea "una sola máquina de estados".
>
> **Fecha**: 2026-08-04

---

## 1. Hallazgo principal

Ninguno de los tres documentos está impuesto por el código: `src/edificio_contratacion.py`
puede resolver P1 → P2 → P3 en el mismo scan de 60 segundos sin dejar marca de que cada paso
ocurrió en su momento. Además, `src/strategy_lab/brake_eval.py` mide "freno" con una ventana
hacia adelante que el motor en vivo (`src/scanner.py`) no tiene ni puede tener, así que
Laboratorio y Edificio ni siquiera miden lo mismo cuando dicen "secuencia".

La secuencia existe como prosa repetida en N documentos, no como máquina de estados en código.

---

## 2. Tabla de contradicciones

Leyenda:
- **A** = `docs/EDIFICIO_CONTRATACION.md`
- **B** = `docs/agente-trader_humano.md`
- **C** = `docs/EDIFICIO_AUDIT_FLOW_2026-08-01.md`

| # | Tema | A (EDIFICIO_CONTRATACION) | B (agente-trader_humano) | C (AUDIT_FLOW) | Tipo de conflicto |
|---|---|---|---|---|---|
| 1 | **Nº de pisos** | 3 (P1-P3) + CONTRATADO | 8 (P0-P7) | 3 | Arquitecturas distintas |
| 2 | **Qué se mueve** | El activo (carnet por par) | La hipótesis (un par puede tener varias hipótesis) | El activo | Incompatible (B multiplica objetos) |
| 3 | **Piso de entrada** | P1 Recepción = paga bien | P0 OBSERVANDO = impulso/swing | P1 = paga bien | A vs B |
| 4 | **Rol del freno** | ALERTA de preparación; tarjeta de acceso a P2; NUNCA disparador | Evidencia dentro de P2 EN_POI (`body_n`, `brake_ratio`) — no es "tarjeta" | Prueba A del P2 | A vs B (rol distinto) |
| 5 | **Rol del extremo stoch** | Prueba B en P2: contexto de la estadía | El cruce debe darse EN extremo (P4 EN_CRUCE) | Prueba B del P2 | B lo mueve de fase |
| 6 | **Cruce K/D** | P3: condición de preparación + separación anti-sticky | P4 → P5 CONFIRMANDO_CRUCE (separación creciente) | P3: sticky PROHIBIDO (49% WR) | A vs B (fase y umbral) |
| 7 | **Martillo** | Gate alternativo **5m** en P3 (body o martillo M5) + martillo M15 mencionado en "estrategia completa" | P6 CONFIRMANDO_VELA: **martillo M15 obligatorio** para subir | No central | **A vs B: distinto timeframe y obligatoriedad** |
| 8 | **Entrada final** | CONTRATADO tras estrategia COMPLETA: cruce + separación (+ vela 5m en código) | CONTRATADA en P7: evidencia suficiente + orquestador decide | CONTRATADO tras cruce + body_5m>0.03 | Coherentes en esencia; difieren en el martillo |
| 9 | **Bajada de piso** | P2→P1 (sin tarjeta/extremo); P3→P2 (sin freno/extremo) | RETROCEDE un piso; nunca expulsa por retroceder | Deuda #3: **no implementado** | B vs C: cuántos pisos se baja |
| 10 | **Expulsión** | Solo Regla 1: dejó de pagar | Cualquier vigilante con `NO` → expulsión | Solo por payout | **A vs B: B expulsa por más causas** |
| 11 | **POI** | 3 POIs obligatorios para CONTRATADO | Historial de evidencia, sin POIs formales | Deuda #8: no hay tracker | A lo exige, B no lo tiene |
| 12 | **Quién decide** | Reglas automáticas por piso | Orquestador = única autoridad (SUBIR/BAJAR/CONTRATAR) | Scanner alimenta reglas automáticas | B introduce un actor que A/C no tienen |
| 13 | **Timeframes** | M15 juez, M5 respaldo, **M1 prohibido como puerta** | Sin mención de timeframes | M15 | Menor |

### Contradicciones internas de B

1. El flujo de ejemplo (línea ~594) dice "Piso 8 — ARCHIVADA", pero B declara 8 pisos P0-P7
   donde `ARCHIVADA` no es un piso sino un estado terminal.
2. Mezcla `CONTRATADA` (estado terminal) dentro del recorrido de pisos.
3. Se autodeclara "Documento arquitectónico fundacional aprobado. Listo para implementación"
   (línea ~634) — lo que lo hace leerse como vigente, aunque no tiene ni una línea de código.

---

## 3. Contraste documento vs código (evidencia)

### 3.1 Código que sí implementa la secuencia (parcialmente)

`src/edificio_contratacion.py` ya tiene los 5 estados y los POIs:

```
PISO_FUERA = 0
PISO_1     = 1  # Recepción: paga bien
PISO_2     = 2  # Cerebro: freno OK + extremo OK
PISO_3     = 3  # Sala de espera: listo para cruce K/D
CONTRATADO = 4  # Entrada al trade
```

`BuildingCard` guarda `p1_at`, `p2_at`, `p3_at`, `contratado_at` — los POIs existen como
timestamps, pero la promoción P1→P2→P3 puede darse en el mismo scan si las condiciones
coinciden, sin verificar que cada POI ocurrió en su momento (dwell time).

### 3.2 Código que NO existe

- No hay vigilantes por piso (B, sección 7).
- No hay orquestador con `SUBIR_PISO/BAJAR_PISO/CONTRATAR` (B, sección 11).
- No hay expediente de hipótesis (B, sección 10).
- No hay POI tracker impuesto por código (A, Regla de POI; C deuda #8).

### 3.3 Laboratorio vs Edificio miden distinto

- `src/strategy_lab/brake_eval.py` calcula `brake_mask` con ventana **hacia adelante**
  (`fwd` velas: `adv <= max_advance_frac * |net|`), es decir, un freno se "confirma" con
  datos que aún no ocurrieron en vivo.
- `src/scanner.py:1516` calcula `_brake_ok` con la última vela cerrada vs la anterior:
  `_last_range < _prev_range * EDIFICIO_BRAKE_CONFIRM_RATIO` — sin ventana hacia adelante.
- Resultado: "freno" en Laboratorio ≠ "freno" en Edificio.

---

## 4. Decisión de versión canónica

**Implementar AHORA: el modelo de 3 pisos de `docs/EDIFICIO_CONTRATACION.md` (A).**

- `docs/agente-trader_humano.md` → marcar como **v2 — no implementado todavía** en su encabezado.
- `docs/EDIFICIO_AUDIT_FLOW_2026-08-01.md` → se mantiene como lista de deuda técnica; sus
  deudas #1-#8 se convierten en requisitos de diseño de la máquina de estados.

### Justificación

1. **Es lo que el código real ya implementa.** `src/edificio_contratacion.py` tiene los 5
   estados, los POIs y las bajadas P3→P2→P1. B no tiene ninguna línea detrás.
2. **Es lo que el Laboratorio ya adoptó.** `src/strategy_lab/experiments/EXP-030/P1_EXCLUIDO.md`
   declara explícitamente "Documento base: `docs/EDIFICIO_CONTRATACION.md`" y experimenta sobre
   P2, P3 y pipeline P2→P3.
3. **B es un cambio de paradigma** (hipótesis paralelas por par, confianza dinámica, orquestador,
   expediente) que exige rediseñar el carnet y el scanner. Migrarlo ahora convertiría la tarea
   en una reescritura total. Como v2 tiene valor: su "expediente" es el futuro del `BuildingCard`.
4. **C ya mide contra A.** Mantener A como ideal mantiene la coherencia de la auditoría.

---

## 5. La secuencia canónica que la máquina de estados debe codificar

Derivada de A + código actual:

```
FUERA → P1          (paga bien ≥ mínimo)
P1   → P2          (freno CONFIRMED con vela M15 CERRADA — dwell: cierre de vela)
P2   → P3          (cruce limpio K/D + separación mantenida EDIFICIO_SEPARATION_WAIT_SEC — dwell: 60s)
P3   → CONTRATADO  (cruce vigente + vela 5m gate + delay 300s — dwell: 5 min)
P3   → P2          (pierde freno o extremo)
P2   → P1          (pierde tarjeta o extremo)
cualquiera → FUERA (dejó de pagar — Regla 1)
```

Requisitos de diseño para la máquina (punto 2 de la tarea, pendiente):

- POIs inmutables por transición aprobada (timestamp de cada paso).
- Rechazo explícito de saltos: P1→P3, P2→CONTRATADO, etc.
- Rechazo de dos transiciones en el mismo tick cuando el diseño exige separación temporal.
- Umbrales desde `src/config.py`, no hardcodeados (`EDIFICIO_BRAKE_CONFIRM_RATIO`,
  `EDIFICIO_SEPARATION_WAIT_SEC`, `EDIFICIO_STICKY_THRESHOLD`, dwell times).
- Un solo consumidor: `src/scanner.py` + `src/edificio_contratacion.py` (vivo) y
  `src/strategy_lab/` (backtests) importan la misma máquina; `brake_eval.py` queda como
  "label generator" explícito, nunca como parte de la secuencia de entrada.

---

## 6. Pendiente (no forma parte de este entregable)

- Punto 2: diseño de `src/sequence_engine.py`.
- Punto 3: migrar scanner/edificio/laboratorio al mismo módulo.
- Punto 4: imposibilitar entrada fuera de secuencia (`is_contratado_valido` en
  `execute_contratados` y todos los paths de `place_order` encontrados en
  `executor.py`, `filter_and_sell_otc.py`, `smc_auto_trader.py`).
- Punto 5: tests de coherencia (saltos, contratación sin 3 POIs, transiciones en el mismo
  timestamp, laboratorio ≡ edificio sobre el mismo dataset).
- Punto 6: consolidar documentación al final (A describe el código real; B marcado v2).
