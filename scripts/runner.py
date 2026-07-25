"""
GitHub Actions Runner for Taiwan Quant Platform.
"""
from __future__ import annotations
import sys
import os
from pathlib import Path
from datetime import date, timedelta
import json

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUTPUT_DIR = ROOT / "reports"
OUTPUT_DIR.mkdir(exist_ok=True)


def save_report(filename, data):
    path = OUTPUT_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    print(f"   Saved: {path}")


def run_pipeline():
    print("=" * 50)
    print("Taiwan Quant Platform - GitHub Actions Runner")
    print(f"Date: {date.today().isoformat()}")
    print("=" * 50)

    print("\n[1] Strategy engine...")
    from data.fetchers.twse import MockFetcher
    from strategies.high_win_rate import HighWinRateEngine
    from data.fetchers.twse import TWSEFetcher
    import urllib.request, ssl
    ssl._create_default_https_context = ssl._create_unverified_context
    try:
        test = urllib.request.urlopen("https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date=20260701&stockNo=2330", timeout=5)
        from data.fetchers.twse import TWSEFetcher
        fetcher = TWSEFetcher()
        print("   Using TWSEFetcher (live data)")
    except Exception:
        fetcher = MockFetcher()
        print("   Using MockFetcher (simulated data)")
    engine = HighWinRateEngine(rr_target=1.5, top_n=5, lookback_days=400)
    recs = engine.scan_universe(fetcher, date.today())
    save_report("recommendations.json", [r.to_dict() for r in recs])
    print(f"   {len(recs)} recommendations generated")

    print("\n[2] Summary...")
    save_report("summary.json", {
        "date": date.today().isoformat(),
        "data_source": "mock",
        "stocks_fetched": 10,
    })

    print("\n[3] Sending to Feishu...")
    app_id = os.environ.get("FEISHU_APP_ID", "")
    app_secret = os.environ.get("FEISHU_APP_SECRET", "")
    chat_id = os.environ.get("FEISHU_CHAT_ID", "")

    if not (app_id and app_secret and chat_id):
        print("   Skipped (no Feishu credentials)")
        return

    try:
        from notification.feishu import build_recommendation_card, send_card_with_app
        recs_path = OUTPUT_DIR / "recommendations.json"
        with open(recs_path) as f:
            recs_data = json.load(f)
        elements = build_recommendation_card(
            date_str=date.today().isoformat(),
            next_date_str=(date.today().isoformat()),
            recs=recs_data,
            summary={"data_source": "mock", "stocks_fetched": 10},
        )
        ok = send_card_with_app(app_id, app_secret, chat_id, "台湾量化日报", elements)
        print("   Feishu card sent!" if ok else "   Send failed")
    except Exception as e:
        print(f"   Error: {e}")


if __name__ == "__main__":
    run_pipeline()
