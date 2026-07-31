"""Panel del Edificio de Contratación para el HUB.

Expone el estado del edificio (pisos, POIs, contratados) al server
para que lo envíe vía WebSocket al frontend.
"""

from __future__ import annotations

import logging
import time

log = logging.getLogger("hub.edificio_panel")

# Los pisos se leen directamente de src/edificio_contratacion y se cachean
# aquí para no acoplar el hub a la importación del módulo src (que trae
# dependencias pesadas). El server hace el puente.


class EdificioPanel:
    """Capa visible del edificio de contratación en el HUB.

    Se alimenta desde server.py que llama a set_state() con el snapshot
    del edificio. El frontend lo recibe vía WebSocket como parte del
    estado general.
    """

    def __init__(self) -> None:
        self._state: dict = {
            "cycle": 0,
            "cards": {},
            "contratados_recientes": [],
            "resumen": {"en_p1": 0, "en_p2": 0, "en_p3": 0, "contratados": 0, "total_dentro": 0},
        }
        self._last_update: float = 0.0

    def set_state(self, edificio_state: dict) -> None:
        """Actualiza el estado del panel desde el snapshot del edificio."""
        self._state = dict(edificio_state)
        self._last_update = time.time()

    def get_state(self) -> dict:
        """Devuelve el estado actual del edificio para el frontend."""
        return dict(self._state)

    @property
    def last_update(self) -> float:
        return self._last_update
