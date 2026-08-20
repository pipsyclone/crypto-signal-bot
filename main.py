import sys
import schedule
import time
from config import SYMBOLS, TIMEFRAME, CHECK_INTERVAL
from indicators import get_ohlcv, calculate_indicators, check_binance_connection
from signal_engine import analyze_signal, predict_next
from telegram_bot import send_message, format_combined_message, check_connection

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def check_signals():
    print(f"\n🔍 Mengecek sinyal untuk {len(SYMBOLS)} pair...")
    results = []

    for symbol in SYMBOLS:
        try:
            df = get_ohlcv(symbol, TIMEFRAME)
            df = calculate_indicators(df)
            signal, score, reasons, last = analyze_signal(df)
            prediction = predict_next(df)

            print(f"{symbol}: {signal} (score: {score}) prediksi {prediction['direction']} {prediction['pct']:+.1f}%")

            results.append({
                "symbol": symbol,
                "signal": signal,
                "score": score,
                "reasons": reasons,
                "last": last,
                "prediction": prediction,
            })

        except Exception as e:
            print(f"  ❌ Error {symbol}: {e}")

    if results:
        msg = format_combined_message(results)
        if send_message(msg):
            print(f"  ✅ Satu pesan gabungan ({len(results)} crypto) terkirim ke Telegram!")
        else:
            print("  ❌ Gagal kirim pesan gabungan")

def main():
    print("🚀 Crypto Signal Bot dimulai!")

    # === Pemeriksaan koneksi dulu ===
    telegram_ok = check_connection()
    binance_ok = check_binance_connection()

    if not telegram_ok:
        print("\n❌ Koneksi Telegram gagal. Perbaiki config.py lalu jalankan lagi.")
        return
    if not binance_ok:
        print("\n❌ Koneksi Binance gagal. Periksa internet lalu jalankan lagi.")
        return

    print("\n📣 Mengirim notifikasi bot aktif...")
    if not send_message("🚀 <b>Crypto Signal Bot aktif!</b>\nMulai memantau pasar..."):
        print("❌ Gagal kirim notifikasi awal — cek log di atas.")
        return

    # Jalankan langsung pertama kali
    check_signals()

    # Jadwalkan setiap X menit
    schedule.every(CHECK_INTERVAL).minutes.do(check_signals)

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()