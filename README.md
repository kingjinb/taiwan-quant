# Taiwan Quant Platform

台湾股票量化分析平台 — 从数据获取到策略回测的全栈架构。

## 架构总览

```
用户界面 (Streamlit Dashboard)
        |
策略层 (MA Crossover / 多因子评分 / ML 策略)
        |
分析层 (技术指标 / 因子计算 / 综合评分)
        |
回测引擎 (事件驱动 / 绩效评估 / 净值曲线)
        |
数据层 (TWSE爬虫 / FinMind API / CSV存储)
        |
台湾证券交易所 (TWSE/TPEX 公开数据)
```

## 模块说明

| 层级 | 模块 | 功能 |
|------|------|------|
| data/fetchers | TWSE/Mock | 数据获取：TWSE 公开数据爬虫 / 模拟数据 |
| data/processors | Cleaner | 数据清洗、OHLC 修复、周/月重采样 |
| data/store | CSVStore | 本地 CSV 缓存管理 |
| analysis/indicators | 技术指标 | MA/RSI/MACD/布林带/KD/成交量指标 |
| analysis/factors | 多因子评分 | 动量/趋势/反转/量能因子的注册与评分 |
| backtest | 回测引擎 | 事件驱动回测、买卖执行、夏普/回撤计算 |
| strategies | 策略模板 | MA 交叉策略(内置)、因子策略、ML 策略(可扩展) |
| execution | 组合管理 | 仓位管理、风险控制、信号执行 |
| dashboard | Streamlit 看板 | 可视化分析、交互式回测 |

## 快速开始

```bash
cd taiwan-quant

# 安装依赖
pip install -r requirements.txt

# 启动看板（使用模拟数据，无需网络）
streamlit run dashboard/app.py

# 或启动 Web 服务
python -m streamlit run dashboard/app.py --server.port 8501
```

## 数据源选择

1. **模拟数据 (MockFetcher)** — 无需网络，自动生成合成数据，用于开发测试
2. **TWSE 公开数据 (TWSEFetcher)** — 直接爬取台湾证交所公开行情，无需注册
3. **FinMind API** — 免费历史数据 API（需注册 token）
4. **永丰金 Shioaji** — 完整交易 API（需券商账户）

## 开发路线

- [x] 数据获取层 (TWSE/Mock)
- [x] 数据清洗与存储
- [x] 技术指标计算
- [x] 多因子评分系统
- [x] 回测引擎
- [x] 策略模板 (MA Cross)
- [x] 组合管理与风控
- [x] Streamlit 看板
- [ ] FinMind API 集成
- [ ] Shioaji 实时数据集成
- [ ] LightGBM/ML 策略
- [ ] 回测报告 PDF 导出
- [ ] 实盘交易接口

## 免责声明

本平台仅供研究学习使用，不构成任何投资建议。
