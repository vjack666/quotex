# Laboratorio — Roadmap y Arquitectura del Motor Científico

> **Documento de respaldo oficial.**
> Aquí se registran todas las decisiones de arquitectura, aprobaciones y hoja de ruta del Laboratorio.
> Si la PC se apaga o se pierde el hilo, este documento es el punto de retorno.

**Estado:** Aprobado como documento de planificación. Pendiente de iniciar implementación.

---

## 1. Aprobaciones fundacionales registradas

| Documento | Estado | Fecha | Rol |
|---|---|---|---|
| `docs/LAB_MARCO_EXPERIMENTAL.md` | ✅ Aprobado como fundacional | 2026-08-04 | Filosofía y leyes del Laboratorio |
| `docs/AUDITORIA_CIENTIFICA_LABORATORIO.md` | ✅ Aprobado como fundacional | 2026-08-04 | Inventario de patrimonio científico |
| `docs/LAB_EVIDENCIA_CIENTIFICA.md` | ✅ Aprobado como fundacional | 2026-08-04 | Tribunal de evidencia y criterios de promoción |

**Regla:**
> Estos tres documentos son constituciones del Laboratorio.
> Cualquier cambio futuro debe ser una evolución motivada por evidencia, no una modificación de filosofía.

---

## 2. Principios rectores aprobados

1. **El Laboratorio descubre conocimiento.**
2. **El Edificio aplica únicamente conocimiento validado.**
3. **El motor de ejecución solo ejecuta.**
4. **El Laboratorio no crea estrategias; crea conocimiento.**
5. **Ninguna condición entra al Edificio sin evidencia reproducible.**
6. **El winrate no es suficiente; se requiere expectativa matemática, robustez, reproducibilidad e impacto sistémico.**
7. **Toda hipótesis debe sobrevivir a intentos de falsación antes de ser promovida.**
8. **Todo conocimiento promovido conserva enlace al experimento que lo validó.**

---

## 3. Arquitectura del motor científico

### 3.1 Componentes y responsabilidades

| Componente | Responsabilidad | Regla de diseño |
|---|---|---|
| `experiment_runner.py` | Orquestador puro | Solo coordina flujo. Sin lógica científica. |
| `evidence.py` | Cálculo estadístico | Solo cálculos. Sin reglas de decisión. |
| `robustness.py` | Pruebas de estrés | Solo ejecuta pruebas. Sin veredicto. |
| `baseline_manager.py` | Administración de baselines | Administra versiones, comparaciones, histórico. |
| `promotion_gate.py` | Tribunal declarativo | Interpreta criterios desde config. Sin umbrales hardcodeados. |
| `registry.py` | Memoria del Laboratorio | Conserva evidencia completa. No solo PASS/FAIL. |
| `EXP-XXX.md` | Contrato de experimento | Define hipótesis, datos, métricas, criterios, falsación, reproducibilidad. |

### 3.2 Decisiones de arquitectura

**`experiment_runner.py`**
- Responsabilidad única: coordinar el flujo de principio a fin.
- No contiene lógica estadística ni de decisión.
- Invoca módulos especializados (`evidence.py`, `robustness.py`, `promotion_gate.py`).
- Genera el informe final y registra el resultado.

**`promotion_gate.py`**
- No tiene reglas hardcodeadas.
- No lee `LAB_EVIDENCIA_CIENTIFICA.md` directamente.
- Consulta una representación estructurada del tribunal: `tribunal_v1.yaml` (o JSON).
- Esa configuración es generada desde `LAB_EVIDENCIA_CIENTIFICA.md`, pero el código nunca parsea Markdown.
- Si cambia un criterio científico, se actualiza el archivo de tribunal, no el código.
- Devuelve veredicto estructurado: `PASS` / `FAIL` / `INCONCLUSIVE` + lista de criterios fallidos.

**Flujo del tribunal:**
```
LAB_EVIDENCIA_CIENTIFICA.md  (documento humano)
          │
          ▼
tribunal_v1.yaml             (config estructurada, versionada)
          │
          ▼
promotion_gate.py            (interpreta criterios)
          │
          ▼
experiment_runner.py         (consulta y aplica)
```

**`EXP-XXX.md`**
- No copia criterios del tribunal.
- Solo indica la versión del tribunal y el baseline utilizados.
- Ejemplo:
  ```yaml
  tribunal:
    version: 1.0
  baseline:
    id: BASELINE-001
    version: 1.2
  ```
- Esto garantiza trazabilidad total: cualquier experimento puede reproducirse con la versión exacta del tribunal con la que fue evaluado.

**`registry.py`**
- No es un simple registro de PASS/FAIL.
- Almacena por experimento:
  - Hipótesis
  - Configuración
  - Dataset utilizado (con checksum)
  - Métricas completas
  - Resultados de robustez
  - Evidencia estadística
  - Informe final
  - Veredicto
- Es la memoria histórica del Laboratorio.

**`baseline_manager.py`**
- Componente nuevo, aprobado.
- Administra:
  - Baselines oficiales
  - Versiones de cada baseline
  - Comparaciones entre experimentos y baseline
  - Historial de reemplazos
- Todo experimento compara contra una referencia consistente y trazable.

### 3.3 Ubicación

- Todo el motor científico vive en `src/strategy_lab/`.
- Aislamiento total del motor de producción.
- No se modifica `src/` core del bot hasta que el motor esté estable.

---

## 4. Hoja de ruta de implementación

| Paso | Entregable | Descripción | Estado |
|---|---|---|---|
| 1 | `EXP-000.md` | Plantilla estándar de experimentos | Completado |
| 2 | `tribunal_v1.yaml` | Representación estructurada del tribunal | Completado |
| 3 | `evidence.py` + tests | Motor estadístico: muestra, p-valor, IC, walk-forward | Completado |
| 4 | `robustness.py` + tests | 5 pruebas de estrés sin veredicto | Completado |
| 5 | `baseline_manager.py` + tests | Administración de baselines oficiales | Completado |
| 6 | `promotion_gate.py` + tests | Tribunal declarativo, lee `tribunal_v1.yaml` | Completado |
| 7 | `registry.py` + tests | Memoria completa con trazabilidad | Completado |
| 8 | `experiment_runner.py` + tests | Orquestador puro + informe Markdown | Completado |
| 9 | `EXP-001` | Primer experimento real usando el motor completo | Pendiente |

**Nota:** los tests son obligatorios en cada paso. Sin tests no se avanza.

---

## 5. Criterios de éxito del hito

El Laboratorio se considera operativo cuando se cumplen **todos** estos criterios:

1. **`EXP-000.md`** aprobado como plantilla estándar.
2. **`experiment_runner.py`** ejecuta un experimento de punta a punta sin intervención manual.
3. **Todas las métricas del tribunal** se calculan automáticamente.
4. **Veredicto automático** coincide con veredicto humano en 3 experimentos de prueba.
5. **Registro automático** en catálogo con trazabilidad completa.
6. **Tests unitarios** para cada módulo (mínimo 80% coverage en `strategy_lab/`).
7. **Primer experimento oficial** (`EXP-001`) completado, veredicto emitido y registrado.

---

## 6. Decisiones pendientes

| Decisión | Opciones | Recomendación | Estado |
|---|---|---|---|
| Criterios del tribunal en `EXP-000.md` | Decisión tomada: tribunal centralizado y versionado | `EXP-000.md` solo indica versión del tribunal y baseline; `promotion_gate.py` lee `tribunal_v1.yaml` | Resuelto |
| Primer experimento | POI volumen / Patient waiting / Otro | Reutilizar caso existente | Pendiente de selección |

---

## 7. Próxima sesión — punto de retorno

Cuando se reinicie el trabajo:

1. Leer este documento para recuperar el contexto.
2. Verificar que `docs/LAB_MARCO_EXPERIMENTAL.md`, `docs/LAB_EVIDENCIA_CIENTIFICA.md` y `docs/AUDITORIA_CIENTIFICA_LABORATORIO.md` siguen siendo los documentos fundacionales.
3. Empezar por **Paso 1**: `EXP-000.md`.
4. Implementar en orden: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8.
5. No saltar pasos. No mezclar cambios en vivo con experimentos.

---

## 8. Referencias cruzadas

- Filosofía: `docs/LAB_MARCO_EXPERIMENTAL.md`
- Evidencia: `docs/LAB_EVIDENCIA_CIENTIFICA.md`
- Patrimonio: `docs/AUDITORIA_CIENTIFICA_LABORATORIO.md`
- Modelo cognitivo Edificio: `docs/agente-trader_humano.md`
- Reportes de auditoría: `docs/reportes de auditorias/`

---

## 9. Historial de cambios

| Fecha | Cambio | Autor |
|---|---|---|
| 2026-08-04 | Aprobación de ajustes arquitectónicos del motor científico | Usuario + Hermes Agent |
| 2026-08-04 | Decisión tribunal: `EXP-XXX.md` no copia criterios; usa `tribunal_v1.yaml` versionado | Usuario + Hermes Agent |
| 2026-08-04 | `EXP-000.md` y `tribunal_v1.yaml` creados; paso 1 completado | Hermes Agent |
| 2026-08-04 | Motor científico paso 1-7 completado: evidence/robustness/baseline/promotion/registry/runner + 29 tests verdes | Hermes Agent |

---

*Este documento es el respaldo oficial del plan de construcción del Laboratorio.*
*Cualquier desviación debe registrarse aquí antes de ejecutarse.*
