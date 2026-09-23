import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import re

# =========================
# Config
# =========================
URLS = {
    "gold": "https://www.tgju.org/profile/geram18",          # طلای 18 عیار (هر گرم)
    "silver": "https://www.tgju.org/profile/silver_999",     # نقره 999 (هر گرم)
    "usd": "https://www.tgju.org/profile/price_dollar_rl",   # دلار آزاد (ریال)
}

DATA_FILE = "data/prices.json"

# =========================
# Helpers
# =========================
def now_tehran():
    return datetime.now(ZoneInfo("Asia/Tehran"))

def jalali_now_str():
    # خروجی نمونه: 1405/07/02 14:35:10
    # تقویم فارسی بدون وابستگی خارجی، با Intl در فرانت هم فرمت می‌شود
    t = now_tehran()
    return t.strftime("%Y-%m-%d %H:%M:%S")

def parse_price_from_tgju(html_text: str):
    """
    تلاش می‌کند قیمت را از ساختارهای رایج TGJU استخراج کند.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    text = soup.get_text(" ", strip=True)

    # الگوهای رایج (ارقام با کاما)
    candidates = []

    # 1) data attributes / price blocks
    for sel in [
        '[data-col="info.last_trade.PDrCotVal"]',
        ".text-5xl",
        ".value",
        ".price",
        "#main",
    ]:
        nodes = soup.select(sel)
        for n in nodes:
            found = re.findall(r"\b\d{1,3}(?:,\d{3})+\b", n.get_text(" ", strip=True))
            candidates.extend(found)

    # 2) fallback روی کل متن
    if not candidates:
        candidates = re.findall(r"\b\d{1,3}(?:,\d{3})+\b", text)

    # فیلتر اعداد نامعتبر/خیلی کوچک
    numeric = []
    for c in candidates:
        v = int(c.replace(",", ""))
        if v > 1000:
            numeric.append(v)

    if not numeric:
        return None

    # اغلب اولین مقدار معتبر همان قیمت جاری است
    return numeric[0]

def fetch_price(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; MarketPulseBot/2.0; +https://github.com/)"
    }
    r = requests.get(url, headers=headers, timeout=25)
    r.raise_for_status()
    return parse_price_from_tgju(r.text)

def ensure_data_dir():
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

def load_existing():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def to_iso_tehran(dt_obj):
    return dt_obj.isoformat()

# =========================
# Main
# =========================
def main():
    ensure_data_dir()
    existing = load_existing()

    now = now_tehran()
    now_iso = to_iso_tehran(now)

    # ساختار خروجی با حفظ مقادیر قبلی
    data = {
        "gold": existing.get("gold"),
        "silver": existing.get("silver"),
        "usd": existing.get("usd"),

        # last_success هر فیلد
        "gold_last_success": existing.get("gold_last_success"),
        "silver_last_success": existing.get("silver_last_success"),
        "usd_last_success": existing.get("usd_last_success"),

        # آخرین اجرای ربات
        "last_run_at": now_iso
    }

    # GOLD (ریال / گرم -> ریال / میلی‌گرم)
    try:
        g = fetch_price(URLS["gold"])
        if g is not None:
            gold_per_mg = round(g / 1000)  # 1 گرم = 1000 میلی‌گرم
            data["gold"] = gold_per_mg
            data["gold_last_success"] = now_iso
    except Exception as e:
        print(f"[WARN] gold fetch failed: {e}")

    # SILVER 999 (ریال / گرم -> ریال / میلی‌گرم)
    try:
        s = fetch_price(URLS["silver"])
        if s is not None:
            silver_per_mg = round(s / 1000)  # 1 گرم = 1000 میلی‌گرم
            data["silver"] = silver_per_mg
            data["silver_last_success"] = now_iso
    except Exception as e:
        print(f"[WARN] silver fetch failed: {e}")

    # USD (ریال)
    try:
        u = fetch_price(URLS["usd"])
        if u is not None:
            data["usd"] = u
            data["usd_last_success"] = now_iso
    except Exception as e:
        print(f"[WARN] usd fetch failed: {e}")

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("[OK] prices.json updated")
    print(json.dumps(data, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
