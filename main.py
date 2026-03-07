import requests
import os
import time
import logging
import pandas as pd
import numpy as np
import mplfinance as mpf

# =========================
# CONFIG
# =========================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BINANCE_TICKER = "https://api.binance.com/api/v3/ticker/24hr"
BINANCE_KLINES = "https://api.binance.com/api/v3/klines"
BINANCE_EXCHANGE = "https://api.binance.com/api/v3/exchangeInfo"

FETCH_INTERVAL = 600

known_symbols = set()

# =========================
# LOGGING
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger()

# =========================
# TELEGRAM
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

# =========================
# FETCH BINANCE DATA
# =========================

def fetch_tickers():

    try:
        r = requests.get(BINANCE_TICKER, timeout=10)
        return r.json()
    except:
        return []

# =========================
# NEW LISTING ALERT
# =========================

def check_new_listings():

    global known_symbols

    try:

        r = requests.get(BINANCE_EXCHANGE)
        data = r.json()

        symbols = {s["symbol"] for s in data["symbols"]}

        if not known_symbols:
            known_symbols = symbols
            return

        new = symbols - known_symbols

        for coin in new:
            send_message(f"🚀 *New Binance Listing*\n\n{coin}")

        known_symbols = symbols

    except Exception as e:
        logger.error(e)

# =========================
# FETCH CANDLES
# =========================

def fetch_candles(symbol):

    params = {
        "symbol": symbol,
        "interval": "1h",
        "limit": 100
    }

    try:

        r = requests.get(BINANCE_KLINES, params=params)

        data = r.json()

        df = pd.DataFrame(data, columns=[
            "time","open","high","low","close","volume",
            "close_time","qav","trades","tbv","tqv","ignore"
        ])

        df["time"] = pd.to_datetime(df["time"], unit="ms")

        df.set_index("time", inplace=True)

        df = df.astype(float)

        return df

    except:
        return None

# =========================
# INDICATORS
# =========================

def calculate_rsi(series, period=14):

    delta = series.diff()

    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()

    rs = gain / loss

    return 100 - (100 / (1 + rs))


def ema(series, period):

    return series.ewm(span=period).mean()

# =========================
# AI SIGNAL SCORE
# =========================

def score_signal(df):

    score = 0

    rsi = calculate_rsi(df["close"])

    ema20 = ema(df["close"], 20)
    ema50 = ema(df["close"], 50)

    latest_rsi = rsi.iloc[-1]

    if latest_rsi < 30:
        score += 2

    if latest_rsi > 70:
        score += 2

    if ema20.iloc[-1] > ema50.iloc[-1]:
        score += 2

    volume_avg = df["volume"].rolling(20).mean()

    if df["volume"].iloc[-1] > volume_avg.iloc[-1] * 2:
        score += 2

    return score, latest_rsi

# =========================
# CHART GENERATION
# =========================

def generate_chart(df, symbol):

    try:

        file = f"{symbol}.png"

        mpf.plot(
            df,
            type="candle",
            volume=True,
            style="charles",
            title=symbol,
            savefig=file
        )

        return file

    except:

        return None

# =========================
# SIGNAL ENGINE
# =========================

def detect_signals(tickers):

    signals = []

    for coin in tickers:

        symbol = coin["symbol"]

        if not symbol.endswith("USDT"):
            continue

        df = fetch_candles(symbol)

        if df is None:
            continue

        score, rsi = score_signal(df)

        if score >= 4:

            signals.append({
                "symbol": symbol,
                "price": float(coin["lastPrice"]),
                "score": score,
                "rsi": rsi,
                "df": df
            })

    return signals

# =========================
# MAIN BOT
# =========================

def run_bot():

    logger.info("Bot started")

    send_message("✅ AI Crypto Signal Bot started")

    while True:

        try:

            check_new_listings()

            tickers = fetch_tickers()

            signals = detect_signals(tickers)

            logger.info(f"{len(signals)} signals found")

            for s in signals[:5]:

                symbol = s["symbol"]
                price = s["price"]
                rsi = s["rsi"]
                score = s["score"]

                msg = f"""
🚨 *AI Crypto Signal*

{symbol}

Price: {price}

RSI: {round(rsi,2)}
Signal Score: {score}/8

Indicators:
• RSI
• EMA Trend
• Volume Spike
"""

                chart = generate_chart(s["df"], symbol)

                if chart:
                    send_chart(msg, chart)
                else:
                    send_message(msg)

        except Exception as e:

            logger.error(e)

        time.sleep(FETCH_INTERVAL)

# =========================
# START
# =========================

if __name__ == "__main__":

    run_bot()
