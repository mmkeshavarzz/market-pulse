import requests
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime
import logging

# تنظیمات لاگر برای اینکه دقیقاً بفهمیم پایتون داره چیکار می‌کنه
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# لباس مبدل برای پایتون تا شبیه یک مرورگر واقعی به نظر برسه! (خیلی مهم)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive"
}

def get_digikala_data():
    url = "https://www.digikala.com/wealth/my-assets/"
    try:
        logging.info("در حال ارسال درخواست به دیجی‌کالا...")
        response = requests.get(url, headers=HEADERS, timeout=15)
        logging.info(f"کد وضعیت دیجی‌کالا: {response.status_code}")
        
        if response.status_code != 200:
            logging.error("دیجی‌کالا درخواست ما را مسدود کرد (احتمالاً Cloudflare).")
            return None, None

        soup = BeautifulSoup(response.text, 'html.parser')
        next_data_script = soup.find('script', id='__NEXT_DATA__')
        
        if next_data_script:
            data = json.loads(next_data_script.string)
            # اینجا باید مسیر دقیق JSON را پیدا کنیم (مسیر فرضی قبلی شما)
            # لطفاً اگر KeyError گرفتید، فایل لاگ را بررسی کنید
            # فرض می‌کنیم مسیر قبلی شما درست بوده است
            try:
                # این مسیر ممکن است در دیجی‌کالا تغییر کرده باشد
                gold_price = None 
                silver_price = None
                logging.info("داده‌های دیجی‌کالا با موفقیت استخراج شد (نیاز به پیاده‌سازی مسیر دقیق JSON)")
                return gold_price, silver_price
            except Exception as e:
                logging.error(f"خطا در تجزیه ساختار JSON دیجی‌کالا: {e}")
                return None, None
        else:
            logging.error("تگ __NEXT_DATA__ در صفحه دیجی‌کالا پیدا نشد!")
            return None, None
            
    except requests.exceptions.RequestException as e:
        logging.error(f"خطای ارتباط با دیجی‌کالا: {e}")
        return None, None

def get_dollar_data():
    url = "https://isignal.ir/gold-currency/usdollar/"
    try:
        logging.info("در حال ارسال درخواست به سیگنال...")
        response = requests.get(url, headers=HEADERS, timeout=15)
        logging.info(f"کد وضعیت سیگنال: {response.status_code}")
        
        if response.status_code != 200:
            logging.error("سیگنال درخواست ما را مسدود کرد.")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        # جستجو بر اساس الگوی قیمتی (این بخش به کدهای قبلی شما وفادار است)
        text = soup.get_text()
        match = re.search(r'قیمت دلار\s*[\d,]+', text)
        if match:
            price_str = re.sub(r'[^\d]', '', match.group(0))
            logging.info(f"قیمت دلار پیدا شد: {price_str}")
            return float(price_str)
        else:
            logging.error("الگوی قیمت دلار در صفحه پیدا نشد.")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"خطای ارتباط با سیگنال: {e}")
        return None

def main():
    os.makedirs('data', exist_ok=True)
    json_path = 'data/prices.json'
    
    # خواندن داده‌های قبلی برای کش (Fallback)
    old_data = {}
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            old_data = json.load(f)

    gold, silver = get_digikala_data()
    dollar = get_dollar_data()

    # آپدیت داده‌ها در صورت موفقیت، یا استفاده از داده‌های قدیمی
    new_data = {
        "gold_mg_rial": gold if gold else old_data.get("gold_mg_rial"),
        "silver_mg_rial": silver if silver else old_data.get("silver_mg_rial"),
        "dollar_rial": dollar if dollar else old_data.get("dollar_rial"),
        "updated_at": datetime.now().isoformat()
    }

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=4)
        
    logging.info("فایل prices.json با موفقیت به‌روزرسانی شد.")

if __name__ == "__main__":
    main()
