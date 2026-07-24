"""
Simulation: daily analysis + recommendations.
Fetches "yesterday" and "today" data, recommends for "tomorrow".
"""
from __future__ import annotations
import sys
import os
from pathlib import Path
from datetime import date, timedelta

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(str(ROOT))

from data.fetchers.twse import MockFetcher
from strategies.high_win_rate import HighWinRateEngine


def simulate():
    print("=" * 64)
    print("  台湾股票量化推荐系统  模拟运行")
    print("=" * 64)

    #  Set dates 
    # Since we use mock data, "today" is just the last date in the dataset.
    # The mock data spans ~1 year, so let"s set analysis_date to the latest.
    mock = MockFetcher()
    sample = mock.fetch_daily_prices("2330")
    last_date = sample["date"].max()
    if hasattr(last_date, "date"):
        analysis_date = last_date.date()
    else:
        analysis_date = last_date

    next_trading_day = analysis_date + timedelta(days=1)
    # Skip weekends
    if next_trading_day.weekday() >= 5:
        next_trading_day = next_trading_day + timedelta(days=7 - next_trading_day.weekday())

    print(f"\n  分析基准日:  {analysis_date}  (模拟今日)")
    print(f"  推荐执行日:  {next_trading_day}  (模拟明日)")
    print(f"  数据源:      MockFetcher (模拟数据)")
    print(f"  R/R 目标:    1.2")
    print(f"  最大止损:    5%")
    print("=" * 64)

    #  Run engine 
    engine = HighWinRateEngine(
        rr_target=1.2,
        max_stop_pct=5.0,
        top_n=5,
        max_return_pct=8.0,
    )

    recs = engine.scan_universe(
        data_provider=mock,
        analysis_date=analysis_date,
    )

    #  Display results 
    if not recs:
        print("\n  今日无符合条件的推荐。")
        print("  原因: 全部股票未通过趋势/量能/RR筛选。")
        return

    print(f"\n   选出 {len(recs)} 支推荐标的\n")

    for i, rec in enumerate(recs, 1):
        print(f"   推荐 #{i} ")
        print(f"   {rec.stock_id} {rec.stock_name}")
        print(f"   信心度: {rec.confidence}  |  综合评分: {rec.score:.1f}/100")
        print(f"   交易参数 ")
        print(f"   建议买入价:  {rec.entry_price:>8.2f}")
        print(f"   止盈目标价:  {rec.target_price:>8.2f}  ({rec.potential_profit_pct:+.2f}%)")
        print(f"   止损价:      {rec.stop_loss:>8.2f}  ({rec.potential_loss_pct:.2f}%)")
        print(f"   R/R 比率:    {rec.rr_ratio:>8.2f}")
        print(f"   建议持仓:    {rec.holding_days:>4d} 个交易日")
        print(f"   依据 ")
        print(f"   {rec.reason}")
        print(f"  ")
        print()

    #  Summary Stats 
    print("   推荐统计 ")
    print(f"   入选数:          {len(recs)}")
    avg_rr = sum(r.rr_ratio for r in recs) / len(recs)
    avg_score = sum(r.score for r in recs) / len(recs)
    print(f"   平均 R/R:        {avg_rr:.2f}")
    print(f"   平均评分:        {avg_score:.1f}")
    high_conf = sum(1 for r in recs if r.confidence == "HIGH")
    print(f"   高信心度:        {high_conf}")
    print(f"   目标止损幅度:    {recs[0].potential_loss_pct:.2f}%")
    print(f"   目标获利幅度:    {recs[0].potential_profit_pct:.2f}%")
    print("  ")
    print()

    #  Feishu format preview 
    print("   飞书消息预览 ")
    print("    台湾量化推荐日报")
    print(f"   分析日期: {analysis_date}  |  执行日期: {next_trading_day}")
    print("  ")
    for rec in recs[:3]:
        for line in rec.to_feishu_card_text().split("\n"):
            print(f"   {line}")
        print("  ")
    print("    仅供参考，不构成投资建议")
    print("  ")


if __name__ == "__main__":
    simulate()


    print(f"  最小止损:    1.5%")
