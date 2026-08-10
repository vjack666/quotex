# Progress — 2026-08-09 — CICLO-001: verificación NN del 74.6% + POI + visuales

## Sesión actual: CICLO-001 (EXP-NN-1, EXP-NN-2, EXP-POI, VISUAL-ESTRATEGIA)

**Estado: CERRADO** (entregados todos los artefactos pedidos por el Cliente).

### Hecho hoy
- **Reconstrucción del gate EXP-076/077** (estocástico FULL 14,3,3 + dirección extremo + válvula K/D ≥5 creciente + arcoíris 7-EMA [5,10,20,40,80,160,320]) sobre EURUSD OTC 60s (76.835 velas) con timing R12 (entry open[i+6] t+300s, exit close[i+21] t+1200s).
- **⚠️ El 74.6% del EXP-076 NO se reproduce** (mejor variante: n=530 WR 42% CALL; objetivo n=1962 WR 74.6%). Script original eliminado de disco; solo queda el reporte histórico. Documentado con transparencia.
- **EXP-NN-1 (red a ciegas, features crudas):** MLP/LGBM → WR 55-58% pero p no significativo (0.13-0.34). NO hay edge recuperable solo con velas crudas.
- **EXP-NN-2 (juez del gate, features del gate):** MLP 46.9% / LGBM 46.7% (p=1.0) — PEOR que azar, incluso top deciles. El gate no codifica edge persistente en test.
- **EXP-POI:** interacción gate×POI REAL y significativa — gate compuesto + entrada dentro de zona POI (swing causal) = **WR 71.1% (n=38) vs 47.2% fuera (n=532), p=0.0025**; con tol=3 pips → 84.2%; min_touches=3 → 81.8%. POI solo no aporta (50.0% vs 48.9%, ns). **Cautela: n=33-38 pequeño.**
- **VISUAL-ESTRATEGIA:** 7 PNG paso a paso de la estrategia (señal CALL real, WIN) en `reports/CICLO-001/VISUAL-ESTRATEGIA/`.
- Reporte completo: `reports/CICLO-001/REPORTE.md`.

### Herramientas instaladas (venv)
- matplotlib 3.11.1, scipy 1.18.0 (necesarias para los experimentos). numpy/pandas/sklearn/lightgbm ya estaban.

### Gotchas
- scipy 1.18: `stats.binom_test` renombrado a `stats.binomtest` (API nueva).
- PowerCell terminal: `*>` y `2>&1 | Out-File` intercalan stderr y corrompen el log (procesos Hermes paralelos escriben al mismo archivo). Leer resultados con `python -c` + npz o con `read` directo.
- `resolve_trade`: los timestamps del CSV son unix absolutos; el índice de la vela de entry/exit es `i + delta_seg//60` (velas contiguas perfectas, gaps=0), NO `ts//60`.

### Pendiente (propuesta para próxima sesión)
1. Validación OOS del hallazgo gate×POI (solo 53 días de datos; buscar más pares OTC o extender el CSV).
2. Intentar recuperar `hermes-verify-exp076.py` desde historial git para reproducir el 74.6% exacto.
3. Bloqueos de commit heredados de la sesión 08-08 (3 conflictos en `specs/lab_protocolo_cientifico/EXP-EDIFICIO-NN-SCORE/*.md`) — siguen sin tocar.

---

# Progress — 2026-08-10 — CICLO-002 + feature 40 (fábrica herramientas) + EXP-084

## Sesión actual: integración fábrica + validación spot + NN spot

**Estado: EN CURSO (EXP-084 delegado, corriendo en background)**

### feature 40 — fábrica de herramientas del Edificio (COMPLETA, verificada)
- Fases A-D construidas en `src/edificio_tools/` (evidence, registry, inspector, assembler, gate, governor, audit, promotion). 16→18 tests formales PASS.
- Gate enchufado al Edificio real (`edificio_contratacion.py`, momento CONTRATADO): ensamblador+inspector+gobernador+auditoría. Fail-safe por excepción. Edificio intacto en lógica de pisos.
- Push real: origin/main = `81089aa`.

### CICLO-002 — validación SPOT M15 REAL (COMPLETA, deuda documentada)
- Composición arcoíris+válvula K/D sobre EURUSD_M15 (543k) y XAUUSD_M15 (346k) REALES.
- Resultado: n=0 en ambos (válvula |K-D| creciente NO ocurre en M15 real). Conclusión honesta: NO EVALUADA por insuficiencia de señales en dominio REAL (R9).
- Diagnóstico: no es DESVIO (sweep 1-5 plano); es la geometría de la válvula.
- Reporte: `reports/CICLO-002/REPORTE_CICLO-002.md`. Push real: `ac7c1dd`.

### EXP-084 — redes neuronales sobre SPOT M15 REAL (COMPLETO, pusheado f65ae9e)
- Subagente científico lanzado; corrió el script (runtime 201s, 889k velas). El subagente NO escribió reporte ni commiteó; CEO terminó: escribió REPORTE_EXP-084.md y pusheó.
- Resultado: AUC test LightGBM 0.5206 (≈azar). WR global test 50.9% (base 50.87%). Por decil: top10=53.6% (p=0.84), top05=54.2% (p=0.35) — NINGUNO significativo vs breakeven 54%.
- DENTRO de POI (hallazgo perdido del CICLO-001): WR 51.8% global, top10 55.2% (p=0.13). FUERA POI 50.7%. Gap EN_POI-FUERA_POI ≈1.1pp (en OTC 60s era ~25pp). **El efecto POI se desvanece en M15 REAL.**
- Feature importances: dominan hour/atr/ret1/wicks; `arcoiris_stack`=6, `k_extremo`=0, `in_poi`=87 (bajo). Las herramientas del Edificio aportan ~0 en M15 real.
- Veredicto: NO hay edge aprendible por NN en SPOT M15 REAL con estas herramientas. Cierra deuda R9 con evidencia negativa (muestra 133k test), más fuerte que el "n=0" de CICLO-002.
- Archivos: `reports/CICLO-002/EXP-084/{exp084_nn_spot_m15.py, _raw_results.json, REPORTE_EXP-084.md}`.

### Estado final del ciclo 2026-08-10
- feature 40 (fábrica): COMPLETA, gate enchufado, 18 tests verdes. Push 81089aa.
- CICLO-002 (validación spot): COMPLETA, deuda R9 documentada. Push ac7c1dd.
- EXP-084 (NN spot M15): COMPLETA, evidencia negativa honesta. Push f65ae9e.
- Conclusión de mercado: la composición arcoíris+válvula K/D (y el efecto POI) es DOMINIO-OTC; no se transporta a M15 REAL. Promover a REAL requiere rediseñar la señal sobre M15.


### Notas de ejecución
- El tracker del sistema repite falsos "changed paths" de temp files ya borrados (hermes-verify-*). Ignorar; verificación real hecha con pytest (18 passed) y remoto confirmado.
- torch NO disponible; se usa LightGBM/MLP tabular (coherente con spec EXP-EDIFICIO-NN-SCORE).

---

# Diagnóstico black box 2026-08-10 (tarde) — 0 contratados

**Pedido Trader-Humano:** ¿por qué no se envían órdenes? ¿se puede saber si las señales hubieran sido WIN/LOSS?

### Por qué no se contrató nada hoy
- **Cuello P1→P2 (FRENO), dominante:** el brake_ok instantáneo (vela en formación) no se sostiene los hasta-15-min que exige la confirmación con vela M15 cerrada (EDIFICIO_BRAKE_CONFIRM_RATIO=0.7). Casi todos los candidatos mueren en "freno CANCELLED (se perdió el brake)".
- **Cuello P2→P3 (cruce limpio):** único confirmado XRPUSD_otc (ratio 0.63/0.60) quedó "sticky en P2" toda la tarde (|K-D|<3.0); el cruce limpio+separación 60s nunca ocurrió → 0 promociones a P3.
- La válvula K/D (EDIFICIO_P3_GATE_MODE="valvula", 08-08) sigue [NO ADOPTADO]: config en modo viejo cross_clean/cruce_limpio.
- Resultado: 0 CONTRATADO, 0 órdenes reales. Las 11 filas BUY del black box de hoy = tests pytest (tickets simulados OID-77/12345, OID-88/1, TICK123).

### Pendiente (aprobado por TH: "solo diagnóstico por ahora")
- Replay WIN/LOSS hipotético de las señales de hoy: extraer activo+ts del log (freno candidato/P2), traer velas M1 reales del broker (get_candles_deep), reconstruir dirección desde stoch M15, simular entrada a 900s. REQUIERE pausar el bot (Quotex = 1 sesión a la vez). Sin fecha comprometida.

---

# Feature 41 — Hub Operacional del Edificio (noche 2026-08-10) — DONE

**Cierre operativo del Edificio + Embudo + hot-reload silencioso.**

- Acceso directo `QUOTEX Web App.lnk` → launcher `scripts/launch_quotex_webapp.bat` → `python app.py`.
- Barrera REAL: `EDIFICIO_ALLOW_REAL=False` (PRACTICE por defecto); REAL solo con OK humano + credenciales. Verificado físicamente en hub: "Balance PRACTICE".
- Massaniello desde el inicio: `STAKE_MODE=massaniello` (no tras 1ra operación).
- Caja negra retención INFINITA (`RETENTION_DAYS=0`) + snapshot PISO_1 + `feature_stream` plano para RNA + tamaño medible de vela (`candle_size_ticks`/`candle_volume`) + account/monto Massaniello + estocástico/POI/freno.
- Verificación UI física: fix campos deshabilitados post-Detener (loadConfig en botToggle) + badge POI/extremo (p2_entry_extreme) en panel Edificio.
- **Embudo (nuevo):** pestaña en hub + endpoint `/api/funnel` que cuenta por piso (P1→P2→P3→CONTRATADO) y explica como profesor por qué se desechan los activos (freno, zona joven, POI). Verificado físicamente: 21 activos en P1 con dirección/payout/stoch/POI/razón.
- **Hot-reload silencioso (nuevo):** endpoint `/api/version` (mtime del index.html); el frontend sondea cada 15s y recarga SOLO cuando el usuario NO mira (`document.hidden || !document.hasFocus()`) → cero parpadeo, cero pestañeo, cero banner.
- 4 tests feature41 en verde. Commit 97debc6 (origin/main). F41 marcada `done` en feature_list.json; ROADMAP Fase 6 actualizado.

**Estado al cerrar:** hub corriendo (puerto 8094) recogiendo datos en DEMO. Bot vivo, Edificio con activos en P1. Cuenta REAL bloqueada.

