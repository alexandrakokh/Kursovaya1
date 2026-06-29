import pandas as pd
from datetime import datetime
from src.utils import load_transactions

def test_load_transactions_returns_dataframe(tmp_path):
    file = tmp_path / "test.xlsx"
    data = {
        "Дата операции": [datetime(2024, 5, 1), datetime(2024, 5, 2)],
        "Номер карты": ["1234", "5678"],
        "Сумма операции": [100.0, 200.0],
        "Сумма платежа": [100.0, 200.0],
        "Категория": ["Супермаркеты", "Фастфуд"],
        "Описание": ["Покупка", "Еда"],
    }
    df_in = pd.DataFrame(data)
    df_in.to_excel(file, index=False)

    result = load_transactions(str(file))
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
    assert "Дата операции" in result.columns
    assert pd.api.types.is_datetime64_any_dtype(result["Дата операции"])
