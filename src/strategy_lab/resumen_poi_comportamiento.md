# Resumen — COMPORTAMIENTO del POI en la fase de freno

> **Fecha:** 2026-08-03. **Datos:** M15 real, spot FX con tick_volume (SMC-SYSTEMS).
> **Pares:** AUDUSD, EURUSD, GBPUSD, NZDUSD, USDCAD, USDCHF, USDJPY.
> **Código:** `src/strategy_lab/poi_behavior.py` + `scripts/run_poi_behavior_experiment.py`.
> **Foco:** el POI como CONTEXTO de la fase 1 (freno). NO es winrate: eso se
> mide al final de la cadena (freno → K/D → señal).

Hipótesis del usuario:
1. El POI es bueno por el % de rebotes que consigue.
2. Cuánto hay que esperar para un freno verdadero.
3. Después de una caída estrepitosa, el POI puede aguantar.
4. El POI puede ser atravesado y volver a usarse para la dirección contraria
   (lo que fue piso puede ser techo y viceversa).

---

## Definiciones

- **Toque direccional:** vela que cruza la banda del POI llegando desde fuera
  (cierre previo > techo → POI como piso; < piso → POI como techo). Cada vela
  cuenta UNA vez (asignada al nivel más cercano).
- **Rebote:** en ≤5 velas el precio se aleja ≥5 pips sin antes cerrar ≥5 pips
  del otro lado del borde.
- **Break:** en ≤5 velas el precio cierra ≥5 pips más allá del borde opuesto.
- **Neutro:** ni rebote ni break en 5 velas.
- **Freno REAL (H2):** impulso de ≥5 pips (15 velas) que muere (detector
  estricto, no el laxo del laboratorio).
- **Caída estrepitosa (H3):** |impulso previo de 15 velas| ≥ percentil 75 del par.
- **Flip (H4):** tras un break, retest del POI desde el otro lado → rebote en
  la dirección contraria (≤10 velas hasta el retest, ≤5 para el rebote).
- **POIs comparados:** swing causal (nivel tocado ≥2 veces, activo 100 velas —
  el POI del laboratorio) vs franjas de volumen A (≥60% POC) y B (VA 70%).

---

## Resultados — POI swing (el POI real del laboratorio)

| Par | Toques | Rebote | Break | Neutro | Freno ≤1 vela | Freno ≤3 | Fuerte | Débil | Oversh. fuerte | Oversh. débil | Flip |
|---|---|---|---|---|---|---|---|---|---|---|---|
| AUDUSD | 3,268 | 0.371 | 0.082 | 0.547 | 0.738 | 0.873 | 0.415 | 0.354 | 2.1 | 0.6 | 0.425 |
| EURUSD | 5,512 | 0.464 | 0.159 | 0.377 | 0.800 | 0.931 | 0.533 | 0.428 | 2.7 | 1.7 | 0.458 |
| GBPUSD | 3,849 | 0.427 | 0.131 | 0.442 | 0.759 | 0.900 | 0.546 | 0.396 | 2.2 | 1.2 | 0.393 |
| NZDUSD | 2,722 | 0.288 | 0.039 | 0.673 | 0.681 | 0.823 | 0.331 | 0.276 | 0.7 | 0.2 | 0.238 |
| USDCAD | 3,182 | 0.365 | 0.076 | 0.559 | 0.719 | 0.868 | 0.457 | 0.337 | 2.8 | 0.4 | 0.384 |
| USDCHF | 3,646 | 0.425 | 0.109 | 0.466 | 0.733 | 0.876 | 0.499 | 0.386 | 1.8 | 0.7 | 0.462 |
| USDJPY | 4,007 | 0.515 | 0.253 | 0.232 | 0.906 | 0.985 | 0.567 | 0.495 | 9.3 | 4.8 | 0.492 |
| **Prom.** | 3,741 | **0.408** | **0.121** | 0.471 | **0.762** | **0.894** | **0.478** | **0.382** | **3.1** | **1.4** | **0.407** |

(Overshoot en pips reales del par.)

## Resultados — franjas de volumen A y B

- Toques: 242–755 (MUY pocos: el precio casi siempre está DENTRO de la franja).
- Rebote: 0.29–0.56. **Break: 0.000 en los 14 casos.** Flip: no aplica.
- Las franjas (5–14% del precio) nunca se atraviesan en 5 velas: son
  **corredores**, no niveles.

---

## Respuestas a las 4 hipótesis

### H1 — ¿El POI sostiene el precio? SÍ, pero con matices

- El swing rebota **41%** de los toques y se deja atravesar **12%**. El 47%
  restante es indecisión (el precio toca y no hace nada notable en 75 min).
- **El swing SÍ es un nivel accionable:** se puede medir, se rompe de verdad y
  se puede gestionar. Ese es el POI que la fase de freno debe usar.
- **Las franjas de volumen gigantes NO son niveles:** nunca se atraviesan
  (break = 0 en todos los pares). Un nivel que no se puede romper no permite
  descarte, stop ni flip. Si se quiere POI de volumen, la banda debe ser de
  pips (15–30), no % del precio.
- NZDUSD es el par con peor comportamiento de POI (rebote 0.288); USDJPY el
  mejor (0.515).

### H2 — ¿Cuánto hay que esperar para un freno verdadero? CASI NADA

- El freno REAL (impulso ≥5 pips que muere) ya está en la vela del toque o la
  siguiente en el **76%** de los toques al swing (68–91% según el par); en ≤3
  velas en el **89%**.
- Implicación para la fase 1: **no hay que esperar**. Toque al POI y freno se
  co-confirman. Si el freno no aparece en ≤3 velas, ese toque no va a producir
  la señal — se puede descartar sin esperar más.

### H3 — ¿El POI aguanta una caída estrepitosa? SÍ — MEJOR que en calma

- El rebote con impulso fuerte previo supera al de calma en **los 7 pares**:
  promedio 0.478 vs 0.382 (**+9.6 puntos**). El POI es más confiable justo
  cuando el precio llega violento.
- El precio **hunde el nivel antes de rebotar**: overshoot fuerte promedio
  3.1 pips (2–3 en majors, 9.3 en JPY) vs 1.4 en calma.
- Implicación: el stop de la fase de freno **no puede ir pegado al nivel**.
  Necesita overshoot + margen (p. ej. overshoot promedio + 1-2 pips por par).

### H4 — ¿Piso roto se vuelve techo? SÍ, ~41% de las veces

- De los breaks del swing, el **40.7%** promedio produce un retest que rebota
  en la dirección contraria (24–49% según el par).
- Es un edge real pero NO mayoría: requiere confirmación extra (el cruce K/D
  de la fase 2 del edificio) antes de operar el flip.
- USDJPY (0.492) y USDCHF (0.462) son los mejores; NZDUSD (0.238) el peor.

---

## Implicaciones de diseño para la fase de freno (edificio)

1. **El POI operativo es el swing fino, NO la franja de volumen gigante.**
   Las franjas de 5–14% son corredores: sin break, sin stop, sin flip.
2. **Timing:** toque + freno se co-confirman en ≤3 velas (89%). La espera no
   aporta.
3. **Stop con margen:** overshoot fuerte promedio 3.1 pips en majors — el nivel
   no aguanta "justo", aguanta con un pequeño hundimiento.
4. **Flip como señal de contra-tendencia:** tras un break confirmado del POI,
   el retest tiene ~41% de flip exitoso — usable como contexto de la fase 2,
   nunca como señal directa.

## Pendientes

- Validar en dominio OTC (los 62 pares P1 con datos de Quotex, paginación
  profunda) — este experimento corrió en spot FX.
- Probar la franja de volumen con banda de pips (15–30) en vez de % del precio.
- El winrate de la cadena completa (freno + POI + K/D) queda para el final.
