import pandas as pd
from datetime import datetime
from src.views import get_greeting, build_main_page_response, build_events_response

def test_get_greeting_morning():
    dt = datetime(2024, 5, 20, 8, 30)
    assert get_greeting(dt) == "Доброе утро"

def test_get_greeting_evening():
    dt = datetime(2024, 5, 20, 19, 0)
    assert get_greeting(dt) == "Добрый вечер"

def test_build_main_page_response():
    data = {
        "Дата операции": [
            datetime(2024, 5, 1, 10, 0),
            datetime(2024, 5, 20, 14, 30),
        ],
        "Номер карты": ["1234567890123456", "1234567890123457"],
        "Сумма операции": [1000.0, 250.0],
        "Сумма платежа": [1000.0, 250.0],
        "Категория": ["Супермаркеты", "Фастфуд"],
        "Описание": ["Лента", "KFC"],
    }
    df = pd.DataFrame(data)
    currency_rates = [{"currency": "USD", "rate": 90.0}]
    stock_prices = [{"stock": "AAPL", "price": 180.0}]

    resp = build_main_page_response(df, "2024-05-20 14:30:00", currency_rates, stock_prices)

    assert resp["greeting"] == "Добрый день"
    assert len(resp["cards"]) == 2
    assert resp["cards"][0]["cashback"] == 10.0

def test_build_events_response_expenses():
    data = {
        "Дата операции": [
            datetime(2024, 5, 1, 10, 0),
            datetime(2024, 5, 2, 12, 0),
            datetime(2024, 5, 3, 15, 0),
        ],
        "Сумма операции": [-1000.0, -250.0, 500.0],  # траты отрицательные
        "Категория": ["Супермаркеты", "Наличные", "Пополнение"],
        "Описание": ["", "", ""],
    }
    df = pd.DataFrame(data)

    resp = build_events_response(df, "2024-05-31 12:00:00", "M")

    assert resp["expenses"]["total_amount"] == 1250
    assert resp["income"]["total_amount"] == 500