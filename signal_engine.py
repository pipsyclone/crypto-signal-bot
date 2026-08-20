import numpy as np


def predict_next(df, bars_ahead=3):
    """
    Prediksi arah & target harga beberapa bar ke depan
    pakai regresi linear 20 candle terakhir.
    """
    closes = df["close"].tail(20).astype(float).to_numpy()
    x = np.arange(len(closes))
    slope, intercept = np.polyfit(x, closes, 1)

    current = closes[-1]
    pred = intercept + slope * (len(closes) - 1 + bars_ahead)
    pct = (pred - current) / current * 100

    if pct > 0.3:
        direction = "🔼 NAIK"
    elif pct < -0.3:
        direction = "🔽 TURUN"
    else:
        direction = "➡️ DATAR"

    return {
        "direction": direction,
        "pct": pct,
        "target": pred,
        "current": current,
        "bars_ahead": bars_ahead,
    }


def analyze_signal(df):
    """
    Tentukan sinyal BUY / SELL / HOLD
    berdasarkan kombinasi RSI + MA + MACD
    """
    if df is None or len(df) < 2:
        raise ValueError("Data tidak cukup untuk analisis")

    last = df.iloc[-1]
    prev = df.iloc[-2]

    score = 0  # positif = bullish, negatif = bearish

    reasons = []

    # === RSI ===
    if last["rsi"] < 30:
        score += 2
        reasons.append("✅ RSI oversold (< 30) → potensi naik")
    elif last["rsi"] > 70:
        score -= 2
        reasons.append("🔴 RSI overbought (> 70) → potensi turun")
    else:
        reasons.append(f"⚪ RSI netral ({last['rsi']:.1f})")

    # === MA Cross ===
    if last["ma20"] > last["ma50"] and prev["ma20"] <= prev["ma50"]:
        score += 2
        reasons.append("✅ Golden Cross MA20 > MA50 → sinyal BUY kuat")
    elif last["ma20"] < last["ma50"] and prev["ma20"] >= prev["ma50"]:
        score -= 2
        reasons.append("🔴 Death Cross MA20 < MA50 → sinyal SELL kuat")
    elif last["ma20"] > last["ma50"]:
        score += 1
        reasons.append("✅ MA20 di atas MA50 → tren naik")
    else:
        score -= 1
        reasons.append("🔴 MA20 di bawah MA50 → tren turun")

    # === MACD ===
    if last["macd"] > last["macd_signal"] and prev["macd"] <= prev["macd_signal"]:
        score += 2
        reasons.append("✅ MACD crossover ke atas → momentum naik")
    elif last["macd"] < last["macd_signal"] and prev["macd"] >= prev["macd_signal"]:
        score -= 2
        reasons.append("🔴 MACD crossover ke bawah → momentum turun")
    elif last["macd"] > last["macd_signal"]:
        score += 1
        reasons.append("✅ MACD di atas sinyal → bullish")
    else:
        score -= 1
        reasons.append("🔴 MACD di bawah sinyal → bearish")

    # === Keputusan Final ===
    if score >= 3:
        signal = "🟢 BUY"
    elif score <= -3:
        signal = "🔴 SELL"
    else:
        signal = "🟡 HOLD"

    return signal, score, reasons, last