"""
Data cleaning and preprocessing utilities.
"""
from __future__ import annotations
import pandas as pd
import numpy as np


def clean_price_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean raw price data: handle missing values, outliers, and types."""
    if df.empty:
        return df

    # Ensure correct types
    numeric_cols = ["open", "high", "low", "close", "volume"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "date" in df.columns and not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df["date"] = pd.to_datetime(df["date"])

    # Remove rows with missing OHLC
    df = df.dropna(subset=["open", "high", "low", "close"])

    # Remove zero-price rows
    df = df[df["close"] > 0]

    # Fix OHLC consistency
    df["high"] = df[["high", "open", "close"]].max(axis=1)
    df["low"] = df[["low", "open", "close"]].min(axis=1)

    # Remove duplicate dates per stock
    if "stock_id" in df.columns:
        df = df.drop_duplicates(subset=["stock_id", "date"], keep="last")

    return df.sort_values(["stock_id", "date"]).reset_index(drop=True)


def add_returns(df: pd.DataFrame) -> pd.DataFrame:
    """Add daily return and log return columns."""
    df = df.copy()
    df["return"] = df["close"].pct_change()
    df["log_return"] = np.log(df["close"] / df["close"].shift(1))
    df["return"] = df["return"].fillna(0)
    df["log_return"] = df["log_return"].fillna(0)
    return df


def resample_to_weekly(df: pd.DataFrame) -> pd.DataFrame:
    """Resample daily data to weekly (end-of-week)."""
    df = df.set_index("date")
    weekly = df.resample("W-FRI").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    })
    weekly = weekly.dropna().reset_index()
    if "stock_id" in df.columns:
        weekly["stock_id"] = df["stock_id"].iloc[0]
    return weekly


def resample_to_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """Resample daily data to monthly (end-of-month)."""
    df = df.set_index("date")
    monthly = df.resample("ME").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    })
    monthly = monthly.dropna().reset_index()
    if "stock_id" in df.columns:
        monthly["stock_id"] = df["stock_id"].iloc[0]
    return monthly
