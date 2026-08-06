# Trader-Humano Review — lab_protocolo_cientifico

> Revisión del SPEC según el apartado "Participación del agente trader-humano
> en el SDD" de `docs/specs.md`. Rol: evaluar sentido de mercado, no código.

## Veredicto

**APROBADO ✅** — con observaciones obligatorias antes de considerar el
laboratorio "cerrado".

## Dictamen (lenguaje trader)

Como trader, mi preocupación nunca es si el código es elegante. Es:
**¿estamos descubriendo una ventaja del mercado o optimizando ruido?**

Tras leer el Charter y el SDD, el laboratorio por primera vez está diseñado
para responder esa pregunta en serio.

### Lo que está correcto

1. **El Charter es correcto** — corto, solo principios inquebrantables, sin
   procedimientos. Eso es una constitución.
2. **El artículo de FDR era obligatorio** — el lab ya vivió el problema
   (36 firmas, comparaciones múltiples). Quedó institucionalizado (Art. 9).
3. **Separar Scientist del Implementer** — antes una persona pensaba,
   programaba, validaba y aprobaba. Ahora hay separación de roles; reduce
   sesgo.
4. **El ciclo científico** — obliga a pensar antes de experimentar, no
   experimentar y justificar después.

### Lo que NO me dejaba tranquilo (y cómo se resolvió)

1. **Falta el concepto de Dominio** → resuelto: **Art. 10 del Charter**
   (REAL ≠ OTC ≠ Crypto ≠ Índices ≠ timeframes; la evidencia no transfiere).
   Nota: EURUSD REAL es entorno de descubrimiento; la validación final para
   OTC debe hacerse sobre datos OTC recolectados por el propio sistema
   (candidato, no evidencia definitiva).
2. **Falta registrar el tamaño del efecto** → resuelto: **R12** + sección
   Effect Size en `validation.md` (umbral mínimo; p significativo pero edge
   irrelevante NO promueve).
3. **No veo costo operacional** → resuelto: **R13** + sección Costo
   operacional en `validation.md` (spread/slippage/latencia/repaint/retraso/
   payout/comisiones; edge neto).
4. **Falta criterio de muerte definitiva** → resuelto: **Art. 12 del Charter**
   (refutada 3× en datasets independientes → archivo definitivo).
5. **Falta principio de parsimonia** → resuelto: **Art. 11 del Charter**
   (entre evidencias equivalentes, se promueve la más simple).

## Puntuación

- Charter: **10/10**
- SDD: **9.8/10**
- Laboratorio completo: **9.9/10**

## Exigencia como Trader-Humano

Los cinco puntos (Dominio, Effect Size, Costo operacional, Muerte definitiva,
Parsimonia) quedaron incorporados en el SPEC (R12/R13/R14) y en el Charter
(Art. 10/11/12). Con eso, el laboratorio alcanza un nivel comparable al de un
entorno serio de investigación cuantitativa: decisiones por evidencia
reproducible, relevancia práctica y disciplina metodológica — no por resultados
llamativos.

## Faltantes / seguimiento

- [ ] Implementer debe cubrir T15/T16/T17 (plantillas validation.md + checklist
      de Art. 10/11/12 en specs.md).
- [ ] ADR-003 (Dominio) y ADR-004 (Parsimonia/Muerte definitiva) al ejecutar
      la Fase 1.
