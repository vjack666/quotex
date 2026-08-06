# Plan de trabajo — Laboratorio LAB-SEC (mañana)

> Estado de hoy (ya commiteado y pusheado a `origin/main`):
> - Fase 7 — motor de secuencia libre + eliminación de look-ahead: `f261c3a`
> - Tribunal versionado (`tribunal_v1.yaml` + 3 tests): `ad39dde`
> - Fase 4 — ranking LightGBM (no encontró señal promovible): `199851e`
>
> Pendiente:
> - FDR/Bonferroni (hueco detectado por revisor externo) — NO escrito todavía
> - Fase 5 — veredicto real del tribunal sobre firmas candidatas

---

## Regla del día (vigente)

Cada paso termina con:
1. corrida de verificación real (no resumen),
2. hash completo de `origin/main` para cotejo independiente desde el clon del usuario.

Nada de "confía en mí". Sin evidencia no hay promoción.

---

## DÓNDE QUEDAMOS (resumen honesto)

- Hipótesis del trader: "freno en POI + cruce de estocástico + martillo antes del cruce".
- El motor libre confirmó que martillo-antes-cruce rinde mejor que martillo-después.
- Fase 4 (LightGBM, solo rankea) NO encontró señal promovible: ninguna firma supera el
  baseline (0.534) con margen real Y n≥500.
  - Mejor candidata con n≥100: `extremo>freno>martillo>cruce` n=110, WR=0.582 (+4.8pp) — n<500.
  - Firma más grande (n=1713): WR=0.537 (+0.3pp) — ruido.
- 36 firmas distintas evaluadas → FDR obligatorio antes de promover.

---

## PASO 1 — Redactar el parche FDR (el hueco real)

- **Qué:** añadir sección `multiple_comparisons` (FDR / Bonferroni) a `tribunal_v1.yaml`
  y un paso en `promotion_gate.py` que ajuste los p-valores de las N firmas evaluadas
  antes del veredicto.
- **Por qué:** hoy se evalúan 36 firmas; por azar algunas caen "arriba". Sin FDR el
  tribunal promovería basura. Lo detectó el revisor externo.
- **Respeta §15** del `LAB_EVIDENCIA_CIENTIFICA.md`: todo cambio al tribunal se aprueba
  por evidencia, no opinión. Se muestra el diff al usuario para su OK antes de commitear.
  NO se mete solo.
- **Verificás:** diff del YAML + hash de commit para cotejo desde tu clon.

## PASO 2 — Fase 5: veredicto real sobre candidatas

- **Qué:** correr `promotion_gate.evaluate()` (ya existe) sobre las 9 firmas con n≥100,
  aplicando FDR del Paso 1.
- **Por qué:** es el tribunal ya aprobado haciendo su trabajo. No se inventa nada nuevo.
- **Resultado esperado (honesto):** casi seguro INCONCLUSIVE para todas. La firma más
  prometedora tiene n=110; el tribunal exige 500 para entrenar con confianza. Ninguna
  con n≥500 supera el baseline.
- **Verificás:** salida cruda de `promotion_gate` + conteo de veredictos.

## PASO 3 — Decisión sobre los datos (el nudo real)

Si el Paso 2 confirma "inconcluso por muestra", dos caminos (el usuario elige):

- **A) Aceptar** que la hipótesis NO es promovible con los datos actuales.
  Conclusión honesta, sin forzar.
- **B) Recolectar más datos:** ampliar ventana temporal o sumar más pares M15 para llevar
  las firmas prometedoras a n≥500.

Nota: correr más código no arregla falta de muestra. Es trabajo de recolección, no de ingeniería.

## PASO 4 — Documentar y cerrar con evidencia

- **Qué:** escribir Fase 5 + FDR en `BITACORA_EXPERIMENTOS.md`, commitear, pushear.
- **Verificás:** hash completo de `origin/main` para cotejo independiente
  (el ciclo que ya se cerró hoy).

## PASO 5 — Limpieza

- Borrar cualquier temporal en `%TEMP%` (`hermes-verify-*`).
- Confirmar que no queda nada sin trackear del laboratorio.
- NO tocar los 22 tests del runtime del bot (deuda ajena; `init.ps1` sigue rojo por eso,
  no por trabajo del laboratorio).

---

## Lo que se necesita del usuario antes de empezar

1. ¿Aprobar el orden (FDR primero → Fase 5 → decisión de datos)?
2. En Paso 3, si confirma "inconcluso": ¿camino A (aceptar) o B (recolectar más datos)?

Con esas dos respuestas se arranca y se conduce hasta el final sin micro-confirmaciones.

---

## Decisiones tomadas (se llenan mañana)

- Orden aprobado: ____ (SÍ / NO / ajuste: ___)
- Paso 3 si es inconcluso: ____ (A / B)
- FDR redactado y aprobado por §15: ____ (hash: ___)
- Fase 5 veredicto: ____ (PROMOVIDO / INCONCLUSIVE / REFUTADO)
- Hash final origin/main: ___
