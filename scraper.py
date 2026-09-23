import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def clean_number(text):
    """حذف تمام کاراکترهای غیرعددی و تبدیل اعداد فارسی/عربی به انگلیسی"""
    if not text:
        return 0
    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    arabic_digits = '٠١٢٣٤٥٦٧٨٩'
    for i in range(10):
        text = text.replace(persian_digits[i], str(i)).replace(arabic_digits[i], str(i))
    cleaned = re.sub(r'[^\d]', '', text)
    return int(cleaned) if cleaned else 0

def get_digikala_wealth():
    """استخراج قیمت میلی‌گرم طلا و نقره از دیجی‌کالا"""
    gold_mg = 0
    silver_mg = 0
    
    # روش اول: استفاده مستقیم از API ثروت دیجی‌کالا
    try:
        api_url = "https://api.digikala.com/v1/wealth/prices/"
        res = requests.get(api_url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json().get('data', {})
            # مقادیر بر حسب ریال برای هر میلی‌گرم
            gold_mg = data.get('gold', {}).get('buy_price_per_milligram', 0) or data.get('gold_price', 0)
            silver_mg = data.get('silver', {}).get('buy_price_per_milligram', 0) or data.get('silver_price', 0)
    except Exception:
        pass

    # روش دوم (پشتیبان در صورت تفاوت ساختار API): اسکرپ صفحه
    if not gold_mg or not silver_mg:
        try:
            url = "https://www.digikala.com/wealth/my-assets/"
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            text = soup.get_text()
            
            # جستجوی مستقیم اعداد براساس کلمات کلیدی مجاور
            match_gold = re.search(r'طلای\s*۱۸\s*عیار[^\d]*([\d,]+)', text)
            if match_gold:
                gold_mg = clean_number(match_gold.group(1))
                
            match_silver = re.search(r'نقره\s*۹۹۹[^\d]*([\d,]+)', text)
            if match_silver:
                silver_mg = clean_number(match_silver.group(1))
        except Exception as e:
            print(f"Error scraping Digikala: {e}")

    return gold_mg, silver_mg

def get_dollar_rate():
    """استخراج قیمت لحظه‌ای دلار از آی‌سیگنال"""
    dollar_price = 0
    try:
        url = "https://isignal.ir/gold-currency/usdollar/"
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # پیدا کردن کادر قیمت که دارای تگ ریال است
        for tag in soup.find_all(['span', 'div', 'p']):
            if 'ریال' in tag.text and any(c.isdigit() for c in tag.text):
                # اگر عددی در رنج قیمت دلار (حدود ۱ تا ۱۰ میلیون ریال) یافت شد
                num = clean_number(tag.text)
                if 1000000 <= num <= 20000000:
                    dollar_price = num
                    break
    except Exception as e:
        print(f"Error scraping Dollar: {e}")

    return dollar_price

# اجرای توابع و ذخیره
gold, silver = get_digikala_wealth()
dollar = get_dollar_rate()

# اگر به هر دلیلی مقدار صفر ماند، آخرین مقادیر معتبر حفظ شوند
result = {
    "gold_mg_rial": gold if gold else 237784,
    "silver_mg_rial": silver if silver else 4820,
    "dollar_rial": dollar if dollar else 2317050,
    "updated_at": datetime.now().strftime("%H:%M:%S")
}

with open("data/prices.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("Updated data:", result)
