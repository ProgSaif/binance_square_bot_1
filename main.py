import requests
import os
import time
import logging
import matplotlib.pyplot as plt
import numpy as np

# ======================
# CONFIG
# ======================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

FETCH_INTERVAL = 600
MAX_RETRIES = 5

BINANCE_TICKER = "https://api.binance.com/api/v3/ticker/24hr"
BINANCE_KLINES = "https://api.binance.com/api/v3/klines"
BINANCE_EXCHANGE = "https://api.binance.com/api/v3/exchangeInfo"

# ======================
# LOGGING
# ======================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger()

known_pairs = set()

# ======================
# TELEGRAM
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

    except Exception as e:

        logger.error(e)


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
# BINANCE DATA
# ======================

def fetch_tickers():

    try:

        r = requests.get(BINANCE_TICKER, timeout=10)

        return r.json()

    except:

        return []


# ======================
# NEW LISTINGS
# ======================

def check_new_listings():

    global known_pairs

    try:

        r = requests.get(BINANCE_EXCHANGE)

        data = r.json()

        symbols = {s["symbol"] for s in data["symbols"]}

        if not known_pairs:

            known_pairs = symbols
            return

        new = symbols - known_pairs

        for coin in new:

            msg = f"🚀 *New Binance Listing*\n\n{coin}"

            send_message(msg)

        known_pairs = symbols

    except Exception as e:

        logger.error(e)


# ======================
# VOLUME SPIKE
# ======================

def detect_volume_spike(tickers):

    signals = []

    for coin in tickers:

        try:

            volume = float(coin["quoteVolume"])
            change = float(coin["priceChangePercent"])

            if volume > 100000000 and abs(change) > 5:

                signals.append(coin)

        except:

            pass

    return signals


# ======================
# BREAKOUT DETECTION
# ======================

def breakout_signal(symbol):

    try:

        params = {
            "symbol": symbol,
            "interval": "1h",
            "limit": 50
        }

        r = requests.get(BINANCE_KLINES, params=params)

        data = r.json()

        closes = np.array([float(c[4]) for c in data])

        resistance = max(closes[:-1])

        if closes[-1] > resistance:

            return True

    except:

        pass

    return False


# ======================
# TP SL CALCULATION
# ======================

def generate_trade_levels(price):

    tp1 = price * 1.03
    tp2 = price * 1.06
    tp3 = price * 1.10
    sl = price * 0.97

    return tp1, tp2, tp3, sl


# ======================
# CHART
# ======================

def generate_chart(symbol):

    try:

        params = {
            "symbol": symbol,
            "interval": "1h",
            "limit": 40
        }

        r = requests.get(BINANCE_KLINES, params=params)

        data = r.json()

        closes = [float(x[4]) for x in data]

        plt.figure(figsize=(6,4))

        plt.plot(closes)

        plt.title(symbol)

        file = f"{symbol}.png"

        plt.savefig(file)

        plt.close()

        return file

    except:

        return None


# ======================
# MAIN SIGNAL ENGINE
# ======================

def run_bot():

    logger.info("Bot started")

    send_message("✅ AI Crypto Signal Bot started")

    while True:

        try:

            check_new_listings()

            tickers = fetch_tickers()

            spikes = detect_volume_spike(tickers)

            for coin in spikes[:5]:

                symbol = coin["symbol"]

                if not symbol.endswith("USDT"):
                    continue

                breakout = breakout_signal(symbol)

                if not breakout:
                    continue

                price = float(coin["lastPrice"])

                tp1, tp2, tp3, sl = generate_trade_levels(price)

                msg = f"""
🚨 *Breakout Signal*

{symbol}

Entry: {price}

TP1: {round(tp1,4)}
TP2: {round(tp2,4)}
TP3: {round(tp3,4)}

SL: {round(sl,4)}

Volume Spike + Breakout
"""

                chart = generate_chart(symbol)

                if chart:

                    send_chart(msg, chart)

                else:

                    send_message(msg)

        except Exception as e:

            logger.error(e)

        time.sleep(FETCH_INTERVAL)


# ======================
# START
# ======================

if __name__ == "__main__":

    run_bot()
