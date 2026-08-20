import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, TIMEZONE

ZONE = ZoneInfo(TIMEZONE)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


def check_connection(timeout=15):
    """Periksa koneksi ke Telegram: token valid & chat_id benar."""
    print("🔌 Memeriksa koneksi Telegram...")
    ok = True

    # 1. Cek token via getMe
    try:
        resp = requests.get(f"{TELEGRAM_API}/getMe", timeout=timeout)
        data = resp.json()
        if resp.status_code == 200 and data.get("ok"):
            bot = data["result"]
            print(f"  ✅ Token valid — bot @{bot['username']} terhubung")
        else:
            print(f"  ❌ Token TIDAK valid: {data.get('description', resp.status_code)}")
            print("     → Ganti TELEGRAM_TOKEN di config.py. Cara dapat token:")
            print("       Buka @BotFather di Telegram → /newbot → salin tokennya")
            ok = False
    except requests.RequestException as e:
        print(f"  ❌ Tidak bisa menjangkau Telegram API (cek internet/proxy): {e}")
        ok = False

    # 2. Cek chat_id via getChat
    if ok:
        try:
            resp = requests.get(
                f"{TELEGRAM_API}/getChat",
                params={"chat_id": TELEGRAM_CHAT_ID},
                timeout=timeout,
            )
            data = resp.json()
            if resp.status_code == 200 and data.get("ok"):
                chat = data["result"]
                name = chat.get("title") or chat.get("username") or chat.get("first_name", "?")
                print(f"  ✅ Chat ID benar — bisa kirim ke '{name}'")
            else:
                print(f"  ❌ Chat ID TIDAK valid: {data.get('description', resp.status_code)}")
                print("     → Ganti TELEGRAM_CHAT_ID di config.py. Cara cek:")
                print("       1) Buka chat dengan bot @userinfobot lalu kirim /start")
                print("       2) Copy angka 'id' yang dikirim bot itu")
                ok = False
        except requests.RequestException as e:
            print(f"  ❌ Gagal cek chat: {e}")
            ok = False

    if ok:
        print("  ✅ Koneksi Telegram OK, siap mengirim sinyal!")
    return ok


def send_message(text, max_retries=3, timeout=15):
    """Kirim pesan ke Telegram dengan retry + validasi respons."""
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(url, json=payload, timeout=timeout)

            if resp.status_code == 200:
                if resp.json().get("ok"):
                    return True
                desc = resp.json().get("description", "unknown error")
                print(f"  ❌ Telegram menolak: {desc}")
                return False

            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", attempt * 2))
                print(f"  ⚠️ Rate limit, tunggu {wait}s...")
                time.sleep(wait)
                continue

            print(f"  ⚠️ HTTP {resp.status_code}, coba lagi ({attempt}/{max_retries})")
            time.sleep(2 ** attempt)  # exponential backoff

        except requests.RequestException as e:
            print(f"  ⚠️ Gagal kirim ({attempt}/{max_retries}): {e}")
            time.sleep(2 ** attempt)

    print("  ❌ Semua percobaan gagal — pesan tidak terkirim")
    return False


def _fmt(value, digits=2, prefix=""):
    """Format angka, aman dari NaN/None."""
    try:
        v = float(value)
        if v != v:  # NaN
            return "—"
        return f"{prefix}{v:,.{digits}f}"
    except (TypeError, ValueError):
        return "—"


def format_message(symbol, signal, score, reasons, last):
    harga = _fmt(last.get("close"), 2, "$")
    rsi = _fmt(last.get("rsi"), 1)
    analisis = "\n".join(reasons) if reasons else "—"

    msg = f"""
📊 <b>CRYPTO SIGNAL</b>
━━━━━━━━━━━━━━━━
🪙 Pair   : <b>{symbol}</b>
💰 Harga  : <b>{harga}</b>
📈 Sinyal : <b>{signal}</b>
⚡ Score  : {score}/6

📋 <b>Analisis:</b>
{analisis}

🕐 RSI: {rsi}
━━━━━━━━━━━━━━━━
⚠️ <i>Bukan financial advice. DYOR!</i>
"""
    return msg.strip()


def format_combined_message(entries):
    """Gabungkan semua sinyal crypto dalam SATU pesan."""
    lines = ["📊 <b>CRYPTO SIGNAL UPDATE</b>", "━━━━━━━━━━━━━━━━"]

    for e in entries:
        symbol = e["symbol"]
        signal = e["signal"]
        score = e["score"]
        harga = _fmt(e["last"].get("close"), 2, "Rp" if symbol.endswith("IDR") else "$")
        rsi = _fmt(e["last"].get("rsi"), 1)

        p = e.get("prediction")
        if p:
            target = _fmt(p["target"], 0, "Rp" if symbol.endswith("IDR") else "$")
            pred_line = (
                f"📈 Prediksi {p['bars_ahead']} bar: {p['direction']} "
                f"({p['pct']:+.1f}%) → target {target}"
            )
        else:
            pred_line = "📈 Prediksi: —"

        lines.append(
            f"🪙 <b>{symbol}</b>\n"
            f"{signal} (score {score:+d})\n"
            f"💰 {harga}\n"
            f"🕐 RSI {rsi}\n"
            f"{pred_line}"
        )
        lines.append("─" * 15)

    waktu = datetime.now(ZONE).strftime("%d/%m/%Y %H:%M:%S")
    lines.append(f"🕒 Update: {waktu} (WIB)")
    lines.append("⚠️ <i>Bukan financial advice. DYOR!</i>")

    return "\n".join(lines).strip()