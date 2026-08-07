# EXP-EDIFICIO-NN-SCORE

¿Un modelo tabular (LightGBM) sobre features **ya existentes del Edificio** mejora el ranking / win-rate OOS respecto al score actual del Edificio?

## Documentos

| Archivo | Contenido |
|---------|-----------|
| `hypothesis.md` | H1 ranking, H2 top-k WR, H3 calibración |
| `risks.md` | Overfit, leakage, n bajo, no reintroducir H2 refutada |
| `validation.md` | Protocolo, criterios, hands-free |
| `design.md` | Pipeline, whitelist, métricas, outputs |
| `HANDS_FREE_ORDER.md` | Orden directa: cerrar POI-STOCH M1 + ejecutar este EXP |

## Relación con EXP-POI-STOCH

POI-STOCH refutó el patrón visual POI+estocástico como edge robusto OOS.  
Este experimento **no** reutiliza esa hipótesis. Solo repondera lo que el Edificio ya calcula.

## Estado

Diseño listo. Pendiente de ejecución hands-free.
