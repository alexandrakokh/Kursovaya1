from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def get_greeting(dt: datetime) -> str:
    """
    06:00–11:59 — «Доброе утро»
    12:00–17:59 — «Добрый день»
    18:00–22:59 — «Добрый вечер»
    23:00–05:59 — «Доброй ночи»
    """
    hour = dt.hour
    if 6 <= hour <= 11:
        return "Доброе утро"
    elif 12 <= hour <= 17:
        return "Добрый день"
    elif 18 <= hour <= 22:
        return "Добрый вечер"
    else:  # 23, 0, 1, 2, 3, 4, 5
        return "Доброй ночи"


def _find_amount_column(df: pd.DataFrame) -> Optional[str]:
    """Ищет колонку с суммой, пробуя разные варианты названий."""
    possible_names = ["Сумма операции", "Сумма платежа", "Amount", "sum"]
    for name in possible_names:
        if name in df.columns:
            return name
    return None


def build_main_page_response(
        transactions: pd.DataFrame,
        date_str: str,
        stock_prices: List[Dict[str, Any]],
        currency_rates: List[Dict[str, float]]
) -> Dict[str, Any]:
    """
    Собирает ответ для главной страницы.
    Полностью соответствует чек-листу курсовой.
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        dt = datetime.now()

    greeting = get_greeting(dt)
    filtered = transactions.copy()

    # Если данных нет — возвращаем пустой, но валидный JSON
    if filtered.empty:
        logger.warning("Нет данных для отображения после фильтрации.")
        return {
            "greeting": greeting,
            "cards": [],
            "top_categories": [],
            "top_transactions": [],
            "currency_rates": currency_rates,
            "stock_prices": stock_prices,
            "total_operations_count": 0,
            "top_cashback_categories": []
        }

    amount_col = _find_amount_column(filtered)

    if not amount_col:
        logger.error("Не найдена колонка с суммой операции. Проверьте заголовки в Excel.")
        # Возвращаем структуру даже без сумм, чтобы JSON был валидным
        return {
            "greeting": greeting,
            "cards": [],
            "top_categories": [],
            "top_transactions": [],
            "currency_rates": currency_rates,
            "stock_prices": stock_prices,
            "total_operations_count": len(filtered),
            "top_cashback_categories": []
        }

    # --- Блок 1: Данные по картам (расходы, поступления, кешбэк) ---
    cards = []
    if "Номер карты" in filtered.columns:
        for card, group in filtered.groupby("Номер карты"):
            spending_group = group[group[amount_col] < 0]
            total_spent = spending_group[amount_col].sum()

            income_group = group[group[amount_col] > 0]
            total_income = income_group[amount_col].sum()

            cashback = abs(total_spent) * 0.01

            cards.append({
                "last_digits": str(card)[-4:] if pd.notna(card) else "Unknown",
                "total_spent": round(total_spent),
                "total_income": round(total_income),
                "cashback": round(cashback)
            })

    # --- Блок 2: Топ-5 транзакций (только траты, без переводов/пополнений) ---
    top_list = []
    spending_df = filtered[filtered[amount_col] < 0].copy()

    if not spending_df.empty:
        exclude_categories = {"Переводы", "Пополнения"}

        if "Категория" in spending_df.columns:
            spending_df["Категория_clean"] = (
                spending_df["Категория"].astype(str).str.strip().str.lower()
            )
            mask_exclude = spending_df["Категория_clean"].isin(
                [c.lower() for c in exclude_categories]
            )
            spending_filtered = spending_df[~mask_exclude]
            spending_filtered = spending_filtered[spending_filtered["Категория_clean"] != "nan"]
        else:
            spending_filtered = spending_df

        if not spending_filtered.empty:
            top_idx = spending_filtered[amount_col].abs().nlargest(5).index
            top_df = spending_filtered.loc[top_idx]

            cols_to_keep = ["Дата операции", amount_col, "Категория", "Описание"]
            cols_final = [c for c in cols_to_keep if c in top_df.columns]

            top_transactions = top_df[cols_final].copy()
            top_transactions.rename(columns={
                "Дата операции": "date",
                amount_col: "amount",
                "Категория": "category",
                "Описание": "description"
            }, inplace=True)

            top_list = top_transactions.to_dict(orient="records")

            # ВАЖНО: формат даты строго dd.mm.yyyy (без времени)
            for t in top_list:
                if isinstance(t.get("date"), pd.Timestamp):
                    t["date"] = t["date"].strftime("%d.%m.%Y")
                else:
                    t["date"] = str(t.get("date", ""))

    # --- Блок 3: Топ категорий (с выделением «Переводы» и «Наличные») ---
    top_categories = []
    rest_amount = 0.0
    special_categories = {"Переводы", "Наличные"}

    if "Категория" in filtered.columns:
        spending_df = filtered[filtered[amount_col] < 0].copy()
        if not spending_df.empty:
            spending_df["Категория_clean"] = (
                spending_df["Категория"].astype(str).str.strip()
            )
            spending_df = spending_df[spending_df["Категория_clean"] != "nan"]

            grouped = spending_df.groupby("Категория_clean")[amount_col].sum()

            # 1. Сначала добавляем «Переводы» и «Наличные» отдельными строками
            for cat in special_categories:
                if cat in grouped.index:
                    top_categories.append({
                        "category": cat,
                        "amount": round(grouped[cat])
                    })
                    grouped = grouped.drop(cat)  # Убираем, чтобы не дублировать в топе

            # 2. Топ-7 остальных категорий
            candidates = grouped
            top_7 = candidates.nlargest(7)

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

    # --- Блок 4: Топ-3 категории для кешбэка (исключая переводы/наличные/пополнения) ---
    top_cashback_categories = []
    exclude_from_cashback = {"Переводы", "Наличные", "Пополнения"}

    if "Категория" in filtered.columns:
        spending_df = filtered[filtered[amount_col] < 0].copy()
        if not spending_df.empty:
            spending_df["Категория_clean"] = (
                spending_df["Категория"].astype(str).str.strip()
            )
            spending_df = spending_df[spending_df["Категория_clean"] != "nan"]

            grouped = spending_df.groupby("Категория_clean")[amount_col].sum()

            # Исключаем категории, за которые кешбэк не начисляется
            for excl in exclude_from_cashback:
                if excl in grouped.index:
                    grouped = grouped.drop(excl)

            if not grouped.empty:
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
        "currency_rates": currency_rates,
        "stock_prices": stock_prices,
        "total_operations_count": len(filtered),
        "top_cashback_categories": top_cashback_categories,
    }

    logger.info(f"build_main_page_response: date={date_str}, processed rows={len(filtered)}")
    return response


def build_events_response(transactions: pd.DataFrame, date_str: str, range_type: str) -> Dict[str, Any]:
    """Заглушка для страницы событий (для соответствия структуре проекта)."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        dt = datetime.now()

    greeting = get_greeting(dt)
    amount_col = _find_amount_column(transactions)

    events = []
    if amount_col and not transactions.empty:
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
                e["date"] = e["date"].strftime("%d.%m.%Y")
            e["description"] = e.get("description", "")

    return {
        "greeting": greeting,
        "events": events,
        "range_type": range_type,
        "total_count": len(transactions)
    }
