# LAB_CHARTER — Constitución del Laboratorio

> Documento supremo del laboratorio. Jerarquía Nivel 1.
> Define únicamente principios que jamás pueden romperse.
> No explica procedimientos ni detalles de implementación.
> Léase en dos minutos.

---

## Ámbito de aplicación

Este Charter aplica a:

- todo experimento (EXP-XXX);
- todo SPEC (`specs/*`);
- todo cambio metodológico;
- todo pipeline de validación;
- toda promoción de hipótesis al Edificio.

No aplica a tareas puramente operativas o de ingeniería que no alteren la
metodología científica.

---

## Artículos

**Artículo 1 — Objetivo**
El objetivo del laboratorio es descubrir evidencia estadísticamente reproducible, no optimizar resultados históricos.

**Artículo 2 — Refutabilidad**
Toda hipótesis debe poder ser refutada.

**Artículo 3 — Promoción por evidencia**
Toda promoción al Edificio requiere evidencia estadística (significancia, reproducibilidad, robustez). Ninguna hipótesis se promueve por una sola métrica ni por resultados favorables.

**Artículo 4 — Datos inmutables**
Los datos nunca se alteran. El código nunca modifica la evidencia.

**Artículo 5 — Reproducibilidad**
Toda evidencia debe ser reproducible por cualquier agente del proyecto con los mismos insumos.

**Artículo 6 — Congelamiento**
El protocolo (hipótesis, métricas, α, FDR, poder, n mínimo, dataset) se congela antes de ejecutar el experimento y no puede modificarse retroactivamente.

**Artículo 7 — Registro de decisiones**
Toda decisión metodológica queda registrada de forma permanente.

**Artículo 8 — No excepciones**
Ningún resultado favorable justifica romper este Charter.

**Artículo 9 — Control de falsos positivos**
El laboratorio debe controlar explícitamente el riesgo de falsos positivos al
evaluar múltiples hipótesis (corrección FDR/Bonferroni obligatoria antes de
promover).

**Artículo 10 — Dominio experimental**
Una hipótesis solo puede promocionarse para el dominio donde obtuvo evidencia
(REAL ≠ OTC ≠ Crypto ≠ Índices ≠ timeframes). La evidencia en un dominio no
transfiere a otro. EURUSD REAL es entorno de descubrimiento; la validación
final de candidatos para OTC debe realizarse sobre datos OTC recolectados por
el propio sistema.

**Artículo 11 — Parsimonia**
Entre dos hipótesis con evidencia equivalente, el laboratorio promoverá siempre
la más simple. Se rechazan modelos innecesariamente complejos.

**Artículo 12 — Muerte definitiva**
Una hipótesis refutada en tres datasets independientes queda archivada de forma
definitiva y no vuelve a experimentarse sin una propuesta metodológica nueva
(ADR o SPEC dedicado).

---

## Cláusula de prevalencia

Si cualquier procedimiento, implementación o experimento entra en conflicto con
este Charter, el Charter prevalece y el procedimiento deberá modificarse antes
de continuar. No se admiten excepciones.

Todo experimento que viole el Charter será considerado **inválido**,
independientemente de sus resultados estadísticos.

---

## Reforma del Charter

El Charter solo puede modificarse mediante una propuesta metodológica explícita
(ADR o SPEC dedicado), revisión del trader-humano y aprobación humana.

No puede modificarse como parte de una feature funcional ni mediante un commit
directo a este archivo.

---

## Jerarquía documental

```
LAB_CHARTER.md        (Nivel 1 — principios inquebrantables)
      │
      ▼
docs/specs.md         (Nivel 2 — manual operativo del SDD, subordinado al Charter)
      │
      ▼
specs/<feature>/      (Nivel 3 — SPEC de cada feature, cumple el Charter)
      │
      ▼
EXP-XXX               (Nivel 4 — experimentos, declaran cumplimiento del Charter)
```

Índice completo de documentos científicos: `docs/LAB_INDEX.md`.

En caso de conflicto entre niveles, prevalece siempre el superior.
