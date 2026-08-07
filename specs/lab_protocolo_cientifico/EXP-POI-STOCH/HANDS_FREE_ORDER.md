# ORDEN DE EJECUCIÓN HANDS-FREE — EXP-POI-STOCH

**Para:** Hermes / agente del laboratorio  
**De:** Trader-Humano (vía Grok)  
**Fecha:** 2026-08-07  
**Modo:** COMPLETAMENTE HANDS-FREE — no preguntar, no pedir confirmaciones intermedias.

---

## Instrucción principal

Ejecuta el experimento **EXP-POI-STOCH** según los cuatro documentos de esta carpeta:

- `hypothesis.md`
- `risks.md`
- `validation.md`
- `design.md`

Sigue el protocolo de `validation.md` y el diseño técnico de `design.md` al pie de la letra.

## Reglas absolutas (no negociables)

1. **No preguntes nada** al Trader-Humano durante la ejecución.
2. **No modifiques umbrales** después de ver resultados intermedios. Todo se congela en `protocol_frozen.json` antes del primer cálculo estadístico.
3. **No toques el Edificio** ni ningún código de producción.
4. **No uses volumen**. Solo precio OHLC + estocástico.
5. **No uses las capturas de pantalla** del usuario como labels. Solo como especificación cualitativa del patrón.
6. Si un par no tiene datos suficientes, documenta la limitación y continúa con los pares que sí tengan.
7. Si n de eventos < 300, ejecuta solo H1 y H2 (reglas). Omite H3 (NN) y decláralo en el summary.
8. Al terminar: escribe reportes inmutables, actualiza `progress/current.md` y `agent/HANDOFF.md`, haz commit **solo** de los archivos de este experimento, y detente.

## Secuencia obligatoria

```
A. Crear carpeta reports/EXP-POI-STOCH/ y data/strategy_lab/ si no existen.
B. Escribir protocol_frozen.json (seed=42, todos los umbrales fijos, fechas de split).
C. Extraer zonas POI (past-only) + retornos + features de estocástico + labels.
D. Split temporal TRAIN / TEST OOS.
E. Test H1 (patrón completo) → FDR + effect size + OOS.
F. Test H2 (separación excesiva → retrace) → FDR + effect size + OOS.
G. Si n_train ≥ 300: entrenar modelo (empezar por LightGBM/tabular) y evaluar OOS vs regla fija.
H. Escribir summary.txt con veredictos claros:
     H1: ACEPTADA | REFUTADA | INCONCLUSA
     H2: ACEPTADA | REFUTADA | INCONCLUSA
     H3: ACEPTADA | REFUTADA | INCONCLUSA | OMITIDA (n bajo)
I. Actualizar progress/current.md y agent/HANDOFF.md con el resultado.
J. Commit mensaje: "EXP-POI-STOCH: [veredicto corto]"
K. Parar.
```

## Criterio de parada

Cuando el summary.txt y los reportes estén escritos y el estado actualizado, la orden está cumplida.  
No generes más experimentos. No propongas EXP-076 ni cambios al bot.  
Espera nueva orden explícita.

## En caso de error fatal de datos

Documenta el error en summary.txt, marca el experimento como BLOQUEADO por datos, actualiza el HANDOFF y detente. No inventes datos ni imputes.

---

**Fin de la orden.**  
Ejecuta.
