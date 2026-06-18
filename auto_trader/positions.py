"""Local position tracking for UI PnL display."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LocalPosition:
    code: str
    name: str
    qty: int
    entry_price: int


@dataclass
class RealizedRecord:
    amount: int
    pct: float


@dataclass
class PositionBook:
    open_positions: dict[str, LocalPosition] = field(default_factory=dict)
    realized: dict[str, RealizedRecord] = field(default_factory=dict)

    def open_or_add(self, code: str, name: str, qty: int, price: int) -> None:
        pos = self.open_positions.get(code)
        if pos is None:
            self.open_positions[code] = LocalPosition(code=code, name=name, qty=qty, entry_price=price)
            return
        total_qty = pos.qty + qty
        if total_qty <= 0:
            return
        avg = int((pos.entry_price * pos.qty + price * qty) / total_qty)
        pos.qty = total_qty
        pos.entry_price = avg

    def close(self, code: str, sell_price: int) -> RealizedRecord | None:
        pos = self.open_positions.pop(code, None)
        if pos is None or pos.entry_price <= 0:
            return None
        amount = (sell_price - pos.entry_price) * pos.qty
        pct = (sell_price - pos.entry_price) / pos.entry_price * 100.0
        rec = RealizedRecord(amount=amount, pct=pct)
        self.realized[code] = rec
        return rec

    def eval_pnl(self, code: str, current: int) -> tuple[int, float] | None:
        pos = self.open_positions.get(code)
        if pos is None or current <= 0:
            return None
        amount = (current - pos.entry_price) * pos.qty
        pct = (current - pos.entry_price) / pos.entry_price * 100.0
        return amount, pct
