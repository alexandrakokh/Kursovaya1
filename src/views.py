from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
import logging


logger = logging.getLogger(__name__)


def get_greeting(dt: datetime) -> str:
    hour = dt.hour
    if 5 <= hour < 12:
        return "Доброе утро"
    elif 12 <= hour < 18:
        return "Добрый день"
    else:
        return "Добрый вечер"


def _find_amount_column(df: pd.DataFrame) -> Optional[str]:
    """
    Ищет колонку с суммой. Пробует разные варианты названий,
    чтобы код работал даже если в Excel заголовки немного отличаются.
    """
    possible_names = ["Сумма операции", "Сумма платежа", "Amount", "sum"]
    for name in possible_names:
        if name in df.columns:
            return name
    return None


def build_main_page_response(
        transactions: pd.DataFrame,
        date_str: str,
        stock_prices: List[Dict[str, Any]],
        currency_rates: List[Dict[str, float]]  # <-- ВАЖНО: теперь передаем курсы извне
) -> Dict[str, Any]:
    """
    Собирает ответ для главной страницы.
    Не делает сетевых запросов. Только обработка данных.
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        dt = datetime.now()

    greeting = get_greeting(dt)

    # Работаем с копией, чтобы не менять оригинальный DataFrame
    filtered = transactions.copy()

    if filtered.empty:
        logger.warning("Нет данных для отображения после фильтрации.")
        return {
            "greeting": greeting,
            "cards": [],
            "top_transactions": [],
            "currency_rates": currency_rates,
            "stock_prices": stock_prices,
            "total_operations_count": 0,
            "top_categories": [],
            "top_cashback_categories": []
        }

    # 1. Находим правильную колонку с суммой
    amount_col = _find_amount_column(filtered)

    if not amount_col:
        logger.error("Не найдена колонка с суммой операции. Проверьте заголовки в Excel.")
        return {
            "greeting": greeting,
            "cards": [],
            "top_transactions": [],
            "currency_rates": currency_rates,
            "stock_prices": stock_prices,
            "total_operations_count": 0,
            "top_categories": [],
            "top_cashback_categories": []
        }

    # --- Блок 1: Данные по картам ---
    cards = []
    if "Номер карты" in filtered.columns:
        for card, group in filtered.groupby("Номер карты"):
            # Траты (сумма < 0)
            spending_group = group[group[amount_col] < 0]
            total_spent = spending_group[amount_col].sum()

            # Поступления (сумма > 0)
            income_group = group[group[amount_col] > 0]
            total_income = income_group[amount_col].sum()

            # Кешбэк (1% от трат)
            cashback = abs(total_spent) * 0.01

            cards.append({
                "last_digits": str(card)[-4:] if pd.notna(card) else "Unknown",
                "total_spent": round(total_spent),
                "total_income": round(total_income),
                "cashback": round(cashback)
            })

    # --- Блок 2: Топ транзакций (крупные покупки) ---
    top_list = []
    # Оставляем только траты (сумма < 0)
    spending_df = filtered[filtered[amount_col] < 0].copy()

    if not spending_df.empty:
        exclude_categories = {"Переводы", "Пополнения"}

        if "Категория" in spending_df.columns:
            # Нормализуем категории: убираем пробелы, приводим к нижнему регистру для сравнения
            spending_df["Категория_clean"] = (
                spending_df["Категория"].astype(str).str.strip().str.lower()
            )

            # Фильтруем исключенные категории
            mask_exclude = spending_df["Категория_clean"].isin(
                [c.lower() for c in exclude_categories]
            )
            spending_filtered = spending_df[~mask_exclude]

            # Убираем строки, где категория была NaN (превратилась в строку "nan")
            spending_filtered = spending_filtered[spending_filtered["Категория_clean"] != "nan"]
        else:
            spending_filtered = spending_df

        if not spending_filtered.empty:
            # Топ-5 по модулю суммы (самые дорогие покупки)
            top_idx = spending_filtered[amount_col].abs().nlargest(5).index
            top_df = spending_filtered.loc[top_idx]

            # Выбираем нужные колонки и переименовываем
            cols_to_keep = ["Дата операции", amount_col, "Категория", "Описание"]
            # Проверка, что все колонки существуют в отфильтрованном DF
            cols_final = [c for c in cols_to_keep if c in top_df.columns]

            top_transactions = top_df[cols_final].copy()
            top_transactions.rename(columns={
                "Дата операции": "date",
                amount_col: "amount",
                "Категория": "category",
                "Описание": "description"
            }, inplace=True)

            top_list = top_transactions.to_dict(orient="records")

            # Форматируем даты в строковый вид
            for t in top_list:
                if isinstance(t.get("date"), pd.Timestamp):
                    t["date"] = t["date"].strftime("%d.%m.%Y %H:%M")
                else:
                    t["date"] = str(t.get("date", ""))

    # --- Блок 3: Топ категорий (расходы) ---
    top_categories = []
    rest_amount = 0.0
    exclude_from_top = {"Переводы", "Наличные"}

    if "Категория" in filtered.columns:
        spending_df = filtered[filtered[amount_col] < 0].copy()
        if not spending_df.empty:
            spending_df["Категория_clean"] = (
                spending_df["Категория"].astype(str).str.strip()
            )
            spending_df = spending_df[spending_df["Категория_clean"] != "nan"]

            grouped = spending_df.groupby("Категория_clean")[amount_col].sum()

            # Формируем топ-7
            candidates = grouped.drop(labels=[k for k in exclude_from_top if k in grouped.index], errors="ignore")
            top_7 = candidates.nlargest(7)

            # Остаток
            rest_series = candidates.drop(labels=top_7.index, errors="ignore")
            rest_amount = rest_series.sum()

            for cat, amt in top_7.items():
                top_categories.append({
                    "category": cat,
                    "amount": round(amt)
                })

            if rest_amount != 0:
                top_categories.append({
                    "category": "Остальное",
                    "amount": round(rest_amount)
                })

    # --- Блок 4: Топ категорий для кешбэка ---
    top_cashback_categories = []
    if "Категория" in filtered.columns:
        spending_df = filtered[filtered[amount_col] < 0].copy()
        if not spending_df.empty:
            spending_df["Категория_clean"] = (
                spending_df["Категория"].astype(str).str.strip()
            )
            spending_df = spending_df[spending_df["Категория_clean"] != "nan"]

            grouped = spending_df.groupby("Категория_clean")[amount_col].sum()
            cashbacks = grouped.abs() * 0.01  # 1% кешбэк

            top_3 = cashbacks.nlargest(3)

            for cat, cb in top_3.items():
                top_cashback_categories.append({
                    "category": cat,
                    "cashback": round(cb)
                })

    response = {
        "greeting": greeting,
        "cards": cards,
        "top_categories": top_categories,
        "top_transactions": top_list,
        "currency_rates": currency_rates,  # <-- Сюда кладем то, что передали снаружи
        "stock_prices": stock_prices,
        "total_operations_count": len(filtered),
        "top_cashback_categories": top_cashback_categories,
    }

    logger.info(f"build_main_page_response: date={date_str}, processed rows={len(filtered)}")
    return response


def build_events_response(transactions: pd.DataFrame, date_str: str, range_type: str) -> Dict[str, Any]:
    """
    Заглушка для страницы событий.
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        dt = datetime.now()

    greeting = get_greeting(dt)

    amount_col = _find_amount_column(transactions)

    events = []
    if amount_col and not transactions.empty:
        # Берем последние 10 записей
        recent_df = transactions.tail(10)

        cols_to_keep = ["Дата операции", amount_col, "Категория", "Описание"]
        cols_final = [c for c in cols_to_keep if c in recent_df.columns]

        events_raw = recent_df[cols_final].copy()
        events_raw.rename(columns={
            "Дата операции": "date",
            amount_col: "amount",
            "Категория": "category",
            "Описание": "description"
        }, inplace=True)

        events = events_raw.to_dict(orient="records")

        for e in events:
            if isinstance(e.get("date"), pd.Timestamp):
                e["date"] = e["date"].strftime("%d.%m.%Y %H:%M")
            e["description"] = e.get("description", "")

    return {
        "greeting": greeting,
        "events": events,
        "range_type": range_type,
        "total_count": len(transactions)
    }
