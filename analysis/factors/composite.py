"""
Multi-factor scoring system customized for Taiwan stock market.
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Dict, List


class FactorRegistry:
    """Registry of named factor computations."""

    def __init__(self):
        self._factors: Dict[str, callable] = {}

    def register(self, name: str, func: callable):
        self._factors[name] = func

    def compute(self, df: pd.DataFrame, factor_names: List[str] = None) -> pd.DataFrame:
        if factor_names is None:
            factor_names = list(self._factors.keys())
        for name in factor_names:
            if name in self._factors:
                df = self._factors[name](df)
        return df

    def list_factors(self) -> List[str]:
        return list(self._factors.keys())


def register_default_factors(registry: FactorRegistry):
    """Register a set of default factors relevant for TWSE."""

    def momentum_1m(df):
        df["factor_mom_1m"] = df["close"].pct_change(21)
        return df

    def momentum_3m(df):
        df["factor_mom_3m"] = df["close"].pct_change(63)
        return df

    def momentum_6m(df):
        df["factor_mom_6m"] = df["close"].pct_change(126)
        return df

    def rsi_mean_rev(df):
        if "rsi" not in df.columns:
            from analysis.indicators.technical import add_rsi
            df = add_rsi(df)
        df["factor_rsi_rev"] = (50 - df["rsi"]) / 50
        return df

    def volume_surge(df):
        if "volume_ratio" not in df.columns:
            from analysis.indicators.technical import add_volume_indicators
            df = add_volume_indicators(df)
        df["factor_volume_surge"] = df["volume_ratio"]
        return df

    def trend_strength(df):
        if "sma_20" not in df.columns:
            from analysis.indicators.technical import add_moving_averages
            df = add_moving_averages(df, [20, 60])
        df["factor_trend"] = (df["sma_20"] - df["sma_60"]) / df["sma_60"]
        return df

    def volatility(df):
        if "return" in df.columns:
            df["factor_volatility"] = df["return"].rolling(20).std()
        else:
            df["factor_volatility"] = np.nan
        return df

    def price_vs_ma(df):
        if "sma_20" not in df.columns:
            from analysis.indicators.technical import add_moving_averages
            df = add_moving_averages(df, [20, 60])
        df["factor_price_vs_ma20"] = df["close"] / df["sma_20"] - 1
        df["factor_price_vs_ma60"] = df["close"] / df["sma_60"] - 1
        return df

    for name, func in [
        ("momentum_1m", momentum_1m),
        ("momentum_3m", momentum_3m),
        ("momentum_6m", momentum_6m),
        ("rsi_mean_rev", rsi_mean_rev),
        ("volume_surge", volume_surge),
        ("trend_strength", trend_strength),
        ("volatility", volatility),
        ("price_vs_ma", price_vs_ma),
    ]:
        registry.register(name, func)


def compute_score(df: pd.DataFrame, factors: Dict[str, float]) -> pd.DataFrame:
    """Build a composite score from weighted factors (z-score normalized)."""
    df = df.copy()
    df["_score"] = 0.0
    for factor_name, weight in factors.items():
        col = f"factor_{factor_name}" if not factor_name.startswith("factor_") else factor_name
        if col not in df.columns:
            continue
        mean = df[col].mean()
        std = df[col].std()
        if std > 0:
            z = (df[col] - mean) / std
            z = z.clip(-3, 3)
            df["_score"] += z * weight
    df["composite_score"] = df["_score"]
    df = df.drop(columns=["_score"])
    return df


TWSE_DEFAULT_WEIGHTS: Dict[str, float] = {
    "momentum_1m": 0.15,
    "momentum_3m": 0.10,
    "momentum_6m": 0.05,
    "rsi_mean_rev": 0.15,
    "volume_surge": 0.15,
    "trend_strength": 0.20,
    "volatility": -0.05,
    "price_vs_ma": 0.15,
}
