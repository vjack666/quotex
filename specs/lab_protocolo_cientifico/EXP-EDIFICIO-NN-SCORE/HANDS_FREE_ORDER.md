# ORDEN DE EJECUCIÓN HANDS-FREE — EXP-EDIFICIO-NN-SCORE

**Para:** Hermes / agente del laboratorio  
**De:** Trader-Humano (vía Grok)  
**Fecha:** 2026-08-07  
**Modo:** COMPLETAMENTE HANDS-FREE — no preguntar, no pedir confirmaciones intermedias.

---

## Instrucción principal

1. **Cierra primero** EXP-POI-STOCH: commit (sin push) de los archivos M1 pendientes (`scripts/lab_exp_poi_stoch_m1.py`, `reports/EXP-POI-STOCH/h2_m1_oos.txt`, `reports/EXP-POI-STOCH/m1_analysis.txt` y lo que falte del EXP). Mensaje: `EXP-POI-STOCH: cierre M1 H2 REFUTADA OOS`.

2. **Ejecuta** EXP-EDIFICIO-NN-SCORE según:
   - `hypothesis.md`
   - `risks.md`
   - `validation.md`
   - `design.md`

## Reglas absolutas

1. No preguntes nada al Trader-Humano durante la ejecución.
2. No modifiques features ni hiperparámetros después de ver OOS.
3. No toques código de producción del Edificio ni del bot.
4. No reintroduzcas como feature prioritaria la H2 de EXP-POI-STOCH (ya refutada en OOS).
5. Solo features de la whitelist (lo que el Edificio ya calcula/loguea).
6. Split temporal estricto. Métricas de decisión = OOS.
7. Reportar tablas con **IC95%** (Wilson o bootstrap) para rates y lifts.
8. Si n_train < 500 → declarar potencia baja; no forzar ACEPTADA.
9. Al terminar: summary con veredictos, actualizar progress/current.md y HANDOFF, commit **solo** archivos de este EXP, **sin push**, y parar.

## Secuencia obligatoria

```
A. Commit cierre EXP-POI-STOCH (M1) sin push.
B. Crear reports/EXP-EDIFICIO-NN-SCORE/.
C. Escribir protocol_frozen.json (seed, split, hyperparams, whitelist, target).
D. Extraer candidatos + features whitelist + labels.
E. Baseline score Edificio (AUC, WR, top-k) en TRAIN y TEST.
F. Entrenar LightGBM (o equivalente) solo en TRAIN.
G. Evaluar OOS: AUC, top-k WR, lift + IC95%, calibración.
H. summary.txt con H1/H2/H3 = ACEPTADA | REFUTADA | INCONCLUSA.
I. Actualizar progress/current.md y agent/HANDOFF.md.
J. Commit solo este EXP. Mensaje: "EXP-EDIFICIO-NN-SCORE: [veredicto corto]".
K. Parar. No integrar. No proponer más EXPs.
```

## Criterio de parada

Reportes escritos + estado actualizado + commit hecho → orden cumplida.  
Espera nueva orden explícita.

## Error fatal de datos

Si no hay candidatos/features/labels suficientes: documentar en summary, marcar BLOQUEADO por datos, actualizar HANDOFF y detener. No inventar datos.

---

**Fin de la orden.**  
Ejecuta.
