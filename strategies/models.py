"""
Data models for stock recommendations.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class Recommendation:
    """A single stock recommendation with full trade parameters."""
    stock_id: str
    stock_name: str
    analysis_date: date
    entry_price: float
    target_price: float
    stop_loss: float
    rr_ratio: float
    holding_days: int
    confidence: str
    score: float
    reason: str
    indicators: dict = field(default_factory=dict)

    @property
    def potential_profit_pct(self) -> float:
        return round((self.target_price / self.entry_price - 1) * 100, 2)

    @property
    def potential_loss_pct(self) -> float:
        return round((1 - self.stop_loss / self.entry_price) * 100, 2)

    def to_dict(self) -> dict:
        return {
            "stock_id": self.stock_id,
            "stock_name": self.stock_name,
            "analysis_date": self.analysis_date.isoformat(),
            "entry_price": round(self.entry_price, 2),
            "target_price": round(self.target_price, 2),
            "stop_loss": round(self.stop_loss, 2),
            "rr_ratio": round(self.rr_ratio, 2),
            "holding_days": self.holding_days,
            "confidence": self.confidence,
            "score": round(self.score, 1),
            "reason": self.reason,
            "potential_profit_pct": self.potential_profit_pct,
            "potential_loss_pct": self.potential_loss_pct,
        }

    def to_feishu_card_text(self) -> str:
        lines = [
            f"**{self.stock_id} {self.stock_name}**",
            f"建议买入价: {self.entry_price:.2f}",
            f"止盈目标价: {self.target_price:.2f}  ({self.potential_profit_pct:+.2f}%)",
            f"止损价:     {self.stop_loss:.2f}  ({self.potential_loss_pct:.2f}%)",
            f"R/R 比率:   {self.rr_ratio:.2f}",
            f"建议持仓:   {self.holding_days} 个交易日",
            f"信心度:     {self.confidence}",
            f"综合评分:   {self.score:.1f}",
            f"依据:       {self.reason}",
        ]
        return "\n".join(lines)
