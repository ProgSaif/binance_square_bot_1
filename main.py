# main.py
import os
import time
import requests
import schedule
from telegram import Bot

# ----------------------------
# Load environment variables
# ----------------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
BINANCE_API = os.getenv("BINANCE_API")

bot = Bot(token=TELEGRAM_TOKEN)
previous_symbols = set()

# ----------------------------
# Binance Market Data
# ----------------------------
def get_market_data():
    url = "https://api.binance.com/api/v3/ticker/24hr"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, list):
            print("Unexpected Binance response:", data)
            return []

        print(f"Fetched {len(data)} coins from Binance")
        return data

    except Exception as e:
        print("Error fetching Binance data:", e)
        return []

# ----------------------------
# New Listings
# ----------------------------
def detect_new_listings(data):
    global previous_symbols
    current_symbols = {coin['symbol'] for coin in data}
    new_listings = current_symbols - previous_symbols
    previous_symbols = current_symbols
    return new_listings

# ----------------------------
# Top Gainers
# ----------------------------
def get_top_gainers(data, top=5):
    sorted_data = sorted(data, key=lambda x: float(x['priceChangePercent']), reverse=True)
    return sorted_data[:top]

# ----------------------------
# Top Losers
# ----------------------------
def get_top_losers(data, top=5):
    sorted_data = sorted(data, key=lambda x: float(x['priceChangePercent']))
    return sorted_data[:top]

# ----------------------------
# Volume Spikes
# ----------------------------
def detect_volume_spikes(data):
    spikes = [coin for coin in data if float(coin['volume']) > 50000000]
    return spikes[:5]

# ----------------------------
# Signal Text Generator (free)
# ----------------------------
def generate_signal_text(symbol, change):
    return f"{symbol} is moving {change}% in 24h! Check the chart for entry, SL, TP levels."

# ----------------------------
# Hashtags
# ----------------------------
def generate_hashtags(symbol):
    coin = symbol.replace("USDT", "")
    tags = [f"#{coin}", "#crypto", "#binance", "#altcoins", "#cryptotrading"]
    return " ".join(tags)

# ----------------------------
# Telegram Post
# ----------------------------
def send_telegram(message):
    try:
        bot.send_message(chat_id=CHAT_ID, text=message)
        print("Telegram sent:", message)
    except Exception as e:
        print("Telegram Error:", e)

# ----------------------------
# Binance Square Post
# ----------------------------
def post_binance(message):
    try:
        url = "https://api.binance.com/sapi/v1/feed/post/create"
        headers = {"X-MBX-APIKEY": BINANCE_API}
        payload = {"type":"text","content":message}
        r = requests.post(url, headers=headers, json=payload)
        print("Binance response:", r.status_code, r.text)
    except Exception as e:
        print("Binance Error:", e)

# ----------------------------
# Generate Full Post
# ----------------------------
def create_post(symbol, change):
    text = generate_signal_text(symbol, change)
    hashtags = generate_hashtags(symbol)
    return f"{text}\n24h Change: {change}%\n{hashtags}"

# ----------------------------
# Main Bot Function
# ----------------------------
def run_signal_bot():
    print("Running signal bot...")
    data = get_market_data()
    if not data:
        print("No data fetched, skipping this run.")
        return

    # --- New Listings ---
    new_tokens = detect_new_listings(data)
    print("New Listings:", new_tokens)
    for token in new_tokens:
        msg = f"🚨 NEW BINANCE LISTING\nToken: {token}\nHigh volatility expected.\n#Binance #Crypto #Trading"
        send_telegram(msg)
        post_binance(msg)

    # --- Top Gainers ---
    gainers = get_top_gainers(data)
    print("Top Gainers:", [g['symbol'] for g in gainers])
    for g in gainers:
        msg = create_post(g['symbol'], g['priceChangePercent'])
        send_telegram(msg)
        post_binance(msg)

    # --- Top Losers ---
    losers = get_top_losers(data)
    print("Top Losers:", [l['symbol'] for l in losers])
    for l in losers:
        msg = create_post(l['symbol'], l['priceChangePercent'])
        send_telegram(msg)
        post_binance(msg)

    # --- Volume Spikes ---
    spikes = detect_volume_spikes(data)
    print("Volume Spikes:", [s['symbol'] for s in spikes])
    for s in spikes:
        msg = create_post(s['symbol'], s['priceChangePercent'])
        send_telegram(msg)
        post_binance(msg)

# ----------------------------
# Immediate Test Run
# ----------------------------
print("Crypto Signal Bot is starting...")
run_signal_bot()  # run immediately on deploy

# ----------------------------
# Scheduler: Run Every 10 Minutes
# ----------------------------
schedule.every(10).minutes.do(run_signal_bot)

while True:
    schedule.run_pending()
    time.sleep(1)
