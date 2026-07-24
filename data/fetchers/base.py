"""
Abstract base class for all data fetchers.
Defines a uniform interface regardless of data source.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional
import pandas as pd


class BaseFetcher(ABC):
    """All data fetchers inherit from this."""

    @abstractmethod
    def fetch_daily_prices(
        self,
        stock_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        """
        Fetch daily OHLCV data.

        Returns DataFrame with columns:
        date, open, high, low, close, volume, stock_id
        """
        ...

    @abstractmethod
    def fetch_stock_list(self) -> pd.DataFrame:
        """
        Fetch all available stock IDs and names.

        Returns DataFrame with columns: stock_id, stock_name, market
        """
        ...

    def fetch_batch(
        self,
        stock_ids: List[str],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        """Fetch multiple stocks and concatenate into one DataFrame."""
        dfs = []
        for sid in stock_ids:
            df = self.fetch_daily_prices(sid, start_date, end_date)
            dfs.append(df)
        return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
