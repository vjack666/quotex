# 🏢 El edificio de contratación

## La idea (en dumi)

El scanner deja de revisar todo de golpe cada 60 segundos. Cada activo entra en un edificio de 3 pisos y va subiendo cuando cumple condiciones. El scanner solo vigila que las tarjetas sigan vigentes y sube de piso cuando corresponde.

---

## Regla N°1 — La única puerta de salida

**Si el activo deja de pagar lo que el usuario pide → se va del edificio. Pierde todo.**
No importa en qué piso esté. La tarjeta de entrada se la quitaron y afuera.

## Regla N°2 — Nadie arranca de cero

Si un activo ya está en el piso 2 o 3, el scanner solo revisa el piso donde está. Las preguntas de los pisos anteriores ya fueron respondidas. Si el piso 1 caducó (bajó el pago) → se va (Regla 1). Pero no reevalúa todo.

## Regla N°3 — Se puede bajar de piso, pero no salir (salvo Regla 1)

Si estando en un piso más alto el activo deja de cumplir la condición del piso actual → vuelve al piso anterior. Sigue en el edificio, esperando recuperar la condición para subir de nuevo.

---

## Temporalidades

- **M15 es el juez principal** — todo se mide en M15. Las extensiones, el freno, el cruce K/D.
- **M5 es el respaldo** — se usa como filtro secundario donde tiene sentido.
- **M1 es contexto visual** — NO se usa como puerta de entrada. Quedó demostrado en simulación con datos reales que M1 nunca está en sobreventa cuando M15 cruza alcista en sobreventa. Intentar filtrar por M1 elimina todas las entradas.

---

## Simulación con datos reales — Resultados

El 30/07/2026 se ejecutó una simulación paso a paso con datos reales de **GBPNZD_otc** (24h de velas M1 reconstruidas a M15). Se evaluaron dos tracks de entrada:

### Track A — Entrada automática en P3 CONTRATADO ✅ (APROBADO)

| Cruce M15 en OS | M15 K | M1 K | Entrada | +15min | Resultado |
|---|---|---|---|---|---|
| 07:45 | 20.9 | 93.5 | 1.91625 | 1.92190 | ✅ +0.29% |
| 08:15 | 11.4 | 86.1 | 1.91501 | 1.91727 | ✅ +0.12% |
| 15:15 | 8.2 | 53.4 | 1.93560 | 1.93439 | ❌ -0.06% |
| 16:15 | 15.6 | 92.3 | 1.93640 | 1.94443 | ✅ +0.41% |

**Win rate: 3/4 = 75%** — La única pérdida fue marginal (-0.06%).

### Track B — Esperar M1 en sobreventa ❌ (DESCARTADO)

**M1 nunca estuvo en sobreventa al momento del cruce M15.** En los 4 eventos, M1 K estaba en 93.5, 86.1, 53.4 y 92.3. Si el sistema esperara M1<20 para entrar, **no habría entrado ninguna vez** — ni siquiera en las 3 ganadoras.

**Conclusión:** El Piso 3 opera con Track A. M1 es solo contexto visual. No se agregan filtros M1.

## Regla de POI — No se salta pisos

El activo **sube piso por piso obligatoriamente**. No puede pasar de P1 a P3 directamente. Cada piso deja una marca (POI) que certifica que la condición fue verificada. Sin los 3 POIs → no hay CONTRATADO.

```
P1 (paga bien) → POI ✅ → sube a P2
P2 (freno OK + extremo OK) → POI ✅ → sube a P3
P3 (cruce K/D en extremo) → POI ✅ → CONTRATADO 🎯
```

---

## Los 3 pisos

### PISO 1 — Recepción (filtro de pago)
- Solo entran OTC que pagan >= lo que el usuario pide
- Si mientras espera en otro piso, el pago baja → se va del edificio (Regla 1)

### PISO 2 — El cerebro (pruebas)

El activo ya pasó recepción. Ahora tiene que pasar **2 pruebas**. NO se exigen las dos en el mismo segundo — el activo puede estar en este piso el tiempo que necesite hasta cumplirlas.

**Prueba A — ¿El impulso está muerto?**
Usa el brake_eval (M15). Mide si después de una extensión clara, el movimiento se está frenando. Si el impulso sigue vivo → no pasa.

**⚠ Regla práctica:** No ser quiquilloso. Si el freno está parcialmente confirmado (el movimiento se está desacelerando aunque no haya muerto del todo), considerar que pasa. El objetivo es filtrar impulsos CLARAMENTE vivos, no buscar la confirmación perfecta.

**Prueba B — ¿Está en extremo?**
El estocástico M15 tiene que estar en zona de sobrecompra (≥80 para PUT) o sobreventa (≤20 para CALL). Si está en el medio → no está listo para el cruce.

**Contexto adicional — Zona relevante (opcional, suma puntos)**
Si hay un nivel de soporte/resistencia HTF cerca del precio actual, es contexto a favor. No obliga, pero si no hay tampoco bloquea.

→ Cuando pasa Prueba A + Prueba B → sube al piso 3

### PISO 3 — Sala de espera del cruce

Ya pagó bien, ya se frenó y ya está en extremo. Ahora solo espera **el cruce limpio de líneas K/D**.

**El problema de los cruces sticky:**
Si K y D están casi pegadas, cualquier movimiento chiquito genera un cruce falso. Para filtrarlos:

- Si K y D están **separadas** (distancia grande) → el cruce es más confiable
- Si K y D están **muy pegadas** → esperar a que se separen primero o ignorar el cruce

El activo puede esperar horas aquí. En cada scan:
1. ¿Sigue pagando bien? No → Fuera (Regla 1)
2. ¿Sigue frenado? No → Vuelve al piso 2
3. ¿Sigue en extremo? No → Vuelve al piso 2
4. **¿Ya hubo cruce limpio K/D (no sticky)?** Sí → **CONTRATADO** (entra al trade)

---

## Comparativa: cerebro HOY vs cerebro REPARTIDO

| Pregunta | Hoy (todo en piso 2, mismo segundo) | Mañana (repartido en pisos) |
|---|---|---|
| Paga bien | Piso 1 | Piso 1 |
| ¿Impulso muerto? | Piso 2, Ley 1 | Piso 2, Prueba A |
| ¿Está en extremo? | Piso 2, Ley 2 | Piso 2, Prueba B (para subir) + Piso 3 (para mantener) |
| Separación K/D | Piso 2, Ley 3 | Piso 3 (para filtrar sticky) |
| Zona HTF | Piso 2, Ley 4 | Piso 2, contexto opcional |
| Rechazo M1 | Piso 2, Ley 5 | ❌ Eliminada (ruido) |
| Cruce K/D | No existe como sala | Piso 3 (evento que dispara entrada) |

---

## Cómo cambia el scanner

**Hoy:** cada 60 segundos revisa TODO otra vez desde cero.

**Mañana:** cada 60 segundos solo chequea:

1. **Piso 3** — los que esperan cruce: ¿siguen pagando? ¿siguen frenados? ¿siguen en extremo? ¿ya cruzó limpio? → si cruzó, entrada.
2. **Piso 2** — los que están en pruebas: ¿ya se frenó? ¿ya está en extremo? → si ambas OK, suben al piso 3.
3. **Piso 1** — los de afuera: ¿algún OTC nuevo ahora paga bien? → entra al piso 2 directo (después pasa al 2).

---

## Fases del plan

### ✅ Fase 0 — Simulación (COMPLETADA)
Simulación paso a paso con 24h de datos reales GBPNZD_otc. Resultados:
- Track A (automático en P3): 75% win rate ✅
- Track B (M1 OS filter): 0% entradas, descartado ❌
- Regla de POI obligatoria (no saltar pisos)
- Brake no quiquilloso

### Fase 1 — Reordenar el cerebro
NO se eliminan las leyes. Se redistribuyen:
- Piso 2 se queda con: brake_eval (impulso muerto, no quiquilloso) + stoch extremo + zona HTF opcional
- Piso 3 se queda con: separación K/D (filtro sticky) + espera del cruce + POI tracker

### Fase 2 — Construir el edificio
Implementar el sistema de 3 pisos. Cada activo tiene un carnet: piso actual, desde cuándo, POIs obtenidos y qué tarjetas tiene. El ingreso solo se produce cuando los 3 POIs están presentes.

### Fase 3 — El vigilante
Modificar el scanner para que en cada ronda solo revise el piso actual de cada activo, no todo desde cero. Flujo: Piso 3 → Piso 2 → Piso 1 (orden inverso, para no demorar a los que están por entrar).

### Fase 4 — Probar
Dejarlo correr en demo con `STRAT_F_FRENO_BRAIN = False` para que la ruta clásica con stoch cross gate funcione mientras se construye el edificio. Después migrar al sistema de pisos.
