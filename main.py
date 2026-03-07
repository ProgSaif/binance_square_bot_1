import requests
import time
import os
import logging
import matplotlib.pyplot as plt
import numpy as np

# =========================
# CONFIG
# =========================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BINANCE_TICKER = "https://api.binance.com/api/v3/ticker/24hr"
BINANCE_KLINES = "https://api.binance.com/api/v3/klines"

FETCH_INTERVAL = 600

# =========================
# LOGGING
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger()

# =========================
# TELEGRAM TEXT
# =========================

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

# =========================
# TELEGRAM CHART
# =========================

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

        logger.info("Chart sent")

    except Exception as e:

        logger.error(e)

# =========================
# FETCH BINANCE DATA
# =========================

def fetch_tickers():

    try:

        r = requests.get(BINANCE_TICKER, timeout=10)

        return r.json()

    except Exception as e:

        logger.error(e)

        return []

# =========================
# DETECT SIGNALS
# =========================

def detect_signals(tickers):

    signals = []

    for coin in tickers:

        try:

            symbol = coin["symbol"]

            if not symbol.endswith("USDT"):
                continue

            price = float(coin["lastPrice"])
            change = float(coin["priceChangePercent"])
            volume = float(coin["quoteVolume"])

            if abs(change) > 5 or volume > 50000000:

                signals.append({
                    "symbol": symbol,
                    "price": price,
                    "change": change
                })

        except:

            pass

    return signals

# =========================
# TP / SL GENERATION
# =========================

def generate_trade_levels(price):

    tp1 = price * 1.03
    tp2 = price * 1.06
    tp3 = price * 1.10
    sl = price * 0.97

    return tp1, tp2, tp3, sl

# =========================
# CHART GENERATION
# =========================

def generate_chart(symbol):

    try:

        params = {
            "symbol": symbol,
            "interval": "1h",
            "limit": 40
        }

        r = requests.get(BINANCE_KLINES, params=params)

        data = r.json()

        closes = [float(c[4]) for c in data]

        plt.figure(figsize=(6,4))

        plt.plot(closes)

        plt.title(symbol)

        file = f"{symbol}.png"

        plt.savefig(file)

        plt.close()

        return file

    except Exception as e:

        logger.error(e)

        return None

# =========================
# MAIN BOT LOOP
# =========================

def run_bot():

    logger.info("Bot started")

    send_message("✅ AI Crypto Signal Bot started")

    while True:

        try:

            logger.info("Fetching market data")

            tickers = fetch_tickers()

            if not tickers:

                time.sleep(FETCH_INTERVAL)
                continue

            signals = detect_signals(tickers)

            logger.info(f"{len(signals)} signals detected")

            for coin in signals[:5]:

                symbol = coin["symbol"]
                price = coin["price"]
                change = coin["change"]

                tp1, tp2, tp3, sl = generate_trade_levels(price)

                msg = f"""
🚨 Crypto Signal

{symbol}

Price: {price}
24h Change: {round(change,2)}%

TP1: {round(tp1,4)}
TP2: {round(tp2,4)}
TP3: {round(tp3,4)}

SL: {round(sl,4)}
"""

                chart = generate_chart(symbol)

                if chart:

                    send_chart(msg, chart)

                else:

                    send_message(msg)

        except Exception as e:

            logger.error(e)

        logger.info("Sleeping...")

        time.sleep(FETCH_INTERVAL)

# =========================
# START
# =========================

if __name__ == "__main__":

    run_bot()
