# Agente Trader Humano — Modelo Cognitivo de Vigilancia

> **El objetivo del sistema es construir, fortalecer o invalidar hipótesis de trading hasta que exista evidencia suficiente para tomar una decisión o descartarla.**

---

## 1. Cambio de paradigma

### Antes: clasificador de señales
El sistema evaluaba eventos independientes:
- "¿Hay brake?" → BUY
- "¿Hay martillo?" → BUY
- "¿Hay cruce?" → BUY

Cada módulo decidía por sí mismo. El resultado era un conjunto de señales sueltas sin continuidad.

### Ahora: proceso humano de vigilancia
El sistema no evalúa eventos. Evalúa **estados**.
No existe un "evento de entrada". Existe una **hipótesis de trading que madura piso por piso**.

```
EURUSD

Hipótesis #381
Posible rebote CALL desde POI H1

Estado: VIVA

Piso 0 — OBSERVANDO
No hay nada interesante todavía.

↓

Piso 1 — CANDIDATO
Apareció un swing reciente.

↓

Piso 2 — EN_POI
Llegó a un área de interés.

↓

Piso 3 — RESPEANDO_POI
Sigue respetando el POI.

↓

Piso 4 — EN_CRUCE
Cruzó el estocástico en extremo.

↓

Piso 5 — CONFIRMANDO_CRUCE
El cruce sigue sano o se debilita.

↓

Piso 6 — CONFIRMANDO_VELA
Esperando martillo/invertido.

↓

Piso 7 — LISTO
El orquestador decide si opera.
```

**Regla fundamental:**
> Una hipótesis solo abandona el edificio cuando pierde la razón por la cual entró.

Ejemplo:
- Entró porque llegó a un POI.
- No sale porque el estocástico se descruzó.
- Sale cuando rompe el POI.

---

## 2. Ciclo de vida de la hipótesis

Una hipótesis no solo cambia de piso. Tiene un ciclo de vida completo.

```
NACE
 ↓
MADURANDO
 ↓
SE FORTALECE
 ↓
INVALIDADA / CONTRATADA / ARCHIVADA
```

| Estado | Significado |
|--------|-------------|
| `VIVA` | La hipótesis está activa y recorriendo pisos |
| `MADURANDO` | Está en proceso de acumular evidencia |
| `INVALIDADA` | Perdió la razón por la cual entró. Se expulsa del edificio. |
| `CONTRATADA` | El orquestador decidió operar. |
| `ARCHIVADA` | Fue operada y cerrada. O fue descartada por el Administrador. |

**Un trader profesional invalida muchas más hipótesis de las que opera.**
Ese balance es saludable. El sistema debe reflejarlo.

---

## 3. El edificio no vigila activos. Vigila hipótesis.

El edificio no mueve pares. Mueve **expedientes de hipótesis**.

Un mismo activo puede generar múltiples hipótesis a lo largo del día.
Cada hipótesis es independiente.
Cada hipótesis tiene su propio expediente, su propio piso y su propio historial.

```
Expediente EURUSD

Hipótesis #381
Posible rebote CALL desde POI H1

Estado: VIVA
Piso actual: 5
Fecha ingreso: 08:00
Motivo ingreso: Swing H1 + llegada a POI

HISTORIAL DE EVIDENCIA
✓ 08:00 — Llegó al POI (body_n=0.18, brake_ratio=0.53)
✓ 08:15 — Respetó POI
✓ 08:30 — Apareció martillo
✓ 09:00 — Cruzó estocástico en zona extrema (K=18)
✓ 09:15 — Separación aumentando (2.1 → 3.8)
✓ 09:30 — Separación alcanzó 5.2

OBSERVACIONES
- Lleva 4 velas esperando
- Separación aumentando
- Sin ruptura del POI

ESTADO ACTUAL: CONFIRMANDO_VELA
PRÓXIMO PISO: LISTO
```

**En el HUB verás 20 hipótesis, no como 20 señales, sino como 20 candidatos, cada uno con su expediente, su piso actual y su historial.**

---

## 4. Cada piso agrega evidencia, no condiciones

El edificio no procesa indicadores. Procesa **conocimiento**.

Cada piso responde una pregunta:

| Piso | Pregunta | Tipo de evidencia |
|------|----------|-------------------|
| Piso 0 | ¿Hay algo que mirar? | Impulso, swings, eventos estructurales |
| Piso 1 | ¿Hay un swing válido? | Estructura, cuerpo, rango |
| Piso 2 | ¿Llegó a un área de interés? | Proximidad a POI, body_n, brake_ratio |
| Piso 3 | ¿Lo está respetando? | Tiempo en POI, rebotes, no ruptura |
| Piso 4 | ¿Existe intención de giro? | Cruce estocástico en zona extrema |
| Piso 5 | ¿Ese giro tiene calidad? | Separación K/D, trayectoria, velocidad |
| Piso 6 | ¿El precio confirmó esa intención? | Martillo/invertido M15 |
| Piso 7 | ¿La evidencia reunida es suficiente? | Expediente completo |

**Cada piso agrega evidencia a favor o en contra de la hipótesis.**
**El expediente no almacena indicadores. Almacena evidencia acumulada.**
**El orquestador no busca una señal perfecta. Evalúa si la evidencia reunida es suficiente para actuar.**

---

## 5. Confianza dinámica

La confianza nunca es fija. Cada vigilante puede aportar evidencia positiva o negativa.
El orquestador calcula continuamente la confianza de la hipótesis.

```python
{
    "hypothesis_id": "381",
    "asset": "EURUSD",
    "direction": "CALL",
    "status": "VIVA",
    "current_floor": 5,
    "confidence": 0.65,
    "evidence": {
        "piso_0": {"score": 0.6, "evidence": "Impulso alcista moderado"},
        "piso_1": {"score": 0.7, "evidence": "Swing confirmado"},
        "piso_2": {"score": 0.8, "evidence": "Llegó al POI con body_n=0.18"},
        "piso_3": {"score": 0.75, "evidence": "Respetó POI por 3 velas"},
        "piso_4": {"score": 0.85, "evidence": "Cruce en zona extrema K=18"},
        "piso_5": {"score": 0.7, "evidence": "Separación creciente 2.1→5.2"},
        "piso_6": {"score": 0.9, "evidence": "Martillo confirmado"},
    },
}
```

**La confianza fluctúa según la evidencia nueva que aporta cada piso.**
No es un número fijo. Es el pulso vivo de la hipótesis.

---

## 6. Vigilancia continua: los pisos inferiores nunca se apagan

Aunque el activo se encuentre en un piso superior, los vigilantes de los pisos inferiores continúan monitoreando sus propias condiciones para detectar invalidaciones tempranas.

```
EURUSD — Piso 5

Piso 5 — CONFIRMANDO_CRUCE
Vigilante: SIGUE

Piso 4 — EN_CRUCE
Vigilante: SIGUE (sigue vigente)

Piso 3 — RESPEANDO_POI
Vigilante: SIGUE (sigue respetando)

Piso 2 — EN_POI
Vigilante: SIGUE (no hubo ruptura)

Piso 1 — CANDIDATO
Vigilante: SIGUE (swing sigue válido)
```

Si en algún momento un vigilante responde `RETROCEDE` o `NO`, el orquestador decide si baja de piso o invalida la hipótesis.

**Nadie se apaga. Todos vigilan. Todo el tiempo.**

---

## 7. Responsabilidades por piso

### Regla de oro
> Un piso es una ubicación, no una decisión. El piso representa el nivel de madurez de la hipótesis. No representa quién tomó la decisión.

### Piso 0 — OBSERVANDO
| Campo | Valor |
|-------|-------|
| **Misión** | Detectar activos que merecen atención |
| **Pregunta** | ¿Hay algo que mirar? |
| **Evidencia positiva** | Impulso suficiente |
| **Evidencia negativa** | No hay señal en N velas |
| **Deja pasar** | Impulso suficiente para considerar candidato |
| **Mantiene esperando** | No hay interés todavía |
| **Pierde condición** | No hay señal en N velas |

### Piso 1 — CANDIDATO
| Campo | Valor |
|-------|-------|
| **Misión** | Confirmar que hay un swing válido |
| **Pregunta** | ¿Hay un swing válido? |
| **Evidencia positiva** | Estructura de swing confirmada |
| **Evidencia negativa** | No se confirma swing en ventana |
| **Deja pasar** | Swing confirmado |
| **Mantiene esperando** | Swing en formación |
| **Pierde condición** | No se confirma swing en ventana |

### Piso 2 — EN_POI
| Campo | Valor |
|-------|-------|
| **Misión** | Verificar que el activo llegó a un área de interés |
| **Pregunta** | ¿Llegó a un área de interés? |
| **Evidencia positiva** | Proximidad a POI, body_n, brake_ratio válidos |
| **Evidencia negativa** | Se aleja del POI sin tocar |
| **Deja pasar** | Llegó al POI |
| **Mantiene esperando** | Se acerca pero no llega |
| **Pierde condición** | Se aleja del POI sin tocar |

### Piso 3 — RESPEANDO_POI
| Campo | Valor |
|-------|-------|
| **Misión** | Confirmar que el activo respeta el área |
| **Pregunta** | ¿Lo está respetando? |
| **Evidencia positiva** | Tiempo dentro del POI, rebotes |
| **Evidencia negativa** | Rompe el POI con convicción |
| **Deja pasar** | Respetó el POI por N velas |
| **Mantiene esperando** | Sigue dentro del POI |
| **Pierde condición** | Rompe el POI con convicción |

### Piso 4 — EN_CRUCE
| Campo | Valor |
|-------|-------|
| **Misión** | Detectar cruce del estocástico en zona extrema |
| **Pregunta** | ¿Existe intención de giro? |
| **Evidencia positiva** | Cruce confirmado en extremo |
| **Evidencia negativa** | Cruce fuera de zona o sin confirmación |
| **Deja pasar** | Cruce confirmado en extremo |
| **Mantiene esperando** | Estocástico se acerca pero no cruza |
| **Pierde condición** | Cruce fuera de zona o sin confirmación |

### Piso 5 — CONFIRMANDO_CRUCE
| Campo | Valor |
|-------|-------|
| **Misión** | Validar que el cruce tiene calidad |
| **Pregunta** | ¿Ese giro tiene calidad? |
| **Evidencia positiva** | Separación >= umbral durante ventana |
| **Evidencia negativa** | Separación decrece o se anula |
| **Deja pasar** | Separación >= umbral durante ventana |
| **Mantiene esperando** | Separación baja pero creciente |
| **Pierde condición** | Separación decrece o se anula |

### Piso 6 — CONFIRMANDO_VELA
| Campo | Valor |
|-------|-------|
| **Misión** | Esperar confirmación de vela |
| **Pregunta** | ¿El precio confirmó esa intención? |
| **Evidencia positiva** | Martillo/invertido M15 |
| **Evidencia negativa** | Velas sin confirmación y separación se pierde |
| **Deja pasar** | Martillo confirmado |
| **Mantiene esperando** | Aún no aparece martillo |
| **Pierde condición** | Velas sin confirmación y separación se pierde |

### Piso 7 — LISTO
| Campo | Valor |
|-------|-------|
| **Misión** | Evaluar si la evidencia reunida es suficiente |
| **Pregunta** | ¿La evidencia reunida es suficiente para actuar? |
| **Evidencia positiva** | Todos los pisos anteriores aprobaron |
| **Evidencia negativa** | El orquestador decide no operar |
| **Deja pasar** | Todos los pisos anteriores aprobaron |
| **Mantiene esperando** | Espera instrucción del orquestador |
| **Pierde condición** | El orquestador decide no operar |

---

## 8. Comportamiento de los vigilantes

Cada vigilante habita un piso.
Su única responsabilidad es observar la condición de su piso.
Nunca compra, nunca vende, nunca decide subir o bajar de piso.

| Respuesta | Significado |
|-----------|-------------|
| `SÍ` | La condición del piso se cumple. Aporta evidencia positiva. |
| `NO` | La condición NO se cumple. Aporta evidencia negativa. La hipótesis es expulsada del edificio. |
| `SIGUE` | La condición se cumple pero no es suficiente para avanzar. Aporta evidencia débil o neutral. La hipótesis se mantiene en el piso. |
| `RETROCEDE` | La hipótesis subió de piso pero ahora pierde la condición. Aporta evidencia negativa fuerte. Vuelve al piso anterior. |

**Nunca** un vigilante dice `BUY` o `SELL`. Nunca.

---

## 9. El Administrador del Edificio

El Administrador del Edificio es la entidad que decide **qué hipótesis merecen atención**.

No toma operaciones. Administra recursos.

### Responsabilidades del Administrador

| Acción | Cuándo |
|--------|--------|
| `ADMITIR` | La hipótesis cumple condiciones mínimas para entrar al Piso 0 |
| `PRIORIZAR` | Asigna `priority_score` basado en urgencia, confianza y potencial |
| `ARCHIVAR` | La hipótesis lleva demasiado tiempo sin evolucionar |
| `EXPULSAR` | Un vigilante respondió `NO` y el orquestador confirmó |

### Criterios de permanencia del Administrador

Cada piso posee un **criterio de permanencia**. Si la hipótesis deja de evolucionar dentro de una ventana razonable, el Administrador puede archivarla.

El criterio no es solo tiempo. Puede ser:
- Volatilidad
- Estructura
- Distancia al POI
- Sesión de mercado
- Número de velas sin novedad

---

## 10. El Expediente de la Hipótesis

Cada hipótesis tiene un expediente que la acompaña durante todo su recorrido.

```python
{
    "hypothesis_id": "381",
    "asset": "EURUSD",
    "direction": "CALL",
    "status": "VIVA",
    "ingress_reason": "Rebote en POI H1",
    "current_floor": 5,
    "ingress_time": "08:00",
    "priority_score": 0.8,
    "attention_level": "HIGH",
    "urgency": "MEDIUM",
    "confidence": 0.65,
    "evidence": {
        "piso_0": {"score": 0.6, "evidence": "Impulso alcista moderado"},
        "piso_1": {"score": 0.7, "evidence": "Swing confirmado"},
        "piso_2": {"score": 0.8, "evidence": "Llegó al POI con body_n=0.18"},
        "piso_3": {"score": 0.75, "evidence": "Respetó POI por 3 velas"},
        "piso_4": {"score": 0.85, "evidence": "Cruce en zona extrema K=18"},
        "piso_5": {"score": 0.7, "evidence": "Separación creciente 2.1→5.2"},
        "piso_6": {"score": 0.9, "evidence": "Martillo confirmado"},
    },
    "history": [
        {"floor": 2, "time": "08:00", "event": "llega_POI", "features": {...}},
        {"floor": 3, "time": "08:15", "event": "sigue_POI", "features": {...}},
        {"floor": 4, "time": "09:00", "event": "cruce_extremo", "features": {...}},
        {"floor": 5, "time": "09:15", "event": "separacion_aumentando", "features": {...}},
    ],
    "observations": [
        "Lleva 4 velas esperando",
        "Separación aumentando",
        "Sin ruptura del POI",
    ],
    "features": {
        "body_n": 0.18,
        "kd_dist": 5.2,
        "separacion_trend": 0.5,
        "wait_cycles": 4,
    },
    "last_decision": "SIGUE",
}
```

### Campos del expediente

| Campo | Descripción |
|-------|-------------|
| `hypothesis_id` | Identificador único de la hipótesis |
| `asset` | Par del activo |
| `direction` | Dirección hipotetizada: CALL o PUT |
| `status` | VIVA / MADURANDO / INVALIDADA / CONTRATADA / ARCHIVADA |
| `ingress_reason` | Por qué entró al edificio |
| `current_floor` | Piso actual |
| `ingress_time` | Cuándo ingresó |
| `priority_score` | 0.0 a 1.0, asignado por el Administrador |
| `attention_level` | HIGH / MEDIUM / LOW |
| `urgency` | Alta / Media / Baja |
| `confidence` | 0.0 a 1.0, nivel de confianza dinámico |
| `evidence` | Evidencia acumulada por piso, con score y descripción |
| `history` | Lista de eventos por piso |
| `observations` | Notas textuales del trader |
| `features` | Features técnicas actuales |
| `last_decision` | Última decisión del vigilante/orquestador |

---

## 11. El Orquestador: única autoridad

El Orquestador es el único que interpreta el edificio completo.

Es el único autorizado para:

| Acción | Cuándo |
|--------|--------|
| `SUBIR_PISO` | Todos los vigilantes del piso actual responden SÍ |
| `BAJAR_PISO` | Un vigilante responde RETROCEDE |
| `MANTENER_PISO` | Un vigilante responde SIGUE |
| `CONTRATAR` | La hipótesis llega a Piso 7 con evidencia suficiente |
| `EXPULSAR` | Un vigilante responde NO |

**Ningún vigilante debe tomar esas decisiones.**

El Orquestador recibe el expediente completo de la hipótesis y decide.

---

## 12. Máquina de estados de vigilancia

```
NACE
 ↓
VIVA / MADURANDO
 ↓
OBSERVANDO
    ↓ (vigilante Piso 0: SÍ)
CANDIDATO
    ↓ (vigilante Piso 1: SÍ)
EN_POI
    ↓ (vigilante Piso 2: SÍ)
RESPEANDO_POI
    ↓ (vigilante Piso 3: SÍ)
EN_CRUCE
    ↓ (vigilante Piso 4: SÍ)
CONFIRMANDO_CRUCE
    ↓ (vigilante Piso 5: SÍ)
CONFIRMANDO_VELA
    ↓ (vigilante Piso 6: SÍ)
LISTO
    ↓ (orquestador: CONTRATAR)
CONTRATADA
    ↓ (cierre por tiempo/TP/SL)
ARCHIVADA
```

**Retrocesos permitidos:**
- `CONFIRMANDO_CRUCE` → `EN_CRUCE` si el cruce pierde calidad.
- `CONFIRMANDO_VELA` → `CONFIRMANDO_CRUCE` si no aparece confirmación.
- `LISTO` → `CONFIRMANDO_VELA` si el contexto cambia antes de la entrada.

**Invalidación:**
- Cualquier piso puede responder `NO` → el orquestador decide si expulsa o da una segunda oportunidad.

**No se permiten saltos.** Una hipótesis no pasa de `OBSERVANDO` a `LISTO` sin recorrer todos los pisos.

---

## 13. Reglas de intervención humana

El operador humano puede intervenir en cualquier momento.

| Acción | Efecto |
|--------|--------|
| `MANTENER` | La hipótesis sigue en el piso actual. No se toca. |
| `ACELERAR` | La hipótesis puede subir de piso si cumple condiciones relajadas. |
| `DESCARTAR` | La hipótesis es expulsada del edificio. Se archiva su expediente. |
| `FORZAR_ENTRADA` | Solo el orquestador puede hacerlo. Usar solo en casos extremos. |

**Regla de oro:**
> Si la hipótesis retrocede de piso, el humano puede decidir si le da una segunda oportunidad en el piso anterior o la descarta definitivamente.

---

## 14. Ejemplo de flujo completo

```
EURUSD — Expediente creado

Hipótesis #381
Posible rebote CALL desde POI H1

Estado: VIVA
Confianza inicial: 0.5

Piso 0 — OBSERVANDO
          Scanner detecta impulso alcista reciente.
          Administrador: ADMITIR (priority_score=0.6)
          Vigilante Piso 0: SÍ
          Evidencia: "Impulso alcista moderado" (+0.1)
          Confianza: 0.5 → 0.6
          → Sube a Piso 1

Piso 1 — CANDIDATO
          Swing confirmado en 07:45 UTC.
          Vigilante Piso 1: SÍ
          Evidencia: "Swing confirmado" (+0.1)
          Confianza: 0.6 → 0.7
          → Sube a Piso 2

Piso 2 — EN_POI
          Llega a POI en 08:00 UTC. body_n=0.18, brake_ratio=0.53.
          Vigilante Piso 2: SÍ
          Evidencia: "Llegó al POI con body_n=0.18" (+0.1)
          Confianza: 0.7 → 0.8
          → Sube a Piso 3

Piso 3 — RESPEANDO_POI
          08:15 UTC: sigue dentro del POI. Vigilante: SIGUE
          Evidencia: "Respetó POI por 1 vela" (+0.05)
          Confianza: 0.8 → 0.85
          08:30 UTC: sigue dentro del POI. Vigilante: SIGUE
          Evidencia: "Respetó POI por 2 velas" (+0.05)
          Confianza: 0.85 → 0.90
          08:45 UTC: sigue dentro del POI. Vigilante: SIGUE
          Evidencia: "Respetó POI por 3 velas" (+0.05)
          Confianza: 0.90 → 0.95
          → Mantiene Piso 3

Piso 4 — EN_CRUCE
          09:00 UTC: cruce estocástico alcista en zona extrema (K=18).
          Separación inicial: 2.1 (baja).
          Vigilante Piso 4: SÍ
          Evidencia: "Cruce en zona extrema K=18" (+0.1)
          Confianza: 0.95 → 1.0
          → Sube a Piso 5

Piso 5 — CONFIRMANDO_CRUCE
          09:15 UTC: separación sube a 3.8. Vigilante: SIGUE
          Evidencia: "Separación creciente 2.1→3.8" (+0.05)
          Confianza: 1.0 → 0.95
          09:30 UTC: separación sube a 5.2. Vigilante: SÍ
          Evidencia: "Separación alcanzó 5.2" (+0.1)
          Confianza: 0.95 → 1.0
          → Sube a Piso 6

Piso 6 — CONFIRMANDO_VELA
          09:45 UTC: martillo M15 confirmado.
          Vigilante Piso 6: SÍ
          Evidencia: "Martillo confirmado" (+0.1)
          Confianza: 1.0 → 1.0
          → Sube a Piso 7

Piso 7 — LISTO
          Orquestador evalúa expediente:
          - Evidencia acumulada: 8 puntos a favor
          - Evidencia negativa: 0
          - Confianza: 1.0
          - Tiempo en edificio: 2h 45min
          - Priority score: 0.8
          → DECISIÓN: CONTRATAR_CALL

          Orden enviada a las 10:00 UTC.
          Estado: CONTRATADA

Piso 8 — ARCHIVADA
          Cierre a las 10:15 UTC.
          Resultado: WIN.
          Expediente archivado.
```

---

## 15. Principios innegociables

1. **El sistema no detecta señales. Construye, fortalecer o invalida hipótesis.**
2. **Un piso es una ubicación, no una decisión.**
3. **Una hipótesis solo abandona el edificio cuando pierde la razón por la cual entró.**
4. **Los vigilantes solo informan: SÍ / NO / SIGUE / RETROCEDE.**
5. **El Orquestador es el único autorizado para subir, bajar, mantener o contratar.**
6. **El Administrador administra recursos y prioridades. No opera.**
7. **Retroceder de piso es normal. No es un error.**
8. **El expediente es obligatorio. Sin expediente, no hay contexto.**
9. **Cada piso agrega evidencia a favor o en contra. El expediente almacena evidencia acumulada.**
10. **El orquestador no busca una señal perfecta. Evalúa si la evidencia reunida es suficiente para actuar.**
11. **La confianza es dinámica. Cada vigilante aporta evidencia. El orquestador recalcula continuamente.**
12. **Los vigilantes de pisos inferiores nunca se apagan. Invalidación temprana es obligatoria.**

---

## 16. Próximos pasos en el laboratorio

1. Definir esquema del Expediente de Hipótesis como estructura de datos central.
2. Definir ciclo de vida de hipótesis: VIVA → MADURANDO → INVALIDADA / CONTRATADA / ARCHIVADA.
3. Implementar máquina de estados por hipótesis.
4. Crear vigilantes por piso con respuestas `SÍ/NO/SIGUE/RETROCEDE`.
5. Implementar Orquestador como única autoridad de decisión.
6. Implementar Administrador del Edificio para admisión, priorización y archivado.
7. Implementar sistema de confianza dinámica por hipótesis.
8. Medir: evidencia por piso, confianza acumulada, tiempo por piso, tasa de retrocesos, tasa de conversión por piso.
9. Entrenar ML para predecir transiciones de estado, no para clasificar señales.

---

*Última actualización: 2026-08-04*
*Estado: Documento arquitectónico fundacional aprobado. Listo para implementación.*
