import sys
import ccxt
import pandas as pd
import ta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

exchange = ccxt.binance({
    "enableRateLimit": True,
    "timeout": 30000,
})


def check_binance_connection():
    """Periksa koneksi ke Binance dan pastikan semua pair tersedia."""
    print("🔌 Memeriksa koneksi Binance...")
    ok = True
    try:
        exchange.load_markets()
        print(f"  ✅ Binance API terhubung ({len(exchange.markets)} market dimuat)")
    except Exception as e:
        print(f"  ❌ Gagal terhubung ke Binance: {e}")
        return False
    return ok

def get_ohlcv(symbol, timeframe="1h", limit=100):
    """Ambil data candlestick dari Binance"""
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df

def calculate_indicators(df):
    """Hitung RSI, MA, MACD — pakai library 'ta'"""

    # RSI (14)
    df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()

    # Moving Average
    df["ma20"] = ta.trend.SMAIndicator(df["close"], window=20).sma_indicator()
    df["ma50"] = ta.trend.SMAIndicator(df["close"], window=50).sma_indicator()

    # MACD
    macd = ta.trend.MACD(df["close"], window_fast=12, window_slow=26, window_sign=9)
    df["macd"]        = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["macd_hist"]   = macd.macd_diff()

    # Buang baris NaN (masa warm-up indikator) agar analisis akurat
    df = df.dropna().reset_index(drop=True)
    return df