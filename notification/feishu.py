

def build_recommendation_card(
    date_str: str,
    next_date_str: str,
    recs: list[dict],
    summary: dict,
    pages_url: str | None = None,
) -> list[dict]:
    """Build a recommendation-focused Feishu card."""
    elements = []

    # Header
    elements.append({
        "tag": "div",
        "text": md(
            f"**分析日期**: {date_str}  |  **推荐执行日**: {next_date_str}\n"
            f"**数据源**: {summary.get('data_source', 'N/A').upper()}  |  "
            f"**监控股数**: {summary.get('stocks_fetched', 0)}"
        ),
    })
    elements.append(hr())

    if not recs:
        elements.append({
            "tag": "div",
            "text": md("今日无符合条件的推荐标的。"),
        })
        elements.append(hr())
    else:
        for i, rec in enumerate(recs[:5], 1):
            profit = rec.get("potential_profit_pct", 0)
            loss = rec.get("potential_loss_pct", 0)
            confidence = rec.get("confidence", "N/A")
            reason = rec.get("reason", "")

            text_lines = [
                f"**推荐 #{i}**  {rec.get('stock_id', '')} {rec.get('stock_name', '')}  |  {confidence}",
                f"建议买入价:  {rec.get('entry_price', 0):.2f}",
                f"止盈目标价:  {rec.get('target_price', 0):.2f}  ({profit:+.2f}%)",
                f"止损价:      {rec.get('stop_loss', 0):.2f}  ({loss:.2f}%)",
                f"R/R 比率:    {rec.get('rr_ratio', 0):.2f}  |  建议持仓: {rec.get('holding_days', 0)} 天",
            ]
            if reason:
                text_lines.append(f"依据: {reason}")

            elements.append({"tag": "div", "text": md("\n".join(text_lines))})
            if i < min(len(recs), 5):
                elements.append({"tag": "hr"})

        # Stats
        avg_rr = sum(r.get("rr_ratio", 0) for r in recs) / len(recs) if recs else 0
        high_c = sum(1 for r in recs if r.get("confidence") == "HIGH")
        elements.append(hr())
        elements.append({
            "tag": "div",
            "text": md(
                f"入选: {len(recs)} 支  |  平均 R/R: {avg_rr:.2f}  |  高信心: {high_c}"
            ),
        })

    # Links
    elements.append(hr())
    if pages_url:
        elements.append({"tag": "div", "text": md(f"[查看完整报告]({pages_url})")})

    elements.append(
        note(f"Taiwan Quant Platform - {date_str}\n仅供参考，不构成投资建议")
    )
    return elements
\n﻿"""
Feishu (Lark) webhook bot client.
Sends interactive card messages to Feishu group chats.
"""
from __future__ import annotations
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

FEISHU_CARD_TEMPLATES = {
    "blue": "blue",
    "wathet": "wathet",
    "green": "green",
    "red": "red",
    "purple": "purple",
    "yellow": "yellow",
    "orange": "orange",
    "carmine": "carmine",
}


def send_text(webhook_url: str, text: str) -> bool:
    """Send a plain text message to Feishu webhook."""
    payload = {
        "msg_type": "text",
        "content": {"text": text},
    }
    return _post(webhook_url, payload)


def send_card(
    webhook_url: str,
    title: str,
    elements: list[dict],
    header_color: str = "blue",
) -> bool:
    """Send an interactive card message to Feishu webhook."""
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "template": header_color,
        },
        "elements": elements,
    }
    payload = {"msg_type": "interactive", "card": card}
    return _post(webhook_url, payload)



def send_card_with_app(
    app_id: str,
    app_secret: str,
    chat_id: str,
    title: str,
    elements: list[dict],
    header_color: str = "blue",
) -> bool:
    """Send interactive card using Feishu custom app (App ID + Secret)."""
    import requests
    try:
        r = requests.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": app_id, "app_secret": app_secret},
            timeout=10,
        )
        token_data = r.json()
        if token_data.get("code") != 0:
            return False
        token = token_data["tenant_access_token"]
    except Exception:
        return False
    card = {
        "config": {"wide_screen_mode": True},
        "header": {"title": {"tag": "plain_text", "content": title}, "template": header_color},
        "elements": elements,
    }
    try:
        r = requests.post(
            "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"receive_id": chat_id, "msg_type": "interactive", "content": json.dumps(card)},
            timeout=10,
        )
        return r.json().get("code") == 0
    except Exception:
        return False

def _post(webhook_url: str, payload: dict) -> bool:
    """POST a message to Feishu webhook."""
    import requests
    try:
        resp = requests.post(
            webhook_url,
            json=payload,
            timeout=10,
            headers={"Content-Type": "application/json"},
        )
        result = resp.json()
        if result.get("StatusCode") == 0 or result.get("code") == 0:
            logger.info("Feishu message sent successfully")
            return True
        else:
            logger.warning(
                "Feishu API returned error: %s", result
            )
            return False
    except requests.RequestException as e:
        logger.error("Failed to send Feishu message: %s", e)
        return False


# ──────────────────────────────────────────
#  Card element helpers
# ──────────────────────────────────────────

def md(text: str) -> dict:
    return {"tag": "lark_md", "content": text}


def hr() -> dict:
    return {"tag": "hr"}


def note(text: str) -> dict:
    return {"tag": "note", "elements": [{"tag": "plain_text", "content": text}]}


def divider() -> dict:
    return {"tag": "hr"}


def build_quant_card(
    date_str: str,
    summary: dict,
    indicators: dict | None = None,
    factor_scores: list | None = None,
    pages_url: str | None = None,
) -> list[dict]:
    """
    Build the element list for a quant daily report card.
    """
    elements = []

    # ── Overview section ──
    elements.append({
        "tag": "div",
        "text": md(
            f"**数据源**: {summary.get('data_source', 'N/A').upper()}\n"
            f"**监控股票数**: {summary.get('stocks_fetched', 0)} 支\n"
            f"**报告日期**: {date_str}"
        ),
    })
    elements.append(hr())

    # ── Top stock indicators ──
    if indicators:
        elements.append({
            "tag": "div",
            "text": md("**📊 台积电 (2330) 最新指标**"),
        })
        fields = _indicators_to_fields(indicators)
        if fields:
            elements.append({"tag": "div", "fields": fields})
        elements.append(hr())

    # ── Factor scores ──
    if factor_scores and len(factor_scores) > 0:
        latest = factor_scores[-1]
        score = latest.get("composite_score", "N/A")
        prev = factor_scores[-2]["composite_score"] if len(factor_scores) > 1 else None
        trend = ""
        if prev is not None and isinstance(score, (int, float)) and isinstance(prev, (int, float)):
            trend = f" (较前日{'+' if score > prev else ''}{score - prev:.2f})"
        elements.append({
            "tag": "div",
            "text": md(f"**📈 多因子综合评分**: {score}{trend}"),
        })
        elements.append(hr())

    # ── Links ──
    links_text = ""
    if pages_url:
        links_text += f"[查看完整报告]({pages_url})\n\n"
    if not links_text:
        links_text = "详细数据见 GitHub 仓库"
    elements.append({
        "tag": "div",
        "text": md(links_text),
    })

    # ── Footer ──
    elements.append(
        note(
            f"🤖 Taiwan Quant Platform · {date_str}\n"
            "⚠️ 本报告仅供参考，不构成投资建议"
        )
    )

    return elements


def _indicators_to_fields(indicators: dict) -> list[dict]:
    """Convert indicator dict to Feishu card field format."""
    LABEL_MAP = {
        "rsi": "RSI(14)",
        "macd": "MACD",
        "macd_signal": "MACD Signal",
        "k": "K值",
        "d": "D值",
        "bb_upper": "布林上轨",
        "bb_lower": "布林下轨",
        "volume_ratio": "成交量比",
        "sma_20": "MA20",
        "sma_60": "MA60",
        "close": "收盘价",
        "return": "日收益率",
    }
    fields = []
    tracked_keys = [
        "close", "return", "rsi", "macd", "k", "d",
        "volume_ratio", "sma_20", "sma_60",
    ]
    for key in tracked_keys:
        if key not in indicators:
            continue
        val = indicators[key]
        if val is None or val == "N/A":
            display = "N/A"
        elif isinstance(val, float):
            fmt = ".2f" if abs(val) < 100 else ".1f"
            display = f"{val:{fmt}}"
        else:
            display = str(val)
        label = LABEL_MAP.get(key, key)
        # Feishu fields: 2 per row, short=true
        fields.append({
            "is_short": True,
            "text": {"tag": "lark_md", "content": f"**{label}**\n{display}"},
        })
    return fields
