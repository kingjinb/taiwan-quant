"""
Prediction tracker for strategy performance monitoring.
Saves recommendations and tracks win/loss rates.
"""
from __future__ import annotations
from pathlib import Path
from datetime import date
from typing import Optional
import json


def load_predictions(path: Path) -> list[dict]:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []


def save_predictions(path: Path, predictions: list[dict]):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(predictions, f, ensure_ascii=False, indent=2)


def add_predictions(predictions: list[dict], recs: list[dict]) -> list[dict]:
    for rec in recs:
        existing = [p for p in predictions if p.get("stock_id") == rec.get("stock_id") and p.get("status") == "pending"]
        if not existing:
            predictions.append({
                "stock_id": rec.get("stock_id"),
                "stock_name": rec.get("stock_name", ""),
                "date": rec.get("analysis_date", ""),
                "entry_price": rec.get("entry_price"),
                "target_price": rec.get("target_price"),
                "stop_loss": rec.get("stop_loss"),
                "rr_ratio": rec.get("rr_ratio"),
                "holding_days": rec.get("holding_days", 3),
                "confidence": rec.get("confidence", "MEDIUM"),
                "reason": rec.get("reason", ""),
                "status": "pending",
                "result_price": None,
                "pnl_pct": None,
            })
    return predictions


def check_predictions(predictions: list[dict], price_data: dict[str, float]) -> list[dict]:
    for pred in predictions:
        if pred.get("status") != "pending":
            continue
        sid = pred.get("stock_id")
        close = price_data.get(sid)
        if close is None:
            continue
        target = pred.get("target_price")
        stop = pred.get("stop_loss")
        if target and close >= target:
            pred["status"] = "hit_target"
            pred["result_price"] = close
            pred["pnl_pct"] = round((close / pred["entry_price"] - 1) * 100, 2)
        elif stop and close <= stop:
            pred["status"] = "hit_stop"
            pred["result_price"] = close
            pred["pnl_pct"] = round((close / pred["entry_price"] - 1) * 100, 2)
    return predictions


def compute_stats(predictions: list[dict]) -> dict:
    resolved = [p for p in predictions if p.get("status") in ("hit_target", "hit_stop")]
    if not resolved:
        return {"total": len(predictions), "resolved": 0, "wr": 0, "avg_win": 0, "avg_loss": 0, "pf": 0}
    wins = [p for p in resolved if p.get("pnl_pct", 0) > 0]
    losses = [p for p in resolved if p.get("pnl_pct", 0) <= 0]
    wr = len(wins) / len(resolved) * 100
    aw = sum(p["pnl_pct"] for p in wins) / len(wins) if wins else 0
    al = sum(p["pnl_pct"] for p in losses) / len(losses) if losses else 0
    pf = abs(aw / al) if al != 0 else 0
    return {
        "total": len(predictions),
        "resolved": len(resolved),
        "pending": sum(1 for p in predictions if p.get("status") == "pending"),
        "wr": round(wr, 1),
        "avg_win": round(aw, 2),
        "avg_loss": round(al, 2),
        "pf": round(pf, 2),
    }
