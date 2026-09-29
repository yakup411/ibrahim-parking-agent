import os
import math
import time

import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def send_telegram_message(message: str):
    if not BOT_TOKEN or not CHAT_ID:
        raise RuntimeError("Telegram configuration is incomplete.")

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    for attempt in range(3):
        try:
            response = requests.post(
                url,
                data={
                    "chat_id": CHAT_ID,
                    "text": message,
                },
                timeout=30,
            )
        except requests.ConnectTimeout:
            if attempt == 2:
                raise
            time.sleep(0.5 * (2**attempt))
            continue

        if response.status_code == 429 and attempt < 2:
            try:
                retry_after = response.json().get("parameters", {}).get("retry_after", 0.5 * (2**attempt))
                retry_after = float(retry_after)
                delay = min(max(retry_after, 0.0), 5.0) if math.isfinite(retry_after) else 0.5 * (2**attempt)
            except (TypeError, ValueError, AttributeError):
                delay = 0.5 * (2**attempt)
            time.sleep(delay)
            continue
        break

    response.raise_for_status()

    result = response.json()
    if not isinstance(result, dict) or result.get("ok") is not True:
        raise RuntimeError("Telegram rejected the message.")
    return result
