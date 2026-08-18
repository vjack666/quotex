"""Canonical namespace for broker/order execution components.

The legacy ``executor.py`` remains the runtime behavior owner during the
incremental extraction. New execution code should depend on the contracts and
small value objects exposed here rather than importing the monolith.
"""
from .contracts import BrokerExecutor, TradeResolver
from .lifecycle import ExecutionContext, TradeLifecycle
from .order_context import OrderContext
from .session import ExecutionSessionSnapshot

__all__ = [
    "BrokerExecutor",
    "TradeResolver",
    "TradeLifecycle",
    "ExecutionContext",
    "OrderContext",
    "ExecutionSessionSnapshot",
]
