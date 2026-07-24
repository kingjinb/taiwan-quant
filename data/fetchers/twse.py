"""
TWSE (鍙版咕璇佸埜浜ゆ槗鎵€) data fetcher.
Directly scrapes from TWSE public APIs - no account required.
"""
from __future__ import annotations
import time
from datetime import date, datetime, timedelta
from typing import List, Optional
import requests
import pandas as pd
from data.fetchers.base import BaseFetcher
from config.settings import settings
import numpy as np


class TWSEFetcher(BaseFetcher):
    """Fetch Taiwan stock data from TWSE/TPEX public endpoints."""

    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
        })
        cfg = settings.twse
        self.timeout = cfg.request_timeout
        self.retry = cfg.retry_times
        self.retry_delay = cfg.retry_delay

    def _request(self, url: str, params: dict) -> Optional[dict]:
        """Send HTTP request with retry logic."""
        for attempt in range(self.retry):
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                if data.get("stat") == "OK":
                    return data
                return None
            except (requests.RequestException, ValueError):
                if attempt < self.retry - 1:
                    time.sleep(self.retry_delay)
        return None

    def fetch_daily_prices(
        self,
        stock_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        """
        Fetch daily OHLCV from TWSE.

        TWSE API returns month-by-month data. We iterate through
        the date range and consolidate.
        """
        start_date = start_date or date.today() - timedelta(days=365)
        end_date = end_date or date.today()

        all_rows = []
        current = date(start_date.year, start_date.month, 1)

        while current <= end_date:
            params = {
                "response": "json",
                "date": current.strftime("%Y%m%d"),
                "stockNo": stock_id,
            }
            # Determine which endpoint based on market
            url = settings.twse.market_data_url
            if stock_id.startswith("6") and len(stock_id) == 4:
                # 涓婃煖 stocks use TPEX
                url = "https://www.tpex.org.tw/web/stock/aftertrading/" \
                      "daily_trading_info/st43_result.php"
                params = {
                    "d": current.strftime("%Y/%m/%d"),
                    "stkno": stock_id,
                }

            data = self._request(url, params)
            if data and "data" in data and data["data"]:
                for row in data["data"]:
                    all_rows.append(row)

            # Move to next month
            if current.month == 12:
                current = date(current.year + 1, 1, 1)
            else:
                current = date(current.year, current.month + 1, 1)

        if not all_rows:
            return pd.DataFrame()

        df = self._parse_twse_rows(all_rows, stock_id)
        # Filter by actual date range
        df = df[(df["date"] >= pd.Timestamp(start_date)) &
                (df["date"] <= pd.Timestamp(end_date))]
        return df.reset_index(drop=True)

    def _parse_twse_rows(self, rows: list, stock_id: str) -> pd.DataFrame:
        """Parse TWSE raw CSV-like rows into a clean DataFrame."""
        records = []
        for row in rows:
            try:
                date_str = row[0]
                # TWSE format: "113/01/02" (姘戝浗骞?
                parts = date_str.split("/")
                if len(parts) == 3:
                    y = int(parts[0]) + 1911 if int(parts[0]) < 2000 else int(parts[0])
                    dt = datetime(y, int(parts[1]), int(parts[2]))
                else:
                    dt = pd.to_datetime(date_str)

                records.append({
                    "stock_id": stock_id,
                    "date": dt,
                    "volume": float(row[1].replace(",", "")),
                    "turnover": float(row[2].replace(",", "")),
                    "open": float(row[3].replace(",", "")),
                    "high": float(row[4].replace(",", "")),
                    "low": float(row[5].replace(",", "")),
                    "close": float(row[6].replace(",", "")),
                })
            except (IndexError, ValueError):
                continue

        df = pd.DataFrame(records)
        if not df.empty:
            df = df.sort_values("date").reset_index(drop=True)
        return df

    def fetch_stock_list(self) -> pd.DataFrame:
        """Fetch basic stock listing info from TWSE."""
        url = "https://www.twse.com.tw/zh/api/code/get"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.encoding = "utf-8"
            data = resp.json()
            records = []
            for item in data:
                parts = item.split("\t")
                if len(parts) >= 2:
                    records.append({
                        "stock_id": parts[0].strip(),
                        "stock_name": parts[1].strip(),
                    })
            return pd.DataFrame(records)
        except (requests.RequestException, ValueError) as e:
            # Fallback to static list
            return pd.DataFrame({
                "stock_id": settings.DEFAULT_STOCK_LIST,
                "stock_name": [settings.STOCK_NAME_MAP.get(s, "")
                               for s in settings.DEFAULT_STOCK_LIST],
            })

    def fetch_realtime_quote(self, stock_id: str) -> Optional[dict]:
        """Fetch real-time quote from TWSE MIS system."""
        url = f"{settings.twse.mis_data_url}/getStockInfo.jsp"
        params = {"ex_ch": f"tse_{stock_id}.tw", "json": "1", "delay": "0"}
        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            data = resp.json()
            if "msgArray" in data and data["msgArray"]:
                msg = data["msgArray"][0]
                return {
                    "stock_id": stock_id,
                    "name": msg.get("n", ""),
                    "price": float(msg.get("z", "0")),
                    "high": float(msg.get("h", "0")),
                    "low": float(msg.get("l", "0")),
                    "open": float(msg.get("o", "0")),
                    "volume": int(msg.get("v", "0")),
                    "change": float(msg.get("d", "0")) if msg.get("d") else 0,
                    "timestamp": msg.get("t", ""),
                }
        except (requests.RequestException, ValueError, KeyError):
            return None
        return None


class MockFetcher(BaseFetcher):
    """Generates synthetic data for development/testing.
       No network access needed.
    """

    def fetch_daily_prices(
        self,
        stock_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        start = pd.Timestamp(start_date or date.today() - timedelta(days=365))
        end = pd.Timestamp(end_date or date.today())
        dates = pd.date_range(start, end, freq="B")  # business days only
        n = len(dates)
        base_price = {"2330": 600, "2317": 100, "2454": 800}.get(stock_id, 100)
        noise = pd.Series(
            (pd.Series(range(n)) * 0.01 + np.random.randn(n)).cumsum()
        )
        closes = base_price + noise * 2
        df = pd.DataFrame({
            "stock_id": stock_id,
            "date": dates,
            "open": closes + np.random.randn(n),
            "high": closes + abs(np.random.randn(n)) * 3,
            "low": closes - abs(np.random.randn(n)) * 3,
            "close": closes,
            "volume": np.random.randint(1000, 50000, n) * 1000,
        })
        return df.reset_index(drop=True)

    def fetch_stock_list(self) -> pd.DataFrame:
        return pd.DataFrame({
            "stock_id": settings.DEFAULT_STOCK_LIST,
            "stock_name": [settings.STOCK_NAME_MAP.get(s, "")
                           for s in settings.DEFAULT_STOCK_LIST],
        })




__all__ = ["TWSEFetcher", "MockFetcher"]

