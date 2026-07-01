import re
import pytest
import pandas as pd
from datetime import datetime
from src.search import normalize_phone, search_by_phone_pattern


class TestNormalizePhone:
    """Тесты для функции normalize_phone."""

    @pytest.mark.parametrize(
        "input_text,expected",
        [
            ("+7 (900) 123-45-67", "79001234567"),
            ("89001234567", "79001234567"),  # 8 -> 7
            ("79001234567", "79001234567"),  # уже 7
            ("9001234567", "9001234567"),  # не 11 цифр — не меняем
            ("+7900123456", "7900123456"),  # 10 цифр — не меняем (нет 8/7 в начале)
            ("abc123xyz", "123"),  # только цифры
            ("", ""),
            (None, ""),  # защита от None
            ("  +7 999 000 00 00  ", "79990000000"),  # пробелы
            ("8 (999) 000-00-00", "79990000000"),  # скобки и тире
        ],
    )
    def test_normalize_phone_various_formats(self, input_text, expected):
        assert normalize_phone(input_text) == expected

    def test_normalize_phone_non_string_input(self):
        # Функция должна корректно обрабатывать не-строки (через str())
        assert normalize_phone(12345) == "12345"
        assert normalize_phone(79001234567) == "79001234567"


class TestSearchByPhonePattern:
    """Тесты для функции search_by_phone_pattern."""

    @pytest.fixture
    def sample_df(self):
        """Базовый набор транзакций (неизменяемый)."""
        data = {
            "Дата операции": [
                datetime(2026, 6, 29, 10, 0),
                datetime(2026, 6, 30, 12, 30),
                datetime(2026, 7, 1, 9, 15),
                datetime(2026, 7, 2, 18, 45),
            ],
            "Сумма операции": [-1500.0, -300.0, 5000.0, -800.0],
            "Категория": ["Продукты", "Такси", "Перевод", "Продукты"],
            "Описание": [
                "Перевод на +7 (900) 123-45-67",
                "Оплата такси 89009876543",
                "Возврат от 79001112233",
                "Покупка без номера",
            ],
        }
        return pd.DataFrame(data)

    @pytest.fixture
    def df_with_multiple_same_phone(self, sample_df):
        """Набор с двумя транзакциями по одному номеру (для теста множественных совпадений)."""
        extra_row = {
            "Дата операции": datetime(2026, 7, 3, 11, 20),
            "Сумма операции": -200.0,
            "Категория": "Связь",
            "Описание": "Платёж на 79001234567 повторно",
        }
        extended_df = pd.concat([sample_df, pd.DataFrame([extra_row])], ignore_index=True)
        return extended_df

    @pytest.fixture
    def df_with_noisy_description(self, sample_df):
        """Версия с «грязным» описанием, но тем же номером."""
        sample_df = sample_df.copy()
        sample_df.loc[0, "Описание"] = "Перевод на телефон: +7(900)-123--45--67!!!"
        return sample_df

    def test_search_exact_match_plus_format(self, sample_df):
        result = search_by_phone_pattern(sample_df, "+7 (900) 123-45-67")
        assert len(result) == 1
        assert result[0]["category"] == "Продукты"
        assert result[0]["amount"] == -1500.0
        assert "123-45-67" in result[0]["description"]

    def test_search_with_8_prefix(self, sample_df):
        result = search_by_phone_pattern(sample_df, "89009876543")
        assert len(result) == 1
        assert result[0]["category"] == "Такси"
        assert result[0]["amount"] == -300.0

    def test_search_partial_match_in_description(self, sample_df):
        # Ищем по части номера: 900123 (входит в 79001234567)
        result = search_by_phone_pattern(sample_df, "900123")
        # Должен найти первую транзакцию, потому что нормализованный номер содержит подстроку
        assert len(result) == 1
        assert result[0]["category"] == "Продукты"

    def test_search_no_matches(self, sample_df):
        result = search_by_phone_pattern(sample_df, "79990000000")
        assert len(result) == 0

    def test_search_empty_dataframe(self):
        df = pd.DataFrame()
        result = search_by_phone_pattern(df, "79001234567")
        assert len(result) == 0

    def test_search_invalid_query_empty(self, sample_df):
        result = search_by_phone_pattern(sample_df, "")
        assert len(result) == 0

        result = search_by_phone_pattern(sample_df, None)
        assert len(result) == 0

    def test_search_returns_correct_columns(self, sample_df):
        result = search_by_phone_pattern(sample_df, "79001234567")
        if result:
            row = result[0]
            assert "date" in row
            assert "amount" in row
            assert "category" in row
            assert "description" in row

    def test_search_date_format_is_string(self, sample_df):
        result = search_by_phone_pattern(sample_df, "79001234567")
        if result:
            assert isinstance(result[0]["date"], str)
            # Проверяем, что формат примерно такой: ДД.ММ.ГГГГ ЧЧ:ММ
            assert re.match(r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}", result[0]["date"])

    def test_search_multiple_matches(self, df_with_multiple_same_phone):
        result = search_by_phone_pattern(df_with_multiple_same_phone, "79001234567")
        assert len(result) == 2
        categories = [r["category"] for r in result]
        assert "Продукты" in categories
        assert "Связь" in categories

    def test_search_with_noisy_description(self, df_with_noisy_description):
        # Описание с лишним шумом, но тот же номер
        result = search_by_phone_pattern(df_with_noisy_description, "79001234567")
        assert len(result) >= 1
        # Проверяем, что найденная транзакция — это именно первая строка
        assert result[0]["category"] == "Продукты"
