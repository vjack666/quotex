# Glosario de acrónimos (ingeniería de software + IA)

> Referencia rápida de los términos usados en la documentación de QUOTEX.
> Aplicados a nuestro sistema de opciones binarias STRAT-F.

## Especificaciones de requisitos
| Acrónimo | Significado | En QUOTEX |
|----------|-------------|-----------|
| SRS | Software Requirements Specification | `docs/engineering/SRS.md` |
| FRS | Functional Requirements Specification | F1–F12 en el SRS |
| NFR | Non Functional Requirements | N1–N9 en el SRS (volumen, tiempo, riesgo) |

## Diseño / arquitectura
| Acrónimo | Significado | En QUOTEX |
|----------|-------------|-----------|
| SDD | Software Design Document | `specs/*/design.md` |
| SAD | Software Architecture Document | `docs/architecture.md` |
| ADD | Architecture Design Document | ADR por componente |
| HLD | High Level Design | diagrama escáner→evaluador→journal→panel |
| LLD | Low Level Design | `evaluate_strat_f` y sus firmas |

## Decisiones y contratos
| Acrónimo | Significado | En QUOTEX |
|----------|-------------|-----------|
| ADR | Architecture Decision Record | `docs/engineering/adr/` |
| RFC | Request For Comments | propuestas pre-cambio |
| API Spec | Especificación de API | `docs/engineering/api_spec.md` |
| UML | Unified Modeling Language | diagramas en `docs/` |
| ERD | Entity Relationship Diagram | `docs/engineering/erd_trade_journal.md` |

## Desarrollo dirigido por pruebas
| Acrónimo | Significado | En QUOTEX |
|----------|-------------|-----------|
| TDD | Test Driven Development | tests primero (279 passed) |
| BDD | Behavior Driven Development | filtros como "DADO/CUANDO/ENTONCES" |
| ATDD | Acceptance Test Driven Development | `tests/test_window_2h.py` (objetivo 5/2h) |
| QA | Quality Assurance | pytest + diag + calibración |
| UAT | User Acceptance Testing | Ruben acepta tras correr en demo |

## IA / agentes / contexto
| Acrónimo | Significado | En QUOTEX |
|----------|-------------|-----------|
| MCP | Model Context Protocol | Engram (memoria) ya conectado |
| A2A | Agent-to-Agent Protocol | futuro (no usado) |
| RAG | Retrieval Augmented Generation | búsqueda en `boblioteca/` |
| CAG | Context-Augmented Generation | boblioteca como contexto fijo del agente |
| DSPy | Declarative Self-improving Python | futuro: calibración automática |
| CoT | Chain of Thought | razonamiento paso a paso del agente |
| ReAct | Reason + Act | modo de trabajo del agente (razona→actúa→observa) |
| ToT | Tree of Thoughts | explorar varias interpretaciones de señal frontera |
