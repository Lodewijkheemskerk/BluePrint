"""
Telegram notification service.
Sends setup alerts to a Telegram chat/channel.
"""
import logging
import httpx
from typing import Optional
from backend.config import settings

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


async def send_telegram_message(text: str) -> bool:
    """Send a message to the configured Telegram chat."""
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.debug("Telegram not configured — skipping notification")
        return False

    url = TELEGRAM_API.format(token=settings.telegram_bot_token)
    payload = {
        "chat_id": settings.telegram_chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                logger.info("Telegram notification sent")
                return True
            else:
                logger.error(f"Telegram API error: {resp.status_code} {resp.text}")
                return False
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False


def format_setup_alert(setup_data: dict) -> str:
    """Format a setup into a Telegram-friendly HTML message."""
    direction_emoji = "\U0001f7e2" if setup_data.get("direction") == "long" else "\U0001f534"
    direction_label = setup_data.get("direction", "").upper()

    lines = [
        f"{direction_emoji} <b>New Setup: {setup_data.get('asset_symbol', '?')}</b>",
        f"Strategy: {setup_data.get('strategy_name', '?')}",
        f"Direction: {direction_label}",
        "",
    ]

    if setup_data.get("entry_price"):
        lines.append(f"Entry: {setup_data['entry_price']:.8g}")
    if setup_data.get("stop_loss"):
        lines.append(f"Stop Loss: {setup_data['stop_loss']:.8g}")
    if setup_data.get("take_profit_1"):
        lines.append(f"TP1: {setup_data['take_profit_1']:.8g}")
    if setup_data.get("take_profit_2"):
        lines.append(f"TP2: {setup_data['take_profit_2']:.8g}")
    if setup_data.get("risk_reward_ratio"):
        lines.append(f"R:R: {setup_data['risk_reward_ratio']:.1f}")
    if setup_data.get("funding_rate") is not None:
        lines.append(f"Funding: {setup_data['funding_rate']*100:.4f}%")

    if setup_data.get("market_regime"):
        lines.append(f"\nRegime: {setup_data['market_regime'].replace('_', ' ').title()}")

    # TradingView link
    symbol = setup_data.get("asset_symbol", "").replace("/", "")
    tv_url = f"https://www.tradingview.com/chart/?symbol=BINANCE:{symbol}"
    lines.append(f'\n<a href="{tv_url}">Open in TradingView</a>')

    return "\n".join(lines)
