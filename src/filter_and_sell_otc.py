"""Filtro de activos OTC por payout y venta PUT en el mejor candidato."""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

from pyquotex.stable_api import Quotex  # type: ignore

from config import CONNECT_RETRIES, MIN_PAYOUT
from connection import get_open_assets, place_order

log = logging.getLogger("filter_and_sell_otc")

DEFAULT_MIN_PAYOUT = max(MIN_PAYOUT, 85)
DEFAULT_AMOUNT = 5.0
DEFAULT_DURATION = 300


@dataclass
class OrderAck:
    symbol: str
    event: str
    ticket_or_id: str
    payout: int
    amount: float
    duration: int
    dry_run: bool


class FilterSellOTC:
    def __init__(
        self,
        client: Quotex,
        min_payout: int = DEFAULT_MIN_PAYOUT,
        amount: float = DEFAULT_AMOUNT,
        duration: int = DEFAULT_DURATION,
        only_open: bool = True,
        account_type: str = "PRACTICE",
    ) -> None:
        self.client = client
        self.min_payout = min_payout
        self.amount = amount
        self.duration = duration
        self.only_open = only_open
        self.account_type = account_type

    async def list_candidates(self) -> List[Tuple[str, int]]:
        return await get_open_assets(self.client, self.min_payout)

    async def _send_put_order(
        self,
        symbol: str,
        payout: int,
        dry_run: bool,
    ) -> OrderAck:
        if dry_run:
            ticket = f"DRY-{int(time.time())}"
            log.info("ACK %s: event=dry-run ref=%s", symbol, ticket)
            return OrderAck(
                symbol=symbol,
                event="dry-run",
                ticket_or_id=ticket,
                payout=payout,
                amount=self.amount,
                duration=self.duration,
                dry_run=True,
            )

        try:
            ok, order_id, _, _, reject = await place_order(
                self.client,
                symbol,
                "put",
                self.amount,
                self.duration,
                dry_run=False,
                account_type=self.account_type,
            )
        except Exception as exc:
            log.error("ACK %s: event=error ref=%s", symbol, exc)
            return OrderAck(
                symbol=symbol,
                event="error",
                ticket_or_id=str(exc),
                payout=payout,
                amount=self.amount,
                duration=self.duration,
                dry_run=False,
            )

        if ok:
            log.info("ACK %s: event=accepted ref=%s", symbol, order_id)
            return OrderAck(
                symbol=symbol,
                event="accepted",
                ticket_or_id=order_id,
                payout=payout,
                amount=self.amount,
                duration=self.duration,
                dry_run=False,
            )

        log.warning("ACK %s: event=rejected ref=%s", symbol, reject)
        return OrderAck(
            symbol=symbol,
            event="rejected",
            ticket_or_id=reject or "",
            payout=payout,
            amount=self.amount,
            duration=self.duration,
            dry_run=False,
        )

    async def run_once(self, dry_run: bool = True) -> List[OrderAck]:
        candidates = await self.list_candidates()
        log.info(
            "Instrumentos evaluados: %d | Filtrados payout > %d%% y abiertos=%s",
            len(candidates),
            self.min_payout,
            self.only_open,
        )

        if not candidates:
            log.warning("No hay activos OTC que cumplan el filtro en este momento.")
            return []

        symbol, payout = candidates[0]
        mode = "DRY-RUN" if dry_run else "LIVE DEMO"
        log.info(
            "Se lanzará venta PUT en %s payout=%d%% | monto=%.2f | duración=%ds | modo=%s",
            symbol,
            payout,
            self.amount,
            self.duration,
            mode,
        )

        ack = await self._send_put_order(symbol, payout, dry_run=dry_run)
        return [ack]