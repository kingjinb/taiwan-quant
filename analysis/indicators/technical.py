"""
Technical indicators for Taiwan stock analysis.
"""
from __future__ import annotations
import pandas as pd
import numpy as np


def add_moving_averages(df: pd.DataFrame, windows: list[int] = None) -> pd.DataFrame:
    df = df.copy()
    windows = windows or [5, 10, 20, 60, 120, 240]
    for w in windows:
        df[f"sma_{w}"] = df["close"].rolling(w).mean()
        df[f"ema_{w}"] = df["close"].ewm(span=w, adjust=False).mean()
    return df


def add_rsi(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0.0).rolling(window).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))
    df["rsi"] = df["rsi"].fillna(50)
    return df


def add_macd(df: pd.DataFrame) -> pd.DataFrame:
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]
    return df


def add_bollinger_bands(df: pd.DataFrame, window: int = 20, std: int = 2) -> pd.DataFrame:
    df["bb_mid"] = df["close"].rolling(window).mean()
    bb_std = df["close"].rolling(window).std()
    df["bb_upper"] = df["bb_mid"] + std * bb_std
    df["bb_lower"] = df["bb_mid"] - std * bb_std
    df["bb_width"] = df["bb_upper"] - df["bb_lower"]
    df["bb_pct"] = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])
    return df


def add_kd(df: pd.DataFrame, window: int = 9) -> pd.DataFrame:
    low_min = df["low"].rolling(window).min()
    high_max = df["high"].rolling(window).max()
    df["rsv"] = 100 * (df["close"] - low_min) / (high_max - low_min).replace(0, np.nan)
    df["k"] = df["rsv"].ewm(com=2, adjust=False).mean()
    df["d"] = df["k"].ewm(com=2, adjust=False).mean()
    return df


def add_volume_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df["volume_sma_5"] = df["volume"].rolling(5).mean()
    df["volume_sma_20"] = df["volume"].rolling(20).mean()
    df["volume_ratio"] = df["volume"] / df["volume_sma_5"].replace(0, np.nan)
    df["obv"] = (df["volume"] * (~df["close"].diff().le(0) * 2 - 1)).cumsum()
    return df



def add_atr(df, period=14):
    """Average True Range for dynamic stop loss."""
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift(1)).abs()
    low_close = (df["low"] - df["close"].shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"] = tr.rolling(period).mean()
    return df


def add_supertrend(df, period=10, multiplier=3.0):
    """Supertrend indicator for trend confirmation."""
    df = add_atr(df, period)
    hl_avg = (df["high"] + df["low"]) / 2
    bu = hl_avg + multiplier * df["atr"]
    bl = hl_avg - multiplier * df["atr"]

    fu = [0.0] * len(df)
    fl = [0.0] * len(df)
    st = [0] * len(df)

    for i in range(1, len(df)):
        b = bu.iloc[i] if not pd.isna(bu.iloc[i]) else 0
        c = bl.iloc[i] if not pd.isna(bl.iloc[i]) else 0

        if b < fu[i-1] or df["close"].iloc[i-1] > fu[i-1]:
            fu[i] = b
        else:
            fu[i] = fu[i-1]

        if c > fl[i-1] or df["close"].iloc[i-1] < fl[i-1]:
            fl[i] = c
        else:
            fl[i] = fl[i-1]

        if st[i-1] == 1:
            st[i] = -1 if df["close"].iloc[i] < fl[i] else 1
        else:
            st[i] = 1 if df["close"].iloc[i] > fu[i] else -1

    df["supertrend"] = st
    line = [fu[i] if st[i] == -1 else fl[i] for i in range(len(df))]
    import numpy as np
    df["supertrend_line"] = [np.nan if v == 0 else v for v in line]
    return df


def add_pullback(df, lookback=10):
    """Pullback detection: distance from MA20 and recent high."""
    if "sma_20" not in df.columns:
        df = add_moving_averages(df, [20])
    df["dist_to_ma20_pct"] = (df["close"] / df["sma_20"] - 1) * 100
    recent_high = df["close"].rolling(lookback).max()
    df["pullback_from_high"] = (recent_high / df["close"] - 1) * 100
    return df


def add_breakout(df, lookback=20):
    """Breakout detection: price breaks above recent high."""
    recent_high = df["high"].rolling(lookback).max().shift(1)
    df["breakout"] = (df["close"] > recent_high).astype(int)
    df["breakout_strength"] = (df["close"] / recent_high - 1) * 100
    return df

def compute_all(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = add_moving_averages(df)
    df = add_rsi(df)
    df = add_macd(df)
    df = add_bollinger_bands(df)
    df = add_kd(df)
    df = add_volume_indicators(df)
    df = add_atr(df)
    df = add_supertrend(df)
    df = add_pullback(df)
    df = add_breakout(df)
    return df
