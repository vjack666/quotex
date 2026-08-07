# Revisión trader-humano — edificio_wyckoff_phasea

### Veredicto
APROBADO

### Dictamen (lenguaje trader)
La hipótesis tiene sentido de mercado: en binarias no necesitamos "el precio
sube mucho", necesitamos "en la próxima ventana el precio está del lado
correcto". El Edificio ya entrega señales; lo sensato es radiografiar QUÉ
estructura precede a sus aciertos (WIN) vs sus fallos (LOSS), y solo después
preguntar si eso es Fase A de Wyckoff. Eso evita imponer la teoría al algoritmo
(curve fitting conceptual).

El embudo es coherente: caja negra Edificio → señales ya etiquetadas
(`edificio_events.parquet` con `win` y `split` OOS) → contexto OHLC previo
extraído de `EURUSD_M15.parquet`. No se re-etiqueta, no se descarga, no se
modifica el Edificio.

Las dos reglas de oro del proyecto están incorporadas y las exijo:
1. El Edificio NO se modifica para encajar en Wyckoff (R1). Wyckoff se usa para
   explicar/clasificar la estructura que el Edificio YA explota.
2. Volumen NUNCA será requisito fundamental de la hipótesis estructural (R6). Si
   aparece valor en volumen, es evidencia adicional, no dependencia.

### Faltantes que exige el trader
- Que el reporte distinga WIN/LOSS usando SOLO la columna `win` existente (hecho:
  R3). No reconstruir veredicto.
- Que el análisis respete `split` train/test para no inflar separación en muestra
  (hecho: R9).
- Que cualquier separación WIN/LOSS futura reporte effect size + prueba, no solo
  medias (hecho: R5).
