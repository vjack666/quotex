# EXP-POI-STOCH — Riesgos y mitigaciones

## R1 — Definición subjetiva de “POI de calidad”
**Riesgo:** El trader identifica POIs visualmente; el detector automático puede generar zonas distintas.  
**Mitigación:** Usar la lógica ya existente de `zone_strength` / clustering de toques + bounce rate de 3 días M15. Fijar umbral mínimo de efficacy/grosor y documentarlo en protocol_frozen. No ajustar a ojo después de ver resultados.

## R2 — Data snooping en umbrales de “saludable” vs “excesivo”
**Riesgo:** Elegir el rango de |K-D| mirando el resultado.  
**Mitigación:** Definir candidatos de umbral a priori (percentiles o valores fijos: sticky = |K-D| < 3 o 5 velas en extremo; excesivo = |K-D| > p80 o p90 de la distribución histórica). Solo un set de umbrales. FDR obligatorio.

## R3 — Look-ahead / leakage en detección de zona
**Riesgo:** Usar toques futuros para definir la zona.  
**Mitigación:** Zona se construye solo con velas anteriores al momento del retorno. El retorno se detecta en tiempo real (precio entra en banda ya definida).

## R4 — Overfit del modelo neuronal
**Riesgo:** La red memoriza ruido de pocos ejemplos.  
**Mitigación:** 
- Mínimo número de eventos (documentar si n < 300 → solo reglas, no NN).
- Split temporal estricto (no random).
- Regularización + early stopping + evaluación solo en OOS.
- Comparar siempre contra regla fija (H1/H2) como baseline.

## R5 — Pares / régimen no estacionario
**Riesgo:** El patrón funciona en 2023 y muere en 2025.  
**Mitigación:** Split OOS temporal obligatorio. Si no sobrevive OOS → refutada aunque TRAIN sea bonito.

## R6 — Confundir “me gusta el momento” con edge
**Riesgo:** El trader marca entradas que ya sabe que salieron bien (selection bias en ejemplos).  
**Mitigación:** El experimento no usa las dos capturas del usuario como labels. Solo busca el patrón de forma sistemática en todo el histórico. Las capturas sirven solo como especificación cualitativa del patrón buscado.

## R7 — Instrumento (sin volumen)
**Riesgo:** No se puede medir absorción real.  
**Mitigación:** Aceptado. El experimento es puramente geométrico + estocástico. No se reclama “energía Wyckoff”. Se documenta la limitación.

## R8 — Hands-free drift
**Riesgo:** El agente modifica umbrales o añade features al ver resultados intermedios.  
**Mitigación:** protocol_frozen.json se escribe ANTES de correr. Cualquier cambio posterior requiere nuevo EXP-ID. El script no tiene parámetros libres en runtime.
