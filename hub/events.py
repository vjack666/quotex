"""Event bus for real-time hub updates."""
import asyncio
import json
import time
from typing import Any


class HubEventBus:
    """In-process pub/sub. Safe to call from sync or async code."""

    def __init__(self) -> None:
        self._queues: list[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=2048)
        self._queues.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        if q in self._queues:
            self._queues.remove(q)

    def publish(self, event_type: str, data: dict | None = None) -> None:
        if not self._queues:
            return
        payload = json.dumps({
            "type": event_type,
            "data": data or {},
            "timestamp": time.time(),
        }, default=str)
        stale: list[asyncio.Queue] = []
        for q in self._queues:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                stale.append(q)
        for q in stale:
            self._queues.remove(q)

    async def publish_async(self, event_type: str, data: dict | None = None) -> None:
        self.publish(event_type, data)


event_bus = HubEventBus()
