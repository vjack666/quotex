# Filosofía del Proyecto — Documento Cero

> "No estamos construyendo un bot de trading. Estamos construyendo un sistema
> capaz de observar, describir y comprender el comportamiento del mercado con
> suficiente fidelidad para que distintas estrategias puedan tomar decisiones
> sobre una base objetiva."

Este documento es la brújula. No se congela ninguna decisión técnica aquí:
se congelan las RAZONES. Si dentro de dos años alguien (humano o IA) no
entiende por qué existe una tabla, un módulo o una regla, la respuesta debe
estar aquí o el cambio no procede.

Fecha de fundación de la segunda generación: 2026-07-27.
Contexto: tras auditoría cuantitativa completa (3 días de caja negra,
~17,000 evaluaciones) se demostró que el sistema de primera generación
(STRAT-F como cadena de filtros) seleccionaba al azar (universo WR 49.5%,
ACCEPTED WR 49.4%, score AUC 0.477 = ruido) y que su instrumento de captura
no podía validar ni refutar la teoría real del trader. La conversación
completa que originó este documento está en la bitácora del proyecto.

---

## Los 7 Principios

### Principio 1
El mercado no se observa mediante indicadores; se observa mediante fenómenos.
El fenómeno de estudio de este proyecto es la TRANSICIÓN DE PRESIÓN:
un impulso que pierde energía al llegar a una zona de atención y produce
un rebote técnico explotable (~15 minutos).

### Principio 2
Los indicadores son instrumentos de medición, no la realidad.
El estocástico no es el mercado. La vela no es el mercado. Son termómetros.
Ningún concepto del modelo de datos puede definirse EN TÉRMINOS de un
instrumento; los instrumentos se enchufan y desenchufan sin tocar el modelo.

### Principio 3
El Observador nunca toma decisiones. Solo describe la realidad con la mayor
fidelidad posible. No sabe que existe Quotex, ni las binarias, ni el dinero.

### Principio 4
Toda hipótesis debe poder ser falsada con datos capturados por el propio
Observador. Ninguna regla entra a producción sin sobrevivir el tribunal:
walk-forward + bootstrap + permutación + placebos + sensibilidad.
(Precedente: el "criterio (a)" murió en este tribunal el 2026-07-27.
Murió bien: eso es el sistema funcionando.)

### Principio 5
Los datos crudos son permanentes. Las interpretaciones son temporales.
Velas verificadas, ticks, precios: eternos. Índices, scores, clasificaciones:
recalculables, siempre con formula_version. Si la teoría cambia, se
reinterpreta la historia sin perderla.

### Principio 6
Toda variable entra al núcleo por evidencia y sale del núcleo por evidencia.
Las variables nacen en el purgatorio (experimental_features). Ascienden si
el Atlas demuestra que discriminan. Descienden si dejan de hacerlo.
Regla anti-monstruo: el núcleo se mantiene pequeño.

### Principio 7
El negocio nunca modifica la observación del mercado.
Quotex, payouts, horizontes de expiración, stakes: capa de negocio, aparte.
Test permanente: si mañana cambiamos de broker o de instrumento financiero,
el Observador se reescribe en menos del 5%.

---

## La arquitectura de 4 capas

```
               MERCADO
                  │ (existe sin nosotros)
                  ▼
 ──────────────────────────────────────
  CAPA 2 · OBSERVADOR
  Graba hechos. No interpreta, no opina,
  no decide, no compra, no vende.
  Es un científico tomando notas.
  Modelo de datos: PTM v3 (congelado).
 ──────────────────────────────────────
                  │
                  ▼
 ──────────────────────────────────────
  CAPA 3 · ATLAS
  No almacena datos: descubre leyes.
  Valida y falsa hipótesis sobre los
  episodios capturados. Es el activo
  más valioso del proyecto: cualquier
  estrategia futura se construye sobre
  él sin recapturar nada.
 ──────────────────────────────────────
                  │
                  ▼
 ──────────────────────────────────────
  CAPA 4a · ESTRATEGAS
  STRAT-F (baseline histórico), futuros
  STRAT-G, ICT, Wyckoff, IA, reglas
  estadísticas. Todos leen el mismo
  conocimiento del Atlas. Ninguno es
  dueño de los datos.
 ──────────────────────────────────────
                  │
                  ▼
 ──────────────────────────────────────
  CAPA 4b · NEGOCIO
  Quotex hoy. Forex, futuros, acciones
  mañana. Traduce resoluciones físicas
  del mercado a resultados económicos.
 ──────────────────────────────────────
```

Fuera del flujo, con puerta de entrada única:

```
  LABORATORIO (módulo separado, no es núcleo)
  Nuevos indicadores, métricas, redes, transformers,
  visión por computadora, lo que sea.
  Camino obligatorio de ascenso:
  LABORATORIO → (demuestra valor) → ATLAS → (confirma) → núcleo Observador.
  Nada salta capas. Así la experimentación constante
  no erosiona la arquitectura.
```

## Reglas de gobierno de documentos

- FILOSOFIA.md (este documento): cambia solo con decisión explícita del
  dueño del proyecto. Es la brújula.
- PTM v3 (docs/PTM_V3.md): CONGELADO. Cambios = nueva versión mayor con
  migración justificada por evidencia del Atlas.
- Constitución / Teoría del Rebote (docs/CONSTITUCION_REBOTE.md): documento
  científico VIVO. Evoluciona cuando aparece mejor evidencia. Nunca se
  congela, siempre se versiona.

## El test de cada revisión futura

Ante cualquier tabla, campo o módulo nuevo, una sola pregunta:

> ¿Esto describe cómo se comportó el mercado, o solo cómo lo medimos?

Si la respuesta es la segunda, va a instrument_readings o al Laboratorio,
nunca al núcleo.
