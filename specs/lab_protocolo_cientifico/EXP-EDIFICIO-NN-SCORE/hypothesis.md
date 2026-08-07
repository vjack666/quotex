# EXP-EDIFICIO-NN-SCORE — Hipótesis

**Dominio:** REAL (features que el Edificio ya calcula + resolución de operaciones / proxy).  
**Tipo:** Descubrimiento (Art. 13). No integración al bot sin validación OOS clara + OK explícito.  
**Fecha diseño:** 2026-08-07  
**Estado:** LISTO PARA EJECUCIÓN HANDS-FREE

---

## Pregunta central

¿Un modelo (LightGBM / equivalente tabular) entrenado solo con features que el Edificio **ya produce** mejora el ranking o el win-rate OOS respecto al score actual del Edificio?

## Hipótesis formales

### H1 — El modelo mejora el ranking OOS
El AUC (o average precision) del modelo en TEST temporal es significativamente superior al AUC del score actual del Edificio sobre los mismos candidatos.

### H2 — El modelo mejora el win-rate en el top-k OOS
Si se opera solo el top 20 % / 30 % de candidatos ordenados por el modelo, el win-rate OOS es superior al win-rate del Edificio sin filtro de modelo (o al top-k del score actual), con IC95% del lift que no incluye 0.

### H3 — El modelo está calibrado
Cuando el modelo asigna probabilidad ≈ p, la frecuencia real de WIN en OOS está dentro de una banda razonable de p (calibration plot / ECE no degradado vs score actual).

## Qué NO se prueba

- No se reintroduce la hipótesis H2 de EXP-POI-STOCH (separación excesiva → retrace) como feature prioritaria tras quedar refutada en OOS.
- No se buscan secuencias mágicas nuevas desde cero.
- No se modifica el código de producción del Edificio.
- No se usa volumen (no disponible de forma fiable en Quotex).

## Features permitidas

Solo las que el Edificio / zone_strength / estocástico **ya calculan** en runtime, por ejemplo:
- score / zona strength / efficacy / line_thickness / impact_velocity
- K, D, |K-D|, sticky flags, cruces, separación
- freno / range contraction flags si existen
- dirección, ATR relativo, session hour (si ya se usa)
- cualquier feature ya logueada en trades o en el pipeline de candidatos

Prohibido: features inventadas post-hoc a partir de resultados de EXP-POI-STOCH refutados.

## Target

- Preferido: resultado real WIN/LOSS de operaciones del Edificio (si hay log suficiente).
- Proxy aceptable: resolución limpia en N velas M15 (mismo criterio de clean usado en labs anteriores), documentado en protocol_frozen.

## Criterio de aceptación

- H1: AUC OOS modelo > AUC OOS score Edificio, con IC o test que no sea compatible con igualdad.
- H2: lift de win-rate en top-k OOS con IC95% del diff que no incluye 0, y n suficiente.
- H3: calibración no peor que el score actual (ECE o bandas).
- Si ninguna se cumple → REFUTADA / no aporta. Se archiva. No se integra.

## Alcance de datos

- Pares y periodo disponibles en el pipeline del Edificio / strategy_lab.
- Split temporal estricto (nunca random). Documentar fechas o índice de corte.
- Mínimo de eventos: documentar; si n_train < 500, declarar potencia baja y tratar resultados como exploratorios.
