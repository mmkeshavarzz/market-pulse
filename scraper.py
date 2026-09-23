import requests
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime, timezone, timedelta
import logging

# تنظیمات لاگر
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# منطقه زمانی تهران (برای ثبت دقیق زمان حتی توی سرورهای خارجی گیت‌هاب)
TEHRAN_TZ = timezone(timedelta(hours=3, minutes=30))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive"
}

def get_digikala_data():
    url = "https://www.digikala.com/wealth/my-assets/"
    try:
        logging.info("در حال ارسال درخواست به دیجی‌کالا... 🛍️")
        response = requests.get(url, headers=HEADERS, timeout=15)
        
        if response.status_code != 200:
            logging.error("دیجی‌کالا درخواست ما را مسدود کرد! 🚫")
            return None, None

        # 🐛 باگ‌فیکس: دیجی‌کالا تگ __NEXT_DATA__ را حذف کرده است.
        # راه‌حل: جستجوی مستقیم قیمت در کل سورس صفحه!
        html_text = response.text
        gold_match = re.search(r'"gold_price"\s*:\s*(\d+)', html_text)
        silver_match = re.search(r'"silver_price"\s*:\s*(\d+)', html_text)
        
        gold_price = float(gold_match.group(1)) if gold_match else None
        silver_price = float(silver_match.group(1)) if silver_match else None
        
        if gold_price and silver_price:
            logging.info(f"طلا: {gold_price} | نقره: {silver_price} 🥇🥈")
            return gold_price, silver_price
        else:
            logging.error("الگوی قیمت طلا و نقره در دیجی‌کالا پیدا نشد!")
            return None, None
            
    except Exception as e:
        logging.error(f"خطای ارتباط با دیجی‌کالا: {e}")
        return None, None

def get_dollar_data():
    url = "https://isignal.ir/gold-currency/usdollar/"
    try:
        logging.info("در حال ارسال درخواست به سیگنال... 📈")
        response = requests.get(url, headers=HEADERS, timeout=15)
        
        if response.status_code != 200:
            logging.error("سیگنال درخواست ما را مسدود کرد. 🚫")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text()
        
        # 🐛 باگ‌فیکس: رجکس منعطف‌تر برای پیدا کردن دلار
        match = re.search(r'دلار\s*آزاد.*?([\d,]{6,})', text, re.DOTALL)
        if match:
            price_str = re.sub(r'[^\d]', '', match.group(1))
            logging.info(f"قیمت دلار پیدا شد: {price_str} 💵")
            return float(price_str)
        else:
            logging.error("الگوی قیمت دلار در صفحه پیدا نشد.")
            return None
    except Exception as e:
        logging.error(f"خطای ارتباط با سیگنال: {e}")
        return None

def main():
    os.makedirs('data', exist_ok=True)
    json_path = 'data/prices.json'
    
    old_data = {}
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            old_data = json.load(f)

    gold, silver = get_digikala_data()
    dollar = get_dollar_data()

    # بررسی اینکه آیا واقعاً قیمت جدیدی گرفتیم یا نه؟
    has_new_data = bool(gold or silver or dollar)
    current_time_tehran = datetime.now(TEHRAN_TZ).isoformat()

    # اگر دیتا نگرفتیم، تاریخ قبلی رو نگه می‌داریم تا توی سایت لو نریم! 😉
    new_data = {
        "gold_mg_rial": gold if gold else old_data.get("gold_mg_rial"),
        "silver_mg_rial": silver if silver else old_data.get("silver_mg_rial"),
        "dollar_rial": dollar if dollar else old_data.get("dollar_rial"),
        "updated_at": current_time_tehran if has_new_data else old_data.get("updated_at", current_time_tehran)
    }

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=4)
        
    logging.info(f"فایل prices.json به‌روزرسانی شد. (دیتا جدید بود؟ {has_new_data})")

if __name__ == "__main__":
    main()
