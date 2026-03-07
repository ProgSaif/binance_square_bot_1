import requests
import time
import os
import logging
import matplotlib.pyplot as plt

# ======================
# CONFIG
# ======================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

COINGECKO_MARKETS = "https://api.coingecko.com/api/v3/coins/markets"
COINGECKO_CHART = "https://api.coingecko.com/api/v3/coins/{}/market_chart"

FETCH_INTERVAL = 600

# ======================
# LOGGING
# ======================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger()

# ======================
# TELEGRAM MESSAGE
# ======================

def send_message(text):

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }

    try:
        requests.post(url, json=payload)
        logger.info("Telegram message sent")

    except Exception as e:
        logger.error(e)

# ======================
# TELEGRAM CHART
# ======================

def send_chart(text, image):

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"

    try:

        with open(image, "rb") as img:

            files = {"photo": img}

            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "caption": text,
                "parse_mode": "Markdown"
            }

            requests.post(url, data=payload, files=files)

    except Exception as e:
        logger.error(e)

# ======================
# FETCH MARKET DATA
# ======================

def fetch_market():

    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 50,
        "page": 1,
        "price_change_percentage": "24h"
    }

    try:

        r = requests.get(COINGECKO_MARKETS, params=params, timeout=10)

        data = r.json()

        logger.info(f"Fetched {len(data)} coins")

        return data

    except Exception as e:

        logger.error(e)

        return []

# ======================
# DETECT SIGNALS
# ======================

def detect_signals(data):

    signals = []

    for coin in data:

        change = coin.get("price_change_percentage_24h")

        if change is None:
            continue

        if abs(change) > 6:

            signals.append(coin)

    return signals

# ======================
# GENERATE CHART
# ======================

def generate_chart(coin):

    try:

        url = COINGECKO_CHART.format(coin["id"])

        params = {
            "vs_currency": "usd",
            "days": "1"
        }

        r = requests.get(url, params=params)

        data = r.json()

        prices = [p[1] for p in data["prices"]]

        plt.figure(figsize=(6,4))

        plt.plot(prices)

        plt.title(coin["symbol"].upper())

        file = f"{coin['symbol']}.png"

        plt.savefig(file)

        plt.close()

        return file

    except Exception as e:

        logger.error(e)

        return None

# ======================
# BOT LOOP
# ======================

def run_bot():

    logger.info("Bot started")

    send_message("✅ Crypto Signal Bot started")

    while True:

        try:

            data = fetch_market()

            signals = detect_signals(data)

            logger.info(f"{len(signals)} signals detected")

            for coin in signals[:5]:

                name = coin["name"]
                symbol = coin["symbol"].upper()
                price = coin["current_price"]
                change = coin["price_change_percentage_24h"]

                msg = f"""
🚨 Crypto Signal

{name} ({symbol})

Price: ${price}
24h Change: {round(change,2)}%
"""

                chart = generate_chart(coin)

                if chart:

                    send_chart(msg, chart)

                else:

                    send_message(msg)

        except Exception as e:

            logger.error(e)

        logger.info("Sleeping...")

        time.sleep(FETCH_INTERVAL)

# ======================
# START
# ======================

if __name__ == "__main__":

    run_bot()
