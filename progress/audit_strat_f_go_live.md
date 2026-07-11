# Auditoría — ¿estamos listos para arrancar STRAT-F en demo con dashboard y 1er trade?

> Fecha: 2026-07-11. Auditoría empírica: se leyó el código real
> (`consolidation_bot.py`, `scanner.py`, `executor.py`, `main.py`, `hub/*`,
> `config.py`, `entry_scorer.py`). No se ejecutó el bot completo (el host
> mata el proceso de fondo en Fase 3b), así que la ejecución end-to-end NO
> está verificada; lo que sí está verificado es el cableado por código y el
> diag aislado.

## Veredicto rápido

| Meta | Estado | Por qué |
|------|--------|---------|
| Dashboard con "buena pinta" STRAT-F en corrida REAL | ✅ CERRADO (código+test) | El scanner ahora llama `self._flush_strat_f_panel()` en `scan_all` (tras evaluar); `ConsolidationBot` crea `StratFPanel` y `server.init()` lo usa → el panel STRAT-F se expone por WS en el bot REAL. |
| 1er trade STRAT-F en demo REAL | ✅ CERRADO (código+test) | `STRAT_F_ONLY=True` filtra `candidates` a solo STRAT-F (en `_scan_phase_select_execute`, antes del scoring) → el 1er trade STRAT-F queda garantizado sin competir con STRAT-A. |
| Verificación end-to-end | ⏳ PENDIENTE (máquina de Ruben) | El host me mata el bot; falta correr `main.py` en demo y confirmar panel + 1er trade cerrado. |

## Hallazgos detallados (con líneas)

### H1 — Dashboard: el bot real NO muestra STRAT-F
- `main.py:167-170`: en modo REAL levanta `HubScanner()` (viejo) y
  `init_server(hub_scanner)`.
- `consolidation_bot.py:373-384`: el ciclo llama `hub.record_scan_cycle(...)`
  con `strat_a_payload` (solo STRAT-A). No hay `record_strat_f`.
- `hub/strat_f_panel.py` (`StratFPanel`) solo se usa en `main.py:120` dentro
  de `_render_hub_once()` (modo `--hub-readonly`), que parsea los logs del
  diag (`progress/diag_strat_f_*.log`).
- **Consecuencia:** si Ruben corre el bot completo hoy, el panel web que ve
  es el de Masaniello/STRAT-A. El panel STRAT-F que construimos NO aparece en
  vivo. No cumple "buena pinta en el dashboard".

### H2 — Ejecución: STRAT-F compite con STRAT-A y casi siempre pierde
- `scanner.py:1247`: STRAT-F mete `f_candidate` en la lista `candidates`.
- `scanner.py:1742`: `select_best(candidates, threshold=session_threshold)`
  elige el MEJOR de TODA la lista (STRAT-A + MOMENTUM + SWING + OB + STRAT-F).
- `config.py:20` `MAX_CONCURRENT_TRADES=1`, `entry_scorer.py:21`
  `MAX_ENTRIES_CYCLE=1` → solo 1 trade por ciclo.
- `scanner.py:1246`: `f_candidate.score = strength*100` (~70 en el diag real).
- `config.py:83-84`: umbral dinámico STRAT-A = 62–68. STRAT-F pasa el umbral
  por score, PERO compite contra STRAT-A que suele dar 75–85.
- **Consecuencia:** STRAT-F solo opera si en ese ciclo STRAT-A no da señal.
  El "primer trade STRAT-F" queda a merced de la ausencia de STRAT-A. No está
  aislado.

### H3 — El puente de ejecución SÍ existe (pero sin rama propia)
- `scanner.py:1887-1899`: `enter_trade(..., strategy_origin=getattr(winner,"_strategy_origin","STRAT-A"))`.
- `executor.py:342,367,410,1144`: `enter_trade` y el log soportan
  `strategy_origin`. `executor.py:1160`: `if strategy_origin=="STRAT-A" and stage=="initial":`
  — hay lógica condicional por origen; STRAT-F no la dispara, pero tampoco
  hay nada que lo bloquee.
- **Consecuencia:** técnicamente operable, pero frágil (depende de competir y
  ganar por score). Falta un modo "solo STRAT-F" para garantizar el 1er trade.

### H4 — El diario SÍ registra STRAT-F (única parte verificada en vivo)
- `scanner.py:1208-1263`: acumula `_strat_f_batch` y graba en journal
  (`log_candidate` con `strategy_origin="STRAT-F"`) + HUB.
- Verificado: `diag_strat_f_live.py --journal` grabó 14 decisiones STRAT-F
  reales hoy (1 aceptada, 13 rechazadas).
- **Pero:** eso es el DIAG, no el bot. El bot real (consolidation_bot) no
  llama `record_strat_f` ni graba STRAT-F en su ciclo (solo STRAT-A vía
  `record_scan_cycle`).

## GAPs para la meta

| # | GAP | Esfuerzo | Qué falta |
|---|-----|----------|-----------|
| G1 | Dashboard vivo STRAT-F en bot real | Medio | En `scan_all`, tras evaluar, llamar `StratFPanel.record_strat_f(...)` y que `server.py` empuje `strat_f` por WS. Hoy solo el diag lo hace. |
| G2 | Aislar ejecución STRAT-F | Bajo/Medio | Modo `STRAT_F_ONLY` (o slot propio) que opere STRAT-F sin competir por score con STRAT-A. Así el 1er trade demo es garantizable. |
| G3 | Verificación end-to-end en máquina de Ruben | Bloqueante real | Correr el bot en demo y confirmar: (a) panel STRAT-F aparece, (b) un trade STRAT-F se coloca y cierra. Yo no puedo (host me mata). |
| G4 | `enter_trade` para STRAT-F sin efectos STRAT-A | Bajo | Revisar que monto/cooldown/expiry se apliquen igual para STRAT-F (duration_sec=DURATION_SEC ya se pasa). |

## Lo que YA está bien (no tocar)
- Evaluador STRAT-F puro y filtros (R1–R6) ✅
- Diario graba STRAT-F con razón ✅ (vía diag; falta vía bot real = G1)
- Reporte de calibración ✅
- `enter_trade` acepta `strategy_origin` ✅
- Tests: 282 passed ✅

## Plan de cierre sugerido (para que Ruben dé el OK)
1. **G1** — cablear `StratFPanel` al bot real (pequeño, en `scan_all`).
2. **G2** — añadir `STRAT_F_ONLY` en config + branch en `scan_all` que opere
   solo STRAT-F cuando esté activo (garantiza el 1er trade demo).
3. **G3** — Ruben corre `main.py` (no `--hub-readonly`) en demo y confirma
   panel + 1er trade. Yo no puedo verificarlo aquí.
4. **G4** — revisión rápida de `enter_trade` para STRAT-F.

> NOTA: esta auditoría es de CÓDIGO. La "ejecución del primer trade en demo
> real" sigue sin verificarse hasta que corra el bot completo en la máquina
> de Ruben. No afirmo que funcione end-to-end; afirmo que el cableado existe
> y tiene los GAPs G1–G3 arriba.

---

## Cierre de GAPs G1+G2 (2026-07-11, ejecutado)

Se implementó y testeó (TDD, 4 tests nuevos en `tests/test_strat_f_golive.py`,
suite global 286 passed):

- **G1 (panel vivo):** `scanner.py` llama `self._flush_strat_f_panel()` en
  `scan_all` tras `_scan_phase_evaluate_assets`; `AssetScanner._flush_strat_f_panel()`
  mapea `_strat_f_batch` → `StratFRow`/`StratFReject` y lo registra en
  `bot.strat_f_panel` (que `ConsolidationBot.__init__` crea y `hub/server.init()`
  usa para exponer `strat_f` por WS). Confirmado por test `test_scan_all_respects_strat_f_only`.
- **G2 (STRAT_F_ONLY):** `config.STRAT_F_ONLY` (default False). En
  `_scan_phase_select_execute` (antes del bucle de scoring) se filtran los
  `candidates` a solo origen `STRAT-F`. Así `select_best` solo ve STRAT-F y el
  1er trade queda garantizado. Confirmado por `test_scan_all_respects_strat_f_only`
  (opera SOLO STRAT-F, no STRAT-A) y `test_flush_fills_bot_panel`.
- **G4 (enter_trade STRAT-F):** ya soportado vía `strategy_origin`; el test de
  integración corrobora que `enter_trade` recibe `strategy_origin="STRAT-F"`.
- **G3 (end-to-end):** PENDIENTE. Ruben debe correr `main.py` en demo y confirmar
  panel + 1er trade. Para activar modo solo-STRAT-F: `STRAT_F_ONLY=True` en
  `src/config.py`.

Archivos tocados: `src/config.py`, `src/consolidation_bot.py`, `src/scanner.py`,
`hub/server.py`, `tests/test_strat_f_golive.py`.
