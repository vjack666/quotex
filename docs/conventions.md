# Convenciones de código

> Homogeneidad extrema. La IA predice mejor cuando el repositorio se parece
> a sí mismo en todas partes.

## Estilo Python

- **Versión:** Python 3.10+ (sintaxis `list[str]` y `|` para uniones permitidas).
- **Formato:** PEP 8. Líneas máximo 100 caracteres.
- **Imports:** stdlib primero, luego dependencias externas, luego locales. Una línea por módulo.
- **Strings:** comillas dobles `"..."` siempre. Comillas simples solo para escapar comillas dobles dentro.
- **f-strings** para interpolación. Nada de `.format()` ni `%`.

## Nombres

| Tipo | Convención | Ejemplo |
|---|---|---|
| Módulos | `snake_case` | `strat_momentum.py` |
| Clases | `PascalCase` | `MassanielloRiskManager` |
| Funciones / variables | `snake_case` | `detect_consolidation` |
| Constantes | `UPPER_SNAKE` | `MIN_PAYOUT` |
| Privadas | prefijo `_` | `_compute_amount` |
| Async | prefijo `async def` | `async def scan_assets` |

## Estructura de archivo

Cada archivo en `src/` empieza con:

```python
"""Una línea describiendo el propósito del módulo."""
from __future__ import annotations

# imports stdlib
import asyncio
from dataclasses import dataclass

# imports externos
import pandas as pd

# imports locales
from src.models import Candle
```

## Tests

- Un archivo de test por módulo: `tests/test_<módulo>.py`.
- Usar `pytest`. Una función por escenario.
- Cada test usa datos sintéticos o grabados en JSON.
- Nombres de test descriptivos: `test_detect_consolidation_returns_zone_when_valid`.
- Tests marcados como `@pytest.mark.integration` si requieren conexión real.

## Manejo de errores

Excepciones del dominio en `src/errors.py`:

```python
class BotError(Exception):
    """Base para errores del bot."""

class ConnectionError(BotError):
    """Error de conexión con el broker."""

class StrategyError(BotError):
    """Error en lógica de estrategia."""

class RiskError(BotError):
    """Violación de límite de riesgo."""
```

El executor captura excepciones del dominio, las registra en el journal y
continúa el ciclo. Nunca propaga stack traces al archivo de log como error
no manejado.

## Logging

Usar `loguru` con niveles:

| Nivel | Cuándo |
|---|---|
| `TRACE` | Datos crudos de velas, payloads websocket |
| `DEBUG` | Decisiones de estrategia descartadas, candidatos con score bajo |
| `INFO` | Órdenes enviadas, resultados, inicio/fin de ciclo |
| `WARNING` | Reconexiones, límites de riesgo接近, activos en blacklist |
| `ERROR` | Fallos de conexión no recuperables, excepciones no esperadas |

## Comentarios

Por defecto **no** se escriben. Solo se permiten cuando explican un *por qué*
no obvio (p. ej. workaround documentado, invariante sutil). Los nombres deben
hacer el resto.
