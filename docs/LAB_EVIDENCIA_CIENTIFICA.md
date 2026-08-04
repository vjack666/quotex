# Laboratorio — Marco de Evidencia Científica

> **Este documento es el tribunal del Laboratorio.**
> **Ningún experimento se considera demostrado hasta que cumple estas reglas.**
> **Sin evidencia reproducible, no hay promoción al Edificio.**

---

## 1. Propósito

El Laboratorio puede descubrir conocimiento durante años.
Pero **descubrir no es demostrar**.

El Marco Experimental (`LAB_MARCO_EXPERIMENTAL.md`) define la filosofía.
Este documento define **qué significa realmente que un experimento está demostrado**.

Sin este tribunal, el Laboratorio sería una sala de ruido.
Con este tribunal, se convierte en un sistema de validación científica.

---

## 2. Principio fundamental

> **Una mejora en el winrate no es evidencia.**
> **Una mejora en el winrate con significancia estadística, reproducibilidad y robustez es evidencia.**

El Laboratorio no busca confirmar hipótesis.
Busca **romperlas**.
Solo las hipótesis que sobreviven a este tribunal son promovidas al Edificio.

---

## 3. Jerarquía de evidencia

El Laboratorio reconoce cinco niveles de evidencia, de menor a mayor confianza:

### 3.1 Observacional
- Lo que se ve en datos históricos sin aislamiento.
- **No promueve al Edificio.**
- Sirve para formular hipótesis, no para demostrarlas.

### 3.2 Aislada
- La condición se mide separada del resto.
- Sin look-ahead.
- Sin combinación con otras condiciones.
- **Puede avanzar al siguiente nivel si cumple los mínimos de muestra y métrica.**

### 3.3 Reproducida
- El mismo experimento se repite en distintos períodos o activos.
- El resultado se mantiene.
- **Puede avanzar al siguiente nivel.**

### 3.4 Robustecida
- Se aplican tests de robustez: walk-forward, bootstrap, stress periods, perturbaciones de parámetros.
- La mejora no depende de una ventana temporal ni de un subconjunto afortunado.
- **Puede avanzar al siguiente nivel.**

### 3.5 Demostrada
- Cumple todos los criterios de este documento.
- Tiene **evidencia reproducible, medible y libre de contaminación**.
- **Sí promueve al Edificio.**

---

## 4. Criterios mínimos de promoción

Para que una condición sea promovida al Edificio, debe cumplir **todos** estos criterios:

### 4.1 Tamaño mínimo de muestra

| Tipo de experimento | Eventos mínimos |
|---|---|
| Condición individual (ej: martillo, cruce) | 60 eventos |
| Condición compuesta (ej: brake + martillo) | 100 eventos |
| Condición multi-activo | 30 eventos por activo, con al menos 2 activos representativos |

**Regla:**
> Si no hay suficientes eventos, el experimento es **inconcluyente**.
> No se promueve.
> No se descarta.
> Se marca para revisión con más datos.

### 4.2 Significancia estadística

El Laboratorio requiere un nivel de confianza mínimo:

| Umbral | Valor |
|---|---|
| Nivel de confianza | 95% |
| p-valor máximo | 0.05 |

Si el p-valor es mayor a 0.05:
- La diferencia observada podría deberse al azar.
- El experimento es **inconcluyente**.
- No se promueve.

**Nota:**
> El Laboratorio prefiere un experimento bien diseñado con resultado negativo,
> que un experimento mal diseñado con resultado positivo.

### 4.3 Intervalos de confianza

Toda métrica principal debe reportarse con su intervalo de confianza del 95%:

| Métrica | Formato |
|---|---|
| Win rate | `WR = 54.2% [50.1%, 58.3%]` |
| Expectativa matemática | `EM = 0.34 [-0.12, 0.80]` |
| Profit factor | `PF = 1.42 [1.05, 1.79]` |

**Regla:**
> Si el intervalo de confianza incluye el valor nulo (0 para diferencia, 1.0 para profit factor),
> el experimento es **inconcluyente**.

### 4.4 Validación temporal

Ningún experimento se evalúa solo en un período.

Se requiere **split temporal obligatorio**:

| Conjunto | Proporción | Uso |
|---|---|---|
| Train | 60-70% | Diseño y ajuste |
| Validation | 15-20% | Selección de candidatos |
| Test | 15-20% | Evaluación final **solo se mira una vez** |

**Regla:**
> El conjunto de test es sagrado.
> No se usa para ajustar parámetros.
> No se usa para elegir entre modelos.
> Solo se usa para veredicto final.

Si el resultado en test difiere del resultado en train en más de un margen tolerado:
- El experimento es **inconcluyente**.
- Se investiga sobreajuste.

### 4.5 Walk-forward

Para experimentos con parámetros o ventanas temporales:

- Se requiere al menos **un ciclo walk-forward**.
- El ciclo divide la historia en ventanas móviles.
- Cada ventana entrena en datos pasados y prueba en datos futuros inmediatos.
- La métrica final es el promedio de las ventanas de prueba.

**Regla:**
> Si el resultado walk-forward difiere del resultado estático en más del 10% relativo,
> el experimento es **inconcluyente**.

### 4.6 Robustez

Todo experimento debe pasar al menos **tres** de estas pruebas:

| Prueba | Descripción |
|---|---|
| Perturbación de parámetros | Variar la condición en ±10% y verificar que el resultado se mantiene. |
| Stress period | Evaluar en períodos de alta volatilidad, baja volatilidad, tendencia y rango. |
| Bootstrap | Remuestrear los eventos 1000 veces y verificar que el winrate medio se mantiene. |
| Multi-activo | Repetir en al menos 2 activos distintos. |
| Multi-timeframe | Repetir en timeframes distintos (ej: M5, M15, H1). |

**Regla:**
> Si falla 2 o más pruebas de robustez, el experimento es **refutado**.
> No se promueve.
> Se archiva como conocimiento negativo.

### 4.7 Criterio de mejora mínima

Una condición no se promueve solo porque "funciona".
Debe demostrar que **agrega valor real al sistema**.

| Criterio | Valor mínimo |
|---|---|
| Mejora en winrate sobre baseline | +3 puntos porcentuales |
| Mejora en expectativa matemática | +10% relativo |
| Profit factor mínimo | > 1.3 |
| Mantenimiento de frecuencia | No reduce eventos en más del 50% |

**Regla:**
> Si la condición mejora una métrica pero empeora otra de forma significativa,
> el experimento es **inconcluyente**.
> El Laboratorio evalúa el sistema completo, no métricas aisladas.

### 4.8 Impacto sistémico

Una condición puede funcionar aislada pero dañar el sistema completo.

Se evalúa:
- ¿Cuántas condiciones existentes se ven afectadas?
- ¿Abre nuevas oportunidades o cierra las actuales?
- ¿Cambia la distribución de ganancias/pérdidas?
- ¿Introduce correlación no deseada?

**Regla:**
> Si el impacto sistémico es negativo o desconocido, el experimento es **inconcluyente**.
> No se promueve hasta que se mida el impacto completo.

---

## 5. Protocolo de verificación

Todo experimento debe seguir este protocolo antes de ser veredictado:

### 5.1 Pre-registro
- Hipótesis escrita en lenguaje humano.
- Diseño experimental definido antes de mirar los resultados.
- Métricas y criterios de aceptación fijados.

### 5.2 Ejecución ciega
- El experimento se ejecuta sin ajustes posteriores.
- No se modifican parámetros después de ver resultados parciales.
- No se elige el período más favorable.

### 5.3 Documentación
- Código del experimento guardado.
- Datos de entrada versionados o con checksum.
- Comandos exactos de ejecución.
- Resultados completos, incluyendo negativos.

### 5.4 Revisión por pares
- Otro agente revisa el experimento antes del veredicto.
- Verifica: causalidad, aislamiento, reproducibilidad, ausencia de look-ahead.

### 5.5 Veredicto
- **Promovido:** cumple todos los criterios.
- **Rechazado:** falsado por evidencia.
- **Inconcluyente:** datos insuficientes o resultados mixtos.
- **Refutado:** falló pruebas de robustez o significancia.

---

## 6. Reglas de falsación

### 6.1 Intento de falsación
- Todo experimento debe incluir un **intento explícito de demostrar que la hipótesis es falsa**.
- No basta con confirmar.
- Si el intento de falsación falla (la hipótesis sobrevive), gana credibilidad.

### 6.2 Múltiples intentos
- Una hipótesis debe sobrevivir a **al menos 3 intentos de falsación** en contextos distintos antes de ser promovida.

### 6.3 Falsación por contraejemplo
- Un solo contraejemplo bien documentado puede **refutar** una hipótesis.
- No se necesitan estadísticas para un contraejemplo válido.

---

## 7. Reproducibilidad

### 7.1 Condiciones de reproducibilidad
Todo experimento debe ser reproducible por otro agente usando:

- Datos de entrada con ruta y checksum.
- Código del experimento.
- Versión de dependencias.
- Comandos exactos de ejecución.
- Semilla aleatoria fija (si aplica).

### 7.2 Verificación de reproducibilidad
- Antes del veredicto, se ejecuta el experimento en un entorno limpio.
- Si los resultados difieren en más del margen tolerado:
  - El experimento es **inconcluyente**.
  - Se investiga la fuente de variabilidad.

---

## 8. Tamaño de muestra y poder estadístico

### 8.1 Cálculo previo
Antes de ejecutar, se calcula el **tamaño de muestra necesario** para detectar la mejora esperada.

| Mejora esperada | Eventos mínimos |
|---|---|
| +5% winrate | 1,200 eventos |
| +10% winrate | 400 eventos |
| +20% winrate | 150 eventos |

### 8.2 Poder estadístico
- Se requiere un poder estadístico de **80%**.
- Si el poder es menor, el experimento es **inconcluyente** aunque el resultado sea positivo.

### 8.3 Eventos insuficientes
- Si no se alcanzan los eventos mínimos, el experimento se marca como **inconcluyente**.
- No se promueve.
- No se descarta.
- Se archiva para revisión futura.

---

## 9. Validación temporal y sobreajuste

### 9.1 Detección de sobreajuste
- Comparar train vs test.
- Si la diferencia en winrate es mayor a 10 puntos porcentuales: **sobreajuste probable**.
- Si el profit factor en test es < 1.0 aunque en train sea > 1.5: **sobreajuste probable**.

### 9.2 Walk-forward obligatorio
- Para cualquier condición con parámetros optimizados.
- Mínimo 3 ventanas walk-forward.
- Promedio de ventanas de prueba como métrica final.

### 9.3 Validación cruzada temporal
- Para experimentos sin parámetros: validación cruzada por bloques temporales.
- 5 bloques como mínimo.
- Cada bloque es un período continuo sin solapamiento.

---

## 10. Pruebas de robustez obligatorias

Todo experimento promovido debe pasar al menos **3 de 5** pruebas:

| Prueba | Criterio de aprobado |
|---|---|
| Perturbación ±10% | Resultado se mantiene en al menos 6 de 10 perturbaciones. |
| Stress period | Resultado en cada régimen (tendencia, rango, alta/baja volatilidad) no cae por debajo del baseline. |
| Bootstrap 1000 | Intervalo de confianza del bootstrap no incluye el valor nulo. |
| Multi-activo | Resultado positivo en al menos 2 de 3 activos. |
| Multi-timeframe | Resultado positivo en al menos 2 timeframes. |

---

## 11. Criterios de descarte y revalidación

### 11.1 Descarte inmediato
Una hipótesis se descarta si:

- Falsada por contraejemplo.
- p-valor > 0.05 y muestra insuficiente para aumentar poder.
- No pasa 2 o más pruebas de robustez.
- Introduce look-ahead o contaminación de datos.

### 11.2 Revalidación obligatoria
Una hipótesis promovida debe **revalidarse** cuando:

- Han pasado **12 meses** desde la última validación.
- El mercado cambia de régimen detectado (ej: volatilidad promedio cambia >30%).
- La frecuencia del escenario cae más del 40% respecto a la validación original.
- Se agrega una nueva condición al Edificio que pueda interactuar.

**Regla:**
> Ninguna condición es permanente en el Edificio.
> Todas deben volver al Laboratorio periódicamente para demostrar que siguen siendo válidas.

### 11.3 Archivo con trazabilidad
Todo experimento archivado debe conservar:

- Hipótesis original.
- Diseño experimental.
- Resultados completos.
- Veredicto y razones.
- Enlace al experimento que lo validó (si fue promovido alguna vez).

---

## 12. Métricas y su interpretación

### 12.1 Win rate
- **No es la métrica principal.**
- Es un indicador, no un veredicto.
- Se interpreta junto con expectativa matemática y profit factor.

### 12.2 Expectativa matemática
- **Es la métrica principal.**
- Fórmula: `EM = (WR × Ganancia promedio) - (LR × Pérdida promedio)`
- Debe ser positiva y estadísticamente distinguishable de cero.

### 12.3 Profit factor
- Complementario a la expectativa matemática.
- Mide la relación entre ganancia total y pérdida total.
- Debe ser > 1.3 para promoción.

### 12.4 Frecuencia
- No basta con tener un profit factor alto con 10 eventos.
- Se requiere una frecuencia mínima viable para que el sistema sea sostenible.

### 12.5 Robustez temporal
- La consistencia en train/test/walk-forward es más importante que el valor absoluto en un solo período.

---

## 13. Prohibiciones explícitas

El Laboratorio **nunca** debe:

- Usar información futura (look-ahead).
- Modificar parámetros después de ver los resultados.
- Elegir el período más favorable para reportar.
- Promover una condición basada solo en observación sin aislamiento.
- Ignorar resultados negativos.
- Eliminar eventos del dataset sin documentar la razón.
- Mezclar conjuntos de train y test.
- Reportar solo métricas positivas ocultando negativas.

---

## 14. Trazabilidad

Todo conocimiento promovido al Edificio debe conservar un enlace permanente al experimento que lo validó.

```yaml
condicion: "martillo_m15_confirmatorio"
promovido_en: "EXP-003"
validado_por: "datos_2008-2026_train_test_walkforward"
evidencia: "WR +5.2%, EM +0.41, PF 1.58, p=0.02, n=240"
revalidar_en: "2027-08-04"
estado: "vigente"
```

**Regla:**
> Cualquier vigilante, regla o condición del Edificio debe poder responder:
> 1. ¿Qué experimento lo creó?
> 2. ¿Con qué datos fue validado?
> 3. ¿Cuál fue la evidencia estadística para promoverlo?

---

## 15. Evolución de este documento

Este documento es **fundacional**.

No se modifica por preferencias.
No se modifica por urgencia.
No se modifica por resultados negativos.

Solo se modifica cuando:
1. Se descubre una falla estructural en los criterios.
2. Se demuestra que un criterio existente es insuficiente o incorrecto.
3. Se aprueba un cambio por evidencia, no por opinión.

Cualquier modificación pasa por el mismo tribunal que evalúa experimentos.

---

## 16. Resumen del tribunal

| Criterio | Umbral | Aprobado si |
|---|---|---|
| Muestra mínima | 60-100 eventos | Se alcanza |
| Significancia | p < 0.05 | Se cumple |
| Intervalo de confianza | 95% | No incluye valor nulo |
| Validación temporal | Train/Val/Test | Resultado consistente |
| Walk-forward | ≥ 3 ventanas | Promedio mantiene mejora |
| Robustez | ≥ 3 de 5 pruebas | Pasa |
| Mejora mínima | WR +3%, EM +10% | Se cumple |
| Impacto sistémico | No negativo | Evaluado y aceptable |
| Reproducibilidad | Verificada | Confirmada |
| Falsación | ≥ 3 intentos | Hipótesis sobrevive |

Si **todos** los criterios se cumplen → **Promovido**.
Si **uno solo** falla → **Inconcluyente o Refutado**.
Nunca se promueve por mayoría.
Nunca se promueve por intuición.
Solo se promueve por evidencia.

---

## 17. Próximos pasos

Una vez aprobado este documento:

1. Definir la plantilla `EXP-XXX.md` que obligue a reportar todos estos criterios.
2. Implementar `experiment_runner.py` que calcule automáticamente: muestra, p-valor, intervalos, walk-forward, robustez.
3. Diseñar EXP-001 con este tribunal desde el día uno.

---

*Última actualización: 2026-08-04*
*Estado: Documento fundacional. Pendiente de aprobación humana.*
