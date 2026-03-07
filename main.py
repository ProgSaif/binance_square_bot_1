import requests
import time
import logging
import os

# =========================
# CONFIG
# =========================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/markets"

FETCH_INTERVAL = 600  # 10 minutes
MAX_RETRIES = 5

# =========================
# LOGGING SETUP
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger()

# =========================
# TELEGRAM SENDER
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
        logger.info("Message sent to Telegram")

    except Exception as e:
        logger.error(f"Telegram error: {e}")

# =========================
# SAFE API FETCH
# =========================

def fetch_market_data():

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

            logger.info(f"Fetching CoinGecko data (attempt {attempt+1})")

            response = requests.get(
                COINGECKO_URL,
                params=params,
                headers=headers,
                timeout=15
            )

            if response.status_code == 429:

                wait = 15 * (attempt + 1)
                logger.warning(f"Rate limited. Waiting {wait}s")
                time.sleep(wait)
                continue

            response.raise_for_status()

            data = response.json()

            logger.info(f"Fetched {len(data)} coins")

            return data

        except Exception as e:

            logger.error(f"API error: {e}")

            wait = 10 * (attempt + 1)
            logger.info(f"Retrying in {wait}s")

            time.sleep(wait)

    return []

# =========================
# SIGNAL GENERATION
# =========================

def generate_signals(data):

    gainers = []
    losers = []

    for coin in data:

        change = coin.get("price_change_percentage_24h")

        if change is None:
            continue

        if change > 1:
            gainers.append(coin)

        elif change < -1:
            losers.append(coin)

    return gainers, losers

# =========================
# FORMAT MESSAGE
# =========================

def format_signal(gainers, losers):

    message = "*🚨 Crypto Market Signals*\n\n"

    if gainers:

        message += "*📈 Top Gainers (>8%)*\n"

        for coin in gainers[:5]:

            message += (
                f"{coin['name']} ({coin['symbol'].upper()})\n"
                f"Price: ${coin['current_price']}\n"
                f"24h Change: {round(coin['price_change_percentage_24h'],2)}%\n\n"
            )

    if losers:

        message += "*📉 Top Losers (<-8%)*\n"

        for coin in losers[:5]:

            message += (
                f"{coin['name']} ({coin['symbol'].upper()})\n"
                f"Price: ${coin['current_price']}\n"
                f"24h Change: {round(coin['price_change_percentage_24h'],2)}%\n\n"
            )

    if not gainers and not losers:
        message += "No strong signals right now."

    return message

# =========================
# BOT LOOP
# =========================

def run_bot():

    logger.info("Crypto Signal Bot is starting...")

    # immediate test message
    send_telegram("✅ Crypto Signal Bot deployed successfully on Railway!")

    while True:

        logger.info("Running signal check...")

        data = fetch_market_data()

        if not data:
            logger.warning("No data fetched, skipping this cycle")
            time.sleep(FETCH_INTERVAL)
            continue

        gainers, losers = generate_signals(data)

        message = format_signal(gainers, losers)

        send_telegram(message)

        logger.info(f"Sleeping {FETCH_INTERVAL}s")

        time.sleep(FETCH_INTERVAL)

# =========================
# START
# =========================

if __name__ == "__main__":
    run_bot()
