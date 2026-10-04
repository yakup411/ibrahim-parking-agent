"""Send one fixed Telegram test message without retries."""

import os
import sys

import requests


TEST_MESSAGE = "🧪 Ibrahim Stellplatz Bot – Telegram-Test erfolgreich ausgelöst."


def main() -> int:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Telegram-Test fehlgeschlagen: Konfiguration fehlt.", file=sys.stderr)
        return 1

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        # Deliberately make one HTTP request only; this test has no retry path.
        response = requests.post(
            url,
            data={"chat_id": chat_id, "text": TEST_MESSAGE},
            timeout=20,
        )
        response.raise_for_status()
        result = response.json()
    except (requests.RequestException, ValueError):
        # Do not print exception details: they may contain the token-bearing URL.
        print("Telegram-Test fehlgeschlagen (HTTP-/Netzwerkantwort ungültig).", file=sys.stderr)
        return 1

    if not isinstance(result, dict) or result.get("ok") is not True:
        print("Telegram hat den Versand nicht bestätigt.", file=sys.stderr)
        return 1

    print("Telegram hat den Versand der Testnachricht bestätigt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
