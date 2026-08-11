# PLAN INGENIERIA IA — Búsqueda del escenario 80%

> Laboratorio de IA sobre el **Edificio de Contratación** (`src/edificio_contratacion.py`).
> Documento vivo: se actualiza a medida que el experimento avanza.
> Fecha: 2026-08-03.

---

## 1. Objetivo

Aplicar **redes neuronales** sobre datos históricos (parquets M15) para encontrar
el **escenario** — derivado del sistema de pisos del Edificio — donde la
estrategia gana **el 80% de las veces**.

La pregunta no es "¿el edificio gana?" sino:
> **¿Qué combinación de condiciones de los pisos produce un escenario con
> acierto ≥ 80% sobre la vela 15m siguiente?**

## 2. Alcance y límites

- **Datos**: parquets M15 descargados en `C:\Users\v_jac\Desktop\SMC-SYSTEMS\data\raw\`
  (7 majors: AUDUSD, EURUSD, GBPUSD, NZDUSD, USDCAD, USDCHF, USDJPY).
- **Simulación**: vela por vela, **causal** (sin look-ahead). Cada evaluación usa
  solo información disponible al cierre de la vela actual.
- **No toca el bot en vivo** ni la DB de la caja negra. Laboratorio aislado.
- **No modifica** `src/edificio_contratacion.py` durante el experimento.
- **Dominio**: spot FX (los parquets), proxy del OTC. Limitación conocida.

---

## 3. Arquitectura del Edificio — separación de responsabilidades

El Edificio no detecta señales. **Acompaña activos**. Cada activo entra con un
**Expediente** y es observado por **Vigilantes de Piso**. Un **Orquestador**
interpreta el edificio completo y decide el destino del expediente.

```
                     ┌─────────────────────────────────────────────┐
                     │              EDIFICIO                       │
                     │                                             │
   EXPEDIENTE ──────►│  P1  P2  P3  ...  Piso N   ◄── ORQUESTADOR  │
   (activo vivo)     │  │   │   │        │        │               │
                     │  V   V   V        V        │               │
                     │ Vig Vig Vig      Vig       │               │
                     │  │   │   │        │        │               │
                     │  └─ observan ─────┘        │               │
                     │                             │               │
                     │  ┌─ Orquestador decide:     │               │
                     │  │  subir / bajar /        │               │
                     │  │  mantener / contratar /  │               │
                     │  │  expulsar              │               │
                     └─────────────────────────────────────────────┘
```

### 3.1 Principios de responsabilidad

1. **El piso es una ubicación, no una decisión.** Un activo *está* en un piso.
   El piso representa el nivel de madurez del activo dentro del edificio. No
   representa quién tomó la decisión.

2. **Cada piso solo observa su propia condición.** El vigilante de un piso nunca
   compra, nunca vende y nunca sabe lo que hacen los demás pisos. Su única
   responsabilidad es responder el estado de la condición que vigila.

3. **El Orquestador es el único que interpreta el edificio completo.** Es el único
   autorizado para decidir: subir de piso, bajar de piso, mantener el piso,
   contratar (operar) o expulsar definitivamente un activo. Ningún vigilante
   debe tomar esas decisiones.

4. **Los pisos no son filtros desechables.** Son lugares donde un activo puede
   permanecer, avanzar o retroceder varias veces. Un activo puede vivir mucho
   tiempo dentro del edificio. El objetivo no es recorrer los pisos rápidamente;
   el objetivo es **madurar**.

5. **Cada piso tiene un propósito explícito.** Misión, qué observa, cuándo deja
   pasar, cuándo mantiene esperando, cuándo informa que perdió la condición.

6. **El edificio funciona como un expediente vivo.** El activo nunca es un
   snapshot. Cada piso agrega información al expediente del activo, que acompaña
   al activo durante todo su recorrido.

7. **No hay paradigma de "detector de señales".** El sistema acompaña activos, no
   detecta eventos.

### 3.2 El Expediente del Activo

El Edificio no mueve pares. Mueve **expedientes**. Cada activo que ingresa genera
un expediente que vive durante toda su estadía:

```
EXPEDIENTE EURUSD
═══════════════════════════════════════════════════════════
Piso actual: P2 — Cerebro
Fecha ingreso: 08:00
Motivo ingreso: Swing H1 (k ≤ 20)

Historial
  ✓ 08:00  P1 — Recepción: payout ≥ mínimo
  ✓ 08:15  P1 → P2: freno CONFIRMED (ratio=0.52)
  ✓ 08:30  P2: extremo vigente (k=18)
  ✗ 08:45  P2: cruce K/D sticky — se mantiene esperando

Observaciones
  Lleva 3 velas en P2. Separación |K−D| aumentando (0.3 → 0.8).
  Sin ruptura del POI. El freno sigue confirmado.
═══════════════════════════════════════════════════════════
```

El expediente reemplaza al concepto de "snapshot de señal". Cada vela, el
Orquestador actualiza el expediente: el vigilante del piso observa, el Orquestador
lee el expediente y decide.

---

## 4. Metodología — el escenario como acompañamiento de un expediente

El escenario no es una secuencia de eventos. Es el **estado maduro de un
expediente** que ha pasado por los pisos del Edificio. La cadena de acompañamiento
es:

```
Expediente ingresado (P1)
  → Vigilante P1 observa: ¿payout OK?
  → Orquestador: sube a P2
  → Vigilante P2 observa: ¿freno CONFIRMED? ¿extremo vigente?
  → Orquestador: mantiene en P2 (espera cruce K/D limpio)
  → Vigilante P3 observa: ¿cruce limpio + separación? ¿martillo 15m?
  → Orquestador: CONTRATA → orden al simulador
  → Simulador: resuelve con la vela 15m siguiente → WIN / LOSS
```

### 4.1 Los pisos y sus vigilantes

| Piso | Misión | Qué observa | Deja pasar (subir) | Mantiene esperando | Informa pérdida (bajar) |
|---|---|---|---|---|---|
| **P1 — Recepción** | Verificar que el activo paga bien y tiene dirección | `payout_ok`, dirección (k≤20 CALL / k≥80 PUT) | payout ≥ mínimo | payout OK pero sin freno aún | payout cae por debajo del mínimo |
| **P2 — Cerebro** | Confirmar el freno y vigilar el contexto de cruce | freno CONFIRMED (ratio < 0.7), extremo vigente, cruce K/D | freno CONFIRMED + extremo vigente | freno CONFIRMED pero cruce sticky/separación insuficiente | freno perdido (brake_ok revocado) o extremo perdido |
| **P3 — Sala de Espera** | Confirmar la entrada con vela 15m | cruce K/D limpio + separación mantenida, vela martillo/invertido | cruce limpio + separación OK + martillo 15m válido | cruce sticky o sin martillo todavía | cruce se vuelve sticky o freno se pierde |
| **CONTRATADO** | Ejecutar y resolver | — | — | — | — (fin del ciclo: WIN/LOSS) |

> **Nota**: el freno es una **alerta de preparación**, no una señal. El cruce K/D
> es una **condición**, no una señal. La **señal final** es el martillo 15m
> confirmado. El WR se evalúa cuando toda la cadena está completa.

### 4.2 Reglas de ejecución (pedido explícito del usuario)

1. **El freno es lo primero** — alerta de preparación. NO es señal.
2. **Esperar el cruce K/D** con las indicaciones ya descritas:
   - Cruce **pegajoso (sticky)** → esperar, no entrar.
   - Cruce **limpio** + separación mantenida → recién ahí se avanza.
3. **Esperar la vela 15m martillo** (o martillo invertido según el caso).
4. Cuando **los escenarios se acumulan en el tiempo**, recién entonces se envía
   la **orden al simulador**.
5. El simulador determina si la **siguiente vela 15m** es ganadora o perdedora.
6. **Descartar los timings del POI** (los tiempos de espera ligados al POI del
   experimento de volumen NO aplican acá).

### 4.3 Dirección del trade

- CALL: extremo estocástico bajo (k ≤ 20) + freno alcista + martillo alcista.
- PUT: extremo estocástico alto (k ≥ 80) + freno bajista + martillo invertido.

---

## 5. Datos y features

### 5.1 Fuente

Parquets M15 (7 majors), columnas a confirmar al inspeccionar:
`timestamp/open/high/low/close/tick_volume` (patrón de `SMC-SYSTEMS/data/raw`).

### 5.2 Features — estado del expediente por vela

Las features no son "indicadores de señal". Son el **estado del expediente**
que el Orquestador lee para decidir. Cada vela, se actualiza:

| Feature | Descripción | Propósito |
|---|---|---|
| `piso` | Piso actual del expediente (0–4) | Estado de madurez |
| `kd_k`, `kd_d`, `kd_dist` | Estocástico M15: K, D, \|K−D\| | Contexto del cruce |
| `cross_clean`, `cross_sticky` | Tipo de cruce reciente | Vigilante P3 |
| `brake_ok`, `brake_confirmed` | Freno detectado / confirmado con vela cerrada | Vigilante P2 |
| `brake_ratio` | range(vela cerrada) / range(referencia) | Calidad del freno |
| `extreme_call`, `extreme_put` | k ≤ 20 / k ≥ 80 | Dirección + contexto P1 |
| `hammer_15m`, `hammer_inv_15m` | Martillo / martillo invertido en vela 15m | Señal final P3 |
| `body_ratio`, `range_pct` | Forma de la vela (body/range, rango relativo) | Calidad de vela |
| `candles_in_piso` | Velas acumuladas en el piso actual | Madurez del expediente |
| `separation_since` | Tiempo desde el cruce limpio | Separación K/D mantenida |
| `poi_breached` | ¿Se rompió el POI desde la entrada? | Integridad del escenario |

### 5.3 Target

- **1** = la vela 15m siguiente cierra en la dirección del trade (WIN).
- **0** = caso contrario (LOSS).

---

## 6. Arquitectura de la red neuronal

### 6.1 Opciones (a decidir en la etapa de diseño)

1. **MLP sobre features agregadas** del expediente (simple, interpretable).
2. **LSTM/GRU** sobre la secuencia de estados del expediente (captura el
   "acumular escenarios en el tiempo").
3. **Convolucional 1D** sobre la ventana de velas (alternativa intermedia).

Recomendación inicial: arrancar con **MLP + features del expediente** como
baseline, y comparar contra la secuencia (LSTM) si el baseline no alcanza 80%.

### 6.2 Split

- Temporal, sin shuffle: `train (70%) / val (15%) / test (15%)` por ventana
  deslizante (walk-forward) para respetar causalidad.

### 6.3 Métricas

- Accuracy, precisión por clase, y **frecuencia del escenario** (cuántas veces
  ocurre en el histórico — un escenario con 80% WR pero 2 ocurrencias es ruido).
- Reportar **cantidad mínima de muestras** por escenario para considerarlo válido.

---

## 7. Simulador

- Recibe una orden `(asset, dirección, timestamp_entrada)` del Orquestador cuando
  un expediente alcanza CONTRATADO.
- Resuelve con la **vela 15m siguiente cerrada**: WIN si el cierre está del lado
  del trade, LOSS si no.
- Registra: fecha, par, dirección, features del expediente, resultado.
- Salida: CSV + resumen con WR global y por sub-escenario.

---

## 8. Entregables

| Entregable | Archivo |
|---|---|
| Documento de diseño de features/red | `ingenieria IA/docs/` (futuro) |
| Código de carga + features | `ingenieria IA/src/features.py` (futuro) |
| Backtest vela por vela (expedientes) | `ingenieria IA/src/backtest_edificio.py` (futuro) |
| Red neuronal | `ingenieria IA/src/modelo.py` (futuro) |
| Resultados | `ingenieria IA/results/` (futuro) |
| Veredicto final | `ingenieria IA/docs/veredicto.md` (futuro) |

---

## 9. Riesgos y limitaciones

1. **Spot ≠ OTC**: los parquets son spot FX; el comportamiento en OTC puede
   diferir. El resultado es una guía, no una promesa.
2. **Frecuencia de escenarios**: el Edificio en vivo produce pocos CONTRATADO;
   el histórico puede tener decenas. Muestras pequeñas → overfitting.
3. **Timings del POI descartados**: si el POI como timing fuera relevante, este
   experimento no lo captura (decisión explícita del usuario).
4. **Estocástico sin look-ahead**: el estocástico se calcula con velas cerradas
   disponibles al momento de la evaluación, nunca con la vela en formación.

---

## 10. Próximos pasos

1. Inspeccionar columnas y volumen de un parquet M15 (EURUSD).
2. Construir `backtest_edificio.py`: simulación causal de expedientes viviendo
   en los pisos del Edificio, vela por vela.
3. Construir `features.py` + dataset del expediente.
4. Baseline MLP → comparar con LSTM si hace falta.
5. Veredicto: ¿existe el escenario 80%? Documentar y ⏸ consultar al humano.
