import re
from typing import List, Dict, Any
import pandas as pd

PHONE_DIGITS_ONLY = re.compile(r"\D")  # всё, что не цифра — удаляем


def normalize_phone(text: str) -> str:
    """Оставляет только цифры. Для 11-значных номеров с 7/8 делает формат 7xxxxxxxxxx."""
    digits = PHONE_DIGITS_ONLY.sub("", str(text))
    if len(digits) == 11 and digits.startswith(("7", "8")):
        return "7" + digits[1:]
    return digits


def search_by_phone_pattern(df: pd.DataFrame, phone_query: str) -> List[Dict[str, Any]]:
    """
    Ищет транзакции, где в описании встречается номер телефона.
    Поддерживает форматы: +7 (900) 000-00-00, 89000000000 и т.п.
    """
    norm_query = normalize_phone(phone_query)
    if not norm_query:
        return []

    def row_matches(row: pd.Series) -> bool:
        desc = str(row.get("Описание", ""))
        norm_desc = normalize_phone(desc)
        # Ищем подстроку нормализованного номера в нормализованном описании
        return norm_query in norm_desc

    matches = df[df.apply(row_matches, axis=1)]

    if matches.empty:
        return []

    out = matches[["Дата операции", "Сумма операции", "Категория", "Описание"]].copy()
    out.rename(
        columns={
            "Дата операции": "date",
            "Сумма операции": "amount",
            "Категория": "category",
            "Описание": "description",
        },
        inplace=True,
    )

    def fmt_date(x):
        if isinstance(x, pd.Timestamp):
            return x.strftime("%d.%m.%Y %H:%M")
        return str(x)

    out["date"] = out["date"].apply(fmt_date)
    return out.to_dict(orient="records")
