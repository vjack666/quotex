# Estado de sesión

<!-- Plantilla — la sesión 2026-07-31 (purga: solo Edificio) está en progress/history.md -->

## 2026-08-01 — Afinamiento P3 EDIFICIO: filtro body_5m > 0.03

### Qué se hizo
- **Afina EDIFICIO en P3 (sala de espera final)**: antes de emitir `CONTRATADO`,
  evalúa la vela 5m cerrada anterior a la entrada.
  Usa `candles_5m[-1]` si está disponible, fallback a `close_candle_5m`.
  Si `body / total_range <= 0.03`, la señal se considera débil y **no entra**.
- **Motivo (dummy)**: control de seguridad en la puerta de entrada. Si el bolso
  (vela) es muy chico, no deja subir porque el riesgo de vuelta es alto.
- **Evidencia**: análisis de 11 trades resueltos últimas 24h (5 wins, 6 losses).
  - Avg body 5m wins: 0.0749
  - Avg body 5m losses: 0.0131
  - Filtro `body_5m > 0.03`: 4/5 wins pasan, 2/6 losses pasan.
    Win rate mejora de 45.5% → ~67% en esta muestra.

### Cambios
- `src/edificio_contratacion.py`:
  - Nuevo parámetro `close_candle_5m` en `evaluate()`.
  - Cálculo de `candle_5m_body` desde raw `candles_5m[-1]` o fallback
    `close_candle_5m.total_range/body`.
  - `contract_now` ahora exige `candle_5m_body is None or > 0.03`.
- `src/scanner.py`:
  - `_feed_edificio()` ya pasa `candles_5m` y `close_candle_5m` al evaluate.
- `tests/test_edificio_contratacion.py`:
  - 10/10 tests verdes.
  - Nuevos tests: filtro vela chica no contrata, vela grande contrata.

### Pendiente
- Nada bloqueado.
- Validar en runtime que las entradas con body chico efectivamente no entran.
