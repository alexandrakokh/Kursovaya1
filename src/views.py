from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
import logging
from src.utils import log_execution_time

logger = logging.getLogger(__name__)


def get_greeting(dt: datetime) -> str:
    hour = dt.hour
    if 6 <= hour <= 11:
        return "Доброе утро"
    elif 12 <= hour <= 17:
        return "Добрый день"
    elif 18 <= hour <= 22:
        return "Добрый вечер"
    else:
        return "Доброй ночи"


def _find_amount_column(df: pd.DataFrame) -> Optional[str]:
    possible_names = ["Сумма операции", "Сумма платежа", "Amount", "sum"]
    for name in possible_names:
        if name in df.columns:
            return name
    return None


@log_execution_time
def build_main_page_response(transactions, report_date_str, now, currency_rates, stock_prices):
    """
    Возвращает словарь строго в формате, который ждут тесты:
    greeting, cards, top_categories, total_operations_count, top_cashback_categories, top_transactions
    """

    # 1. Приветствие
    hour = now.hour
    if 5 <= hour < 12:
        greeting = "Доброе утро"
    elif 12 <= hour < 18:
        greeting = "Добрый день"
    elif 18 <= hour < 23:
        greeting = "Добрый вечер"
    else:
        greeting = "Доброй ночи"

    # Если DataFrame пустой
    if transactions.empty:
        return {
            "greeting": greeting,
            "cards": [],
            "top_categories": [],
            "total_operations_count": 0,
            "top_cashback_categories": [],
            "top_transactions": [],
            "currency_rates": currency_rates,
            "stock_prices": stock_prices,
        }

    # Проверка наличия колонки «Сумма операции»
    if "Сумма операции" not in transactions.columns:
        return {
            "greeting": greeting,
            "cards": [],
            "top_categories": [],
            "total_operations_count": len(transactions),
            "top_cashback_categories": [],
            "top_transactions": [],
            "currency_rates": currency_rates,
            "stock_prices": stock_prices,
        }

    total_ops = len(transactions)

    # --- Расчёт по картам (cards) ---
    cards_data = []
    grouped_by_card = transactions.groupby("Номер карты")
    for card_num, group in grouped_by_card:
        total_spent = group["Сумма операции"].sum()
        cashback = abs(total_spent) * 0.01
        cards_data.append({
            "last_digits": str(card_num)[-4:],
            "total_spent": int(total_spent),
            "cashback": int(cashback)
        })

    # --- Топ-транзакции (исключаем «Переводы») ---
    tx_df = transactions.copy()
    if "Категория" in tx_df.columns:
        tx_df = tx_df[tx_df["Категория"] != "Переводы"]

    top_tx = []
    if not tx_df.empty and "Сумма операции" in tx_df.columns:
        # Сортируем по убыванию модуля суммы (т.к. траты отрицательные, сортируем по возрастанию)
        tx_sorted = tx_df.sort_values(by="Сумма операции", ascending=True)
        top_n = tx_sorted.head(5)
        for _, row in top_n.iterrows():
            date_val = row["Дата операции"]
            if isinstance(date_val, datetime):
                date_str = date_val.strftime("%d.%m.%Y")
            else:
                date_str = str(date_val)
            top_tx.append({
                "date": date_str,
                "category": row["Категория"],
                "amount": int(row["Сумма операции"])
            })

    # --- Топ-категории (с обработкой «Остальное») ---
    cat_grouped = transactions.groupby("Категория")["Сумма операции"].sum()
    # Сортируем по убыванию модуля суммы
    cat_sorted = cat_grouped.reindex(cat_grouped.abs().sort_values(ascending=False).index)

    top_cats = []
    rest_amount = 0

    # Берем первые 7 категорий
    items = list(cat_sorted.items())
    first_7 = items[:7]
    others = items[7:]

    for cat, amount in first_7:
        top_cats.append({
            "category": cat,
            "amount": int(amount)
        })

    # Если есть остальные категории — суммируем их в «Остальное»
    if others:
        rest_amount = sum(amount for _, amount in others)
        top_cats.append({
            "category": "Остальное",
            "amount": int(rest_amount)
        })

    # --- Кешбэк-категории (исключаем спецкатегории: Переводы, Наличные) ---
    special_cats = {"Переводы", "Наличные"}
    cb_cats = [c for c in top_cats if c["category"] not in special_cats]

    return {
        "greeting": greeting,
        "cards": cards_data,
        "top_categories": top_cats,
        "total_operations_count": total_ops,
        "top_cashback_categories": cb_cats,
        "top_transactions": top_tx,
        "currency_rates": currency_rates,
        "stock_prices": stock_prices,
    }
