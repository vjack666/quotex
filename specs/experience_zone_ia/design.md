# Design — IA de Zonas (Feature 28)

> Reemplaza `zone_memory.py` con una IA lectora de la memoria única (F27).

## Flujo

```
Candidato (asset, direction, nivel de entrada)
        │
        ▼
ExperienceEngine.distribute()  ── modo activo (RZ7, reusa F27)
        │  empuja experiencias de la zona (mismo asset + proximidad de nivel)
        ▼
ZoneIA.score(candidato, similares)  ── SOLO LEE (RZ5)
        │  clustering por proximidad de evento.nivel + agregación de WR
        ▼
zone_confidence ∈ [0,1]  ── salida, no se escribe en memoria
        │
        ├── entry_scorer: reemplaza _score_zone_memory_adj (RZ4a)
        └── scanner/decision_engine: reemplaza veto "zone_memory wall" (RZ4b)
```

## Módulos

- `src/zone_ia.py` (NUEVO): `ZoneIA` con `score(candidate, similars)` →
  `zone_confidence`. Clustering por proximidad de `evento.nivel` (banda
  relativa ~0.1–0.2%, igual que el prototipo). Agregación: WR de experiencias
  cerradas en la zona → mapeo a [0,1] (centrado en 0.5). Sin rol hardcoded.
- `src/entry_scorer.py`: `_score_zone_memory_adj` se sustituye por
  `_score_zone_ia(candidate)` que llama `ZoneIA.score` (detrás `ZONE_IA_ENABLED`).
- `src/scanner.py` + `src/entry_decision_engine.py`: el veto "wall" usa
  `zone_confidence < UMBRAL` en vez de `score_zone_memory`.
- `src/zone_memory.py`: ELIMINADO. Retirar imports en scanner, entry_scorer,
  entry_decision_engine, models (`zone_memory: list` → se conserva el campo
  pero se llena desde la memoria, o se elimina si no hay otro uso).
- `config.py`: `ZONE_IA_ENABLED = True`.

## Reutilización del prototipo

`scripts/zone_ia_prototype.py` ya tiene el clustering por proximidad y la
agregación de WR validados contra la memoria real (33 zonas / 25 assets).
El módulo `src/zone_ia.py` promueve esa lógica a código del bot, con la misma
restricción de CERO reglas. El prototipo queda como script de auditoría.

## Contrato de salida

`zone_confidence` ∈ [0,1]. Se combina en el score como ajuste aditivo leve
(±N pts, igual filosofía que la distribución de F27), NO multiplicativo, para
no romper el umbral de STRAT-F (73). El veto "wall" usa umbral bajo
(ej. `zone_confidence < 0.30` → rechazar STRAT-A en esa zona).

## Alternativas descartadas

- Mantener `zone_memory.py` y sumar la IA: dos fuentes de verdad (R9).
- Regla "3 toques = soporte": anti-patrón R9, el modelo debe descubrirlo.
- `_DECAY_TABLE`: decaimiento por heurística prohibido (R9/RZ6).
- Tabla `reaction_zones` aparte: silo, viola R3 de F27.
