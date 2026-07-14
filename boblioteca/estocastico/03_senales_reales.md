# 03 — Señales reales (con ejemplos de la vida)

Todas las señales vienen de los ejemplos documentados de StockCharts
(ChartSchool). Son casos reales de acciones, no inventados. La mecánica es la
misma para Forex/OTC binarias: solo cambia el timeframe.

## 1) Cruce %K / %D (la señal de disparo)

- **Cruce alcista**: %K cruza por encima de %D estando en **sobrevendido (<=20)**.
  Posible compra/rebote.
- **Cruce bajista**: %K cruza por debajo de %D estando en **sobrecomprado (>=80)**.
  Posible venta/caída.

Los cruces en zona extrema son fuertes. Fuera de extrema, dan mucho whipsaw
(StockCharts lo admite: "signal line crosses, moves below 80, and moves above
20 are frequent and prone to whipsaw").

## 2) Divergencia (la señal #1 de Lane)

- **Divergencia alcista**: el precio hace un **mínimo más bajo**, pero el
  estocástico hace un **mínimo más alto**. Menos momentum bajista → rebote
  alcista viene.
- **Divergencia bajista**: el precio hace un **máximo más alto**, pero el
  estocástico hace un **máximo más bajo**. Menos momentum alcista → caída viene.

Confirmación de divergencia (esto es clave):
- Alcista: quiebre de resistencia en precio O cruce del estocástico por encima de 50.
- Bajista: quiebre de soporte en precio O cruce del estocástico por debajo de 50.

## 3) Set-ups de Lane (la joya menos conocida)

Lane identificó otra forma de divergencia para anticipar pisos/techos:

- **Bull set-up**: el precio hace un **máximo más bajo**, pero el estocástico
  hace un **máximo más alto**. Momentum alcista se fortalece → la próxima baja
  debería ser un piso operable.
- **Bear set-up**: el precio hace un **mínimo más alto**, pero el estocástico
  hace un **mínimo más bajo**. Momentum bajista se fortalece → el próximo rebote
  debería ser un techo importante.

Ojo: el set-up NO es la señal, es el aviso. La señal llega después, cuando el
estocástico se vuelve extremo en la dirección esperada.

## Ejemplos reales (StockCharts)

### Crown Castle (CCI) — tendencia alcista, ignorar sobrecompra
Uptrend desde julio. Usaron Full (20,5,5). El estocástico bajó **bajo 20** a
principios de septiembre y noviembre → cada vuelta **por encima de 20** avisó
que la subida continuaba. **Lección**: en tendencia alcista, ignorás las
lecturas de sobrecompra y only buscás sobreventa para sumarte al tren.

### Autozone (AZO) — tendencia bajista, ignorar sobreventa
Techo en mayo, arranca bajista. Full (10,3,3) para más sensibilidad. El
estocástico marcaba sobrecompra en los rebotes; la sobreventa se ignoraba
porque la tendencia mandaba. **Lección**: en bajista, buscás sobrecompra para
vender el rebote, ignorás la sobreventa.

### International Game Tech (IGT) — divergencia alcista real
Feb-mar 2010: el precio hizo un mínimo más bajo, el estocástico un mínimo más
alto (divergencia alcista). Confirmación en 3 pasos: (1) cruce de %K sobre %D
o vuelta sobre 20, (2) cruce sobre 50, (3) quiebre de resistencia en precio.
El estocástico quedó sobre 50 de marzo a mayo. **Lección**: la divergencia se
confirma, no se opera sola.

### Kohls (KSS) — divergencia bajista con whipsaw
Abril 2010: precio en máximos crecientes, estocástico en máximos decrecientes
(divergencia bajista). Pero los cruces tempranos engañaban: KSS seguía subiendo.
La señal limpia fue el quiebre de soporte + estocástico bajo 50. **Lección**:
las señales tempranas no siempre son limpias; el quiebre de estructura confirma.

### Network Appliance (NTAP) — bull set-up
Junio 2009: precio con máximo más bajo, estocástico con máximo más alto (bull
set-up). Foreshadow de un piso. NTAP cayó bajo su mínimo de junio, el
estocástico bajó bajo 20 (sobrevendido) y ahí sí: acción al cruzar sobre su
línea de señal, sobre 20, o tras quiebre de resistencia. **Lección**: el
set-up avisa el piso, el extremo da la entrada.

### Motorola (MOT) — bear set-up
Nov-dic 2009: precio con mínimo más alto, estocástico con mínimo más bajo (bear
set-up) + bajada bajo 20. Momentum bajista fuerte. El rebote no duró; el
estocástico ni volvió a 80 y dio vuelta bajo su línea de señal. **Lección**: el
bear set-up avisa el techo.

## Qué nos llevamos a STRAT-F

- El estocástico M15 nos da el **contexto de extremo del rango**.
- Nunca operamos solo por él: confirmamos con fractal M5 + zona + rechazo M1.
- En tendencia M15 clara, lo usamos al revés: buscamos extremo a favor de la
  tendencia para entrar en el pullback, no contra ella.
- La "confirmación por 50" la podemos usar como filtro extra de sesgo.

---
Fuentes: StockCharts ChartSchool (ejemplos CCI, AZO, IGT, KSS, NTAP, MOT).
