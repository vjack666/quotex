# Pacient Waiting — Reporte de Analisis Edificio

## Hipotesis
En lugar de descartar cruces K/D con separacion baja, esperar N velas adicionales
para ver si K/D desarrolla separacion real. Si alcanza umbral X, entrada con mejor calidad.

## Dataset base
- Eventos analizados: 946
- Separacion <= 3: 504 (53.3%)
- Separacion > 5: 61 (6.4%)

## Resumen por umbral

| Umbral | Eventos que alcanzan | % del total | Winrate si espera | Wait promedio | Wait mediano |
|--------|----------------------|-------------|-------------------|---------------|---------------|
| 2.0 | 946.0 | 100.0% | 37.1% | 0.0 | 0.0 |
| 3.0 | 946.0 | 100.0% | 30.9% | 0.6 | 1.0 |
| 4.0 | 945.0 | 99.9% | 26.0% | 1.2 | 1.0 |
| 5.0 | 943.0 | 99.7% | 22.7% | 1.9 | 1.0 |
| 6.0 | 931.0 | 98.4% | 19.9% | 2.7 | 1.0 |

## Trade-off por bucket de separacion original

| Bucket | Count | Winrate original | reach_5 | winrate_wait_5 |
|--------|-------|------------------|---------|----------------|
| 2-3 | 504 | 35.9% | 503 | 21.5% |
| 3-4 | 259 | 32.0% | 257 | 18.7% |
| 4-5 | 122 | 41.8% | 122 | 26.2% |
| >5 | 61 | 59.0% | 61 | 42.6% |

## Hallazgos clave
- De 504 eventos con separacion baja original (<=3), el porcentaje que alcanza separacion >=5 si espera es 99.8%.
- Winrate general con espera para umbral 5: 22.7%
- Trade-off: esperar mas velas aumenta separacion pero reduce cantidad de entradas ejecutables.

## Propuesta ML: features para 'pacient waiting'
- `sep_trend_3`: pendiente de separacion K/D en ultimas 3 velas pre-cruce (crece/decrece).
- `sep_velocity`: cambio de separacion por vela en ventana pre-cruce.
- `wait_cycles_needed`: velas hasta alcanzar threshold X; NaN si nunca alcanza.
- `max_sep_in_wait`: separacion maxima alcanzada en ventana de espera.
- `sep_at_entry`: separacion en la vela de entrada efectiva.
- `patience_flag`: 1 si el sistema tuvo que esperar al menos 1 vela; 0 si entrada inmediata.
- `time_to_threshold_binary`: 1 si alcanza threshold dentro de N velas; 0 si no.

## Recomendacion operativa
- No descartar automaticamente separacion <= 3. Esperar hasta 5 velas; si alcanza >=5, calidad sube.
- Si en ventana de espera la separacion decrece o no despega, descartar (patience_flag=0 + sep_trend negativo).
