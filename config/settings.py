"""
Central configuration for Taiwan Quant Platform.
"""
from __future__ import annotations
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TWSEConfig:
    base_url: str = "https://www.twse.com.tw"
    market_data_url: str = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
    mis_data_url: str = "https://mis.twse.com.tw/stock/api"
    request_timeout: int = 30
    retry_times: int = 3
    retry_delay: float = 1.0


@dataclass
class TPEXConfig:
    base_url: str = "https://www.tpex.org.tw"
    stock_data_url: str = "https://www.tpex.org.tw/web/stock/aftertrading"
    request_timeout: int = 30


@dataclass
class FinMindConfig:
    base_url: str = "https://api.finmindtrade.com/api/v4"


@dataclass
class DataStorageConfig:
    root: Path = Path(__file__).parent.parent / "data"
    raw_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "data" / "raw")
    processed_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "data" / "processed")
    cache_enabled: bool = True
    cache_ttl_days: int = 1
    def __post_init__(self):
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)


@dataclass
class BacktestConfig:
    initial_capital: float = 1_000_000
    commission_pct: float = 0.001425
    tax_pct: float = 0.003
    min_commission: float = 20
    trade_unit: int = 1000


@dataclass
class Settings:
    twse: TWSEConfig = field(default_factory=TWSEConfig)
    tpex: TPEXConfig = field(default_factory=TPEXConfig)
    finmind: FinMindConfig = field(default_factory=FinMindConfig)
    storage: DataStorageConfig = field(default_factory=DataStorageConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    log_level: str = "INFO"
    finmind_token: str = field(default_factory=lambda: os.getenv("FINMIND_TOKEN", ""))
    shioaji_key: str = field(default_factory=lambda: os.getenv("SHIOAJI_KEY", ""))
    shioaji_secret: str = field(default_factory=lambda: os.getenv("SHIOAJI_SECRET", ""))


settings = Settings()


DEFAULT_STOCK_LIST: List[str] = [
    # 半导体/电子
    "2330", "2317", "2454", "2382", "2308",
    "2303", "2357", "2383", "3231", "3034",
    "3711", "6669", "3008", "3661", "4938",
    "5347", "6446", "8046",
    # 金融
    "2881", "2882", "2886", "2891", "2884",
    "2880", "2883", "2885", "2887", "2890",
    "2892", "5880", "2801", "5876", "5871",
    "6005",
    # 传产
    "1303", "1301", "1326", "2002", "1216",
    "2207", "2603", "2609", "2618", "2637",
    # 科技/通信
    "2412", "3045", "4904", "2301", "2356",
    # 电商
    "8454",
    # 热门ETF
    "0050", "0056", "006208", "00713", "00878",
]

STOCK_NAME_MAP: Dict[str, str] = {
    # 半导体/电子
    "2330": "\u53f0\u79ef\u7535", "2317": "\u9e3f\u6d77", "2454": "\u8054\u53d1\u79d1",
    "2382": "\u5e7f\u8fbe", "2308": "\u53f0\u8fbe\u7535",
    "2303": "\u8054\u7535", "2357": "\u534e\u7855", "2383": "\u53f0\u5149\u96fb",
    "3231": "\u7eac\u521b", "3034": "\u8054\u548f",
    "3711": "\u65e5\u6708\u5149", "6669": "\u7eac\u9896", "3008": "\u5927\u7acb\u5149",
    "3661": "\u4e16\u82afKY", "4938": "\u548c\u7855",
    "5347": "\u4e16\u754c", "6446": "\u836f\u534e\u836f", "8046": "\u5357\u7535",
    # 金融
    "2881": "\u5bcc\u90a6\u91d1", "2882": "\u56fd\u6cf0\u91d1",
    "2886": "\u5146\u4e30\u91d1", "2891": "\u4e2d\u4fe1\u91d1", "2884": "\u7389\u5c71\u91d1",
    "2880": "\u534e\u5357\u91d1", "2883": "\u5f00\u53d1\u91d1", "2885": "\u5143\u5927\u91d1",
    "2887": "\u53f0\u65b0\u91d1", "2890": "\u6c38\u4e30\u91d1", "2892": "\u7b2c\u4e00\u91d1",
    "5880": "\u5408\u5e93\u91d1", "2801": "\u5f70\u94f6",
    "5876": "\u4e0a\u6d77\u5546\u94f6", "5871": "\u4e2d\u79dfKY",
    "6005": "\u7fa4\u76ca\u8bc1",
    # 传产
    "1303": "\u5357\u4e9a", "1301": "\u53f0\u5851", "1326": "\u53f0\u5316",
    "2002": "\u4e2d\u94a2", "1216": "\u7edf\u4e00",
    "2207": "\u548c\u6cf0\u8f66", "2603": "\u957f\u8363", "2609": "\u9633\u660e",
    "2618": "\u957f\u8363\u822a", "2637": "\u6167\u6d0bKY",
    # 科技/通信
    "2412": "\u4e2d\u534e\u7535", "3045": "\u53f0\u6e7e\u5927", "4904": "\u8fdc\u4f20",
    "2301": "\u5149\u5b9d\u79d1", "2356": "\u82f1\u4e1a\u8fbe",
    # 电商/其他
    "8454": "\u5bcc\u90a6\u5a92",
    # ETF
    "0050": "\u5143\u5927\u53f0\u6e7e50", "0056": "\u5143\u5927\u9ad8\u80a1\u606f",
    "006208": "\u5bcc\u90a6\u53f050", "00713": "\u5143\u5927\u53f0\u6e7e\u9ad8\u606f\u4f4e\u6ce2",
    "00878": "\u56fd\u6cf0\u6c38\u7eed\u9ad8\u80a1\u606f",
}

