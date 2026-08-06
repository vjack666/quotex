# Auditoría P3 (cruce de líneas) + documentación del laboratorio — 2026-08-03

> Verificación de que el piso 3 está completo (cruce limpio, no sticky, con
> separación) y de que la documentación del laboratorio e investigaciones
> refleja la realidad del código. Trabajamos para **binarias (OTC)**, no forex.
>
> Regla: **no se modifica código hasta que el humano apruebe** este documento.

---

## 1. Estado de los pisos (verificado contra código, no contra claims)

| Piso | Función según plan | Real en código | Estado |
|---|---|---|---|
| P1 — Recepción | Filtra pares que pagan bien según exigencias del usuario | `payout_ok = payout >= MIN_PAYOUT` (scanner.py `_feed_edificio`:3037) | ✅ OK |
| P2 — Cerebro | Evalúa el freno (tarjeta de acceso) + extremo | `if brake_ok:` arranca candidato → CONFIRMED con vela M15 cerrada → P2 (edificio:350-385). Estadía = tarjeta + extremo vigente (:436-451) | ✅ OK (corregido hoy) |
| P2 → Hub | Mostrar quiénes subieron a P2 porque frenaron | Badge `freno ✓ ratio` en toda card CONFIRMED + `p2Lights` nueva semántica (index.html:954+, 1160+) | ✅ OK (corregido hoy) |
| P3 — Sala de espera | Evaluar cruce de línea con **separación** y que **no sea sticky** | Puerta P2→P3: `cross_ok and not cross_sticky` + separación K/D sostenida 60s (edificio:410-429) | ⚠️ Parcial (ver §2) |

---

## 2. Auditoría P3 — hallazgos

### 2.1 Lo que está bien

- **Puerta P2→P3** (edificio:410-429): exige cruce limpio (`cross_ok and not cross_sticky`) + `cross_separation_since` sostenido `EDIFICIO_SEPARATION_WAIT_SEC` (60s) antes de promover. Un cruce con tick aislado o pegajoso NO sube.
- **Sticky** (edificio_executor.py:44): `is_sticky_cross` = `|K-D| < 3.0`. Filtra cruces falsos de K y D pegadas.
- **En P2**: si el cruce se pierde o se vuelve sticky, la separación se reinicia (edificio:430-435).
- **Gate 5m + delay 300s** en P3 (edificio:480-516): la vela M5 debe confirmar (body fuerte o martillo) y la orden se ejecuta al inicio de la próxima vela M15. Correcto para binarias (evita ejecutar en medio de vela).
- **Mantenimiento en P3**: si pierde freno o extremo → baja a P2 (edificio:463-476).

### 2.2 ⚠️ Brecha real: el sticky no se re-exige al MOMENTO de la entrada en P3

- En P3, la entrada exige SOLO `cross_ok` (edificio:477: `if not cross_ok: stay`).
- `cross_ok` y `cross_sticky` son independientes (scanner.py:1504 vs `is_sticky_cross`):
  un cruce puede ser `cross_ok=True` Y `cross_sticky=True` al mismo tiempo.
- Consecuencia: un par que entró a P3 con cruce limpio puede, minutos después,
  tener un cruce NUEVO pegajoso (`|K-D|<3`) que SÍ pasa el gate 5m y marca entrada.
- El plan (`docs/EDIFICIO_CONTRATACION.md`) y el pedido del usuario dicen:
  P3 espera "cruce de línea que tenga separación y NO sea sticky".
- **Fix propuesto (1 línea + test)**: en P3, entrada exige `cross_ok and not cross_sticky`.

### 2.3 ⚠️ Riesgo menor: cruce sobre vela en formación

- `_cross_up/_cross_down` (scanner.py:1502-1503) usan el stoch del cache 15m
  (`candles_15m_by_asset` ← HTF `_fetch_15m` → `fetch_candles`).
- El fetch con `end_time=time.time()` normalmente devuelve velas CERRADAS
  históricas, pero no hay verificación explícita (a diferencia del freno, que
  espera `brake_reference_ts` ≠ vela nueva).
- **Mitigación existente**: la separación de 60s en la puerta P2→P3 + re-exigir
  `cross_ok` en P3 + gate 5m + delay 300s hace que un cruce espurio de vela en
  formación no llegue a orden. Con el fix 2.2 (no-sticky en P3) el riesgo queda
  cubierto. No hace falta más para binarias.

### 2.4 Conclusión P3

- **Falta 1 condición para estar completo**: `not cross_sticky` en la entrada de P3.
- No es quisquilloso: es exactamente lo que dice el plan (cruce limpio no sticky).
- El resto del piso 3 está correcto y alineado a binarias (vencimientos cortos,
  ejecución al inicio de vela, no a mitad).

---

## 3. Auditoría de la documentación del laboratorio e investigaciones

| Documento | Qué es | Estado |
|---|---|---|
| `docs/EDIFICIO_CONTRATACION.md` | Plan ideal del edificio | ✅ Actualizado hoy (tarjeta de acceso, orden correcto, PISO 2) |
| `docs/EDIFICIO_AUDIT_FLOW_2026-08-01.md` | Auditoría del 01-08 contra motor ANTIGUO | ⚠️ **DESACTUALIZADO**: describe "mismo scan `brake_ok and extreme_ok`", "sin espera post-freno", "entra igual si sticky", "sin POI tracker" — todo eso YA cambiado. Si se lee hoy, hace creer que hay deudas que ya se pagaron. |
| `docs/EDIFICIO_RULES_AUDIT_2026-08-01.md` | Tabla de reglas vivas del 01-08 | ⚠️ **DESACTUALIZADO**: puerta P3 describe `cross_ok or cross_sticky` (ya no); rule_version `2026-08-01b` (hoy `2026-08-03a`); falta constantes nuevas (SEPARATION_WAIT, HAMMER, BRAKE_CONFIRM, POST_BRAKE). |
| `docs/EDIFICIO_TROUBLESHOOTING.md` | Problemas conocidos y fixes | ✅ Vivo (frescura 07-31 documentada) |
| `progress/current.md` | Estado de sesión | ✅ Actualizado hoy |
| `progress/todos_cruce_lineas_2026-08-03.md` | Tanda T4 (cruce K/D) | ✅ Activa; Fase A (telemetría) NO hecha aún |
| `progress/todos_direction_source_2026-08-03.md` | Tanda T2 (direction_source) | ✅ Fase A implementada SIN commitear (D2) |
| `progress/impl_experience_zone_ia.md` | Laboratorio STRAT-F (F28) | ✅ Done, coherente, trazabilidad RG→test |
| `progress/impl_market_geometry_ctx.md` | Laboratorio STRAT-F (F29) | ✅ Done, coherente, trazabilidad RG→test |
| `progress/impl_experience_engine.md` | Laboratorio STRAT-F (F27) | ✅ Done (feature del motor de memoria) |
| `progress/RESUMEN_AUTONOMO.md` | Resumen STRAT-F demo (12-07) | ✅ Histórico, coherente |
| `progress/ARQUITECTURA_2GEN.md` | Arquitectura 2GEN (anterior) | ✅ Histórico |
| `progress/plan_completado/` | Tandas archivadas | ✅ Correcto |

**Conclusión documental:**
- El LABORATORIO (investigaciones F27-F29, STRAT-F) está **completo y coherente**: done, trazado a tests, con aprendizajes. No hay pendiente ahí.
- **Deuda documental real**: `EDIFICIO_AUDIT_FLOW_2026-08-01.md` y
  `EDIFICIO_RULES_AUDIT_2026-08-01.md` describen el motor de hace 2 días y hoy
  desinforman. Deben actualizarse (o marcarse como históricos con el estado real).

---

## 4. Pendientes que bloquean (heredados, verificar que no haya olvidados)

| ID | Pendiente | Estado |
|---|---|---|
| D1 | Tests ensucian la DB real de la caja negra (`get_black_box` sin mockear) | ⚠️ PENDIENTE — CRÍTICO, bloquea medición |
| D2 | Fase A (direction_source) implementada SIN COMMITEAR + bug menor scanner.py:1501 (`direction_source="M15"` sin dirección) | ⚠️ PENDIENTE |
| A1-A6 | Telemetría del cruce por ciclo (clasificar cruces con datos reales) | ⚠️ PENDIENTE — es la Fase A de la tanda T4 |
| B1 | Demo ≥1h con telemetría (acción del usuario) | ⏳ Espera a A1-A6 |

---

## 5. Mejoras sugeridas (aceptadas, sin ser quisquilloso — binarias)

1. **P3: exigir `cross_ok and not cross_sticky` en la entrada** — completa el piso 3
   según el plan. 1 línea + 1 test. NO es quisquilloso: es el filtro anti-cruce falso.
2. **Actualizar los 2 docs de auditoría del 01-08** — deuda documental que hoy
   desinforma. O marcarlos como históricos (encabezado "SUPERSEDED por 2026-08-03").
3. **No agregar más filtros** — para binarias con vencimientos cortos, la demora
   excesiva mata la oportunidad. La cadena actual (freno→extremo→cruce limpio
   sostenido→separación→gate 5m→delay) ya es suficiente. Ser quisquilloso aquí
   resta entradas sin ganar WR.
4. (Opcional, ya cubierto por la separación) verificación explícita de velas
   cerradas para el cruce — NO recomendado ahora: añade complejidad sin evidencia
   de falla.

---

## 6. Orden de ejecución propuesto (tras aprobación humana)

```
1. Fix P3 sticky (edificio_contratacion.py:477) + test      → P3 completo
2. D1: aislar DB de tests (tmp_path/monkeypatch)            → medición confiable
3. D2: revisar bug direction_source + commitear Fase A      → deuda saldada
4. A1-A6: telemetría del cruce por ciclo                    → datos para clasificar
5. Actualizar/marcar docs de auditoría 01-08                → documental al día
6. (Usuario) B1: demo ≥1h → C1-C3: análisis → ⏸ aprobación
```

Cada paso: tests verdes + `init.ps1` sin crecer los 32 fallos preexistentes.
No se bumpea `EDIFICIO_RULE_VERSION` por telemetría; SÍ por el fix del P3 (cambio de regla).
