# EXP-EDIFICIO-NN-SCORE — Riesgos y mitigaciones

## R1 — Overfit al score del Edificio
**Riesgo:** El modelo solo aprende a copiar el score actual.  
**Mitigación:** Comparar siempre modelo vs score Edificio en OOS. Si AUC/lift no superan al score, se declara “no aporta”.

## R2 — Leakage temporal
**Riesgo:** Features o labels usan información futura.  
**Mitigación:** Todas las features se calculan solo con datos ≤ timestamp del candidato. Label = resolución posterior. Split temporal por tiempo, no por shuffle.

## R3 — Poca muestra de trades reales
**Riesgo:** Si solo hay cientos de trades del Edificio, cualquier NN/boosting overfittea.  
**Mitigación:** 
- Preferir proxy de resolución sobre todos los candidatos (no solo trades ejecutados) si el log de trades es pequeño.
- Si n_train < 500 → solo modelo simple (o solo ranking lineal) y veredicto “exploratorio / INCONCLUSA por n”.
- Regularización fuerte + early stopping sobre validation temporal interna del TRAIN.

## R4 — Reintroducir hipótesis ya refutadas
**Riesgo:** Meter |K-D| excesivo u otras features de EXP-POI-STOCH como “mejora”.  
**Mitigación:** Lista blanca de features = solo las que el Edificio ya usa o loguea. Cualquier feature nueva requiere justificación y queda documentada; no se prioriza H2 refutada.

## R5 — Confundir correlación en TRAIN con edge operable
**Riesgo:** AUC alto en TRAIN, colapso en OOS.  
**Mitigación:** Métrica de decisión = solo OOS. Gap TRAIN−TEST se reporta; si gap > 0.08 en AUC, se señala sobreajuste.

## R6 — Integración prematura al bot
**Riesgo:** “Como la red dice 58 %, lo metemos al Edificio”.  
**Mitigación:** Este EXP es descubrimiento. Prohibido tocar código de producción. Cualquier integración requiere nuevo EXP de validación + OK explícito del Trader-Humano.

## R7 — Target proxy ≠ dinero real
**Riesgo:** Clean bounce en N velas no es exactamente WIN de binaria (expiry, payout, timing).  
**Mitigación:** Documentar el proxy. Si existen logs de trades reales con WIN/LOSS, usarlos como target principal y el proxy como secundario.

## R8 — Hands-free drift
**Riesgo:** Ajustar hiperparámetros o features después de ver OOS.  
**Mitigación:** protocol_frozen.json antes de entrenar. Un solo set de hiperparámetros predefinidos. Cambios = nuevo EXP-ID.
