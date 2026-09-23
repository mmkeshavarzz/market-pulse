import traceback
import json
import os
import re
from datetime import datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup


DATA_FILE = "data/prices.json"

DIGIKALA_URL = "https://www.digikala.com/wealth/my-assets/"
ISIGNAL_URL = "https://isignal.ir/gold-currency/usdollar/"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Referer": "https://www.google.com/",
}

# اگر قیمت موجود در payload دیجی‌کالا تومان باشد، به ریال تبدیل می‌شود.
DIGIKALA_PRICE_UNIT = "toman"


def normalize_digits(value: str) -> str:
    """تبدیل اعداد فارسی و عربی به انگلیسی."""
    translation_table = str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
        "01234567890123456789",
    )
    return value.translate(translation_table)


def parse_number(value: Any) -> Optional[int]:
    """استخراج عدد صحیح از متن یا مقدار عددی."""
    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        return int(value)

    text = normalize_digits(str(value))
    text = (
        text.replace(",", "")
        .replace("،", "")
        .replace("٬", "")
        .replace(" ", "")
    )

    match = re.search(r"\d+", text)
    return int(match.group()) if match else None


def convert_to_rial(value: int, unit: str) -> int:
    """تبدیل تومان به ریال."""
    normalized_unit = normalize_digits(unit).strip().lower()

    if normalized_unit in {"toman", "تومان"}:
        return value * 10

    return value


def find_asset_price(
    node: Any,
    title_pattern: str,
) -> Optional[int]:
    """
    جست‌وجوی بازگشتی قیمت بر اساس عنوان دارایی.
    ترتیب title و price در JSON مهم نیست.
    """
    if isinstance(node, dict):
        title = str(
            node.get("title_fa")
            or node.get("title")
            or node.get("name")
            or ""
        )

        if re.search(title_pattern, title, flags=re.IGNORECASE):
            for price_key in (
                "price",
                "current_price",
                "sell_price",
                "buy_price",
                "amount",
            ):
                price = parse_number(node.get(price_key))

                if price is not None and price > 0:
                    return price

        for child in node.values():
            result = find_asset_price(child, title_pattern)

            if result is not None:
                return result

    elif isinstance(node, list):
        for child in node:
            result = find_asset_price(child, title_pattern)

            if result is not None:
                return result

    return None


def fetch_digikala_prices() -> tuple[Optional[int], Optional[int]]:
    """
    دریافت قیمت طلای ۱۸ عیار و نقره ۹۹۹.
    خروجی برحسب ریال است.
    """
    try:
        response = requests.get(
            DIGIKALA_URL,
            headers=REQUEST_HEADERS,
            timeout=30,
        )
        response.raise_for_status()

        print(
            "Digikala status:",
            response.status_code,
            "content length:",
            len(response.text),
        )

        soup = BeautifulSoup(response.text, "html.parser")
        next_data = soup.find(
            "script",
            id="__NEXT_DATA__",
        )

        if next_data is None:
            raise RuntimeError(
                "داده __NEXT_DATA__ در پاسخ دیجی‌کالا پیدا نشد."
            )

        raw_json = (
            next_data.string
            or next_data.get_text()
        )

        payload = json.loads(raw_json)

        gold_raw = find_asset_price(
            payload,
            r"طلای?\s*(۱۸|18)\s*عیار",
        )

        silver_raw = find_asset_price(
            payload,
            r"نقره\s*(۹۹۹|999)",
        )

        gold_rial = (
            convert_to_rial(
                gold_raw,
                DIGIKALA_PRICE_UNIT,
            )
            if gold_raw is not None
            else None
        )

        silver_rial = (
            convert_to_rial(
                silver_raw,
                DIGIKALA_PRICE_UNIT,
            )
            if silver_raw is not None
            else None
        )

        return gold_rial, silver_rial

    except Exception as error:
        print(f"Digikala Fetch Error: {error}")
        traceback.print_exc()
        return None, None



def fetch_isignal_dollar() -> Optional[int]:
    """
    استخراج قیمت دلار از صفحه سیگنال.
    خروجی برحسب ریال است.
    """
    try:
        response = requests.get(
            ISIGNAL_URL,
            headers=REQUEST_HEADERS,
            timeout=30,
        )
        response.raise_for_status()

        print(
            "iSignal status:",
            response.status_code,
            "content length:",
            len(response.text),
        )

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        text = normalize_digits(
            soup.get_text(" ", strip=True)
        )

        matches = re.findall(
            r"([\d,٬،]+)\s*(ریال|تومان)",
            text,
            flags=re.IGNORECASE,
        )

        candidates: list[int] = []

        for raw_value, unit in matches:
            value = parse_number(raw_value)

            if value is None:
                continue

            value_rial = convert_to_rial(
                value,
                unit,
            )

            if 500_000 <= value_rial <= 100_000_000:
                candidates.append(value_rial)

        if not candidates:
            raise RuntimeError(
                "هیچ قیمت معتبر دلاری در صفحه سیگنال پیدا نشد."
            )

        return candidates[0]

    except Exception as error:
        print(f"iSignal Fetch Error: {error}")
        traceback.print_exc()
        return None


def tehran_now() -> str:
    """تولید زمان فعلی به وقت تهران."""
    return datetime.now(
        ZoneInfo("Asia/Tehran")
    ).strftime("%Y-%m-%d %H:%M:%S")


def read_previous_data() -> dict[str, Any]:
    """خواندن داده قبلی برای جلوگیری از حذف ناگهانی فایل."""
    default_data = {
        "gold_mg_rial": 0,
        "silver_mg_rial": 0,
        "dollar_rial": 0,
        "updated_at": "نامشخص",
    }

    if not os.path.exists(DATA_FILE):
        return default_data

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            previous_data = json.load(file)

        if not isinstance(previous_data, dict):
            return default_data

        return {**default_data, **previous_data}

    except Exception as error:
        print(f"Read previous data error: {error}")
        return default_data


def main() -> None:
    print("Fetching prices...")

    gold_rial, silver_rial = fetch_digikala_prices()
    dollar_rial = fetch_isignal_dollar()

    # اگر هر منبعی شکست خورد، Workflow باید شکست بخورد.
    # این کار جلوی تازه نمایش داده شدن قیمت قدیمی را می‌گیرد.
    errors = []

    if gold_rial is None:
        errors.append("قیمت طلا دریافت نشد.")

    if silver_rial is None:
        errors.append("قیمت نقره دریافت نشد.")

    if dollar_rial is None:
        errors.append("قیمت دلار دریافت نشد.")

    if errors:
        raise RuntimeError(" | ".join(errors))

    new_data = {
        "gold_mg_rial": gold_rial,
        "silver_mg_rial": silver_rial,
        "dollar_rial": dollar_rial,
        "updated_at": tehran_now(),
    }

    os.makedirs(
        os.path.dirname(DATA_FILE),
        exist_ok=True,
    )

    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(
            new_data,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print("Update successful:")
    print(json.dumps(new_data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
