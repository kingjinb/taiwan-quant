"""
Signal generator that translates strategy orders to portfolio actions.
"""
from __future__ import annotations
from typing import List
from backtest.engine import Order
from execution.portfolio import PortfolioManager


class SignalExecutor:
    """Execute trading signals against a portfolio."""

    def __init__(self, portfolio: PortfolioManager):
        self.portfolio = portfolio

    def execute(self, orders: List[Order], prices: dict):
        for order in orders:
            price = prices.get(order.stock_id)
            if price is None:
                continue
            if order.signal == "BUY":
                alloc = self.portfolio.cash * order.confidence * 0.95
                shares = int(alloc / price / 1000) * 1000
                if shares > 0 and self.portfolio.can_buy(order.stock_id, shares * price):
                    self.portfolio.buy(order.stock_id, shares, price)
            elif order.signal == "SELL":
                pos = self.portfolio.positions.get(order.stock_id)
                if pos:
                    shares = int(pos["shares"] * order.confidence / 1000) * 1000
                    if shares > 0:
                        self.portfolio.sell(order.stock_id, shares, price)

    def get_summary(self, prices: dict) -> dict:
        equity = self.portfolio.total_equity(prices)
        return {
            "cash": round(self.portfolio.cash, 2),
            "equity": round(equity, 2),
            "positions": len(self.portfolio.positions),
            "return_pct": round((equity / self.portfolio.initial_capital - 1) * 100, 2),
        }
