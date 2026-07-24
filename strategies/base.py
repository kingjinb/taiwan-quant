"""
Base strategy interface for Taiwan stock quant.
"""
from __future__ import annotations
from datetime import date
from typing import List
import pandas as pd
from backtest.engine import Order


class BaseStrategy:
    """All strategies inherit from this."""

    def __init__(self, name: str = "base"):
        self.name = name
        self.orders: List[Order] = []

    def generate_signals(self, df: pd.DataFrame) -> List[Order]:
        """
        Generate trading signals from price data.
        Returns a list of Order objects.
        """
        raise NotImplementedError

    def reset(self):
        self.orders = []


class MACrossoverStrategy(BaseStrategy):
    """
    Classic MA Crossover strategy.
    Buy when fast MA crosses above slow MA, sell on cross below.
    """

    def __init__(
        self,
        fast_window: int = 5,
        slow_window: int = 20,
        stock_id: str = "2330",
        name: str = "MA_Crossover",
    ):
        super().__init__(name)
        self.fast_window = fast_window
        self.slow_window = slow_window
        self.stock_id = stock_id

    def generate_signals(self, df: pd.DataFrame) -> List[Order]:
        from analysis.indicators.technical import add_moving_averages

        df = add_moving_averages(df, [self.fast_window, self.slow_window])
        fast_col = f"sma_{self.fast_window}"
        slow_col = f"sma_{self.slow_window}"

        if fast_col not in df.columns or slow_col not in df.columns:
            return []

        in_position = False
        orders = []
        for i in range(1, len(df)):
            prev_fast = df[fast_col].iloc[i - 1]
            prev_slow = df[slow_col].iloc[i - 1]
            curr_fast = df[fast_col].iloc[i]
            curr_slow = df[slow_col].iloc[i]

            if pd.isna(prev_fast) or pd.isna(prev_slow):
                continue

            if prev_fast <= prev_slow and curr_fast > curr_slow and not in_position:
                orders.append(Order(
                    date=df["date"].iloc[i].date(),
                    stock_id=self.stock_id,
                    signal="BUY",
                    confidence=0.8,
                ))
                in_position = True
            elif prev_fast >= prev_slow and curr_fast < curr_slow and in_position:
                orders.append(Order(
                    date=df["date"].iloc[i].date(),
                    stock_id=self.stock_id,
                    signal="SELL",
                    confidence=0.8,
                ))
                in_position = False

        return orders
