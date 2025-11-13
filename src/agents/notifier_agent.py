# src/agents/notifier_agent.py
import requests
from ..utils.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

def send_telegram_message(text: str, parse_mode="Markdown"):
    """
    Send a message via Telegram bot.
    Supports Markdown or HTML formatting.
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": parse_mode
    }
    try:
        r = requests.post(url, data=payload, timeout=10)
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"[Notifier] Failed to send Telegram message: {e}")
        return False


def notify_trade(symbol, side, qty, price, pnl=None):
    """
    Sends a formatted trade notification to Telegram.
    """
    emoji = "📈" if side.lower() == "buy" else "📉"
    pnl_text = f"\n💰 *PnL:* {pnl:.2f} USD" if pnl is not None else ""
    message = (
        f"{emoji} *Trade Executed!*\n"
        f"• *Symbol:* {symbol}\n"
        f"• *Side:* {side.upper()}\n"
        f"• *Quantity:* {qty}\n"
        f"• *Price:* {price:.2f} USD"
        f"{pnl_text}\n"
        f"🕒 _Notified by Autonomous Trading Agent_"
    )
    send_telegram_message(message)


def notify_error(error_message):
    """
    Sends an error alert to Telegram.
    """
    message = f"⚠️ *Error Alert*\n```\n{error_message}\n```"
    send_telegram_message(message, parse_mode="Markdown")
