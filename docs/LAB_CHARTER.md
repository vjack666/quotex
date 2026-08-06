# LAB_CHARTER — Constitución del Laboratorio

> Documento supremo del laboratorio. Jerarquía Nivel 1.
> Define únicamente principios que jamás pueden romperse.
> No explica procedimientos ni detalles de implementación.
> Léase en dos minutos.

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

---

## Cláusula de prevalencia

Si cualquier procedimiento, implementación o experimento entra en conflicto con
este Charter, el Charter prevalece y el procedimiento deberá modificarse antes
de continuar. No se admiten excepciones.

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

En caso de conflicto entre niveles, prevalece siempre el superior.
