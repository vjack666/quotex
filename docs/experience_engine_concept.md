# Experience Engine — Concepto (no spec)

> Documento de definición de paradigma. NO es un SDD: no contiene tablas, schema,
> columnas ni código. Solo fija QUÉ es la memoria del mercado en este proyecto y
> cómo se relaciona con los modelos de IA. El SDD (con implementación) se redacta
> DESPUÉS de aprobar este concepto.

---

## 1. Cambio de paradigma

El proyecto ha sido, hasta ahora: **crear detectores** (soportes, resistencias,
FVG, order blocks, zonas, momentum). Cada detector es una regla o heurística que
decide qué es "importante".

El siguiente paso no es "mejorar los detectores". Es **crear memoria**:

- Un detector SABE porque tú le programaste la regla.
- Una IA con memoria puede empezar a desarrollar CRITERIO, porque ha vivido el
  mercado muchas veces y relaciona lo que vio con lo que ocurrió después.

Una IA sin memoria solo ejecuta reglas. Una IA con memoria puede aprender.

---

## 2. La Market Memory NO es una base de datos

La base de datos es solo una IMPLEMENTACIÓN de la memoria. El concepto es otro:

> La Market Memory es el **sistema nervioso** del proyecto. Cada vez que el mercado
> cambia, el sistema adquiere una EXPERIENCIA. Esa experiencia debe ser reutilizable
> por cualquier modelo futuro, sin re-capturar ni re-estructurar los datos.

Por eso el nombre correcto no es "Market Memory" (almacén). Es **Experience Engine**:
el mercado no se memoriza, **se experimenta**. Cada vela, reacción, ruptura, operación
y contexto es una experiencia. Las IAs no aprenden de velas, indicadores o zonas;
aprenden de **experiencias completas del mercado**.

---

## 3. Unidad de información: la EXPERIENCIA, no el snapshot

No registramos fotografías (snapshots). Registramos ARCOS.

Un snapshot es una foto congelada en T. Una experiencia es un arco:

```
contexto previo  →  evento  →  evolución  →  resultado  →  consecuencias
```

Una operación NO empieza cuando el scanner dice BUY. Empieza mucho antes (contexto:
estructura, zonas vivas, estocástico, horario, correlación) y termina mucho después
(evolución: pips recorridos, invalidación de estructura, qué hizo un activo
correlacionado, patrón que apareció).

Una experiencia tiene, como mínimo narrativo:
- **contexto previo**: el estado del mercado ANTES del evento.
- **evento**: lo que ocurrió (reacción en un nivel, ruptura, entrada, etc.).
- **evolución**: cómo se desarrolló después (movimiento, invalidación, tiempo).
- **resultado**: el desenlace medible (WIN/LOSS, pips, estructura rota o no).
- **consecuencias**: efectos de segundo orden (otro activo, patrón emergente, sesgo).

Esto es mucho más rico que un snapshot y es lo que hace reutilizable la memoria:
cualquier IA futura lee el arco completo y pregunta lo que quiera, sin que hayamos
anticipado su pregunta al capturar.

---

## 4. Datos vs conocimiento

- **Datos**: OHLC, estocástico, RSI, hora, zona, volatilidad, noticias.
- **Conocimiento**: aparece cuando el sistema relaciona esos datos con lo que ocurrió
  DESPUÉS.

La inteligencia nace de esa relación, no de acumular datos. El Experience Engine
acumula experiencias (datos + después); las IAs extraen el conocimiento.

---

## 5. Flujo único

```
Mercado
   │
   ▼
Observación  (captura el arco de experiencia en cada cambio relevante)
   │
   ▼
Experience Engine  (adquiere y DISTRIBUYE la experiencia)
   │
   ├── IA de Entradas      (Feature 18 — ya existe, primer lector)
   ├── IA de Zonas         (futuro)
   ├── IA de Patrones      (futuro)
   ├── IA de Tendencias    (futuro)
   ├── IA de Riesgo        (futuro)
   ├── IA de Volatilidad   (futuro)
   └── IA futura           (cualquier modelo, sin tocar la captura)
```

Todas las IAs leen EXACTAMENTE la misma memoria. Ninguna escribe reglas. Ninguna
modifica la memoria. Todas aprenden de ella.

---

## 6. Definición de "aprender una experiencia"

> El sistema registra un arco completo del mercado (contexto previo → evento →
> evolución → resultado → consecuencias) y ACUMULA esos arcos para que cualquier
> modelo futuro consulte "experiencias parecidas a esta" y obtenga una DISTRIBUCIÓN
> de outcome, sin que el sistema haya codificado de antemano qué variable importa.

El sistema NO sabe por qué una zona funcionó. Solo sabe que experiencias con cierto
perfil terminaron en +18 pips el 78% de las veces. Eso es aprender: relacionar, no
reglar.

---

## 7. Modo del Engine: ACTIVO

El Experience Engine es ACTIVO, no un pozo pasivo:

- Adquiere una experiencia en cada cambio relevante del mercado.
- La DISTRIBUYE a las IAs conectadas cuando ocurre algo similar en vivo.
- Las IAs reaccionan con un Confidence Score (o distribución) basado en la memoria.

Esto es distinto de un modelo que solo infiere al scorear (modo pasivo). El engine
empuja experiencias a las IAs; las IAs no van a buscarlas.

Feature 18 (Entry Intelligence Agent) hoy opera en modo pasivo (infiere al scorear).
Al migrar a este paradigma, se vuelve un lector activo del engine: recibe la
experiencia del arco y emite el Confidence Score de entrada.

---

## 8. Contrato de las IAs (regla de hierro)

1. Las IAs SOLO LEEN la memoria. Nunca escriben en ella.
2. Las IAs NO modifican otras IAs ni la captura.
3. Toda IA se entrena desde la MISMA fuente de experiencias.
4. El engine puede alimentar IAs nuevas sin re-capturar ni re-estructurar datos.

Esto es lo que hace que sea un cerebro y no 5 silos. Si una IA necesita escribir
algo, lo publica como Confidence Score hacia afuera, no hacia la memoria.

---

## 9. Qué NUNCA se hace (anti-patrones del paradigma anterior)

- NO "si hay 3 toques → soporte".
- NO "si existe FVG → zona".
- NO "si hay Order Block → entrar".
- NO decaimiento de zonas por heurística fija (`_DECAY_TABLE`).
- NO tablas separadas por tipo de detector (`reaction_zones`, `expired_zones` con
  reglas de rol hardcoded).
- NO modelos especializados alimentados por tablas diferentes.

El modelo descubre esas relaciones. El humano no las programa.

---

## 10. Relación con Feature 18 (Entry Intelligence Agent)

F18 es el PRIMER lector del Experience Engine. Hoy se entrena desde `scan_candidates`
+ `trade_journal` (tablas con propósito). Al materializarse este concepto, F18 se
re-entrena desde la memoria única, leyendo el arco de experiencia de cada entrada.
El contrato no cambia: F18 emite un Confidence Score de entrada. Solo cambia la
FUENTE de donde aprende (de tablas con propósito → memoria de experiencias).

---

## 11. Siguiente paso

Cuando este concepto esté aprobado, se redacta el SDD (con schema, ingesta y
entrenamiento) como feature nueva. El schema se deduce SOLO de la definición de
arco de experiencia (§3) — por eso no se diseña antes del concepto.

Hasta entonces: no se toca el bot, no se crea tabla, no se escribe código.
