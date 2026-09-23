import requests
from bs4 import BeautifulSoup
import json
import re
import os
from datetime import datetime

# فایل دیتای قبلی که نباید خرابش کنیم!
DATA_FILE = 'data/prices.json'

def clean_number(text):
    if not text: return None
    # تبدیل اعداد فارسی/عربی به انگلیسی
    translation_table = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')
    text = text.translate(translation_table)
    # استخراج فقط اعداد
    numbers = re.findall(r'\d+', text)
    if numbers:
        return int(''.join(numbers))
    return None

def fetch_digikala_prices():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    gold, silver = None, None
    try:
        # روش اول: استفاده از دیتای مخفی Next.js در صفحه ثروت دیجی‌کالا
        res = requests.get("https://www.digikala.com/wealth/my-assets/", headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        next_data = soup.find('script', id='__NEXT_DATA__')
        
        if next_data:
            data = json.loads(next_data.text)
            # این مسیر ممکنه بسته به آپدیت‌های دیجی‌کالا تغییر کنه، اما معمولاً تو state ها هست
            # اینجا یک روش جستجوی هوشمند تو دیکشنری پیاده می‌کنیم
            str_data = json.dumps(data)
            
            # جستجوی قیمت طلا (مثلا 18 عیار) با RegEx تو کل JSON
            gold_match = re.search(r'"title_fa":"طلای 18 عیار".*?"price":(\d+)', str_data)
            if gold_match:
                gold = int(gold_match.group(1)) * 10 # تبدیل تومان به ریال در صورت نیاز (بستگی به خروجی دیجی‌کالا داره)
                
            silver_match = re.search(r'"title_fa":"نقره 999".*?"price":(\d+)', str_data)
            if silver_match:
                silver = int(silver_match.group(1)) * 10
                
    except Exception as e:
        print(f"Digikala Fetch Error: {e}")
    
    return gold, silver

def fetch_isignal_dollar():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        res = requests.get("https://isignal.ir/gold-currency/usdollar/", headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # پیدا کردن تگ دقیقی که قیمت رو داره (معمولاً تو هدینگ‌ها یا جداول اصلی)
        # این سلکتور رو باید بر اساس ساختار دقیق آی‌سیگنال تنظیم کنی. 
        # ما دنبال اولین عدد بزرگ معقول می‌گردیم
        price_tags = soup.find_all(['span', 'p', 'h2', 'h3'])
        for tag in price_tags:
            text = tag.get_text().replace(',', '').strip()
            if 'ریال' in text or 'تومان' in text:
                num = clean_number(text)
                if num and 50000 < num < 10000000: # یک بازه معقول برای قیمت دلار
                    # اگر تومان بود به ریال تبدیل کن
                    if 'تومان' in text:
                        num *= 10
                    return num
    except Exception as e:
        print(f"iSignal Fetch Error: {e}")
    return None

def main():
    # 1. خواندن قیمت‌های قبلی (تا اگر آپدیت نشد، دیتای چرت و پرت نشون ندیم)
    old_data = {"gold_mg_rial": 0, "silver_mg_rial": 0, "dollar_rial": 0}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
        except:
            pass

    print("Fetching new prices...")
    gold, silver = fetch_digikala_prices()
    dollar = fetch_isignal_dollar()

    # 2. ترکیب دیتای جدید و قدیم
    new_data = {
        "gold_mg_rial": gold if gold else old_data.get("gold_mg_rial", 0),
        "silver_mg_rial": silver if silver else old_data.get("silver_mg_rial", 0),
        "dollar_rial": dollar if dollar else old_data.get("dollar_rial", 0),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # 3. ذخیره فایل
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)
        
    print("Update successful!")
    print(new_data)

if __name__ == "__main__":
    main()
