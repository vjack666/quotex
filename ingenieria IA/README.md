# Ingeniería IA — Búsqueda del escenario 80%

> Laboratorio de inteligencia artificial aplicada al **Edificio de Contratación**.
> Objetivo: encontrar, con redes neuronales sobre datos históricos, el escenario
> derivado del sistema de pisos donde la tasa de acierto sobre la vela 15m
> siguiente alcance **≥ 80%**.

## Estado

- **2026-08-03**: creación del laboratorio y documentación metodológica inicial.
- Plan técnico completo: [`PLAN_INGENIERIA_IA.md`](PLAN_INGENIERIA_IA.md).

## Documentos

| Archivo | Contenido |
|---|---|
| `PLAN_INGENIERIA_IA.md` | Objetivo, hipótesis, pipeline, features, arquitectura NN, simulador, métricas, entregables y referencias |
| `docs/veredicto_*.md` | (futuro) Veredicto final: ¿existe el escenario 80%? |

## Reglas de laboratorio

1. El laboratorio **NO toca el bot en vivo** ni la DB de la caja negra.
2. Simulación **vela por vela y causal**: cada decisión se toma con la
   información disponible al cierre de la vela actual. Sin look-ahead.
3. El escenario se construye sobre el **sistema de pisos** del Edificio, no
   como estrategia aislada.
4. **Descartados los timings del POI**: el POI no aporta timing de espera en
   este experimento; solo contexto de zona.
5. Toda hipótesis nueva se documenta antes de ejecutarse.
6. No se modifica el código del Edificio durante este experimento.
