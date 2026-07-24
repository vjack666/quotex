# Requirements — IA de Zonas (Experience Engine, Feature 28)

> **Feature ID:** 28
> **Status:** spec_ready
> **Depends on:** Feature 27 (Experience Engine — memoria única)
> **Reemplaza:** `src/zone_memory.py` (OBSOLETO, anti-patrón R9)
> **Concepto:** `docs/experience_engine_concept.md`

---

## Contexto

La Feature 27 creó la memoria única del mercado (arcos de experiencia
append-only en `data/market_memory/`). La Feature 18 (Entry Intelligence Agent)
ya lee esa memoria. El prototipo `scripts/zone_ia_prototype.py` demostró que
una SEGUNDA IA — Zonas — puede descubrir zonas de reacción SIN reglas, leyendo
la misma memoria.

Hoy STRAT-A y STRAT-F dependen de `zone_memory.py`, que es detección por
REGLA (rol hardcoded soporte/resistencia, radio fijo, `_DECAY_TABLE`). Eso
viola R9. Esta feature elimina `zone_memory.py` y lo reemplaza por una IA de
Zonas que aprende desde la memoria única, emitiendo un `zone_confidence`.

---

## RZ1 — Zonas descubiertas por la memoria, no por regla

LA IA de Zonas DEBE descubrir zonas de reacción del mercado agrupando
experiencias de la memoria única por proximidad de `evento.nivel` (clustering
por distancia de nivel), SIN usar umbral de "N toques", SIN rol hardcoded
soporte/resistencia, SIN `_DECAY_TABLE`. La zona es una salida de la IA, no
una etiqueta del capturador.

---

## RZ2 — Una sola fuente (la memoria única)

LA IA de Zonas DEBE leer EXCLUSIVAMENTE `ExperienceMemory` (Feature 27). NO
DEBE leer `expired_zones`, ni tablas SQLite de journal, ni construir su propia
base. El schema de captura NO cambia para acomodar esta IA.

---

## RZ3 — Emite zone_confidence (0–1)

CUANDO la IA evalúa un candidato, DEBE emitir `zone_confidence` ∈ [0,1]
que representa la fortaleza de reacción observada en la zona de ese nivel
(mismo asset, misma dirección, proximidad de nivel) según las experiencias
cerradas de la memoria. 1.0 = reacción siempre favorable; 0.0 = siempre desfavorable.

---

## RZ4 — Reemplaza zone_memory en STRAT-A y STRAT-F

CUANDO esta feature está activa, el bot DEBE usar `zone_confidence` para:
(a) sustituir el ajuste `zone_memory` en `entry_scorer._score_zone_memory_adj`
(b) sustituir el veto "zone_memory wall" en `scanner.py` / `entry_decision_engine.py`
por un veto basado en `zone_confidence` bajo umbral. `zone_memory.py` DEBE ser
ELIMINADO y sus imports retirados.

---

## RZ5 — Solo lectura

MIENTRAS la IA de Zonas consulta la memoria, DEBE garantizarse que SOLO LEE
(`query_similar` / agregación). NUNCA escribe en la memoria ni modifica otra IA.
Publica `zone_confidence` hacia el scorer, no hacia la memoria.

---

## RZ6 — Sin reglas de detección

EL sistema NO DEBE contener lógica que decida por regla si un nivel "es"
soporte o resistencia, ni radio fijo, ni decaimiento. Las zonas y su fortaleza
son salida del clustering + agregación sobre la memoria.

---

## RZ7 — Modo activo (reutiliza el engine)

LA IA de Zonas DEBE aprovechar el modo activo del Experience Engine (R5 de F27):
al evaluar un candidato, el engine distribuye las experiencias similares de la
zona y la IA responde con `zone_confidence`. No va a buscar; el engine empuja.

---

## RZ8 — Tests

LOS tests DEBEN cubrir: (a) la IA descubre zonas por clustering sin reglas
usando la memoria real; (b) emite `zone_confidence` coherente (zona con WR alto
→ confidence alto); (c) el reemplazo en STRAT-A/F retira todo import de
`zone_memory` y el bot arranca sin él; (d) la memoria NO crece al evaluar
(solo lectura).

---

## RZ9 — Bandera de activación

LA feature DEBE estar detrás de `ZONE_IA_ENABLED` en `config.py` (default True
tras migración). Si está off, el scorer NO aplica `zone_confidence` (fallback
limpio, sin tocar el umbral base).

---

## RZ10 — Sin tocar el bot hasta aprobar

MIENTRAS la feature esté en `spec_ready`, NO DEBE modificarse el bot en vivo ni
eliminarse `zone_memory.py`. La implementación se hace tras aprobación humana.
