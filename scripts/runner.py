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

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(str(ROOT))

OUTPUT_DIR = ROOT / "reports"
OUTPUT_DIR.mkdir(exist_ok=True)


def run_pipeline():
    print("=" * 50)
    print("Taiwan Quant Platform - GitHub Actions Runner")
    print(f"Date: {date.today().isoformat()}")
    print("=" * 50)

    # 1. Fetch data
    print("\n[1] Fetching stock data...")
    from data.fetchers.twse import TWSEFetcher, MockFetcher
    from config.settings import DEFAULT_STOCK_LIST

    import urllib.request
    use_mock = True
    try:
        # Quick connectivity test (3s timeout)
        r = urllib.request.urlopen(
            "https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date=20260701&stockNo=2330",
            timeout=3
        )
        data = json.loads(r.read().decode())
        if data.get("stat") == "OK":
            fetcher = TWSEFetcher()
            print("   Using TWSEFetcher (live data)")
            use_mock = False
        else:
            raise Exception("TWSE API not available")
    except Exception:
        fetcher = MockFetcher()
        print("   Using MockFetcher (simulated data)")

    # Fetch top stocks
    end = date.today()
    start = end - timedelta(days=365)
    all_data = {}
    for sid in DEFAULT_STOCK_LIST[:10]:  # Top 10 for speed
        df = fetcher.fetch_daily_prices(sid, start, end)
        if not df.empty:
            all_data[sid] = df.to_dict("records")
        print(f"   {sid}: {len(df)} rows")

    # 2. Compute indicators for a sample stock (2330)
    print("\n[2] Computing technical indicators...")
    from analysis.indicators.technical import compute_all
    from data.processors.cleaner import clean_price_data

    sample_df = clean_price_data(fetcher.fetch_daily_prices("2330", start, end))
    if not sample_df.empty:
        df_tech = compute_all(sample_df)
        latest = df_tech.iloc[-1].to_dict()
        # Convert to JSON-serializable
        indicators = {}
        for k, v in latest.items():
            try:
                json.dumps(v)
                indicators[k] = v
            except (TypeError, OverflowError):
                indicators[k] = str(v)
        save_report("indicators_2330.json", indicators)
        print(f"   Latest indicators for 2330 saved")

    # 3. Factor scoring
    print("\n[3] Computing multi-factor scores...")
    from analysis.factors.composite import (
        FactorRegistry, register_default_factors, compute_score,
        TWSE_DEFAULT_WEIGHTS,
    )
    registry = FactorRegistry()
    register_default_factors(registry)
    if not sample_df.empty:
        df_factors = registry.compute(df_tech.copy())
        df_scored = compute_score(df_factors, TWSE_DEFAULT_WEIGHTS)
        if "composite_score" in df_scored.columns:
            score_history = df_scored[["date", "composite_score"]].tail(60)
            score_history["date"] = score_history["date"].astype(str)
            save_report("factor_scores_2330.json", score_history.to_dict("records"))

    # 4. Generate summary
    print("\n[4] Generating summary report...")
    summary = {
        "date": date.today().isoformat(),
        "data_source": "mock" if use_mock else "twse",
        "stocks_fetched": len(all_data),
        "stocks": list(all_data.keys()),
        "latest_indicators": indicators if sample_df.empty is False else {},
    }
    save_report("summary.json", summary)

    # 5. Generate HTML report
    print("\n[5] Generating HTML report...")
    generate_html_report(summary, indicators if sample_df.empty is False else {})


    # 6. Send to Feishu
    print("\n[6] Sending to Feishu...")
    webhook_url = os.environ.get("FEISHU_WEBHOOK_URL", "")
    app_id = os.environ.get("FEISHU_APP_ID", "")
    app_secret = os.environ.get("FEISHU_APP_SECRET", "")
    chat_id = os.environ.get("FEISHU_CHAT_ID", "")

    sent = False
    if app_id and app_secret and chat_id:
        try:
            from notification.feishu import build_quant_card, send_card_with_app
            with open(OUTPUT_DIR / "summary.json") as f:
                summary = json.load(f)
            ind_path = OUTPUT_DIR / "indicators_2330.json"
            indicators = {}
            if ind_path.exists():
                with open(ind_path) as f: indicators = json.load(f)
            fs_path = OUTPUT_DIR / "factor_scores_2330.json"
            factor_scores = []
            if fs_path.exists():
                with open(fs_path) as f: factor_scores = json.load(f)
            pages_url = os.environ.get("PAGES_URL", "")
            elements = build_quant_card(
                date_str=date.today().isoformat(),
                summary=summary,
                indicators=indicators,
                factor_scores=factor_scores,
                pages_url=pages_url,
            )
            ok = send_card_with_app(app_id, app_secret, chat_id, "台湾量化日报", elements)
            if ok:
                print("   Feishu card sent via app!")
                sent = True
        except Exception as e:
            print(f"   Feishu app error: {e}")

    if not sent and webhook_url:
        try:
            from notification.feishu import build_quant_card, send_card
            with open(OUTPUT_DIR / "summary.json") as f:
                summary = json.load(f)
            ind_path = OUTPUT_DIR / "indicators_2330.json"
            indicators = {}
            if ind_path.exists():
                with open(ind_path) as f: indicators = json.load(f)
            fs_path = OUTPUT_DIR / "factor_scores_2330.json"
            factor_scores = []
            if fs_path.exists():
                with open(fs_path) as f: factor_scores = json.load(f)
            pages_url = os.environ.get("PAGES_URL", "")
            elements = build_quant_card(
                date_str=date.today().isoformat(),
                summary=summary,
                indicators=indicators,
                factor_scores=factor_scores,
                pages_url=pages_url,
            )
            ok = send_card(webhook_url, "台湾量化日报", elements)
            print("   Feishu card sent!" if ok else "   Failed to send")
            sent = ok
        except Exception as e:
            print(f"   Feishu error: {e}")

    if not sent:
        print("   Skipped (no Feishu credentials)")

        print("\nDone! All reports saved to:", OUTPUT_DIR)


def save_report(filename: str, data):
    path = OUTPUT_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    print(f"   Saved: {path}")


def generate_html_report(summary: dict, indicators: dict):
    html = [
        "<html><head><meta charset='utf-8'>",
        "<title>Taiwan Quant Report</title>",
        "<style>body{font-family:sans-serif;max-width:800px;margin:auto;padding:20px}",
        "h1{color:#1a73e8}.card{border:1px solid #ddd;border-radius:8px;padding:16px;margin:12px 0}",
        ".metric{display:inline-block;margin:8px 16px;text-align:center}",
        ".metric .value{font-size:24px;font-weight:bold}.metric .label{color:#666;font-size:12px}</style></head><body>",
        f"<h1>台湾量化日报 - {summary['date']}</h1>",
        "<div class='card'><h2>运行摘要</h2>",
        f"<p>数据源: {'模拟' if summary['data_source']=='mock' else 'TWSE实时'}</p>",
        f"<p>获取股票数: {summary['stocks_fetched']}</p>",
        "</div>",
    ]

    if indicators:
        html.append("<div class='card'><h2>台积电(2330) 最新指标</h2>")
        for key, val in indicators.items():
            if isinstance(val, (int, float)):
                html.append(
                    f"<div class='metric'><div class='value'>{val:.2f}</div>"
                    f"<div class='label'>{key}</div></div>"
                )
        html.append("</div>")

    html.append(
        "<p style='color:#999;font-size:12px;margin-top:40px'>"
        "Generated by Taiwan Quant Platform · GitHub Actions</p>"
    )
    html.append("</body></html>")

    with open(OUTPUT_DIR / "report.html", "w", encoding="utf-8") as f:
        f.write("\n".join(html))
    print("   Saved: report.html")


if __name__ == "__main__":
    run_pipeline()



