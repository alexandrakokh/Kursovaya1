import pandas as pd
from datetime import datetime
from src.reports import spending_by_category

def test_spending_by_category_returns_dataframe():
    data = {
        "Дата операции": [
            datetime(2024, 4, 1),
            datetime(2024, 5, 1),
        ],
        "Сумма операции": [-100, -200],
        "Категория": ["Супермаркеты", "Супермаркеты"],
        "Описание": ["", ""],
    }
    df = pd.DataFrame(data)
    res = spending_by_category(df, "Супермаркеты", "2024-06-01")
    assert isinstance(res, pd.DataFrame)