# main.py
import os
import time
import requests
import schedule
from telegram import Bot
from PIL import Image
from io import BytesIO
import openai

# Load environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
BINANCE_API = os.getenv("BINANCE_API")
OPENAI_KEY = os.getenv("OPENAI_KEY")

bot = Bot(token=TELEGRAM_TOKEN)
openai.api_key = OPENAI_KEY

previous_symbols = set()

# --- Binance Market Data ---
def get_market_data():
    url = "https://api.binance.com/api/v3/ticker/24hr"
    data = requests.get(url).json()
    return data

# --- New Listings ---
def detect_new_listings(data):
    global previous_symbols
    current_symbols = {coin['symbol'] for coin in data}
    new_listings = current_symbols - previous_symbols
    previous_symbols = current_symbols
    return new_listings

# --- Top Gainers ---
def get_top_gainers(data, top=5):
    sorted_data = sorted(data, key=lambda x: float(x['priceChangePercent']), reverse=True)
    return sorted_data[:top]

# --- Top Losers ---
def get_top_losers(data, top=5):
    sorted_data = sorted(data, key=lambda x: float(x['priceChangePercent']))
    return sorted_data[:top]

# --- Volume Spikes ---
def detect_volume_spikes(data):
    spikes = [coin for coin in data if float(coin['volume']) > 50000000]
    return spikes[:5]

# --- AI Signal Text Generator ---
def generate_ai_text(symbol, change):
    prompt = f"Write a short crypto trading signal post for {symbol} with 24h change {change}%. Make it engaging and short."
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}]
    )
    return response.choices[0].message.content

# --- Hashtags ---
def generate_hashtags(symbol):
    coin = symbol.replace("USDT", "")
    tags = [f"#{coin}", "#crypto", "#binance", "#altcoins", "#cryptotrading"]
    return " ".join(tags)

# --- Chart Screenshot (TradingView) ---
def get_chart(symbol):
    url = f"https://s.tradingview.com/widgetembed/?symbol=BINANCE:{symbol}"
    img = requests.get(url).content
    filename = f"{symbol}.png"
    with open(filename, "wb") as f:
        f.write(img)
    return filename

# --- Telegram Post ---
def send_telegram(message, image=None):
    if image:
        bot.send_photo(chat_id=CHAT_ID, photo=open(image, "rb"), caption=message)
    else:
        bot.send_message(chat_id=CHAT_ID, text=message)

# --- Binance Square Post ---
def post_binance(message):
    url = "https://api.binance.com/sapi/v1/feed/post/create"
    headers = {"X-MBX-APIKEY": BINANCE_API}
    payload = {"type":"text","content":message}
    requests.post(url, headers=headers, json=payload)

# --- Generate Post ---
def create_post(symbol, change):
    ai_text = generate_ai_text(symbol, change)
    hashtags = generate_hashtags(symbol)
    message = f"{ai_text}\n24h Change: {change}%\n{hashtags}"
    return message

# --- Main Bot Function ---
def run_signal_bot():
    data = get_market_data()

    # New Listings
    new_tokens = detect_new_listings(data)
    for token in new_tokens:
        msg = f"🚨 NEW BINANCE LISTING\nToken: {token}\nHigh volatility expected.\n#Binance #Crypto #Trading"
        chart = get_chart(token)
        send_telegram(msg, chart)
        post_binance(msg)

    # Top Gainers
    gainers = get_top_gainers(data)
    for g in gainers:
        msg = create_post(g['symbol'], g['priceChangePercent'])
        chart = get_chart(g['symbol'])
        send_telegram(msg, chart)
        post_binance(msg)

    # Top Losers
    losers = get_top_losers(data)
    for l in losers:
        msg = create_post(l['symbol'], l['priceChangePercent'])
        chart = get_chart(l['symbol'])
        send_telegram(msg, chart)
        post_binance(msg)

    # Volume Spikes
    spikes = detect_volume_spikes(data)
    for s in spikes:
        msg = create_post(s['symbol'], s['priceChangePercent'])
        chart = get_chart(s['symbol'])
        send_telegram(msg, chart)
        post_binance(msg)

# --- Scheduler ---
schedule.every(10).minutes.do(run_signal_bot)

print("Crypto Signal Bot is running...")

while True:
    schedule.run_pending()
    time.sleep(1)
