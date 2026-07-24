# Implementación — IA de Zonas (Feature 28)

Fecha: 2026-07-24 · status: done

## Tesis
Una memoria única (Experience Engine, F27) alimenta múltiples IAs que SOLO
LEEN. La IA de Zonas es la SEGUNDA lectora (tras la Entry Intelligence, F18).
Reemplaza a `zone_memory.py` (detector por reglas: rol fijo soporte/resistencia,
radio fijo 0.4%, `_DECAY_TABLE`), que fue BORRADO.

## Qué se hizo
- `src/zone_ia.py` (nuevo): `ZoneIA` descubre zonas por clustering de proximidad
  de `evento.nivel` (banda ±0.15%) y emite `zone_confidence` = WR observado en
  el nivel. `ZoneIA.is_wall()` veta si confidence < 0.30. CERO reglas.
- `config.py`: `ZONE_IA_ENABLED = True`.
- `entry_scorer.py`: `_score_zone_memory_adj` → `_score_zone_ia`; breakdown
  `zone_memory` → `zone_confidence` (crudo) + `zone_confidence_adj` (±8pt).
- `scanner.py`: veto wall de zone_memory → `ZoneIA.is_wall`.
- `entry_decision_engine.py`: Veto 9 usa `ZoneIA.is_wall` (veto_type
  ZONE_MEMORY_WALL); borrada `_check_zone_memory_no_wall`.
- `models.py`: campo `zone_memory` eliminado; añadido `zone_confidence`.
- `vip_library.py`: lee `zone_confidence_adj`.
- `zone_memory.py` BORRADO.

## Trazabilidad RZ → test
- RZ1 (descubrimiento por proximidad, sin rol): test_zone_ia::test_discover_zones_clusters_without_rules
- RZ2 (WR por zona reproducible): seed en tests + verificación manual
- RZ3 (zone_confidence coherente): test_zone_ia::test_zone_confidence_coherent, test_zone_confidence_insufficient_sample
- RZ4 (reemplazo total, sin legacy): test_htf_zone_wiring (migrado) + borrado de zone_memory.py
- RZ4b (wall por umbral): test_zone_ia::test_zone_ia_wall, test_htf_zone_wiring::test_zone_ia_wall_veto
- RZ5 (solo lectura): test_zone_ia::test_zone_ia_only_reads (memoria no crece)
- RZ6 (sin _DECAY_TABLE/reglas): test_discover_zones_clusters_without_rules
- RZ7 (modo activo reusa engine): cableado en entry_scorer._finalize_scoring
- RZ8 (breakdown en scorer): test_htf_zone_wiring::test_score_breakdown_zone_confidence_nonzero
- RZ9 (STRAT-F ajuste por zona): idem, zona_confidence_adj != 0

## Verificación
`pytest tests/test_zone_ia.py tests/test_htf_zone_wiring.py tests/test_experience_engine.py
tests/test_observation.py tests/test_experience_distrib.py tests/test_ml_features.py
tests/test_ml_scorer.py tests/test_train_lightgbm.py tests/test_entry_intelligence.py
tests/test_train_from_memory.py` → 86 passed.

Imports del bot OK; cero imports residuales a `zone_memory` en `src/`.
