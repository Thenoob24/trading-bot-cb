import requests
import pandas as pd

# Paramètres
symbol = "BTCUSDT"
interval = "15m"
limit = 500  # Nombre de bougies à récupérer

# URL de l'API Binance
url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"

# Récupération des données
response = requests.get(url).json()

# Transformation en DataFrame
df = pd.DataFrame(response, columns=["timestamp", "open", "high", "low", "close", "volume", "_", "_", "_", "_", "_", "_"])
df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")  # Conversion timestamp en date
df = df[["timestamp", "open", "high", "low", "close", "volume"]]  # Garder seulement les colonnes utiles

# Sauvegarde en CSV
df.to_csv("historical_data.csv", index=False)
print("Données sauvegardées dans historical_data.csv ✅")
