"""
Event-driven backtesting engine for Taiwan stock strategies.
"""
from __future__ import annotations
from datetime import date
from dataclasses import dataclass, field
from typing import List, Optional
import pandas as pd
import numpy as np
from config.settings import settings


@dataclass
class Trade:
    date: date
    stock_id: str
    action: str
    price: float
    shares: int
    commission: float
    tax: float = 0.0


@dataclass
class Position:
    stock_id: str
    shares: int = 0
    avg_cost: float = 0.0

    @property
    def market_value(self, current_price: float) -> float:
        return self.shares * current_price

    @property
    def pnl(self, current_price: float) -> float:
        return self.shares * (current_price - self.avg_cost)


@dataclass
class Portfolio:
    cash: float
    positions: dict = field(default_factory=dict)
    trades: list = field(default_factory=list)
    equity_curve: list = field(default_factory=list)


@dataclass
class Order:
    date: date
    stock_id: str
    signal: str
    confidence: float = 1.0


class BacktestEngine:
    def __init__(self, initial_capital: float = None):
        cfg = settings.backtest
        self.initial_capital = initial_capital or cfg.initial_capital
        self.commission_pct = cfg.commission_pct
        self.tax_pct = cfg.tax_pct
        self.min_commission = cfg.min_commission
        self.trade_unit = cfg.trade_unit
        self.portfolio: Optional[Portfolio] = None

    def run(self, price_data: pd.DataFrame, orders: List[Order]) -> Portfolio:
        self.portfolio = Portfolio(cash=self.initial_capital)
        orders = sorted(orders, key=lambda o: o.date)
        price_data = price_data.sort_values("date").reset_index(drop=True)
        order_idx = 0
        daily_equity = []

        for _, row in price_data.iterrows():
            current_date = row["date"]
            if isinstance(current_date, pd.Timestamp):
                current_date = current_date.date()
            stock_id = row["stock_id"]

            if stock_id not in self.portfolio.positions:
                self.portfolio.positions[stock_id] = Position(stock_id=stock_id)

            price = row["close"]
            while order_idx < len(orders) and orders[order_idx].date <= current_date:
                order = orders[order_idx]
                if order.stock_id == stock_id:
                    self._execute_order(order, price, stock_id)
                order_idx += 1

            total_equity = self._calculate_equity(price_data, current_date)
            daily_equity.append({
                "date": current_date,
                "equity": total_equity,
                "cash": self.portfolio.cash,
            })

        self.portfolio.equity_curve = daily_equity
        return self.portfolio

    def _execute_order(self, order: Order, price: float, stock_id: str):
        pos = self.portfolio.positions[stock_id]
        if order.signal == "BUY":
            alloc = self.portfolio.cash * order.confidence * 0.98
            shares = int(alloc / price / self.trade_unit) * self.trade_unit
            if shares <= 0:
                return
            cost = shares * price
            commission = max(cost * self.commission_pct, self.min_commission)
            total_cost = cost + commission
            if total_cost <= self.portfolio.cash:
                total_shares = pos.shares + shares
                total_cost_basis = pos.shares * pos.avg_cost + cost
                pos.avg_cost = total_cost_basis / total_shares if total_shares > 0 else 0
                pos.shares = total_shares
                self.portfolio.cash -= total_cost
                self.portfolio.trades.append(Trade(
                    date=order.date, stock_id=stock_id, action="BUY",
                    price=price, shares=shares, commission=commission,
                ))
        elif order.signal == "SELL" and pos.shares > 0:
            shares_to_sell = min(pos.shares, int(order.confidence * pos.shares))
            if shares_to_sell <= 0:
                return
            proceeds = shares_to_sell * price
            commission = max(proceeds * self.commission_pct, self.min_commission)
            tax = proceeds * self.tax_pct
            net_proceeds = proceeds - commission - tax
            pos.shares -= shares_to_sell
            self.portfolio.cash += net_proceeds
            self.portfolio.trades.append(Trade(
                date=order.date, stock_id=stock_id, action="SELL",
                price=price, shares=shares_to_sell,
                commission=commission, tax=tax,
            ))

    def _calculate_equity(self, price_data: pd.DataFrame, current_date) -> float:
        total = self.portfolio.cash
        for stock_id, pos in self.portfolio.positions.items():
            if pos.shares <= 0:
                continue
            mask = (price_data["stock_id"] == stock_id) & \
                   (price_data["date"] <= pd.Timestamp(current_date))
            relevant = price_data[mask]
            if not relevant.empty:
                current_price = relevant.iloc[-1]["close"]
                total += pos.shares * current_price
        return total

    def summary(self) -> dict:
        if not self.portfolio or not self.portfolio.equity_curve:
            return {}
        eq = pd.DataFrame(self.portfolio.equity_curve)
        if eq.empty:
            return {}
        start_equity = eq["equity"].iloc[0]
        end_equity = eq["equity"].iloc[-1]
        total_return = (end_equity / start_equity - 1) * 100
        eq["daily_return"] = eq["equity"].pct_change()
        sharpe = np.sqrt(252) * eq["daily_return"].mean() / \
                 (eq["daily_return"].std() + 1e-10)
        eq["peak"] = eq["equity"].cummax()
        eq["drawdown"] = (eq["equity"] - eq["peak"]) / eq["peak"] * 100
        max_dd = eq["drawdown"].min()
        return {
            "initial_capital": self.initial_capital,
            "final_equity": end_equity,
            "total_return_pct": round(total_return, 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "num_trades": len(self.portfolio.trades),
            "equity_curve": eq,
        }
