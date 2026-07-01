# Verificación — Cómo demostrar que el trabajo funciona

> Regla de oro: **el agente no dice "funciona", lo demuestra**.
> Toda feature termina con evidencia ejecutable, no con afirmaciones.

## Niveles de verificación

### Nivel 1 — Tests unitarios (obligatorio)

Toda función pública en `src/` tiene al menos un test en `tests/` que:

1. Cubre el camino feliz.
2. Cubre al menos un camino de error si la función puede fallar.

Comando:
```powershell
python -m pytest tests/ -v
```

### Nivel 2 — Test de integración (obligatorio para features con I/O)

Las features que tocan el broker se verifican con datos grabados:

```python
import pytest
import json
from src.strat_momentum import detect_momentum

def test_momentum_with_recorded_data():
    candles = json.load(open("tests/data/eurusd_momentum.json"))
    result = detect_momentum(candles)
    assert result["direction"] == "call"
    assert result["confidence"] > 0.7
```

### Nivel 3 — Smoke test end-to-end (opcional pero recomendado)

Antes de cerrar la sesión, ejecuta el flujo completo en modo dry-run:

```powershell
python src/main.py --hub-readonly --once
```

Esto ejecuta un ciclo de escaneo sin enviar órdenes. Verifica que no hay
excepciones no manejadas.

### Nivel 4 — Trazabilidad de requirements (obligatorio para features con `"sdd": true`)

Cada `R<n>` de `specs/<name>/requirements.md` debe poder mapearse a al
menos un test concreto en `tests/`. El reviewer rechaza si falta cobertura.

El implementer documenta el mapa en `progress/impl_<name>.md`:

```markdown
## Trazabilidad
- R1 → `test_parallel_scan_all_assets`
- R2 → `test_parallel_scan_timeout_recovery`
```

## Anti-patrones (no hacer)

- ❌ "He añadido el código, debería funcionar." → falta test ejecutable.
- ❌ Test que solo verifica que la función no lanza excepción. → tiene que
  comprobar el resultado concreto.
- ❌ Tests que dependen de conexión real al broker. → usa datos grabados.
- ❌ Marcar la feature como `done` sin pasar `.\init.ps1`.

## Verificación final antes de cerrar

```powershell
.\init.ps1
# debe terminar con [OK] Entorno listo
```

Si `init.ps1` está rojo, **no** marques nada como `done`. Anota el bloqueo
en `progress/current.md` con estado `blocked` en `feature_list.json`.
