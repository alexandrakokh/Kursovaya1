# src/services.py
from datetime import datetime
from typing import List, Dict, Any
import math
import re
import logging

logger = logging.getLogger(__name__)


def investment_bank(month: str, transactions: List[Dict[str, Any]], limit: int) -> float:
    total = 0.0
    for t in transactions:
        date_str = t.get("Дата операции", "")
        if not isinstance(date_str, str):
            continue
        if not date_str.startswith(month):
            continue

        try:
            amount = float(t.get("Сумма операции", 0))
        except (ValueError, TypeError):
            continue

        if amount <= 0:
            continue

        rounded = math.ceil(amount / limit) * limit
        diff = rounded - amount
        total += diff

    return round(total, 2)


def analyze_cashback_categories(transactions: List[Dict[str, Any]], year: int, month: int) -> Dict[str, float]:
    result: Dict[str, float] = {}
    for t in transactions:
        dt = t.get("Дата операции")
        if isinstance(dt, str):
            try:
                dt = datetime.strptime(dt, "%Y-%m-%d")
            except ValueError:
                continue
        if not isinstance(dt, datetime):
            continue

        if dt.year != year or dt.month != month:
            continue

        category = t.get("Категория", "Прочее")
        if not category or category.strip() == "":
            category = "Прочее"

        try:
            amount = float(t.get("Сумма операции", 0))
        except (ValueError, TypeError):
            continue

        if amount <= 0:
            continue

        result[category] = result.get(category, 0.0) + amount / 100.0

    return result


PHONE_REGEX = re.compile(r"(?:\+7|7|8)\s?(?:\(?\d{3}\)?|\d{3})[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}")
PERSON_TRANSFER_REGEX = re.compile(r"[А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.")


def search_transactions(transactions: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    print("=== search_transactions ЗАПУЩЕНА ===")
    q = query.lower().replace('ё', 'е')
    print(f"--- NORMALIZED QUERY: {repr(q)} ---")

    result = []
    for i, t in enumerate(transactions):
        desc_raw = t.get("Описание", "")
        cat_raw = t.get("Категория", "")

        # Нормализуем
        desc = str(desc_raw).lower().replace('ё', 'е')
        cat = str(cat_raw).lower().replace('ё', 'е')

        print(f"[{i}] desc_raw={repr(desc_raw)} | desc={repr(desc)} | cat={repr(cat)} | match={q in desc or q in cat}")

        if q in desc or q in cat:
            result.append(t)

    print(f"=== search_transactions ГОТОВА: найдено {len(result)} ===")
    return result


def find_phone_numbers(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    result = []
    for t in transactions:
        desc = str(t.get("Описание", ""))
        if PHONE_REGEX.search(desc):
            result.append(t)
    return result


def find_person_transfers(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    result = []
    for t in transactions:
        cat = t.get("Категория", "")
        desc = t.get("Описание", "")

        if cat != "Переводы":
            continue

        if PERSON_TRANSFER_REGEX.search(str(desc)):
            result.append(t)

    return result

