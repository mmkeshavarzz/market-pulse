import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time

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
    """استخراج قیمت میلی‌گرم طلا و نقره از سایت دیجی‌کالا"""
    gold_mg = 0
    silver_mg = 0
    
    # تلاش برای استخراج مستقیم از ساختار دیتای صفحه دیجی کالا
    try:
        url = "https://www.digikala.com/wealth/"
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # دیجی کالا دیتا رو تو اسکریپت های JSON در پایین صفحه جاساز میکنه. ما اونا رو میخونیم.
        script_tags = soup.find_all('script', type='application/json')
        for script in script_tags:
            try:
                data = json.loads(script.string)
                # میگردیم تو JSON تا قیمت ها رو پیدا کنیم. ساختار ممکنه عوض شه پس کلیدهای محتمل رو چک میکنیم
                str_data = str(data)
                
                # جستجوی قیمت طلا (معمولا در حوالی کلمات کلیدی gold_price یا قیمت طلا)
                gold_match = re.search(r'(?i)gold(?:_price)?.*?[\'"]?:\s*(\d{5,7})', str_data)
                if gold_match:
                    gold_mg = int(gold_match.group(1))
                    
                # جستجوی قیمت نقره
                silver_match = re.search(r'(?i)silver(?:_price)?.*?[\'"]?:\s*(\d{3,5})', str_data)
                if silver_match:
                    silver_mg = int(silver_match.group(1))
                    
                if gold_mg > 0 and silver_mg > 0:
                    break # پیدا کردیم، دیگه نیازی به گشتن نیست
                    
            except:
                continue
                
        # اگر از JSON درنیومد، سعی میکنیم از تکست صفحه اعداد رو هوشمندتر دربیاریم
        if not gold_mg or not silver_mg:
            text = soup.get_text(separator=' ')
            
            # اعداد بالای 200,000 ریال نزدیک به کلمه طلا
            if not gold_mg:
                gold_candidates = re.findall(r'طلا.*?(\d{3}[,٫]\d{3}|\d{6,7})', text)
                for cand in gold_candidates:
                    num = clean_number(cand)
                    if 200000 < num < 300000:
                        gold_mg = num
                        break
            
            # اعداد بین 4000 تا 6000 نزدیک به کلمه نقره
            if not silver_mg:
                silver_candidates = re.findall(r'نقره.*?(\d{1}[,٫]\d{3}|\d{4,5})', text)
                for cand in silver_candidates:
                    num = clean_number(cand)
                    if 4000 < num < 6000:
                        silver_mg = num
                        break

    except Exception as e:
        print(f"Error scraping Digikala: {e}")

    return gold_mg, silver_mg

def get_dollar_rate():
    """استخراج قیمت لحظه‌ای دلار از آی‌سیگنال"""
    dollar_price = 0
    for attempt in range(3): # سه بار تلاش میکنیم
        try:
            url = "https://isignal.ir/gold-currency/usdollar/"
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            for tag in soup.find_all(['span', 'div', 'p']):
                if 'ریال' in tag.text and any(c.isdigit() for c in tag.text):
                    num = clean_number(tag.text)
                    if 1000000 <= num <= 20000000:
                        dollar_price = num
                        return dollar_price # به محض پیدا کردن برمیگردونه
        except Exception as e:
            print(f"Attempt {attempt+1} - Error scraping Dollar: {e}")
            time.sleep(2)
            
    return dollar_price

# اجرای توابع
print("Fetching prices...")
gold, silver = get_digikala_wealth()
dollar = get_dollar_rate()

print(f"Extracted -> Gold: {gold}, Silver: {silver}, Dollar: {dollar}")

# ذخیره (با Fallbackهای معقول تر در صورت قطعی سایت ها)
result = {
    "gold_mg_rial": gold if gold else 237784,
    "silver_mg_rial": silver if silver else 4820,
    "dollar_rial": dollar if dollar else 2317050,
    "updated_at": datetime.now().strftime("%H:%M:%S")
}

with open("data/prices.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("✅ Data successfully saved to data/prices.json")
