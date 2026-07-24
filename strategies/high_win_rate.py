"""
Short-term strategy engine with Supertrend, ATR, and pullback/breakout entry.
Framework: Trend Filter → Entry Signal → ATR Stop → R/R → Score
"""
from __future__ import annotations
from datetime import date, timedelta
from typing import List, Optional
import pandas as pd
import numpy as np
from strategies.models import Recommendation
from config.settings import DEFAULT_STOCK_LIST, STOCK_NAME_MAP


class HighWinRateEngine:
    """
    Three-stage short-term strategy for Taiwan stocks.
    Stage 1: Trend Filter (Supertrend + MA alignment + volume)
    Stage 2: Entry Signal (Pullback / Breakout / Momentum)
    Stage 3: R/R & ATR Stop → Score → Rank
    """

    def __init__(
        self,
        rr_target: float = 1.2,
        max_stop_pct: float = 5.0,
        min_stop_pct: float = 1.5,
        top_n: int = 3,
        max_return_pct: float = 8.0,
        st_multiplier: float = 3.0,
        atr_period: int = 10,
        atr_stop_multiplier: float = 2.5,
        pullback_threshold: float = 2.0,
        lookback_days: int = 400,
    ):
        self.rr_target = rr_target
        self.max_stop_pct = max_stop_pct
        self.min_stop_pct = min_stop_pct
        self.top_n = top_n
        self.max_return_pct = max_return_pct
        self.st_multiplier = st_multiplier
        self.atr_period = atr_period
        self.atr_stop_multiplier = atr_stop_multiplier
        self.pullback_threshold = pullback_threshold
        self.lookback_days = lookback_days
        self.stock_name_map = STOCK_NAME_MAP

    def analyze(
        self,
        stock_id: str,
        df: pd.DataFrame,
        analysis_date: date,
    ) -> Optional[Recommendation]:
        if df.empty or len(df) < 60:
            return None

        from analysis.indicators.technical import (
            compute_all, add_supertrend, add_pullback, add_breakout
        )
        df = compute_all(df.copy())
        df = add_supertrend(df, period=self.atr_period, multiplier=self.st_multiplier)
        df = add_pullback(df)
        df = add_breakout(df)

        latest = df.iloc[-1]

        # ═══════════════════════════════════
        # Stage 1: Trend Filters (ALL must pass)
        # ═══════════════════════════════════
        close = latest.get("close", np.nan)
        sma20 = latest.get("sma_20", np.nan)
        sma60 = latest.get("sma_60", np.nan)
        rsi = latest.get("rsi", 50)
        vol_ratio = latest.get("volume_ratio", 1.0)
        supertrend = latest.get("supertrend", 0)
        atr = latest.get("atr", np.nan)

        if any(pd.isna(x) for x in [close, sma20, sma60]):
            return None

        # Filter 1: Supertrend must show uptrend
        if supertrend != 1:
            return None

        # Filter 2: Price > MA20 (short-term trend intact)
        if close <= sma20:
            return None

        # Filter 3: RSI > 45 (not too weak)
        if rsi < 45:
            return None

        # Filter 4: Volume not too low
        if vol_ratio < 1.0:
            return None

        # ═══════════════════════════════════
        # Stage 2: Entry Signals (at least 1 must pass)
        # ═══════════════════════════════════
        entry_signals = []

        # Signal A: Pullback
        dist_ma20 = latest.get("dist_to_ma20_pct", 999)
        dist_ma20_val = latest.get("dist_to_ma20_pct", 0)
        pullback = latest.get("pullback_from_high", 0)
        if 0 <= dist_ma20 <= self.pullback_threshold and pullback >= 2.0:
            entry_signals.append(("pullback", min(pullback / 5, 1.0)))

        # Signal B: Breakout
        is_breakout = latest.get("breakout", 0)
        b_strength = latest.get("breakout_strength", 0)
        if is_breakout == 1 and b_strength > 0:
            entry_signals.append(("breakout", min(b_strength / 3, 1.0)))

        # Signal C: Momentum (MACD positive + RSI rising)
        macd = latest.get("macd", 0)
        macd_signal = latest.get("macd_signal", 0)
        if macd > macd_signal and rsi > 50:
            entry_signals.append(("momentum", min((rsi - 50) / 30, 1.0)))
        # Signal D: Basic uptrend fallback
        if rsi > 55 and dist_ma20_val > 0:
            entry_signals.append(("趋势上行", min(0.5, (rsi - 50) / 40)))

        if not entry_signals:
            return None

        # Use the best entry signal weight
        max_signal_weight = max(w for _, w in entry_signals)
        signal_names = "+".join(s for s, _ in entry_signals)

        # ═══════════════════════════════════
        # Stage 3: Multi-factor Scoring
        # ═══════════════════════════════════

        # Trend alignment score (0-25)
        trend_score = min(25, max(0, (close / sma60 - 1) * 500))

        # Supertrend strength (0-20): distance above Supertrend line
        st_line = latest.get("supertrend_line", close)
        if not pd.isna(st_line) and st_line > 0:
            st_score = min(20, max(0, (close / st_line - 1) * 400))
        else:
            st_score = 10

        # Entry quality score (0-20)
        entry_score = min(20, max_signal_weight * 20)

        # Volume score (0-20)
        volume_score = min(20, max(0, vol_ratio * 10))

        # Volatility stability score (0-15)
        if not pd.isna(atr) and close > 0:
            atr_pct = atr / close * 100
            vol_score = max(0, min(15, 15 * (1 - min(atr_pct, 5) / 5)))
        else:
            vol_score = 7

        composite_score = trend_score + st_score + entry_score + volume_score + vol_score

        # Confidence
        if composite_score >= 70:
            confidence = "HIGH"
        elif composite_score >= 55:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        # ═══════════════════════════════════
        # Stage 4: ATR-based Stop + R/R Target
        # ═══════════════════════════════════
        entry_price = close

        # ATR-based stop distance: at least min_stop_pct, capped at max_stop_pct
        atr_distance = entry_price * self.max_stop_pct / 100
        if not pd.isna(atr) and atr > 0:
            atr_distance = max(atr * self.atr_stop_multiplier, entry_price * self.min_stop_pct / 100)
        atr_stop = entry_price - min(atr_distance, entry_price * self.max_stop_pct / 100)

        # Technical stop: MA60 or 10-day low
        recent_low = df["low"].rolling(10).min().iloc[-1]
        stop_loss = max(atr_stop, sma60, recent_low)

        # Calculate stop distance
        stop_distance = entry_price - stop_loss
        if stop_distance <= 0:
            return None

        # Target
        target_price = entry_price + stop_distance * self.rr_target
        max_target = entry_price * (1 + self.max_return_pct / 100)
        if target_price > max_target:
            target_price = max_target

        # Actual R/R
        rr_ratio = (target_price - entry_price) / stop_distance if stop_distance > 0 else 0
        if rr_ratio < 1.0:
            return None

        # ═══════════════════════════════════
        # Holding Period Estimate
        # ═══════════════════════════════════
        if not pd.isna(atr) and atr > 0:
            target_move = (target_price / entry_price - 1)
            holding_days = max(3, min(30, int(target_move / (atr / entry_price))))
        else:
            holding_days = 10

        # Build reason
        reasons = []
        reasons.append(f"Supertrend多头")
        if "pullback" in signal_names:
            reasons.append(f"均线回踩({dist_ma20:.1f}%)")
        if "breakout" in signal_names:
            reasons.append("突破")
        if "momentum" in signal_names:
            reasons.append("MACD转正")
        reason_str = " + ".join(reasons)

        stop_pct = round(stop_distance / entry_price * 100, 2)
        target_pct = round((target_price / entry_price - 1) * 100, 2)

        return Recommendation(
            stock_id=stock_id,
            stock_name=self.stock_name_map.get(stock_id, ""),
            analysis_date=analysis_date,
            entry_price=round(entry_price, 2),
            target_price=round(target_price, 2),
            stop_loss=round(stop_loss, 2),
            rr_ratio=round(rr_ratio, 2),
            holding_days=holding_days,
            confidence=confidence,
            score=round(composite_score, 1),
            reason=reason_str,
            indicators={
                "close": round(close, 2),
                "atr_pct": round(atr / close * 100, 2) if not pd.isna(atr) else 0,
                "rsi": round(rsi, 1),
                "supertrend": int(supertrend),
                "dist_ma20_pct": round(dist_ma20, 2) if not pd.isna(dist_ma20) else 0,
                "volume_ratio": round(vol_ratio, 2),
                "stop_pct": stop_pct,
                "target_pct": target_pct,
            },
        )

    def scan_universe(
        self,
        data_provider,
        analysis_date: date,
        stock_ids: Optional[List[str]] = None,
    ) -> List[Recommendation]:
        if stock_ids is None:
            stock_ids = [s for s in DEFAULT_STOCK_LIST if len(s) == 4]
        end = analysis_date
        start = end - timedelta(days=self.lookback_days)

        recommendations = []
        for sid in stock_ids:
            try:
                df = data_provider.fetch_daily_prices(sid, start, end)
                rec = self.analyze(sid, df, analysis_date)
                if rec:
                    recommendations.append(rec)
            except Exception:
                continue

        recommendations.sort(key=lambda r: r.score, reverse=True)
        return recommendations[:self.top_n]