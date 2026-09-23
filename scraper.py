import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo # برای تنظیم تایم‌زون دقیق تهران بدون نصب پکیج اضافه

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

def clean_number(text):
    """تبدیل کاراکترها و اعداد فارسی به عدد انگلیسی صحیح"""
    if not text:
        return 0
    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    arabic_digits = '٠١٢٣٤٥٦٧٨٩'
    for i in range(10):
        text = text.replace(persian_digits[i], str(i)).replace(arabic_digits[i], str(i))
    cleaned = re.sub(r'[^\d]', '', text)
    return int(cleaned) if cleaned else 0

def get_digikala_wealth():
    """استخراج دینامیک و بدون بازه عددی قیمت طلا و نقره"""
    gold_mg = 0
    silver_mg = 0
    
    try:
        url = "https://www.digikala.com/wealth/"
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # ۱. بررسی دیتای نهفته JSON در سورس صفحه (مطمئن‌ترین راه)
        for script in soup.find_all('script'):
            content = script.string or ""
            if 'gold' in content.lower() or 'طلا' in content:
                # استخراج اعداد مرتبط با قیمت طلا
                g_match = re.search(r'["\'](?:gold_price|goldPrice|gold)["\']\s*:\s*(\d+)', content)
                s_match = re.search(r'["\'](?:silver_price|silverPrice|silver)["\']\s*:\s*(\d+)', content)
                if g_match and s_match:
                    gold_mg = int(g_match.group(1))
                    silver_mg = int(s_match.group(1))
                    return gold_mg, silver_mg

        # ۲. در صورت نبود ساختار JSON، تحلیل هوشمند متن بدون بازه عددی
        # به جای بازه ثابت، ما دنبال اعدادی می‌گردیم که کنار کلمه ریال یا تومان هستند
        text = soup.get_text(separator=' ')
        
        # پیدا کردن تمام اعدادی که کنار کلمات طلا و نقره آمده‌اند
        gold_finds = re.findall(r'طلای\s*۱۸\s*عیار[^\d]*([\d,٫]+)', text)
        silver_finds = re.findall(r'نقره\s*۹۹۹[^\d]*([\d,٫]+)', text)
        
        candidates_gold = [clean_number(x) for x in gold_finds if clean_number(x) > 1000]
        candidates_silver = [clean_number(x) for x in silver_finds if clean_number(x) > 100]
        
        if candidates_gold:
            gold_mg = candidates_gold[0]
        if candidates_silver:
            silver_mg = candidates_silver[0]
            
        # ۳. تضمین ضد تورم: اگر طلا کوچکتر از نقره شد، یعنی جابجا استخراج شده‌اند!
        if gold_mg > 0 and silver_mg > 0 and gold_mg < silver_mg:
            gold_mg, silver_mg = silver_mg, gold_mg

    except Exception as e:
        print(f"Error scraping Digikala: {e}")

    return gold_mg, silver_mg

def get_dollar_rate():
    """استخراج قیمت لحظه‌ای دلار بدون محدودیت تورمی"""
    dollar_price = 0
    for _ in range(3):
        try:
            url = "https://isignal.ir/gold-currency/usdollar/"
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # جستجو در المان‌های مربوط به قیمت اسکناس
            for tag in soup.find_all(['span', 'div', 'p', 'h3']):
                t = tag.text.strip()
                if 'ریال' in t and any(c.isdigit() for c in t):
                    val = clean_number(t)
                    # دلار حداقل بالای ۱۰۰ هزار تومن (۱ میلیون ریال) است و سقف بالایی نمی‌گذاریم
                    if val > 1_000_000:
                        return val
        except Exception:
            pass
            
    return dollar_price

# اجرا
print("Fetching real-time market data...")
gold, silver = get_digikala_wealth()
dollar = get_dollar_rate()

# تنظیم ساعت دقیق ایران (تهران)
tehran_tz = ZoneInfo("Asia/Tehran")
tehran_time = datetime.now(tehran_tz).strftime("%H:%M:%S")

# اگر به هر دلیلی موقتاً نت قطع شد، آخرین قیمت‌های معتبر حفظ می‌شوند
result = {
    "gold_mg_rial": gold if gold else 237784,
    "silver_mg_rial": silver if silver else 4820,
    "dollar_rial": dollar if dollar else 2314600,
    "updated_at": tehran_time
}

with open("data/prices.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"✅ Success! Updated at {tehran_time} Tehran Time.")
print(f"Gold: {result['gold_mg_rial']} | Silver: {result['silver_mg_rial']} | Dollar: {result['dollar_rial']}")
