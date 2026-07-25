"""
GitHub Actions Runner for Taiwan Quant Platform.
Fetches data, runs analysis, and generates reports.
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


def run_pipeline():
    print("=" * 50)
    print("Taiwan Quant Platform - GitHub Actions Runner")
    print(f"Date: {date.today().isoformat()}")
    print("=" * 50)

    print("\n[1] Fetching stock data...")
    from data.fetchers.twse import MockFetcher
    from config.settings import DEFAULT_STOCK_LIST

    fetcher = MockFetcher()
    print("   Using MockFetcher (simulated data)")

    end = date.today()
    start = end - timedelta(days=365)
    all_data = {}
    for sid in DEFAULT_STOCK_LIST[:10]:
        df = fetcher.fetch_daily_prices(sid, start, end)
        if not df.empty:
            all_data[sid] = df.to_dict("records")
        print(f"   {sid}: {len(df)} rows")

    print("\n[1b] Running strategy engine...")
    from strategies.high_win_rate import HighWinRateEngine
    engine = HighWinRateEngine(rr_target=1.5, top_n=5, lookback_days=400)
    try:
        recs = engine.scan_universe(fetcher, date.today())
        save_report("recommendations.json", [r.to_dict() for r in recs])
        print(f"   Generated {len(recs)} recommendations")
    except Exception as e:
        print(f"   Strategy error: {e}")
        save_report("recommendations.json", [])

    print("\n[2] Generating summary...")
    summary = {
        "date": date.today().isoformat(),
        "data_source": "mock",
        "stocks_fetched": len(all_data),
        "stocks": list(all_data.keys()),
    }
    save_report("summary.json", summary)

    print("\n[3] Sending to Feishu...")
    app_id = os.environ.get("FEISHU_APP_ID", "")
    app_secret = os.environ.get("FEISHU_APP_SECRET", "")
    chat_id = os.environ.get("FEISHU_CHAT_ID", "")
    webhook_url = os.environ.get("FEISHU_WEBHOOK_URL", "")

    sent = False
    if app_id and app_secret and chat_id:
        try:
            from notification.feishu import build_quant_card, send_card_with_app

            recs_path = OUTPUT_DIR / "recommendations.json"
            recommendations = []
            if recs_path.exists():
                with open(recs_path) as f:
                    recommendations = json.load(f)

            if recommendations:
                from notification.feishu import build_recommendation_card
                elements = build_recommendation_card(
                    date_str=date.today().isoformat(),
                    next_date_str=(date.today().isoformat()),
                    recs=recommendations,
                    summary=summary,
                )
            else:
                elements = build_quant_card(
                    date_str=date.today().isoformat(),
                    summary=summary,
                    indicators={},
                    factor_scores=[],
                )
            ok = send_card_with_app(app_id, app_secret, chat_id, "台湾量化日报", elements)
            if ok:
                print("   Feishu card sent via app!")
                sent = True
        except Exception as e:
            print(f"   Feishu app error: {e}")

    if not sent:
        print("   Skipped (no Feishu credentials)")

    print("\nDone!")


def save_report(filename, data):
    path = OUTPUT_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    print(f"   Saved: {path}")


if __name__ == "__main__":
    run_pipeline()
