import requests
from bs4 import BeautifulSoup
import json
import re
import os
from datetime import datetime, timedelta, timezone

DATA_FILE = 'data/prices.json'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def clean_number(text):
    """
    دریافت اولین عدد معتبر از متن بدون چسباندن اعداد اضافی (مثل سال یا تاریخ)
    """
    if not text: return None
    # تبدیل اعداد فارسی/عربی به انگلیسی
    translation_table = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')
    text = text.translate(translation_table)
    
    # حذف کاما و فاصله
    text = text.replace(',', '').replace('،', '').replace(' ', '')
    
    # پیدا کردن اولین گروه عددی متوالی
    match = re.search(r'\d+', text)
    if match:
        return int(match.group(0))
    return None

def fetch_digikala_prices():
    gold, silver = None, None
    try:
        res = requests.get("https://www.digikala.com/wealth/my-assets/", headers=headers, timeout=12)
        soup = BeautifulSoup(res.text, 'html.parser')
        next_data = soup.find('script', id='__NEXT_DATA__')
        
        if next_data:
            str_data = next_data.string
            
            # جستجوی قیمت طلا (دیجی‌کالا قیمت را به تومان می‌دهد، در 10 ضرب می‌کنیم تا ریال شود)
            gold_match = re.search(r'"title_fa":"طلای 18 عیار".*?"price":(\d+)', str_data)
            if gold_match:
                gold = int(gold_match.group(1)) * 10
                
            # جستجوی قیمت نقره
            silver_match = re.search(r'"title_fa":"نقره 999".*?"price":(\d+)', str_data)
            if silver_match:
                silver = int(silver_match.group(1)) * 10
    except Exception as e:
        print(f"Digikala Fetch Error: {e}")
        
    return gold, silver

def fetch_isignal_dollar():
    dollar = None
    try:
        res = requests.get("https://isignal.ir/gold-currency/usdollar/", headers=headers, timeout=12)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        price_tags = soup.find_all(['span', 'p', 'h2', 'h3', 'div'])
        for tag in price_tags:
            text = tag.get_text().strip()
            # پیدا کردن متنی که نشانه دلار و ریال/تومان دارد
            if 'دلار' in text or 'ریال' in text or 'تومان' in text:
                num = clean_number(text)
                
                # فیلتر هوشمند: قیمت دلار باید در یک بازه منطقی باشد
                if num and 40000 < num < 2000000:
                    if num < 150000: # اگر عدد کوچک است، یعنی به تومان نوشته شده
                        num *= 10
                    dollar = num
                    break
    except Exception as e:
        print(f"iSignal Fetch Error: {e}")
        
    return dollar

def get_tehran_time():
    """محاسبه ساعت به وقت تهران (بدون وابستگی به تنظیمات سرور گیت‌هاب)"""
    tz = timezone(timedelta(hours=3, minutes=30))
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

def main():
    old_data = {"gold_mg_rial": 0, "silver_mg_rial": 0, "dollar_rial": 0, "updated_at": "نامشخص"}
    
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
        except:
            pass

    print("در حال استخراج قیمت‌های جدید...")
    gold, silver = fetch_digikala_prices()
    dollar = fetch_isignal_dollar()

    # بررسی اینکه آیا حداقل یکی از قیمت‌ها با موفقیت دریافت شد؟
    any_updated = bool(gold or silver or dollar)

    # مقادیر جدید: اگر موفق بود عدد جدید، وگرنه عدد قبلی
    new_data = {
        "gold_mg_rial": gold if gold else old_data.get("gold_mg_rial", 0),
        "silver_mg_rial": silver if silver else old_data.get("silver_mg_rial", 0),
        "dollar_rial": dollar if dollar else old_data.get("dollar_rial", 0),
        # اگر اطلاعات جدیدی گرفتیم زمان را تغییر بده، در غیر این صورت زمان آخرین آپدیتِ موفق را نگه دار
        "updated_at": get_tehran_time() if any_updated else old_data.get("updated_at", get_tehran_time())
    }

    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=4)

    print("عملیات به پایان رسید!")
    print(new_data)

if __name__ == "__main__":
    main()
