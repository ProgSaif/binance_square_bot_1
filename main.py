import requests
import time
import os
import logging
import matplotlib.pyplot as plt

# =========================
# CONFIG
# =========================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

COINGECKO_MARKET_URL = "https://api.coingecko.com/api/v3/coins/markets"
COINGECKO_CHART_URL = "https://api.coingecko.com/api/v3/coins/{}/market_chart"

FETCH_INTERVAL = 600
MAX_RETRIES = 5

# =========================
# LOGGING
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger()

# =========================
# TELEGRAM TEXT MESSAGE
# =========================

def send_telegram(message):

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("Telegram credentials missing")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        logger.info("Telegram message sent")

    except Exception as e:
        logger.error(f"Telegram error: {e}")

# =========================
# TELEGRAM PHOTO MESSAGE
# =========================

def send_chart(message, chart_file):

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"

    try:

        with open(chart_file, "rb") as photo:

            files = {"photo": photo}

            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "caption": message,
                "parse_mode": "Markdown"
            }

            r = requests.post(url, data=payload, files=files)
            r.raise_for_status()

            logger.info("Chart sent to Telegram")

    except Exception as e:
        logger.error(f"Telegram chart error: {e}")

# =========================
# FETCH MARKET DATA
# =========================

def fetch_market():

    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 50,
        "page": 1,
        "price_change_percentage": "24h"
    }

    headers = {
        "User-Agent": "crypto-signal-bot"
    }

    for attempt in range(MAX_RETRIES):

        try:

            logger.info("Fetching market data...")

            r = requests.get(
                COINGECKO_MARKET_URL,
                params=params,
                headers=headers,
                timeout=15
            )

            if r.status_code == 429:

                wait = 20 * (attempt + 1)
                logger.warning(f"Rate limited. Waiting {wait}s")
                time.sleep(wait)
                continue

            r.raise_for_status()

            data = r.json()

            logger.info(f"Fetched {len(data)} coins")

            return data

        except Exception as e:

            logger.error(f"API error: {e}")

            wait = 10 * (attempt + 1)
            time.sleep(wait)

    return []

# =========================
# GENERATE CHART IMAGE
# =========================

def generate_chart(coin_id):

    try:

        url = COINGECKO_CHART_URL.format(coin_id)

        params = {
            "vs_currency": "usd",
            "days": "1",
            "interval": "hourly"
        }

        r = requests.get(url, params=params, timeout=15)

        data = r.json()

        prices = [p[1] for p in data["prices"]]

        plt.figure(figsize=(6,4))

        plt.plot(prices)

        plt.title(f"{coin_id.upper()} 24H Chart")
        plt.xlabel("Time")
        plt.ylabel("Price")

        filename = f"{coin_id}_chart.png"

        plt.savefig(filename)

        plt.close()

        return filename

    except Exception as e:

        logger.error(f"Chart generation failed: {e}")

        return None

# =========================
# DETECT SIGNALS
# =========================

def detect_signals(data):

    gainers = []
    losers = []

    for coin in data:

        change = coin.get("price_change_percentage_24h")

        if change is None:
            continue

        if change > 8:
            gainers.append(coin)

        elif change < -8:
            losers.append(coin)

    return gainers, losers

# =========================
# MAIN BOT
# =========================

def run_bot():

    logger.info("Crypto Signal Bot starting...")

    send_telegram("✅ Crypto Signal Bot deployed successfully on Railway!")

    while True:

        logger.info("Running signal check...")

        data = fetch_market()

        if not data:

            logger.warning("No market data fetched")

            time.sleep(FETCH_INTERVAL)

            continue

        gainers, losers = detect_signals(data)

        signals = gainers[:3] + losers[:3]

        if not signals:

            send_telegram("No strong signals right now.")

        for coin in signals:

            name = coin["name"]
            symbol = coin["symbol"].upper()
            price = coin["current_price"]
            change = coin["price_change_percentage_24h"]

            message = f"""
🚨 Crypto Signal

{name} ({symbol})

Price: ${price}
24h Change: {round(change,2)}%
"""

            chart = generate_chart(coin["id"])

            if chart:

                send_chart(message, chart)

            else:

                send_telegram(message)

        logger.info(f"Sleeping {FETCH_INTERVAL}s")

        time.sleep(FETCH_INTERVAL)

# =========================
# START
# =========================

if __name__ == "__main__":

    run_bot()
