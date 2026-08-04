# Laboratorio — Marco Experimental Fundacional

> **El Laboratorio es la autoridad científica del proyecto QUOTEX.**
> **El Edificio nunca crece por intuición. Crece porque el Laboratorio demuestra, con evidencia, que una nueva condición aumenta la probabilidad de éxito.**

---

## 1. Propósito

El Laboratorio existe para **descubrir conocimiento estadísticamente útil** sobre el Edificio de Contratación.

No diseña estrategias completas.
No optimiza parámetros de trading.
No decide entradas en vivo.

Su única función es **responder preguntas concretas** sobre condiciones individuales, medir su impacto real, y promover al Edificio solo aquellas que demuestran valor estadístico reproducible.

El objetivo del Laboratorio es **aumentar la calidad estadística global del sistema**, priorizando la esperanza matemática, la robustez y la reproducibilidad por encima de cualquier métrica individual.

---

## 2. Leyes fundamentales

### 2.1 Objetivo
El objetivo del Laboratorio no es crear estrategias. Es **descubrir conocimiento estadísticamente útil**.

### 2.2 Unidad de trabajo
La unidad de trabajo del Laboratorio no es una estrategia completa. Es una **hipótesis experimental**.

### 2.3 Pregunta única
Cada experimento debe intentar responder **una sola pregunta**.

### 2.4 Aislamiento
Cada condición debe aislarse para medir cuánto aporta realmente al:
- Win rate
- Loss rate
- Frecuencia del escenario
- Expectativa matemática

### 2.5 Fracaso como conocimiento
El fracaso de un experimento no es un error. Es **conocimiento adquirido** y debe quedar documentado.

### 2.6 Puerta de entrada al Edificio
Ninguna condición entra al Edificio sin haber sido **promovida por el Laboratorio**.

### 2.7 Tecnología libre
El Laboratorio puede experimentar con cualquier técnica: estadística clásica, simulaciones, optimización, clustering, redes neuronales, árboles de decisión, modelos bayesianos, aprendizaje por refuerzo o cualquier otra herramienta de IA si ayuda a medir mejor una hipótesis.

### 2.8 Reproducibilidad
Cada experimento debe ser **reproducible por cualquier agente** del proyecto.

### 2.9 Permanencia del conocimiento
El conocimiento generado permanece aunque la hipótesis sea descartada.

### 2.10 La evidencia tiene prioridad
Las decisiones del Laboratorio nunca se basarán en opiniones, intuición o preferencias personales.

Si la evidencia contradice una hipótesis aceptada, la hipótesis deberá ser modificada o descartada.

En el Laboratorio no existen verdades permanentes. Solo existe evidencia disponible.

### 2.11 Falsación
El propósito de un experimento no es demostrar que una hipótesis es correcta.

Su propósito es intentar demostrar que es falsa.

Solo las hipótesis que sobreviven múltiples intentos de falsación pueden ser promovidas al Edificio.

---

## 3. Separación de responsabilidades

### Laboratorio
- Descubre conocimiento.
- Diseña experimentos.
- Valida o rechaza hipótesis.
- Promueve conocimiento validado al Edificio.

### Edificio de Contratación
- No experimenta.
- Solo utiliza conocimiento previamente validado.
- Construye hipótesis de trading utilizando vigilantes y pisos.
- El Orquestador toma la decisión final.

**Nunca se invierte el flujo.**
El Edificio no propone condiciones.
El Laboratorio no decide entradas en vivo.

---

## 4. Objetivos y métricas de aceptación

El Laboratorio no busca maximizar el winrate aislado.
Busca **mejorar la calidad estadística global del sistema**.

Para aceptar una nueva condición, se evalúan como mínimo:

| Métrica | Descripción |
|---------|-------------|
| **Win rate** | Proporción de aciertos sobre el total de eventos. |
| **Loss rate** | Proporción de fallos. |
| **Expectativa matemática** | `(WR × Ganancia promedio) − (LR × Pérdida promedio)`. |
| **Profit Factor** | `Ganancia total / Pérdida total`. |
| **Número de oportunidades** | Frecuencia del escenario en el histórico. |
| **Robustez** | Estabilidad del resultado en distintos períodos y activos. |
| **Estabilidad temporal** | Comportamiento consistente en train / val / test. |
| **Impacto sistémico** | Cómo afecta la nueva condición al resto de condiciones vigentes. |

**Criterio mínimo de promoción:**
Una condición se promueve al Edificio si y solo si:
1. Mejora la métrica principal sobre el baseline en al menos **2 activos** o en el conjunto global.
2. La mejora es **estadísticamente distinguishable** de ruido.
3. Mantiene una **cantidad mínima viable** de eventos.
4. No introduce **look-ahead** ni contaminación de datos.
5. No degrada métricas secundarias críticas (ej: profit factor, estabilidad temporal).

Si falla en **uno solo** de estos criterios, la condición es **rechazada** y archivada.

---

## 5. Patrimonio intelectual del Laboratorio

Todo experimento, exitoso o fallido, aumenta el patrimonio de conocimiento del proyecto.

El conocimiento nunca se elimina. Solo cambia de estado:

| Estado | Significado |
|--------|-------------|
| `vigente` | Promovido al Edificio y en uso. |
| `reemplazado` | Fue superado por una condición mejor. |
| `refutado` | Falsado por evidencia posterior. |
| `histórico` | Archivado como referencia. |

Dentro de dos años, el Laboratorio debe poder responder:
- ¿Qué condiciones probamos?
- ¿Cuáles funcionaron?
- ¿Cuáles no?
- ¿Por qué las descartamos?

Ese archivo es el activo más valioso del proyecto.

---

## 6. Tipos de experimento

El Laboratorio no está limitado a backtests clásicos.
Puede investigar cualquier forma de conocimiento que ayude a medir una hipótesis.

### 6.1 Experimentos estadísticos
Pruebas de significancia, correlaciones, tests de normalidad, bootstrap, permutaciones.

### 6.2 Experimentos geométricos
Estructuras de precio, zonas, POIs, retrocesos, expansions, fibonacci.

### 6.3 Experimentos temporales
Timings, duraciones, sesiones, ventanas de espera, secuencias.

### 6.4 Experimentos de indicadores
Efectividad de filtros, umbrales, combinaciones, zonas extremas.

### 6.5 Experimentos de ML
Features, modelos, regularización, selección, importancia de variables.

### 6.6 Experimentos con redes neuronales
MLP, LSTM, CNN 1D, transformadores, attention, embeddings.

### 6.7 Experimentos bayesianos
Actualización de creencias, priors, posteriors, probabilistic calibration.

### 6.8 Experimentos de interacción entre condiciones
Sinergias, condicionales, efectos de combinación, cancelaciones.

### 6.9 Experimentos de robustez
Walk-forward, validación cruzada temporal, stress periods, regimes.

### 6.10 Experimentos de sensibilidad
Barras de error, perturbaciones, estabilidad de parámetros.

### 6.11 Experimentos de causalidad
Intervenciones, contrafactuales, tests de causalidad, gráficos acíclicos.

**Regla:**
> Cualquier método es válido si es medible, reproducible y respeta la causalidad.

---

## 7. Ciclo de vida de un experimento

```
Hipótesis
   ↓
Diseño experimental
   ↓
Ejecución
   ↓
Resultados
   ↓
¿Cumple criterios de promoción?
   ↓
 NO                ↓  SÍ
Archivo como        Promoción al Edificio
conocimiento        como vigilante de piso
```

### 7.1 Formulación de la hipótesis
Se escribe en lenguaje humano, clara y medible.

**Ejemplo:**
> "Esperar 2 velas de respeto al POI aumenta el winrate de los brakes confirmados."

### 7.2 Diseño experimental
Define:
- Población: qué activos, qué período, qué timeframe.
- Baseline: condición actual contra la que se compara.
- Variable a medir: la condición que se evalúa.
- Métricas: winrate, lossrate, expectativa, profit factor, frecuencia.
- Criterios de aceptación y rechazo.
- Protocolo de reproducibilidad: comandos exactos, versiones de datos, semillas.

### 7.3 Ejecución
Se ejecuta sobre datos históricos, respetando:
- **Causalidad estricta**: no se usa información futura.
- **Aislamiento**: se mide solo la condición bajo prueba.
- **Reproducibilidad**: mismos datos, mismos parámetros, mismo código.

### 7.4 Documentación
Todo experimento se documenta en un archivo estructurado:

```
EXP-NNN.md
- Hipótesis
- Diseño
- Ejecución
- Resultados
- Decisión: promovido / rechazado / inconcluyente
- Conocimiento generado
```

### 7.5 Decisión
- **Promovido**: pasa al Edificio como vigilante de piso.
- **Rechazado**: se archiva. El conocimiento queda disponible para futuras referencias.
- **Inconcluyente**: se marca para revisión con más datos o mejor diseño.

---

## 8. Reproducibilidad

Todo experimento debe poder ser reproducido por cualquier agente del proyecto.

Para garantizarlo:
- Los datos de entrada son versionados o referenciados por ruta y checksum.
- El código del experimento se guarda en `src/strategy_lab/experimentos/`.
- Los resultados se guardan en `src/strategy_lab/results/exp-NNN/`.
- El archivo `EXP-NNN.md` incluye comandos exactos de ejecución.

**No existe un experimento que no se pueda volver a correr.**

---

## 9. Integración Laboratorio → Edificio

El Laboratorio no modifica el Edificio directamente.
Promueve conocimiento validado.

El flujo es:

```
Laboratorio: "La condición X mejora el winrate en 3 activos."
   ↓
Edificio: adopta la condición como vigilante de piso nuevo.
   ↓
Orquestador: incorpora la nueva evidencia al expediente.
```

**Condiciones prohibidas en el Edificio sin paso previo por el Laboratorio:**
- Nuevos indicadores.
- Nuevos filtros.
- Nuevos tiempos de espera.
- Nuevos umbrales.
- Cualquier regla que afecte la toma de decisiones.

---

## 10. Principios de experimentación

1. **Una pregunta por experimento.**
2. **Aislamiento de variables.** Medir una condición a la vez.
3. **Falsación.** Intentar demostrar que la hipótesis es falsa, no confirmarla.
4. **Causalidad.** Sin look-ahead. Sin fuga de datos.
5. **Evidencia sobre opinión.** La evidencia tiene prioridad sobre cualquier intuición.
6. **Transparencia.** Resultados negativos se publican igual que los positivos.
7. **Permanencia.** El conocimiento generado no se borra, incluso si la hipótesis es descartada.
8. **Tecnología agnostic.** Cualquier método es válido si es medible y reproducible.
9. **Impacto sistémico.** Evaluar no solo la condición aislada, sino su efecto sobre el sistema completo.
10. **Patrimonio intelectual.** Todo experimento, exitoso o fallido, aumenta el conocimiento del proyecto.

---

## 11. Estructura de carpetas

```
src/strategy_lab/
├── experimentos/
│   ├── EXP-001/
│   │   ├── experimento.py
│   │   ├── resultados.csv
│   │   └── EXP-001.md
│   ├── EXP-002/
│   └── ...
├── results/
│   ├── exp-001/
│   └── ...
└── LAB_MARCO_EXPERIMENTAL.md
```

---

## 12. Próximos pasos

1. Aprobar este documento como constitución del Laboratorio.
2. Definir la plantilla `EXP-NNN.md`.
3. Implementar `experiment_runner.py` respetando estas leyes.
4. Diseñar EXP-001: "¿Esperar 2 velas de respeto al POI mejora la calidad?"

---

*Última actualización: 2026-08-04*
*Estado: Documento fundacional. Pendiente de aprobación humana.*
