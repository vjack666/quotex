# Estado de sesión — auditoría y roadmap STRAT-F

> Sesión: 2026-07-11 | Operador: Ruben | Agente: Hermes

## 1. Auditoría del repo (código real)

### Estado del bot tras borrar Strategy B
- **Strategy B (Wyckoff Spring) BORRADA físicamente**: `src/strat_b.py`,
  `src/strategy_spring_sweep.py`, `tests/test_strat_b.py` ya no existen.
- `src/strat_support.py` conserva `find_strong_support_2m` + `candles_to_dataframe`
  (extraídos para que MOMENTUM siga funcionando).
- Bot 100% Strategy A + MOMENTUM + REVERSAL_SWING + ORDER_BLOCK. pytest 246 passed.
- **Deuda hallada**: `docs/ROADMAP.md` y el viejo `feature_list.json` aún listaban
  `strat_b.py` como módulo vivo y `strat_b` en acceptance criteria. Ambos BORRADOS
  en esta sesión (ya no reflejaban la realidad).

### Módulos vivos en `src/` (reales, 50+ archivos)
Estrategias orquestadas por `scanner.py` (1763 líneas):
| Estrategia | Módulo | Detecta sobre | `_strategy_origin` |
|---|---|---|---|
| STRAT-A (consolidación) | `strat_a.py` | 5m (evaluate) | STRAT-A |
| Momentum 1m | `strat_momentum.py` | 1m | STRAT-MOMENTUM |
| Reversal swing | `strat_reversal_swing.py` | 1m | STRAT-REVERSAL-SWING |
| Order block | `strat_order_block.py` | 1m | STRAT-ORDER-BLOCK |

### Hallazgo clave para la nueva estrategia
- **Ninguna estrategia aplica el marco fractal M15/M5/M1 de los libros** de
  `boblioteca/` (Wyckoff + Fractales Bill Williams). Los libros son teoría
  separada del bot.
- El scanner solo prefetcha **5m y 1m** (`scan_prefetch.py` → `ScanCycleData`
  expone `candles_5m`, `candles_1m`). Para una estrategia con contexto M15
  hace falta bajar también **15m**.
- `htf_scanner.py` (315 líneas) ya trae 15m en background, pero no está cableado
  al ciclo de evaluación del scanner principal.

### Biblioteca `boblioteca/` (conocimiento aplicable)
- `wyckoff/`: 11 archivos. Regla de oro: entradas SOLO en líneas naranjas
  (soporte/resistencia), fases A–E, marco M15 (mayor/contexto) · M5 (media/
  estructura) · M1 (menor/ejecución), expiración 3 min.
- `fractales/`: 10 archivos. Fractal Bill Williams = 5 velas, marca giro.
  Reversión (techo/suelo) y ruptura (breakout). Mismo marco M15/M5/M1.

## 2. Decisión: nueva estrategia STRAT-F (Fractal / Wyckoff)

Une ambos libros en UN detector con jerarquía fractal:
- **M15 (mayor)**: contexto — define si el par está en rango Wyckoff o tendencia.
  La mayor manda; si M15 dice "rango roto", no operamos rebotes.
- **M5 (media)**: estructura — fractal Bill Williams (5 velas) en una banda
  naranja (zona Wyckoff) = evento de entrada.
- **M1 (menor)**: ejecución — vela que toca la banda y la rechaza (no cierra fuera).

Esto reemplaza la fragmentación actual (4 estrategias que no se hablan) por una
sola coherente con la teoría de los libros. Arranca **acomodando el scanner**
(que prefetch 15m y cable STRAT-F).

## 3. Roadmap nuevo → ver `feature_list.json` y `docs/ROADMAP.md`
