# Constitución del Rebote Técnico — Documento científico VIVO

Estado: NUNCA SE CONGELA. Evoluciona cuando aparece mejor evidencia.
Cada cambio se versiona y se justifica con datos del Atlas.
Versión: 1.0 (2026-07-27, fundación de la segunda generación)

Relación con los demás documentos:
- docs/FILOSOFIA.md — la brújula (principios, capas). Cambia solo con
  decisión explícita del dueño del proyecto.
- docs/PTM_V3.md — el modelo de datos del Observador. CONGELADO.
- Este documento — la TEORÍA. Vive, respira y se falsa con datos.

---

## Qué estamos intentando detectar

> El primer rebote técnico de aproximadamente 15 minutos que aparece
> cuando un impulso fuerte pierde presión al llegar a una zona donde
> se espera la aparición de la contraparte.

NO es una estrategia de reversión. NO es sobrecompra/sobreventa.
Es una estrategia de TRANSICIÓN DE PRESIÓN. La pelota lanzada con
fuerza contra el suelo: no esperamos que salga volando hacia arriba
para siempre; solo queremos el primer bote.

## Las 6 Leyes

### Ley 1 — El mercado se mueve por ciclos de presión
No existen compras ni ventas aisladas. Existen fases:
presión → agotamiento/freno → equilibrio → nueva presión.
El objetivo NO es capturar la tendencia: es capturar el rebote que
aparece en la transición entre una presión dominante y el equilibrio.

### Ley 2 — El impulso se define por desplazamiento, no por indicadores
Muchas velas consecutivas, poco retroceso, mucho recorrido, alta
pendiente, cuerpos homogéneos. Eso es un impulso. No importa el RSI.
No importa el estocástico. "El mercado viene corriendo" ≠ "está bajista".

### Ley 3 — La zona POI no produce entradas; produce atención
Nunca se compra porque el precio llegó a la zona. Se compra porque:
zona + impulso previo + freno + confirmación. La zona solo dice
"ahora presta atención".

### Ley 4 — El estocástico no predice; sincroniza
El cruce solo dice "empieza a frenarse". Lo que importa es la
GEOMETRÍA: pendiente, aceleración, ángulo — no el valor absoluto ni
el cruce. 95 bajando con decisión vale más que 80 plano. El estocástico
es el reloj que dice "es el momento" cuando la historia YA ocurrió.

### Ley 5 — Las velas no son patrones; son evidencia
Un martillo no significa compra. Significa "aquí apareció oposición".
Nunca decidir con una sola vela: la evidencia es la SECUENCIA
(cuerpos achicándose → mechas contra el impulso → primer cierre
contrario). La historia, no la foto.

### Ley 6 — La operación dura 15 minutos
No necesitamos el cambio de tendencia. Solo que el rebote sobreviva
~15 minutos. Esto cambia el entrenamiento completo: la pregunta no es
"¿girará el mercado?" sino "¿existe alta probabilidad de que durante
los próximos 15 minutos el precio deje de caer (o subir) lo suficiente?"

## Los 5 Módulos conceptuales

M1 Intensidad del impulso — ¿qué tan fuerte fue el empuje?
M2 Índice de freno ★ el corazón — ¿la presión dominante pierde fuerza?
   (achique de cuerpos, mechas contra, primer cierre contrario,
   pérdida de pendiente). No buscamos reversión: pérdida de velocidad.
M3 POI / AttentionZone — ¿estamos donde se espera reacción?
M4 Sincronía temporal — el estocástico como reloj, no como origen.
M5 Calidad del rebote — ¿tiene energía para sobrevivir 15 minutos?

## La historia canónica (cronología pura, sin indicadores)

1. El precio recorre mucho terreno en poco tiempo, casi sin devolver
   nada. Velas del mismo color, cuerpos parecidos: una escalera.
2. Llega a un lugar donde antes hubo pelea. Hasta aquí NADA es señal.
3. Primer cambio: el paso se acorta. Los cuerpos se achican respecto
   a los del viaje.
4. Segundo cambio: aparecen huellas del otro bando — mechas que apuntan
   CONTRA el viaje. Alguien empezó a comprar lo que otros venden.
5. Tercer cambio: una vela cierra del lado contrario. No es giro;
   es el primer "no" audible.
6. El rebote nace ahí y solo necesita vivir 15 minutos.
Si el paso NO se acorta al llegar (velas siguen enormes), la zona se
atraviesa como papel: esa es la LOSS típica.
Los pasos 3-4-5 son UNA secuencia, no tres condiciones sueltas.

## Historias de referencia (catálogo inicial)

A. Impulso → freno limpio → POI → rebote → WIN
B. Impulso → SIN freno → POI → continuación → LOSS
C. Impulso débil → POI → ruido → sin dirección → NO OPERAR
D. Impulso → freno → POI → estocástico aún apunta al extremo →
   esperar → segundo cruce → WIN
E. Freno correcto pero rebote insuficiente (murió antes de 15 min) →
   LOSS de sincronización, no de tesis.

## Estado de la evidencia (v1.0 — actualizar con cada hallazgo del Atlas)

VALIDADO (LAB-001, 14 años EURUSD M1, 117,169 episodios, 2026-07-27):
- LA PRUEBA CENTRAL PASÓ: la muerte del empuje predice el rebote.
  MUERTE TOTAL (avance chico + <10% del pico + velas alternadas) →
  REBOUND 69.8% (n=16,834) vs 23.7% el resto; empuje VIVO → 13.1%.
  Walk-forward 2012-19: 69.3% / 2020-26: 70.5%. Placebo p<0.001.
  Refina el M2: lo que predice NO es la suavidad de la caída (la
  pendiente sola dio señal invertida) sino la MUERTE COMPLETA del
  impulso. Ver docs/LAB_001_MUERTE_EMPUJE.md.
- Límite: fenómeno ≠ trade (falta MFE/MAE y timing, Fase B) y
  EURUSD real ≠ OTC Quotex (validación final con captura viva).

VALIDADO (auditoría 3 días caja negra, 2026-07-27):
- El sistema de 1ª generación NO implementa esta teoría (2 ausencias,
  3 contradicciones — ver auditoría teoría vs código).
- Su universo de candidatos es una moneda (WR 49.5%): sin impulso
  medido, "zona tocada" es 50/50 por definición.
- El score de 1ª generación es ruido (AUC 0.477, n=561).
- Los vetos R4 / R1-CALL / stoch_extreme_against SÍ aportan EV
  (muestras grandes) — son fragmentos toscos de la Ley 5 y del M2.

PENDIENTE DE FALSACIÓN (requiere datos del Observador, 2-3 semanas):
- La prueba central: ¿impulso fuerte + freno alto >> impulso fuerte
  sin freno? (Atlas v0: INCONCLUSA por sesgo de muestreo — el
  instrumento viejo casi no capturó impulsos.)
- Energy como concepto medible.
- Las familias de transition_type.

MUERTO (tribunal de falsación 2026-07-27):
- Criterio (a) como regla fija (contaminación + solapamiento temporal
  + replicable por placebos). Nota: murió apuntando en la dirección
  de esta teoría (distancia a banda + no-sobreextensión ≈ proxies
  toscos del freno en la POI).

## Protocolo de cambio de esta Constitución

1. Toda modificación cita la evidencia del Atlas que la motiva
   (n de episodios, IC, resultado del tribunal de falsación).
2. Se incrementa la versión y se deja la anterior en el historial.
3. Nada de lo aquí escrito es sagrado excepto el método:
   hipótesis → observación → falsación → solo entonces, regla.
