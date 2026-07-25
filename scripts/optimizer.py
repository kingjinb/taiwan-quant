"""
Auto optimizer: runs grid search on historical data to find optimal strategy parameters.
"""
from __future__ import annotations
import sys
import os
from pathlib import Path
from datetime import date, timedelta
import json
import itertools

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from data.fetchers.twse import TWSEFetcher
from analysis.indicators.technical import compute_all
from data.processors.cleaner import add_returns
from config.settings import DEFAULT_STOCK_LIST

GRID = {
    "rr_target": [1.0, 1.2, 1.5],
    "max_stop_pct": [4.0, 5.0],
    "min_stop_pct": [1.0, 1.5],
    "atr_stop_multiplier": [2.0, 2.5, 3.0],
}

STOCK_IDS = [s for s in DEFAULT_STOCK_LIST if len(s) == 4][:15]
DAYS = 500


def fetch_and_precompute():
    """Fetch data for all stocks and pre-compute indicators."""
    fetcher = TWSEFetcher()
    cache = {}
    today = date.today()
    start = today - timedelta(days=DAYS)
    for sid in STOCK_IDS:
        try:
            df = fetcher.fetch_daily_prices(sid, start, today)
            if df.empty or len(df) < 60:
                continue
            df = add_returns(df)
            df = compute_all(df)
            cache[sid] = df
            print(f"   {sid}: {len(df)} days")
        except Exception as e:
            print(f"   {sid}: error - {str(e)[:50]}")
    return cache


def run_backtest(cache, params):
    total_trades = 0
    wins = 0
    pnls = []
    for sid, df in cache.items():
        for i in range(200, len(df)):
            bar = df.iloc[i]
            close = bar["close"]
            if any(pd.isna(x) for x in [bar.get("sma_20", 0), bar.get("sma_60", 0), bar.get("rsi", 0)]):
                continue
            if bar["supertrend"] != 1 or close <= bar["sma_20"] or bar["rsi"] < 40 or bar.get("volume_ratio", 0) < 1.0:
                continue
            atr = bar.get("atr", 0)
            atr_dist = max(atr * params["atr_stop_multiplier"], close * params["min_stop_pct"] / 100)
            stop = close - min(atr_dist, close * params["max_stop_pct"] / 100)
            risk = close - stop
            if risk <= 0:
                continue
            target = close + risk * params["rr_target"]
            for j in range(i + 1, min(i + 10, len(df))):
                future = df.iloc[j]
                if future["low"] <= stop:
                    pnls.append((stop - close) / close * 100)
                    if (stop - close) / close * 100 > -0.5:
                        wins += 1
                    total_trades += 1
                    break
                if future["high"] >= target:
                    pnls.append((target - close) / close * 100)
                    wins += 1
                    total_trades += 1
                    break
    if total_trades == 0:
        return {"trades": 0, "wr": 0, "avg_pnl": 0, "pf": 0}
    win_pnls = [p for p in pnls if p > 0]
    loss_pnls = [p for p in pnls if p <= 0]
    wr = wins / total_trades * 100
    aw = sum(win_pnls) / len(win_pnls) if win_pnls else 0
    al = sum(loss_pnls) / len(loss_pnls) if loss_pnls else 0
    ap = sum(pnls) / total_trades
    pf = abs(aw / al) if al != 0 else 0
    return {"trades": total_trades, "wr": round(wr, 1), "avg_pnl": round(ap, 2), "pf": round(pf, 2)}


import pandas as pd  # noqa


def grid_search(cache):
    keys = list(GRID.keys())
    values = list(GRID.values())
    results = []
    for combo in itertools.product(*values):
        params = dict(zip(keys, combo))
        r = run_backtest(cache, params)
        results.append((params, r))
    return results


def save_params(params, metrics):
    path = ROOT / "config" / "params.json"
    data = {
        "rr_target": params["rr_target"],
        "max_stop_pct": params["max_stop_pct"],
        "min_stop_pct": params["min_stop_pct"],
        "atr_stop_multiplier": params["atr_stop_multiplier"],
        "optimized_date": date.today().isoformat(),
        "optimized_metrics": metrics,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"   Saved to {path}")


def main():
    print("=" * 55)
    print("AUTO OPTIMIZER - Grid Search")
    total_combos = len(list(itertools.product(*GRID.values())))
    print(f"Stocks: {len(STOCK_IDS)}, Combos: {total_combos}, Days: {DAYS}")
    print("=" * 55)
    print("\n[1] Fetching and pre-computing...")
    cache = fetch_and_precompute()
    print(f"   {len(cache)} stocks cached")
    if len(cache) < 3:
        print("ERROR: Too few stocks. Aborting.")
        return
    print("\n[2] Running grid search...")
    results = grid_search(cache)
    print(f"   {len(results)} combos completed")
    print("\n[3] Top 10 by PF:")
    print(f"{'RR':>4} {'MaxS':>4} {'MinS':>4} {'ATR':>4} | {'Trds':>5} {'WR':>5} {'AvgP':>7} {'PF':>5}")
    print("-" * 55)
    for params, r in sorted(results, key=lambda x: x[1]["pf"], reverse=True)[:10]:
        print(f"{params['rr_target']:>4.1f} {params['max_stop_pct']:>4.1f} {params['min_stop_pct']:>4.1f} {params['atr_stop_multiplier']:>4.1f} | {r['trades']:>5} {r['wr']:>5.1f} {r['avg_pnl']:>+7.2f} {r['pf']:>5.2f}")
    valid = [(p, r) for p, r in results if r["trades"] >= 30]
    if not valid:
        print("\n[4] No valid combo (min 30 trades)")
        return
    best = max(valid, key=lambda x: x[1]["pf"] * x[1]["wr"] * (x[1]["trades"] ** 0.5) / 1000)
    params, r = best
    print(f"\n[4] BEST: {params}")
    print(f"    Trades={r['trades']}, WR={r['wr']}%, Avg={r['avg_pnl']:+.2f}%, PF={r['pf']}")
    save_params(params, r)
    print("\nDone. Strategy will use these params on next run.")


if __name__ == "__main__":
    main()
