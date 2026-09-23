import json
import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

def clean_to_number(text: str) -> int:
    if not text:
        return 0
    for p, a in zip("۰۱۲۳۴۵۶۷۸۹", "٠١٢٣٤٥٦٧٨٩"):
        text = text.replace(p, str("۰۱۲۳۴۵۶۷۸۹".index(p))).replace(a, str("٠١٢٣٤٥٦٧٨٩".index(a)))
    nums = re.sub(r"[^\d]", "", text)
    return int(nums) if nums else 0

def fetch_dollar() -> int:
    try:
        res = requests.get("https://isignal.ir/gold-currency/usdollar/", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        elem = soup.find(string=re.compile(r"ریال"))
        if elem:
            return clean_to_number(elem.find_parent().text)
    except Exception as e:
        print(f"خطا در دریافت دلار: {e}")
    return 2314600

def fetch_metals() -> dict:
    try:
        res = requests.get("https://api.digikala.com/v1/wealth/market/summary/", headers=HEADERS, timeout=12)
        if res.status_code == 200:
            d = res.json().get("data", {})
            return {
                "gold": d.get("gold_price_per_mg", 4250) * 10,
                "silver": d.get("silver_price_per_mg", 120) * 10
            }
    except Exception as e:
        print(f"خطا در دریافت طلا/نقره: {e}")
    return {"gold": 42500, "silver": 1200}

if __name__ == "__main__":
    metals = fetch_metals()
    dollar = fetch_dollar()

    payload = {
        "goldMgRial": metals["gold"],
        "silverMgRial": metals["silver"],
        "dollarRial": dollar,
        "lastUpdated": datetime.utcnow().isoformat() + "Z"
    }

    os.makedirs("data", exist_ok=True)
    with open("data/prices.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print("نرخ‌ها با موفقیت ذخیره شدند:", payload)
