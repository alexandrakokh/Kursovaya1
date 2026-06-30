import pytest
from src.services import (
    investment_bank,
    analyze_cashback_categories,
    search_transactions,
    find_phone_numbers,
    find_person_transfers,
)
from datetime import datetime


class TestInvestmentBank:
    @pytest.fixture
    def transactions(self):
        return [
            {"Дата операции": "2026-01-05", "Сумма операции": 123.45},
            {"Дата операции": "2026-01-10", "Сумма операции": 78.90},
            {"Дата операции": "2026-02-03", "Сумма операции": 200.00},
        ]

    def test_investment_bank_basic_rounding_limit_10(self, transactions):
        result = investment_bank("2026-01", transactions, 10)
        assert result == pytest.approx(7.65)

    def test_investment_bank_limit_50(self, transactions):
        result = investment_bank("2026-01", transactions, 50)
        # 123.45 -> 150 (diff 26.55), 78.90 -> 100 (diff 21.10) = 47.65
        assert result == 47.65

    def test_investment_bank_limit_100(self, transactions):
        result = investment_bank("2026-01", transactions, 100)
        # 123.45 -> 200 (diff 76.55), 78.90 -> 100 (diff 21.10) = 97.65
        assert result == 97.65

    def test_investment_bank_no_matching_month(self, transactions):
        result = investment_bank("2026-12", transactions, 10)
        assert result == 0.0

    def test_investment_bank_empty_list(self):
        result = investment_bank("2026-01", [], 10)
        assert result == 0.0

    def test_investment_bank_only_negative_amounts(self):
        transactions = [
            {"Дата операции": "2026-01-01", "Сумма операции": -100},
            {"Дата операции": "2026-01-02", "Сумма операции": -50},
        ]
        result = investment_bank("2026-01", transactions, 10)
        assert result == 0.0


class TestAnalyzeCashbackCategories:
    @pytest.fixture
    def transactions(self):
        return [
            {"Дата операции": "2026-05-10", "Категория": "Продукты", "Сумма операции": 1000},
            {"Дата операции": "2026-05-15", "Категория": "Такси", "Сумма операции": 500},
            {"Дата операции": "2026-06-01", "Категория": "Продукты", "Сумма операции": 800},
        ]

    def test_analyze_cashback_basic(self, transactions):
        result = analyze_cashback_categories(transactions, 2026, 5)
        assert "Продукты" in result
        assert "Такси" in result
        # cashback 1%
        assert result["Продукты"] == 10.0
        assert result["Такси"] == 5.0

    def test_analyze_cashback_empty_list(self):
        result = analyze_cashback_categories([], 2026, 5)
        assert result == {}

    def test_analyze_cashback_no_matches(self, transactions):
        result = analyze_cashback_categories(transactions, 2026, 12)
        assert result == {}


class TestSearchTransactions:
    @pytest.fixture
    def transactions(self):
        return [
            {"Категория": "Продукты", "Описание": "Покупка в Пятерочке"},
            {"Категория": "Такси", "Описание": "Поездка до дома"},
            {"Категория": "Переводы", "Описание": "Перевод Ивану И."},
            {"Категория": "Продукты", "Описание": ""},
        ]

    def test_search_by_category(self, transactions):
        result = search_transactions(transactions, "продукты")
        assert len(result) >= 2
        assert all(t["Категория"].lower() == "продукты" for t in result)

    def test_search_by_description(self, transactions):
        print("=== test_search_by_description ЗАПУЩЕН ===")
        for i, t in enumerate(transactions):
            print(i, "desc:", repr(t.get("Описание")))
        print("query:", repr("пятёрочка"))

        result = search_transactions(transactions, "пятерочке")
        print("result count:", len(result), result)
        assert len(result) >= 1, f"Ничего не найдено по запросу 'пятёрочка', результат={result}"

    def test_search_no_match(self, transactions):
        result = search_transactions(transactions, "абсолютно несуществующее слово")
        assert len(result) == 0

    def test_search_empty_query(self, transactions):
        result = search_transactions(transactions, "")
        # пустая строка должна находить всё (т.к. "" in любой строке)
        assert len(result) == len(transactions)

    def test_search_case_insensitive(self, transactions):
        result = search_transactions(transactions, "ПЯТЁРОЧКЕ")
        assert len(result) >= 1


class TestFindPhoneNumbers:
    @pytest.fixture
    def transactions(self):
        return [
            {"Категория": "Разное", "Описание": "Звонок +79991234567"},
            {"Категория": "Другое", "Описание": "Номер 8 (999) 123-45-67"},
            {"Категория": "Прочее", "Описание": "Без номера тут ничего нет"},
        ]

    def test_find_phone_numbers_all_formats(self, transactions):
        result = find_phone_numbers(transactions)
        assert len(result) == 2

    def test_find_phone_numbers_none(self):
        transactions = [{"Категория": "Прочее", "Описание": "Тут вообще нет телефонов"}]
        result = find_phone_numbers(transactions)
        assert len(result) == 0


class TestFindPersonTransfers:
    @pytest.fixture
    def transactions(self):
        return [
            {"Категория": "Переводы", "Описание": "Перевод Ивану И."},
            {"Категория": "Переводы", "Описание": "Перевод Марии С."},
            {"Категория": "Продукты", "Описание": "Перевод Сергею К."},  # не переводы — не должно попасть
            {"Категория": "Переводы", "Описание": "Перевод без инициалов"},
            {"Категория": "Переводы", "Описание": "Перевод ООО Ромашка"},
        ]

    def test_find_person_transfers_matches(self, transactions):
        print("=== test_find_person_transfers_matches ЗАПУЩЕН ===")
        for i, t in enumerate(transactions):
            print(i, t.get("Категория"), repr(t.get("Описание")))

        result = find_person_transfers(transactions)
        print("found count:", len(result), result)

        assert len(result) == 2, f"Ожидается 2 перевода физлицам, а найдено {len(result)}"

        descs = [t["Описание"] for t in result]
        assert "Перевод Ивану И." in descs, "Не найден перевод Ивану И."
        assert "Перевод Марии С." in descs, "Не найден перевод Марии С."

    def test_find_person_transfers_wrong_category(self, transactions):
        # В фикстуре есть «Перевод Сергею К.» с категорией Продукты — он не должен попасть
        result = find_person_transfers(transactions)
        assert not any("Сергею К." in t["Описание"] for t in result if t["Категория"] != "Переводы")

    def test_find_person_transfers_no_matches(self):
        transactions = [
            {"Категория": "Переводы", "Описание": "Перевод без инициалов"},
            {"Категория": "Переводы", "Описание": "Перевод ООО Ромашка"},
        ]
        result = find_person_transfers(transactions)
        assert len(result) == 0
