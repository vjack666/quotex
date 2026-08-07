# Informe de Agentes — Edificio ↔ Wyckoff Fase A (fase R0–R3)

> Convención: cada agente escribe su parte. El líder (Hermes) compila y cierra.
> Sesión 2026-08-07. Solo se usa evidencia anclada (datos en disco, reporte inmutable).
> Reglas de oro (ADR-039): (1) Edificio NO se modifica para encajar en Wyckoff;
> (2) volumen NUNCA requisito.

---

## 1. Trader-Humano

Rol: dueño del objetivo final y del marco de mercado.

- **Cambio de dirección**: el objetivo final es usar el Edificio como detector/timing
  de la **Fase A de Wyckoff para binarias**. No construir otro sistema alrededor del
  ratio `move/vol`.
- **Decisión de método**: radiografiar primero QUÉ estructura precede a los aciertos
  del Edificio (WIN) y a sus fallos (LOSS); después —y solo después— preguntar si eso
  es Fase A de Wyckoff. Eso evita imponer la teoría al algoritmo (curve fitting
  conceptual).
- **Reglas de oro dictadas y exigidas**:
  1. El Edificio **NO se modifica** para encajar en Wyckoff. Wyckoff se usa para
     explicar/clasificar la estructura que el Edificio YA explota.
  2. Volumen **NUNCA será requisito** fundamental. Si aporta, es evidencia adicional,
     no dependencia.
- **Aprobó el SDD** de la feature `edificio_wyckoff_phasea` (requirements/design/tasks).
- **Delegó los roles a la IA** y pidió aviso "cuando consigas la estructura adecuada".

---

## 2. Scientist

Rol: hipótesis, método, interpretación.

- **Hipótesis (R0–R3)**: ¿qué estructura de precio (OHLC+tiempo) precede a los WIN
  del Edificio, y cómo difiere de la que precede a los LOSS?
- **Diseño**:
  - Caja negra Edificio (no se toca `src/`).
  - Señales ya etiquetadas en `src/strategy_lab/results/edificio_events.parquet`
    (columna `win`, `split` train/test = OOS natural).
  - Contexto OHLC M15 previo (ventana N=20 velas) de
    `data/strategy_lab/cohorte_real_eurusd/EURUSD_M15.parquet` (543k velas, spot).
  - Features SOLO OHLC+tiempo: tendencia, impulso, compresión, lucha estructural.
- **Resultado (N = 946 señales con ventana válida)**. Separadores WIN/LOSS por
  |Cohen d| en TEST/OOS:
  1. `compression_ratio` — compresión de rango (ratio rango primeras 5 / últimas 5). **El más fuerte.**
  2. `break_fail_rate` — fallos de ruptura (tocar extremo y cerrar adentro).
  3. `impulse_mean_range` — rango medio de la ventana.
  4. `overlap_sum` — solapamiento entre velas.
  5. `body_range_ratio` — cuerpo/rango.
  - En TRAIN aparecen también `impulse_mean_range`, `overlap_sum`, `wick_ratio`,
    `body_range_ratio`. **Compresión y fallo de ruptura aparecen en ambos lados**
    → no es ruido de muestra.
- **Interpretación**: el Edificio ya explota **compresión + lucha de precios**; eso es
  la traducción OHLC de la Fase A de Wyckoff (agotamiento post-impulso, lucha en
  rango, fallos de ruptura). Todo **sin volumen** → regla de oro sostenida.
- **Retracción honesta (disciplina del proyecto)**: EW-1 (`move/vol` en 6E) no halló
  lo buscado — el −0.52 es reversión mecánica MA(1) del ratio, no memoria Wyckoff.
  EW-1 bajó a investigación auxiliar (`lab_ew_brake_link.py`, paralelo). NO se pagó
  Databento.

---

## 3. Engineer / Implementer

Rol: código y ejecución.

- Creó `scripts/lab_phaseA_radiografia.py` (standalone, **sin imports del Edificio**).
- Bugs corregidos en runtime:
  - variable `wick` era array → `float()` ilegal (eliminada; se usó `wick_ratio`).
  - división por `rng == 0` (velas sin rango) → `safe_rng` con máscara NaN.
  - `body_range` duplicado → dejado solo el cálculo seguro.
- **No tocó `src/`** (Edificio congelado, R1 cumplido).
- Usó **solo datasets en disco** (EURUSD_M15, edificio_events). Sin red, sin compras.
- Reporte inmutable en `data/strategy_lab/ew_reports/PHASEA-RADIO/`
  (`result.json` + `summary.md` + `protocol_frozen.json`).

---

## 4. Reviewer / QA

Rol: verificación y Charter.

- Verificación **ad-hoc** (no suite green; los scripts del lab están fuera de pytest
  por diseño del Lab Charter):
  - `py_compile` OK; import limpio sin side-effects.
  - Ejecución real: `rc 0`, **sin warnings**, 946 señales, reporte generado.
  - `src/` intacto confirmado; datos en disco; volumen no requisito.
- Protocolo inmutable: `protocol_frozen.json` con hashes de datasets + script + entorno.
- Declaración Charter: **Sí**.
- Temps de diagnóstico creados y borrados; repo limpio de temporales.

---

## 5. Líder (Hermes)

Rol: coordinación y cierre.

- SDD `edificio_wyckoff_phasea` cerrado y **APROBADO** por Trader-Humano.
- `ADR-039` escrito (reglas de oro). Feature `id 39` registrada en `feature_list.json`
  (`spec_ready`, `sdd: true`).
- **R0–R3 ejecutados y verificados** (commit `f7f13fe`, en `origin/main`, 0 ahead/0 behind).
- **La estructura adecuada YA se consiguió**: compresión de rango + fallos de ruptura
  son los separadores de WIN/LOSS del Edificio, coherentes con Fase A de Wyckoff, sin
  volumen. Se avisa al Trader-Humano según lo pedido.

---

## 6. Addendum R4 — Mapeo estructural explícito a Fase A (ejecutado)

Rol: Scientist + Engineer (reporte `data/strategy_lab/ew_reports/PHASEA-R4/`).

- **Entregable 1 — Mapa evento→Wyckoff en OHLC puro** (`wyckoff_map.json`):
  PS=agotamiento inicial; SC=clímax+rechazo; AR=expansión contraria; ST=retorno+menor
  continuación; Spring/UT=falsa ruptura=fallo de ruptura+cierre adentro. Nada de volumen.
- **Entregable 2 — Phase_A_Score (0..7)** por señal, solo precio: agotamiento +
  compresión + solapamiento + fallos_ruptura + rechazo_extremos + reducción_continuación
  + cambio_régimen. Normalizado por **rank dentro de cada split** (sin look-ahead OOS).
- **Entregable 3 — Comparación WIN vs LOSS del Edificio** con ese score:
  - TEST/OOS: WIN=3.60 vs LOSS=3.46, **d=0.27**; %>4 WIN 6.5% vs LOSS 3.7%.
  - TRAIN: WIN=3.68 vs LOSS=3.40, **d=0.37**; %>4 WIN 32.8% vs LOSS 21.5%.
- **Veredicto honesto (falsación parcial)**: la estructura de Fase A SÍ está presente
  en los WIN (señal real, aparece en OOS y en ambos lados), pero la separación es
  **MODESTA** (d 0.27–0.37). El Edificio no es un detector limpio de Fase A; pesca algo
  de esa transición, pero no es su mecanismo dominante. No se descarta la hipótesis, pero
  tampoco se coronó. Esto protege contra el sobre-ajuste conceptual.
- Regla de oro cumplida: volumen NUNCA requisito; Edificio (src/) intacto; solo datos en disco.

---

## 7. Addendum R5 — Estructura independiente del Edificio (ejecutado)

Rol: Scientist (reporte `data/strategy_lab/ew_reports/PHASEA-R5/`). Diseño autorizado
por Trader-Humano: **NO mirar WIN/LOSS ni señal del Edificio**.

- **R5-A**: `Phase_A_Score` sobre **todo el mercado M15** (108.657 ventanas, solo OHLC+tiempo).
- **R5-B (trayectoria)**: autocorrelación del score lag1=**0.505**, lag2=0.22, lag3=0.16.
  El score es **persistente en el tiempo** → es un proceso/clúster, no vela aislada.
  Coherente con Wyckoff como secuencia (tendencia→agotamiento→lucha→compresión), no como
  "vela rara".
- **R5-C (consecuencia sin Edificio)**: retorno a 3 velas por tercil de score ≈ **0** en
  todos (bajo +2.5e-6, medio −1.9e-6, alto −8.7e-6); OOS (2ª mitad) también ≈0. La
  estructura **NO predice dirección ni expansión del mercado por sí sola**.
- **Ablation**: al quitar compression/overlap/break_fail la correlación con ruptura cae
  ~0.04–0.05; **ningún componente domina** → señal repartida y débil, no hay 2–3 piezas
  mágicas.
- **Veredicto (falsación útil)**: el `Phase_A_Score` tiene comportamiento propio
  (persistencia temporal) pero **NO genera edge direccional propio**. Lo que R4 vio fue
  correlación con *cuándo el Edificio acierta*, no con el movimiento del mercado. Esto
  confirma la arquitectura del Trader-Humano: **Wyckoff = contexto/filtro**, no gatillo ni
  generador de dirección. El siguiente paso real es R6 (cruzar contexto + Edificio).
- Regla de oro cumplida: sin volumen, sin Edificio, sin win/loss; caja negra intacta.

---

## 8. Addendum R6 — Contexto (Fase A) × Edificio: la matriz (ejecutado)

Rol: Scientist (reporte `data/strategy_lab/ew_reports/PHASEA-R6/`).

- Matriz: `Phase_A_Score` de la ventana M15 previa al `brake_time` (solo OHLC+tiempo, rank
  **por split** para no contaminar OOS) → terciles Fase A baja/media/alta → cruce con `win`
  del Edificio (946 señales).
- **TRAIN**: baja=27.0% · media=33.8% · alta=47.6% · chi²=21.46, p≈0.000 → pendiente
  creciente y significativa: el contexto Fase A SÍ filtra el timing del Edificio en muestra.
- **TEST/OOS**: baja=32.2% · media=43.3% · alta=43.3% · chi²=3.10, p≈0.54 → pendiente se
  aplana y NO es significativa. No es el filtro robusto 52/56/63 esperado.
- **Veredicto (falsación parcial)**: el efecto de filtrado existe en TRAIN pero **se degrada
  fuera de muestra**. No se descarta del todo (test sigue ligeramente creciente 32→43), pero
  **no es un filtro fiable** todavía. Confirma la disciplina del Trader-Humano: **NO meter el
  score dentro del Edificio**. El edge del Edificio no se explica ni se amplifica de forma
  robusta por la estructura de Fase A medida.
- Conclusión R0–R6: la estructura tipo Fase A es **contexto marginal y no robusto** del edge
  del Edificio. Wyckoff como "filtro duro" no se sostiene OOS con estos 7 componentes.
- Regla de oro cumplida: sin volumen; Edificio (src/) caja negra intacta.

---

## 9. Addendum R7 — Edificio como binaria: dirección + expiración (ejecutado)

Rol: Engineer + Scientist (reporte `data/strategy_lab/ew_reports/PHASEA-R7/`). OFFLINE, caja
negra intacta, **sin filtro Wyckoff**.

- El evento del Edificio ya trae `direction` (CALL/PUT) y `brake_time`. Se recalcula el win
  **desde el precio** con horizonte H fijo (1–5 velas M15), payout asumido 80% (OFFLINE, no
  dinero real). Break-even binario = 55.6% (payout 80%).
- **Cobertura**: solo **EURUSD** tiene M15 en disco (286 eventos: 205 train / 81 test). Los
  otros 5 assets del Edificio (AUDUSD, GBPUSD, NZDUSD, USDCAD, USDCHF, USDJPY) **no tienen
  precio en disco** → brecha de datos honesta, no se cambia de instrumento.
- **RESULTADO** (win rate / EV):
  - TRAIN: win_orig 37.1% · H1=44.9%(EV −0.19) · H2=48.8%(−0.12) · H3=48.8%(−0.12) ·
    H4=49.3%(−0.11) · H5=46.8%(−0.16)
  - TEST/OOS: win_orig 45.7% · H1=26.0%(−0.53) · H2=28.4%(−0.49) · H3=26.0%(−0.53) ·
    H4=29.6%(−0.47) · H5=27.2%(−0.51)
- **Veredicto (falsación clara de viabilidad binaria)**: el Edificio **NO es rentable como
  binaria**. El mejor caso (H4, train) llega a ~49% / EV −0.11; en TEST/OOS cae a 26–30% /
  EV −0.47..−0.53. El edge del Edificio **no es un edge de dirección binaria a horizonte
  fijo**. R10 (producción binaria) **DESCARTADO** para este dataset/horizontes. No es Wyckoff
  lo que lo arruina: la dirección no bate el break-even.
- Conclusión R0–R7: la rama "Wyckoff-como-filtro" es marginal/no robusta (R6) y el Edificio
  como binaria no es rentable (R7). Ambas líneas agotadas con evidencia.
- Regla de oro cumplida: offline; Edificio (src/) caja negra intacta; sin volumen; sin Wyckoff.

- **R4** — ✅ HECHO. Mapeo explícito + Phase_A_Score + comp WIN/LOSS.
- **R5** — ✅ HECHO (ver Addendum R7 arriba). Estructura independiente: persistente en el
  tiempo pero SIN edge direccional propio → Wyckoff = contexto/filtro, no gatillo.
- **R6** — ✅ HECHO (ver Addendum R8). Contexto × Edificio: filtra en TRAIN (27/34/48%) pero
  se degrada en TEST/OOS (32/43/43%, no significativo) → filtro MARGINAL y no robusto.
- **R7** — ✅ HECHO (ver Addendum R9). Edificio como binaria (EURUSD, offline, sin Wyckoff):
  win rate 44-49% train / 26-30% test, EV siempre <0 → NO rentable → R10 descartado.
- **Conclusión R0–R7**: ambas líneas (Wyckoff-filtro y Edificio-binaria) agotadas con evidencia.
  Decisión del Trader-Humano: archivar la rama o reenfocar (requiere OK).
