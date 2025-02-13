from logging import log
import time
import pandas as pd
import ta
from binance.client import Client
from flask import Flask, render_template_string
from threading import Thread

# ⚠️ ENTRE TES CLÉS API BINANCE ICI
API_KEY = "b1iSUhVmS1wyO6lLy7eKqgjp8NQ1zBCaVSHv47nE1toXuuFZ2tBpyMIsOrOzd6Vk"
API_SECRET = "88huAzdkhbn0YvKwPwERsilXg7TY7NGSMOStdA5dGFZZQ8eiFNuG66lDchm7o37f"

# Connexion à Binance
client = Client(API_KEY, API_SECRET)

# 🔹 Paramètres du bot
CAPITAL_MAX = 50  # Montant max investi par trade (en USDT)
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70  # Vente RSI > 70
RSI_OVERSOLD = 30  # Achat RSI < 30
MIN_VOLUME = 100000  # Volume min pour éviter les cryptos illiquides

# Flask app setup
app = Flask(__name__)
LOG_FILE = "logs.txt"
logs = []


def log_message(message):
    
    print(message)
    logs.append(message)
    
    # Sauvegarde persistante des logs avec encodage UTF-8
    with open("logs.txt", "a", encoding="utf-8") as log_file:
        log_file.write(message + "\n")


def load_logs():
    with open("logs.txt", "r", encoding="utf-8") as file:
        return file.readlines()


def get_balance():
    balance = client.get_asset_balance(asset="USDT")
    return float(balance["free"])

def get_usdt_pairs():
    tickers = client.get_exchange_info()["symbols"]
    return [t["symbol"] for t in tickers if t["symbol"].endswith("USDT") and t["status"] == "TRADING"]

def get_historical_data(symbol, interval, limit=100):
    try:
        klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
        df = pd.DataFrame(klines, columns=["timestamp", "open", "high", "low", "close", "volume", "_", "_", "_", "_", "_", "_"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df["close"] = df["close"].astype(float)
        df["volume"] = df["volume"].astype(float)
        return df
    except Exception as e:
        log_message(f"❌ Erreur récupération {symbol}: {e}")
        return None

def calculate_rsi(df):
    return ta.momentum.RSIIndicator(df["close"], window=RSI_PERIOD).rsi().iloc[-1]

def find_best_crypto(pairs):
    best_crypto = None
    lowest_rsi = 100
    for pair in pairs:
        df = get_historical_data(pair, Client.KLINE_INTERVAL_15MINUTE)
        if df is not None and len(df) > RSI_PERIOD:
            rsi = calculate_rsi(df)
            volume = df["volume"].iloc[-1]
            if rsi < lowest_rsi and volume > MIN_VOLUME:
                lowest_rsi = rsi
                best_crypto = pair
    return best_crypto, lowest_rsi

def place_buy_order(symbol, amount_usdt):
    price = float(client.get_symbol_ticker(symbol=symbol)["price"])
    quantity = round(amount_usdt / price, 6)
    try:
        order = client.create_order(
            symbol=symbol,
            side="BUY",
            type="MARKET",
            quantity=quantity
        )
        log_message(f"✅ ACHAT {symbol}: {order}")
    except Exception as e:
        log_message(f"❌ ERREUR ACHAT {symbol}: {e}")

def place_sell_order(symbol):
    asset = symbol.replace("USDT", "")
    balance = client.get_asset_balance(asset=asset)
    quantity = float(balance["free"])
    if quantity > 0.0001:
        try:
            order = client.create_order(
                symbol=symbol,
                side="SELL",
                type="MARKET",
                quantity=round(quantity, 6)
            )
            log_message(f"✅ VENTE {symbol}: {order}")
        except Exception as e:
            log_message(f"❌ ERREUR VENTE {symbol}: {e}")

def run_bot():
    while True:
        log_message("\n🔄 Analyse du marché...")
        usdt_pairs = get_usdt_pairs()
        best_crypto, best_rsi = find_best_crypto(usdt_pairs)
        
        if best_crypto:
            log_message(f"📊 MEILLEURE OPPORTUNITÉ : {best_crypto} | RSI: {best_rsi:.2f}")
            balance = get_balance()
            log_message(f"💰 Solde USDT: {balance:.2f}")
            if best_rsi < RSI_OVERSOLD and balance >= 10:
                amount_to_invest = min(balance, CAPITAL_MAX)
                place_buy_order(best_crypto, amount_to_invest)
            for pair in usdt_pairs:
                df = get_historical_data(pair, Client.KLINE_INTERVAL_15MINUTE)
                if df is not None and len(df) > RSI_PERIOD:
                    rsi = calculate_rsi(df)
                    if rsi > RSI_OVERBOUGHT:
                        place_sell_order(pair)
        else:
            log_message("❌ Aucune opportunité trouvée")
        log_message("⏳ Attente de 15 minutes avant la prochaine analyse...")
        time.sleep(900)

@app.route('/')
def index():
    logs = load_logs()
    return render_template_string("""
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <title>Python Trade Bot Logs</title>
        <script>
          function refreshLogs() {
            fetch('/logs')
              .then(response => response.text())
              .then(data => {
                document.getElementById('logs').innerText = data;
              });
          }
          setInterval(refreshLogs, 5000);
        </script>
      </head>
      <body>
        <div class="container">
          <h1>Python Trade Bot Logs</h1>
          <pre id="logs">{{ logs }}</pre>
        </div>
      </body>
    </html>
    """, logs="".join(logs))

@app.route('/logs')
def get_logs():
    return "".join(load_logs())

if __name__ == '__main__':
    bot_thread = Thread(target=run_bot)
    bot_thread.start()
    app.run(host='0.0.0.0', port=5000)
