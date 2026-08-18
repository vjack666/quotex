import asyncio
from execution.reconnect import ensure_connection

class _Bot:
    async def ensure_connection(self):
        return True

class _FailingBot:
    async def ensure_connection(self):
        raise RuntimeError("offline")

def test_reconnect_success():
    assert asyncio.run(ensure_connection(_Bot())) is True

def test_reconnect_failure_is_safe():
    assert asyncio.run(ensure_connection(_FailingBot())) is False
