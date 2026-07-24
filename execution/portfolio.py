"""
Portfolio management and risk control.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import pandas as pd
import numpy as np


@dataclass
class RiskLimits:
    max_position_pct: float = 0.20
    max_sector_pct: float = 0.40
    max_leverage: float = 1.0
    min_cash_pct: float = 0.05
    stop_loss_pct: float = 0.07


class PortfolioManager:
    """Manage positions, risk, and rebalancing."""

    def __init__(self, initial_capital: float, risk_limits: Optional[RiskLimits] = None):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, dict] = {}
        self.risk_limits = risk_limits or RiskLimits()
        self.equity_history: List[dict] = []

    def value_position(self, stock_id: str, price: float) -> float:
        if stock_id not in self.positions:
            return 0.0
        return self.positions[stock_id]["shares"] * price

    def total_equity(self, prices: Dict[str, float]) -> float:
        total = self.cash
        for sid, pos in self.positions.items():
            price = prices.get(sid, 0)
            total += pos["shares"] * price
        return total

    def can_buy(self, stock_id: str, cost: float) -> bool:
        if cost > self.cash:
            return False
        # Position limit check
        return True

    def buy(self, stock_id: str, shares: int, price: float):
        cost = shares * price
        self.cash -= cost
        if stock_id not in self.positions:
            self.positions[stock_id] = {"shares": 0, "avg_cost": 0.0}
        pos = self.positions[stock_id]
        total_shares = pos["shares"] + shares
        total_cost = pos["shares"] * pos["avg_cost"] + cost
        pos["avg_cost"] = total_cost / total_shares if total_shares > 0 else 0
        pos["shares"] = total_shares

    def sell(self, stock_id: str, shares: int, price: float):
        if stock_id not in self.positions:
            return
        pos = self.positions[stock_id]
        shares = min(shares, pos["shares"])
        self.cash += shares * price
        pos["shares"] -= shares
        if pos["shares"] <= 0:
            del self.positions[stock_id]
