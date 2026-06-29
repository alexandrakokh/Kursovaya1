from datetime import datetime
from typing import List, Dict, Any, Optional
import math
import re
import logging

logger = logging.getLogger(__name__)

def investment_bank(month: str, transactions: List[Dict[str, Any]], limit: int) -> float:
    """
    Считает сумму, которая попала бы в «Инвесткопилку» при округлении до limit.
    month: 'YYYY-MM'
    transactions: список словарей с полями:
      - Дата операции: 'YYYY-MM-DD'
      - Сумма операции: число
    limit: шаг округления (10, 50, 100)
    """
    total = 0.0
    for t in transactions:
        date_str = t.get("Дата операции", "")
        if not date_str.startswith(month):
            continue
        amount = float(t.get("Сумма операции", 0))
        if amount <= 0:
            continue  # только траты
        rounded = math.ceil(amount / limit) * limit
        diff = rounded - amount
        total += diff
    logger.info("investment_bank: month=%s, limit=%d, total=%.2f", month, limit, total)
    return round(total, 2)


def analyze_cashback_categories(
    transactions: List[Dict[str, Any]],
    year: int,
    month: int
) -> Dict[str, float]:
    """
    Анализ выгодности категорий повышенного кешбэка.
    Возвращает словарь: {категория: потенциальный кешбэк (1 руб на 100 руб)}
    """
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
        amount = float(t.get("Сумма операции", 0))
        if amount <= 0:
            continue

        result[category] = result.get(category, 0.0) + amount / 100.0

    logger.info("analyze_cashback_categories: year=%d, month=%d, categories=%d", year, month, len(result))
    return result


PHONE_REGEX = re.compile(
    r"""
    (?:\+7|8)                 # код страны
    \s?                       # опциональный пробел
    (?:\(?\d{3}\)?|\d{3})     # код города/оператора
    [\s\-]?                   # разделитель
    \d{3}                     # 3 цифры
    [\s\-]?                   # разделитель
    \d{2}                     # 2 цифры
    [\s\-]?                   # разделитель
    \d{2}                     # 2 цифры
    """,
    re.VERBOSE
)

PERSON_TRANSFER_REGEX = re.compile(r"\b[А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.\b")


def search_transactions(transactions: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    """Простой поиск по описанию и категории."""
    q = query.lower()
    result = []
    for t in transactions:
        desc = str(t.get("Описание", "")).lower()
        cat = str(t.get("Категория", "")).lower()
        if q in desc or q in cat:
            result.append(t)
    logger.info("search_transactions: query=%s, found=%d", query, len(result))
    return result


def find_phone_numbers(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Поиск транзакций, содержащих мобильные номера в описании."""
    result = []
    for t in transactions:
        desc = str(t.get("Описание", ""))
        if PHONE_REGEX.search(desc):
            result.append(t)
    logger.info("find_phone_numbers: found=%d", len(result))
    return result


def find_person_transfers(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Поиск переводов физлицам: категория «Переводы» и описание содержит «Имя Ф.»"""
    result = []
    for t in transactions:
        cat = t.get("Категория", "")
        desc = t.get("Описание", "")
        if cat != "Переводы":
            continue
        if PERSON_TRANSFER_REGEX.search(str(desc)):
            result.append(t)
    logger.info("find_person_transfers: found=%d", len(result))
    return result
