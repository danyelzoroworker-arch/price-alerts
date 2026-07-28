"""
===================================================================
 بوت تنبيهات أسعار مجاني - كريبتو + أسهم/فوركس
 يبعت تنبيه على تيليجرام والإيميل لما السعر يوصل لمستوى معين
===================================================================

المكتبات المطلوبة (مجانية بالكامل):
    pip install requests yfinance

مصادر الأسعار:
    - الكريبتو: Binance Public API (مجاني، بدون مفتاح API)
    - الأسهم/الفوركس: Yahoo Finance عبر مكتبة yfinance (مجاني)

طريقة التشغيل:
    python price_alert_bot.py

البوت هيفضل شغال في الخلفية ويفحص الأسعار كل CHECK_INTERVAL ثانية.
اتركه شغال على جهازك أو على سيرفر صغير (زي VPS ببلاش أو Raspberry Pi)
عشان يفضل بيراقب على مدار الساعة.
"""

import time
import smtplib
import requests
from email.mime.text import MIMEText
from datetime import datetime

# ===================================================================
# 1) الإعدادات - املأ بياناتك هنا
# ===================================================================

# --- إعدادات تيليجرام ---
# 1. افتح تيليجرام ودور على @BotFather وابعتله /newbot واتبع الخطوات
#    هيديك TOKEN زي كده: 123456789:ABCdefGhIJKlmNoPQRstuVWXyz
# 2. ابعت أي رسالة للبوت بتاعك، بعدين افتح اللينك ده في المتصفح
#    (غيّر TOKEN باللي أخدته):
#    https://api.telegram.org/botTOKEN/getUpdates
#    وهتلاقي "chat":{"id": 123456789 ...} - ده الـ CHAT_ID بتاعك
TELEGRAM_BOT_TOKEN = "8963105964:AAFvRK7PJ-8IrTvvmD5ZGLeW6uuJXD_GZy0"
TELEGRAM_CHAT_ID = "8584543262"
# --- إعدادات الإيميل (مثال لجيميل) ---
# لازم تعمل "App Password" من إعدادات حساب جوجل (مش الباسورد العادي)
# من هنا: https://myaccount.google.com/apppasswords
EMAIL_ENABLED = True
EMAIL_SENDER = "your_email@gmail.com"
EMAIL_APP_PASSWORD = "ضع_كلمة_مرور_التطبيق_هنا"
EMAIL_RECEIVER = "your_email@gmail.com"   # ممكن تكون نفس الإيميل
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# --- كل قد إيه (بالثواني) يفحص الأسعار ---
CHECK_INTERVAL = 60  # كل دقيقة - قلل الرقم لو عايز فحص أسرع

# ===================================================================
# 2) قائمة التنبيهات - ضيف/احذف/عدّل براحتك
# ===================================================================
# market: "crypto" أو "stock" (الأسهم والفوركس بتتعامل بنفس الطريقة عبر yfinance)
# condition: "above" (فوق) أو "below" (تحت)
#
# أمثلة:
#   كريبتو: symbol = "BTCUSDT", "ETHUSDT" ...الخ (زي أسماء أزواج Binance)
#   أسهم:   symbol = "AAPL", "TSLA" ...الخ
#   فوركس:  symbol = "EURUSD=X", "GBPUSD=X" ...الخ (صيغة Yahoo Finance)

ALERTS = [
    {"symbol": "BTCUSDT", "market": "crypto", "target_price": 70000, "condition": "above"},
    {"symbol": "ETHUSDT", "market": "crypto", "target_price": 3000, "condition": "below"},
    {"symbol": "AAPL", "market": "stock", "target_price": 200, "condition": "above"},
    {"symbol": "EURUSD=X", "market": "stock", "target_price": 1.05, "condition": "below"},
]

# بعد ما يتبعت التنبيه، إمتى يسمحله يتبعت تاني لنفس المستوى (بالثواني)
# ده عشان السعر لو فضل مذبذب حوالين المستوى ميضربكش برسايل كتير
RE_ALERT_COOLDOWN = 3600  # ساعة واحدة

# ===================================================================
# 3) دوال جلب الأسعار
# ===================================================================

def get_crypto_price(symbol: str):
    """يجيب سعر عملة رقمية من Binance (مجاني، بدون مفتاح API)."""
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return float(resp.json()["price"])
    except Exception as e:
        print(f"[خطأ] فشل جلب سعر {symbol} من Binance: {e}")
        return None


def get_stock_price(symbol: str):
    """يجيب سعر سهم أو زوج فوركس من Yahoo Finance (مجاني)."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d", interval="1m")
        if data.empty:
            data = ticker.history(period="5d")
        return float(data["Close"].iloc[-1])
    except Exception as e:
        print(f"[خطأ] فشل جلب سعر {symbol} من Yahoo Finance: {e}")
        return None


def get_price(alert: dict):
    if alert["market"] == "crypto":
        return get_crypto_price(alert["symbol"])
    else:
        return get_stock_price(alert["symbol"])


# ===================================================================
# 4) دوال إرسال التنبيهات
# ===================================================================

def send_telegram(message: str):
    if not TELEGRAM_BOT_TOKEN or "ضع_" in TELEGRAM_BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
    except Exception as e:
        print(f"[خطأ] فشل إرسال تيليجرام: {e}")


def send_email(subject: str, message: str):
    if not EMAIL_ENABLED or "ضع_" in EMAIL_APP_PASSWORD:
        return
    try:
        msg = MIMEText(message)
        msg["Subject"] = subject
        msg["From"] = EMAIL_SENDER
        msg["To"] = EMAIL_RECEIVER
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_APP_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
    except Exception as e:
        print(f"[خطأ] فشل إرسال الإيميل: {e}")


def notify(message: str):
    print(f"[تنبيه] {message}")
    send_telegram(message)
    send_email("🔔 تنبيه سعر", message)


# ===================================================================
# 5) الحلقة الرئيسية للمراقبة
# ===================================================================

def condition_met(price: float, alert: dict) -> bool:
    if alert["condition"] == "above":
        return price >= alert["target_price"]
    else:
        return price <= alert["target_price"]


def main():
    print("=== بدء تشغيل بوت التنبيهات ===")
    print(f"عدد التنبيهات المُعرّفة: {len(ALERTS)}")
    for a in ALERTS:
        a["last_triggered_at"] = 0  # وقت آخر تنبيه اتبعت (لأجل الـ cooldown)

    while True:
        now = time.time()
        for alert in ALERTS:
            price = get_price(alert)
            if price is None:
                continue

            symbol = alert["symbol"]
            target = alert["target_price"]
            cond_txt = "أعلى من أو يساوي" if alert["condition"] == "above" else "أقل من أو يساوي"
            print(f"{datetime.now().strftime('%H:%M:%S')} | {symbol}: {price} (الهدف: {cond_txt} {target})")

            if condition_met(price, alert):
                if now - alert["last_triggered_at"] >= RE_ALERT_COOLDOWN:
                    message = (
                        f"🚨 وصل سعر {symbol} إلى {price}\n"
                        f"الشرط: {cond_txt} {target}"
                    )
                    notify(message)
                    alert["last_triggered_at"] = now

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nتم إيقاف البوت.")
