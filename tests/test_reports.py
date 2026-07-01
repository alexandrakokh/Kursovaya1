import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import patch
from src.reports import (
    _get_spending_df,
    spending_by_category,
    spending_by_weekday,
    spending_by_workday,
)


@pytest.fixture
def sample_df():
    """
    Фикстура: DataFrame с разными типами операций (траты, доходы, переводы).
    Это важно, чтобы проверить, что _get_spending_df правильно отсекает не-траты.
    """
    data = {
        "Дата операции": [
            datetime(2026, 6, 29, 10, 0),  # пн
            datetime(2026, 6, 30, 12, 0),  # вт
            datetime(2026, 7, 3, 14, 0),  # пт
            datetime(2026, 7, 4, 9, 0),  # сб
            datetime(2026, 7, 5, 11, 0),  # вс
            datetime(2026, 7, 6, 8, 0),  # пн
        ],
        "Категория": [
            "Продукты",
            "Такси",
            "Продукты",
            "Развлечения",
            "Развлечения",
            "Продукты",
        ],
        "Сумма операции": [
            -1500.0,  # трата
            -300.0,  # трата
            -2000.0,  # трата
            -800.0,  # трата (выходные)
            -500.0,  # трата (выходные)
            10000.0,  # доход (не должен попасть в траты!)
        ],
    }
    return pd.DataFrame(data)


class TestGetSpendingDF:
    """Тесты для вспомогательной функции _get_spending_df."""

    def test_filters_only_negative_amounts(self, sample_df):
        result = _get_spending_df(sample_df)
        # В sample_df одна строка с доходом 10000, её не должно быть в результате
        assert len(result) == 5
        assert (result["Сумма операции"] < 0).all()

    def test_returns_empty_if_no_spending(self):
        df = pd.DataFrame({"Сумма операции": [100, 200, 300]})
        result = _get_spending_df(df)
        assert result.empty

    def test_fallback_column_name(self):
        # Проверяем, что сработает фолбэк на "Сумма платежа"
        df = pd.DataFrame({"Сумма платежа": [-100, -200], "Категория": ["A", "B"]})
        result = _get_spending_df(df)
        assert not result.empty
        assert len(result) == 2

    def test_missing_amount_column_returns_empty(self):
        df = pd.DataFrame({"Категория": ["A"]})
        result = _get_spending_df(df)
        assert result.empty


class TestSpendingByCategory:
    """Тесты для spending_by_category."""

    @patch("src.reports._save_report")
    def test_correct_total_for_category(self, mock_save):
        df = pd.DataFrame(
            {
                "Дата операции": [datetime(2026, 6, 29)] * 3,
                "Категория": ["Продукты", "Продукты", "Такси"],
                "Сумма операции": [-500, -300, -100],
            }
        )

        result = spending_by_category(df, "Продукты")

        assert result["category"] == "Продукты"
        assert result["total_amount"] == -800.0
        assert result["rows"] == 2
        # _save_report был вызван ровно 1 раз
        assert mock_save.call_count == 1

    @patch("src.reports._save_report")
    def test_category_not_found_returns_zero(self, mock_save):
        df = pd.DataFrame({"Дата операции": [datetime(2026, 6, 29)], "Категория": ["Такси"], "Сумма операции": [-100]})

        result = spending_by_category(df, "Продукты")

        assert result["category"] == "Продукты"
        assert result["total_amount"] == 0.0
        assert result["rows"] == 0

    @patch("src.reports._save_report")
    def test_whitespace_and_case_normalization(self, mock_save):
        """Проверяем, что нормализация категорий работает."""
        df = pd.DataFrame(
            {
                "Дата операции": [datetime(2026, 6, 29)],
                "Категория": ["  продукты  "],  # с пробелами
                "Сумма операции": [-200],
            }
        )

        result = spending_by_category(df, "продукты")

        assert result["total_amount"] == -200.0


class TestSpendingByWeekday:
    """Тесты для spending_by_weekday (по дням недели)."""

    @patch("src.reports._save_report")
    def test_weekday_distribution(self, mock_save):
        # Создадим данные: траты в пн, вт, сб, вс
        df = pd.DataFrame(
            {
                "Дата операции": [
                    datetime(2026, 6, 29),  # пн (0)
                    datetime(2026, 6, 30),  # вт (1)
                    datetime(2026, 7, 4),  # сб (5)
                    datetime(2026, 7, 5),  # вс (6)
                ],
                "Категория": ["A", "A", "B", "B"],
                "Сумма операции": [-100, -200, -50, -70],
            }
        )

        result = spending_by_weekday(df)

        # Формат результата: ключи — строки "0".."6"
        assert isinstance(result, dict)
        assert "0" in result and result["0"] == -100.0
        assert "1" in result and result["1"] == -200.0
        assert "5" in result and result["5"] == -50.0
        assert "6" in result and result["6"] == -70.0
        # Остальные дни должны быть 0.0
        for i in [2, 3, 4]:
            assert str(i) in result and result[str(i)] == 0.0

        assert mock_save.call_count == 1

    @patch("src.reports._save_report")
    def test_empty_dataframe_returns_zeros(self, mock_save):
        df = pd.DataFrame()
        result = spending_by_weekday(df)

        for i in range(7):
            assert result[str(i)] == 0.0


class TestSpendingByWorkday:
    """Тесты для spending_by_workday (будни vs выходные)."""

    @patch("src.reports._save_report")
    def test_work_vs_weekend_split(self, mock_save):
        # Траты: пн, пт, сб, вс
        df = pd.DataFrame(
            {
                "Дата операции": [
                    datetime(2026, 6, 29),  # пн (будний)
                    datetime(2026, 7, 3),  # пт (будний)
                    datetime(2026, 7, 4),  # сб (выходной)
                    datetime(2026, 7, 5),  # вс (выходной)
                ],
                "Категория": ["A", "A", "B", "B"],
                "Сумма операции": [-100, -400, -50, -60],
            }
        )

        result = spending_by_workday(df)

        assert abs(result["work"] - (-500.0)) < 1e-9  # -100 -400
        assert abs(result["weekend"] - (-110.0)) < 1e-9  # -50 -60
        assert mock_save.call_count == 1

    @patch("src.reports._save_report")
    def test_empty_dataframe_returns_zeros_workday(self, mock_save):
        df = pd.DataFrame()
        result = spending_by_workday(df)

        assert result["work"] == 0.0
        assert result["weekend"] == 0.0
