"""
Taiwan Quant Platform - Streamlit Dashboard
Entry point that ties together data, analysis, backtesting, and strategies.
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date, timedelta

st.set_page_config(
    page_title="台湾股票量化平台",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("台湾股票量化分析平台")
st.markdown("---")


# ========== SIDEBAR ==========
st.sidebar.header("设置")

# Data source selection
data_source = st.sidebar.selectbox(
    "数据源",
    ["模拟数据 (无需网络)", "TWSE 公开数据"],
    help="模拟数据用于开发测试，TWSE 需要网络连接",
)

# Stock selection
from config.settings import DEFAULT_STOCK_LIST, STOCK_NAME_MAP

stock_ids = [s for s in DEFAULT_STOCK_LIST if len(s) == 4]
stock_labels = [f"{s} - {STOCK_NAME_MAP.get(s, '')}" for s in stock_ids]
selected_label = st.sidebar.selectbox("选择股票", stock_labels, index=0)
selected_stock = stock_ids[stock_labels.index(selected_label)]

# Date range
st.sidebar.subheader("日期范围")
end_date = date.today()
start_date = end_date - timedelta(days=365)
start_date = st.sidebar.date_input("开始日期", start_date)
end_date = st.sidebar.date_input("结束日期", end_date)


# ========== DATA LOADING ==========
@st.cache_data(ttl=3600)
def load_data(stock_id: str, start: date, end: date, source: str):
    if source == "模拟数据 (无需网络)":
        from data.fetchers.twse import MockFetcher
        fetcher = MockFetcher()
    else:
        from data.fetchers.twse import TWSEFetcher
        fetcher = TWSEFetcher()
    df = fetcher.fetch_daily_prices(stock_id, start, end)
    if df.empty:
        return df
    from data.processors.cleaner import clean_price_data, add_returns
    df = clean_price_data(df)
    df = add_returns(df)
    return df


with st.spinner("加载数据中..."):
    df = load_data(selected_stock, start_date, end_date, data_source)

if df.empty:
    st.warning(f"未获取到 {selected_stock} 的数据。请检查股票代码或使用模拟数据。")
    st.stop()


# ========== MAIN DASHBOARD ==========

# ---- Row 1: Key Metrics ----
st.subheader("关键指标")
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    latest = df.iloc[-1]
    st.metric("最新收盘价", f'{latest["close"]:.2f}', f'{latest.get("return", 0)*100:.2f}%')
with col2:
    high_52w = df["high"].max()
    st.metric("52周最高", f"{high_52w:.2f}")
with col3:
    low_52w = df["low"].min()
    st.metric("52周最低", f"{low_52w:.2f}")
with col4:
    avg_vol = int(df["volume"].mean())
    st.metric("日均成交量", f"{avg_vol:,}")
with col5:
    total_ret = (df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100
    st.metric("区间涨幅", f"{total_ret:.2f}%")

# ---- Row 2: Price Chart with Technicals ----
st.subheader("技术分析图表")

from analysis.indicators.technical import compute_all

df_tech = compute_all(df.copy())

fig = make_subplots(
    rows=3, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.05,
    row_heights=[0.5, 0.25, 0.25],
    subplot_titles=("价格与均线", "成交量", "RSI"),
)

# Candlestick chart
fig.add_trace(
    go.Candlestick(
        x=df_tech["date"],
        open=df_tech["open"],
        high=df_tech["high"],
        low=df_tech["low"],
        close=df_tech["close"],
        name="K线",
    ),
    row=1, col=1,
)

# Moving averages
if "sma_20" in df_tech.columns:
    fig.add_trace(go.Scatter(
        x=df_tech["date"], y=df_tech["sma_20"],
        line=dict(color="orange", width=1), name="MA20",
    ), row=1, col=1)
if "sma_60" in df_tech.columns:
    fig.add_trace(go.Scatter(
        x=df_tech["date"], y=df_tech["sma_60"],
        line=dict(color="blue", width=1), name="MA60",
    ), row=1, col=1)

# Volume bars
colors = ["red" if c >= o else "green" for c, o in
          zip(df_tech["close"], df_tech["open"])]
fig.add_trace(
    go.Bar(x=df_tech["date"], y=df_tech["volume"],
           marker_color=colors, name="成交量", opacity=0.6),
    row=2, col=1,
)

# RSI
if "rsi" in df_tech.columns:
    fig.add_trace(
        go.Scatter(x=df_tech["date"], y=df_tech["rsi"],
                   line=dict(color="purple", width=1), name="RSI"),
        row=3, col=1,
    )
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

fig.update_layout(height=700, showlegend=True, xaxis_rangeslider_visible=False)
st.plotly_chart(fig, use_container_width=True)

# ---- Row 3: Technical Indicators Table ----
st.subheader("最新技术指标")
latest_tech = df_tech.iloc[-1]
indicator_cols = {
    "RSI(14)": f'{latest_tech.get("rsi", "N/A"):.1f}',
    "MACD": f'{latest_tech.get("macd", "N/A"):.3f}',
    "MACD Signal": f'{latest_tech.get("macd_signal", "N/A"):.3f}',
    "K值": f'{latest_tech.get("k", "N/A"):.1f}',
    "D值": f'{latest_tech.get("d", "N/A"):.1f}',
    "布林上轨": f'{latest_tech.get("bb_upper", "N/A"):.2f}',
    "布林下轨": f'{latest_tech.get("bb_lower", "N/A"):.2f}',
    "成交量比": f'{latest_tech.get("volume_ratio", "N/A"):.2f}',
}
cols = st.columns(len(indicator_cols))
for i, (name, val) in enumerate(indicator_cols.items()):
    cols[i].metric(name, val)

# ---- Row 4: Strategy Signals ----
st.subheader("策略信号")

col1, col2 = st.columns(2)
with col1:
    fast_ma = st.number_input("快线周期", min_value=2, max_value=50, value=5)
with col2:
    slow_ma = st.number_input("慢线周期", min_value=10, max_value=200, value=20)

if st.button("生成交易信号", type="primary"):
    from strategies.base import MACrossoverStrategy
    strategy = MACrossoverStrategy(
        fast_window=int(fast_ma),
        slow_window=int(slow_ma),
        stock_id=selected_stock,
    )
    orders = strategy.generate_signals(df.copy())
    if orders:
        o_df = pd.DataFrame([{
            "日期": o.date,
            "信号": o.signal,
            "信心度": f"{o.confidence:.0%}",
        } for o in orders])
        st.dataframe(o_df, use_container_width=True)

        # Run backtest
        if st.button("运行回测"):
            from backtest.engine import BacktestEngine
            engine = BacktestEngine()
            engine.run(df.copy(), orders)
            result = engine.summary()

            if result:
                r1, r2, r3, r4 = st.columns(4)
                r1.metric("总收益率", f'{result["total_return_pct"]:.2f}%')
                r2.metric("夏普比率", f'{result["sharpe_ratio"]:.2f}')
                r3.metric("最大回撤", f'{result["max_drawdown_pct"]:.2f}%')
                r4.metric("交易次数", result["num_trades"])

                # Equity curve
                eq_df = result["equity_curve"]
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(
                    x=eq_df["date"], y=eq_df["equity"],
                    fill="tozeroy", name="净值曲线",
                ))
                fig2.update_layout(height=400, title="回测净值曲线")
                st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("未生成交易信号")

# ---- Row 5: Factor Analysis (if enabled) ----
st.subheader("因子评分分析")
if st.checkbox("启用多因子评分"):
    from analysis.factors.composite import (
        FactorRegistry, register_default_factors, compute_score,
        TWSE_DEFAULT_WEIGHTS,
    )
    registry = FactorRegistry()
    register_default_factors(registry)
    st.write("已注册因子:", ", ".join(registry.list_factors()))

    df_factors = registry.compute(df_tech.copy())
    df_scored = compute_score(df_factors, TWSE_DEFAULT_WEIGHTS)

    if "composite_score" in df_scored.columns:
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=df_scored["date"], y=df_scored["composite_score"],
            fill="tozeroy", name="综合评分",
        ))
        fig3.add_hline(y=0, line_dash="dash", line_color="gray")
        fig3.update_layout(height=300, title="多因子综合评分走势")
        st.plotly_chart(fig3, use_container_width=True)

# ---- Footer ----
st.markdown("---")
st.caption("免责声明：本平台仅供研究学习使用，不构成任何投资建议。")
