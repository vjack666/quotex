# Plan Edificio — Agente Trader Humano

> Este documento es la ÚNICA voz autorizada para decidir cómo se implementa
> la secuencia del Edificio de Contratación en código. Cualquier otro
> documento existente queda subordinado a este plan hasta que se complete
> la migración.
>
> Estado: BORRADOR para aprobación humana.

---

## 1. Auditoría previa — contradicciones vivas

| Tema | EDIFICIO_CONTRATACION.md | agente-trader_humano.md | EDIFICIO_AUDIT_FLOW_2026-08-01.md |
|------|--------------------------|------------------------|-----------------------------------|
| Modelo | 3 pisos: Recepción, Cerebro, Entrada | 8 pisos con vigilantes y expediente | 3 pisos con flujo de auditoría |
| Entrada | implied por P3 | piso 7 / 8 LISTO | implied por P3 |
| Confirmación | no define “confirmado” formal | define POI, brake, cruce, separación | checklist por piso |
| Unicidad de secuencia | no forzada | forzada por orquestador | implied |

Conclusión: **ninguna versión está impuesta por el código**. El scanner puede resolver
P1→P2→P3 en el mismo instante sin dejar huella de paso por piso intermedio.

---

## 2. Versión canónica

Se adopta **EDIFICIO_CONTRATACION.md como base canónica v1**, con las
siguientes reglas endurecidas en código:

- 3 pisos oficiales en producción: `RECEPCION` → `CEREBRO` → `ENTRADA`
- El modelo de 8 pisos queda como **v2 futura** documentada en
  `agente-trader_humano.md`, pero **no se implementa todavía**.
- `EDIFICIO_AUDIT_FLOW_2026-08-01.md` se usa como referencia de auditoría,
  no como definición operativa.

---

## 3. Máquina de estados única — `sequence_engine.py`

Responsabilidades:
- estados válidos
- transiciones permitidas
- condiciones de entrada/salida por estado
- dwell time mínimo por estado
- registro inmutable por transición (`POI`)
- rechazo explícito de saltos y de doble transición en mismo timestamp

Entradas:
- features desde `compute_features.py`
- parámetros desde `src/config.py`

Salida:
- `StateTransition`: `{from_floor, to_floor, timestamp, evidence, allowed}`

Regla dura:
- si `allowed == False`, **no se evalúa el siguiente piso** en el mismo tick.

---

## 4. Dos consumidores, un solo motor

Consumidor 1 — **Edificio en vivo**:
- `src/scanner.py` y `src/edificio_contratacion.py` consultan
  `sequence_engine` para cada activo.
- Se eliminan los ifs sueltos de `brake_ok/cross_ok/extreme_ok`.

Consumidor 2 — **Laboratorio**:
- `src/strategy_lab/backtester.py` y `experiment_runner.py` usan el mismo
  `sequence_engine` sobre dataset histórico.
- `brake_eval.py` pasa a ser **solo label generator** para validación
  retrospectiva, nunca secuencia de entrada.

---

## 5. Puerta de entrada única

Ningún código puede marcar `CONTRATADO` ni disparar orden sin pasar por:

```python
sequence_engine.is_contratado_valido(card) -> bool
```

Auditoría obligatoria antes de merge:
- listar todos los paths que hoy marcan entrada o ejecutan orden
- confirmar que todos pasan por `sequence_engine`
- reportar excepciones encontradas

---

## 6. Tests que prueban coherencia

- saltar piso → FAIL
- contratar sin 3 POIs → FAIL
- dos transiciones mismo timestamp cuando dwell time lo prohíbe → FAIL
- Laboratorio y Edificio sobre mismo dataset → misma traza de transiciones

---

## 7. Orden de implementación

1. `docs/PLAN_EDIFICIO_SECUENCIA.md` → aprobación humana
2. `src/sequence_engine.py` + tests unitarios
3. Migrar Laboratorio a `sequence_engine.py`
4. Migrar Edificio en vivo a `sequence_engine.py`
5. Auditar y cerrar paths bypass
6. Actualizar docs oficiales y marcar v2 futura

---

## 8. Próximo experimento

Una vez aprobado este plan, el primer experimento es **EXP-036**:
comparar traza de transiciones del Laboratorio vs Edificio en vivo sobre
un dataset fijo, para confirmar que ambos consumidores producen exactamente
la misma secuencia.
