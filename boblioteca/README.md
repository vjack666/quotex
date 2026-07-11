# 📚 BOBLIOTECA

Biblioteca de libros cortos sobre trading aplicado a **opciones binarias**.
Cada libro es una carpeta; cada archivo dentro es un tema. Todo usa el mismo
marco fractal: temporalidad **M15 (la más grande / contexto)** ·
**M5 (media / estructura)** · **M1 (la más pequeña / ejecución)**, y
**expiración de 3 min**.
En binarias M15 es el tope (no subimos a H1/H4). La temporalidad mayor manda:
nunca operes una señal de M1 que vaya contra M15.

## Libros disponibles

### 1 · Wyckoff aplicado a binarias  →  carpeta `wyckoff/`
Método de Wyckoff (Richard Wyckoff). Entradas SOLO en las dos líneas naranjas
continuas del rango (soporte y resistencia). Cubre las 5 fases A→E.

Temas (`wyckoff/`):
- `00_indice.md` — mapa del libro + imagen de referencia.
- `01_la_esencia_wyckoff.md` — qué es Wyckoff y tu imagen.
- `02_regla_lineas_naranjas.md` — la regla de oro: entradas solo en las bandas naranjas.
- `03_marco_temporal_15_5_1.md` — M15 (mayor) / M5 (media) / M1 (menor), expiración 3 min.
- `04_fase_a.md` … `08_fase_e.md` — teoría + binarias de cada fase.
- `09_ejemplo_completo.md` — recorrido sobre la imagen, fase a fase.
- `10_gestion_riesgo.md` — tamaño, rachas, checklist.

### 2 · Fractales aplicados a binarias  →  carpeta `fractales/`
Fractal de Bill Williams (patrón de 5 velas que marca giros). Lo usamos como
marcador de estructura, no como señal mágica.

Temas (`fractales/`):
- `f_00_indice.md` — mapa del libro + fuentes.
- `f_01_que_es.md` — qué es un fractal y por qué sirve en binarias.
- `f_02_como_se_forma.md` — las 5 velas, fractal verdadero/falso.
- `f_03_marco_temporal.md` — M15 (mayor) / M5 (media) / M1 (menor), expiración 3 min.
- `f_04_reversal.md` — fractal como techo/suelo (CALL/PUT).
- `f_05_breakout.md` — ruptura del fractal a favor del momentum.
- `f_06_con_soporte_resistencia.md` — fractal en nivel clave (une con Wyckoff).
- `f_07_doble_fractal.md` — dos fractales en la misma zona = entrada fuerte.
- `f_08_multi_temporalidad.md` — alinear fractales de M15 (mayor) y M5 (media) con M1.
- `f_09_gestion_riesgo.md` — tamaño, señales falsas, checklist.

### 3 · Cómo se forman las velas (rastro del mercado)  →  carpeta `formacion_velas/`
El suelo de todo lo anterior: qué es una vela en realidad (resumen de miles de
trades), cómo el broker la arma tick a tick (Open/High/Low/Close), y por qué
**nunca se evalúa una sola vela aislada**: el mercado se va formando y deja un
rastro (order flow comprimido). Aplicable a M1/M5/M15.

Temas (`formacion_velas/`):
- `00_indice.md` — mapa + fuentes.
- `01_que_es_una_vela.md` — OHLC es el resumen de un rastro, no 4 números sueltos.
- `02_tick_a_vela.md` — cómo el broker agrupa ticks en una vela.
- `03_cuerpo_vs_mecha.md` — el cuerpo = quien dominó; la mecha = dónde fue rechazado.
- `04_el_rastro.md` — order flow comprimido: imbalance / absorción / agotamiento.
- `05_no_una_sola_vela.md` — el principio de Ruben: formación + rastro, no vela aislada.
- `06_aplicado_binarias.md` — lectura de M15/M5/M1 sin caer en la vela suelta.
- `07_gestion_riesgo.md` — esperar el cierre; la mecha fugaz no es rechazo.

## Por dónde empezar
1. Si querés rebotes en rangos claros: lee **Wyckoff** (`wyckoff/02_regla_lineas_naranjas.md`).
2. Si querés marcar giros con un indicador: lee **Fractales** (`fractales/f_01_que_es.md`).
3. Para entender por qué NO se opera una vela suelta: lee **Formación de velas** (`formacion_velas/05_no_una_sola_vela.md`).
4. Para combinar ambos: usa `fractales/f_06_con_soporte_resistencia.md` (fractal en las bandas naranjas).

## Regla común a los tres libros
El marco grande (**M15**) manda, el pequeño (**M1**) obedece. **M5** es la escala
media donde vive la estructura (eventos Wyckoff o el fractal en un nivel clave).
Expiración siempre 3 min. La paciencia en el nivel correcto ES la estrategia.
