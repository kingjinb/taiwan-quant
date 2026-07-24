"""
Local CSV-based data storage.
"""
from __future__ import annotations
from datetime import date, timedelta
from pathlib import Path
from typing import Optional
import pandas as pd
from config.settings import settings


class CSVStore:
    """Stores and retrieves stock data as CSV files."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or settings.storage.raw_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _file_path(self, stock_id: str) -> Path:
        return self.base_dir / f"{stock_id}.csv"

    def save(self, stock_id: str, df: pd.DataFrame) -> None:
        """Append or overwrite stock data."""
        path = self._file_path(stock_id)
        if path.exists():
            existing = pd.read_csv(path, parse_dates=["date"])
            df = pd.concat([existing, df], ignore_index=True)
            df = df.drop_duplicates(subset=["date"], keep="last")
            df = df.sort_values("date")
        df.to_csv(path, index=False, encoding="utf-8")

    def load(
        self,
        stock_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        path = self._file_path(stock_id)
        if not path.exists():
            return pd.DataFrame()
        df = pd.read_csv(path, parse_dates=["date"])
        if start_date:
            df = df[df["date"] >= pd.Timestamp(start_date)]
        if end_date:
            df = df[df["date"] <= pd.Timestamp(end_date)]
        return df.sort_values("date").reset_index(drop=True)

    def needs_update(self, stock_id: str, max_age_days: int = 1) -> bool:
        """Check if cached data needs refreshing."""
        path = self._file_path(stock_id)
        if not path.exists():
            return True
        df = pd.read_csv(path, parse_dates=["date"])
        if df.empty:
            return True
        last_date = df["date"].max()
        # TWSE only has data on business days
        return (date.today() - last_date.date()) > timedelta(days=max_age_days)

    def list_stored(self) -> list:
        """List all stock IDs with cached data."""
        return [p.stem for p in self.base_dir.glob("*.csv")]

    def delete(self, stock_id: str) -> None:
        """Remove cached data for a stock."""
        path = self._file_path(stock_id)
        if path.exists():
            path.unlink()
