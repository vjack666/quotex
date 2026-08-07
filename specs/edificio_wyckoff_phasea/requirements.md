Este SPEC cumple el Laboratory Charter (docs/LAB_CHARTER.md). No modifica ninguno de sus principios.

# Requirements — Detector Estructural de Fase A (ruta Edificio↔Wyckoff)

Objetivo maestro: descubrir qué características estructurales del mercado dan
ventaja al Edificio, y mapearlas contra la lógica de Wyckoff Fase A, usando
principalmente precio/rango/secuencia/tiempo. El Edificio se trata como caja
negra (NO se modifica). Volumen = variable de investigación, NUNCA dependencia.

Esta feature cubre las fases R0–R3 del roadmap (congelar → inventario
estructural → radiografía WIN/LOSS → descubrimiento estructural). R4–R10 quedan
como features siguientes (ver design.md roadmap).

## R1 (R0 — Congelar Edificio)
El sistema NO DEBE modificar la lógica de `src/edificio_contratacion.py` ni de
`src/scanner.py` durante esta fase. El Edificio se trata como caja negra.

## R2 (Inventario estructural OHLC+tiempo)
El sistema DEBE extraer features estructurales usando SOLO OHLC y tiempo de velas
M15/M5 (tendencia, impulso, compresión, lucha estructural). El volumen NO DEBE
ser requisito de ninguna feature de esta fase.

## R3 (Radiografía WIN/LOSS)
El sistema DEBE clasificar las señales históricas del Edificio en WIN/LOSS usando
la trazabilidad existente en `src/strategy_lab/results/edificio_events.parquet`
(columna `win`), sin re-etiquetar ni reconstruir el veredicto.

## R4 (Contexto previo)
CUANDO se clasifica una señal, el sistema DEBE extraer el contexto estructural de
las N velas M15 previas al `brake_time` de la señal (ventana configurable,
default N=20), alineado por timestamp.

## R5 (Reporte de radiografía)
El sistema DEBE producir un reporte que compare las distribuciones de las
features estructurales entre el grupo WIN y el grupo LOSS (medias, medianas,
effect size, y al menos una prueba de separación por grupo).

## R6 (Regla de oro: volumen nunca requisito)
SI el análisis sugiere que el volumen aporta separación, el sistema NO DEBE
promover el volumen a dependencia estratégica; se registrará como evidencia
adicional, no como requisito de la hipótesis estructural.

## R7 (Datos inmutables ya en disco)
El sistema DEBE usar únicamente datasets ya presentes en disco
(`EURUSD_M15.parquet` en `data/strategy_lab/cohorte_real_eurusd/` o
`data/smc_borrowed/`, y `edificio_events.parquet`). El sistema NO DEBE descargar
datos de red ni comprar feeds.

## R8 (Inmutabilidad y Charter)
El reporte y los resultados DEBEN ser inmutables (hash de dataset + script +
entorno en `protocol_frozen.json`), y el experimento DEBE cerrar con la
declaración de cumplimiento del Charter (Sí).

## R9 (Separación OOS por split nativo)
El sistema DEBE respetar la columna `split` (train/test) de `edificio_events.parquet`
para validar cualquier separación WIN/LOSS fuera de muestra, sin mezclar cohortes.

## Trazabilidad (se completa en progress/impl_edificio_wyckoff_phasea.md al implementar)
- R1 → test_congelamiento_edificio_no_toca_src
- R2 → test_features_solo_ohlc
- R3 → test_clasificacion_winloss_usa_columna_win
- R4 → test_contexto_previo_ventana_n
- R5 → test_reporte_radiografia_separacion
- R6 → test_volumen_no_requisito
- R7 → test_usa_datasets_inmutables
- R8 → test_reporte_inmutable_charter
- R9 → test_split_oos_respetado
