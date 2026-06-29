from datetime import datetime
from src.services import investment_bank, analyze_cashback_categories, find_phone_numbers, find_person_transfers

def test_investment_bank():
    transactions = [
        {"Дата операции": "2024-05-01", "Сумма операции": 110},
        {"Дата операции": "2024-05-10", "Сумма операции": 240},
    ]
    total = investment_bank("2024-05", transactions, 100)
    # 110 -> 200 (diff 90), 240 -> 300 (diff 60) => 150
    assert total == 150.0

def test_analyze_cashback_categories():
    transactions = [
        {"Дата операции": datetime(2024, 5, 1), "Категория": "Супермаркеты", "Сумма операции": 5000},
        {"Дата операции": datetime(2024, 5, 2), "Категория": "Фастфуд", "Сумма операции": 3000},
    ]
    res = analyze_cashback_categories(transactions, 2024, 5)
    assert res["Супермаркеты"] == 50.0
    assert res["Фастфуд"] == 30.0
