# Hypothesis — EXP-040 (embudo del Edificio sobre EURUSD REAL)

> Plantilla: `docs/lab_templates/hypothesis.md`. Cumple `docs/LAB_CHARTER.md`
> (Art. 6 congelamiento, Art. 10 dominio). Experimento del laboratorio ya
> aprobado (feature 38). NO es nueva feature SDD: es uso del lab.

## Pregunta

¿Existe al menos una **firma de secuencia** (orden real de eventos
freno→extremo→cruce→separación→martillo) que, sobre datos EURUSD REAL,
tenga winrate estadísticamente superior al baseline Y edge NETO positivo
después de costo operacional?

Esto ataca el embudo roto de EXP-039 (40→2→0→0 en vivo): el problema no es
falta de señales, es embudo mal calibrado + edge bajo en promedio pero
POSITIVO en secuencias concretas.

## Dominio (Art. 10)

- **Cohorte**: EURUSD REAL (M15), HistData/SMC_ROOT. 114.237 velas 2022-2026.
- **TF**: M15.
- **Promoción**: SOLO para EURUSD REAL. No vale para OTC sin re-validación
  (ADR-002). El descubrimiento en REAL es candidato, no evidencia para OTC.

## H0 / H1

- **H0**: ninguna firma de secuencia supera WR > 0.53 con FDR controlado y
  n ≥ 100 en EURUSD REAL. (El embudo no es rescatable por secuencia.)
- **H1**: al menos una firma (orden freno→extremo→martillo→cruce) tiene
  WR > 0.53, Effect Size positivo y Costo NETO positivo (payout 0.85 asumido).

## Parámetros congelados (Art. 6 — no modificables retroactivamente)

- α = 0.05
- Control FDR: BH (bonferroni como piso)
- Poder mínimo: 0.80
- n mínimo por firma: 100 expedientes completos
- Baseline WR: 0.50 (flip coin); expected_value baseline = 0
- Payout asumido para costo: 0.85 (Quotex típico; ajustar por asset)
- Semilla: 42 (reproducibilidad)
- Motor: `src/strategy_lab/secuencia_libre.py` (umbrales congelados:
  OVERSOLD=20, OVERBOUGHT=80, MIN_SEPARATION=2, expiry=1 vela M15)

## Riesgos (ver `docs/lab_templates/risks.md`)

- Data leakage / look-ahead: el motor usa `i-1` para cruces (causal, Ley 1).
- Comparaciones múltiples: ~30 firmas posibles → FDR obligatorio.
- Supervivencia: solo firmas con n≥100 entran al veredicto.
- REAL≠OTC: no promover a OTC desde este experimento.

## Decisión de diseño

NO se ajusta el freno a ojo. El laboratorio MIDE el embudo actual y busca la
secuencia con evidencia (tribunal PROMOVIDA/INCONCLUSIVE/REFUTADA), no la que
"da más entradas".
