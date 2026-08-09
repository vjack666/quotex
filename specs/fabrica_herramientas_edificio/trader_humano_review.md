# Revisión trader-humano — fabrica_herramientas_edificio

## Veredicto
APROBADO

## Dictamen (lenguaje trader)
El spec formaliza correctamente: herramientas (evidencia, no orden), ensamblador,
inspector, gobernador, y el cambio conceptual clave — la unidad de decisión humana
es el CICLO, no el experimento aislado (R0). El orquestador congela el lote y
prohíbe re-ajuste adaptativo (R12); la matriz global sintetiza al cierre (R13).

Segunda corrección (esta sesión): faltaba formalizar el reporte individual por EXP
y su persistencia en Git. Ya incorporado:
- R14: cada EXP deja `EXP-NNN_reporte.md` en `reports/CICLO-XXX/EXP-NNN/` (evidencia
  primaria: hipótesis, config congelada, n, WR, OOS, timing, anomalías, conclusión
  DEL experimento). No se elimina por existir la matriz global.
- R15: tras cada EXP y tras la matriz, `git add`+`commit`+`push` con prefijo
  `EXP-NNN:` / `CYCLE-XXX:` para revisión externa en GitHub (incl. ChatGPT).
- R16: el ciclo NO se cierra (no hay matriz) si falta el reporte de algún EXP del
  lote, salvo error explícitamente registrado.

Esto conserva tu antigua orden (reporte .md por EXP + commit/push) y la nueva
arquitectura de ciclo. Tres niveles documentales: reporte individual = primaria,
matriz = secundaria, decisión humana = terciaria.

## Faltantes que exige el trader
Ninguno. El spec está completo para aprobar e iniciar el ciclo.

## Estado
APROBADO. Pendiente aprobación humana final (puerta SDD) para pasar spec_ready →
in_progress y ejecutar el lote EXP-076..080 como ciclo autónomo.
