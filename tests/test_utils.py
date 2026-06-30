import pandas as pd
from pathlib import Path
import tempfile
from unittest.mock import patch, MagicMock
from src.utils import load_transactions


class TestLoadTransactions:
    """Тесты для функции load_transactions из utils.py"""

    @patch("src.utils.pd.read_excel")
    def test_file_not_found(self, mock_read_excel):
        """Тест: файл не существует -> пустой DataFrame"""
        # Подменяем поведение: если файл не найден, выбрасываем ошибку
        mock_read_excel.side_effect = FileNotFoundError("No such file")

        result = load_transactions("non_existent_file.xlsx")

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    @patch("src.utils.pd.read_excel")
    def test_empty_dataframe(self, mock_read_excel):
        """Тест: файл найден, но пустой -> предупреждение и пустой DF"""
        mock_read_excel.return_value = pd.DataFrame()

        result = load_transactions()

        assert result.empty
        # Здесь можно проверить логи, если настроишь caplog, но пока просто проверяем результат

    @patch("src.utils.pd.read_excel")
    def test_missing_date_column(self, mock_read_excel):
        """Тест: нет колонки 'Дата операции' -> пустой DF"""
        df = pd.DataFrame({"Сумма операции": [100, 200]})
        mock_read_excel.return_value = df

        result = load_transactions()

        assert result.empty

    @patch("src.utils.pd.read_excel")
    def test_dates_strict_format(self, mock_read_excel):
        """Тест: даты в формате ДД.ММ.ГГГГ ЧЧ:ММ:СС парсятся верно"""
        data = {
            "Дата операции": ["31.12.2021 16:44:00", "01.01.2022 09:00:00"],
            "Сумма операции": [100.5, 200.0],
            "Категория": ["Продукты", "Такси"],
            "Номер карты": ["1234", "5678"]
        }
        df_input = pd.DataFrame(data)
        mock_read_excel.return_value = df_input

        result = load_transactions()

        assert not result.empty
        assert len(result) == 2
        assert pd.api.types.is_datetime64_any_dtype(result["Дата операции"])
        assert result["Дата операции"].iloc[0].year == 2021

    @patch("src.utils.pd.read_excel")
    def test_dates_strict_and_cleanup(self, mock_read_excel, caplog):
        """
        Тест: проверяем, что строгий формат работает, а мусорные строки удаляются.
        Это честный тест под текущую логику парсинга.
        """
        data = {
            "Дата операции": [
                "31.12.2021 16:44:00",  # Хороший строгий формат
                "01.01.2022 09:00:00",  # Ещё один хороший строгий формат
                "НЕ ДАТА"  # Мусор — должен удалиться
            ],
            "Сумма операции": [100, 200, 300],
            "Категория": ["A", "B", "C"],
            "Номер карты": ["1", "2", "3"]
        }
        df_input = pd.DataFrame(data)
        mock_read_excel.return_value = df_input

        with caplog.at_level("WARNING"):
            result = load_transactions()

        assert not result.empty
        # Ожидаем ровно 2 строки (обе хорошие), мусор удалён
        assert len(result) == 2, f"Ожидалось 2 строки, а получилось {len(result)}"

        # Проверяем, что было предупреждение об удалении мусора
        assert any("Удалено" in msg or "Удалена" in msg for msg in caplog.messages)

    @patch("src.utils.pd.read_excel")
    def test_amount_non_numeric(self, mock_read_excel):
        """Тест: сумма не число -> превращается в 0"""
        data = {
            "Дата операции": ["01.01.2022 10:00:00"] * 3,
            "Сумма операции": [100, "abc", None],
            "Категория": ["X", "Y", "Z"],
            "Номер карты": ["1", "2", "3"]
        }
        df_input = pd.DataFrame(data)
        mock_read_excel.return_value = df_input

        result = load_transactions()

        assert not result.empty
        # Проверяем, что нечисловые значения стали 0
        assert result["Сумма операции"].iloc[1] == 0
        assert result["Сумма операции"].iloc[2] == 0

    @patch("src.utils.pd.read_excel")
    def test_category_strip_spaces(self, mock_read_excel):
        """Тест: категории с пробелами -> пробелы убраны"""
        data = {
            "Дата операции": ["01.01.2022 10:00:00"] * 3,
            "Сумма операции": [10, 20, 30],
            "Категория": [" Продукты ", "Такси  ", "  Переводы"],
            "Номер карты": ["1", "2", "3"]
        }
        df_input = pd.DataFrame(data)
        mock_read_excel.return_value = df_input

        result = load_transactions()

        categories = result["Категория"].tolist()
        assert categories == ["Продукты", "Такси", "Переводы"]

    @patch("src.utils.pd.read_excel")
    def test_missing_required_columns(self, mock_read_excel):
        """Тест: отсутствует 'Номер карты' -> ошибка и пустой DF"""
        data = {
            "Дата операции": ["01.01.2022 10:00:00"],
            "Сумма операции": [100],
            "Категория": ["Еда"]
            # Нет колонки Номер карты
        }
        df_input = pd.DataFrame(data)
        mock_read_excel.return_value = df_input

        result = load_transactions()

        assert result.empty

    def test_real_file_creation_and_loading(self):
        """
        Тест: создаём реальный временный Excel-файл, читаем его.
        Это полезно, чтобы проверить, что функция реально работает с файлом.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test_ops.xlsx"

            # Создаём тестовые данные
            data = {
                "Дата операции": ["31.12.2021 16:44:00"],
                "Сумма операции": [999.99],
                "Категория": ["Супермаркет"],
                "Номер карты": ["9876"]
            }
            df_to_save = pd.DataFrame(data)
            df_to_save.to_excel(file_path, index=False)

            # Вызываем функцию с явным путём
            result = load_transactions(str(file_path))

            assert not result.empty
            assert result.iloc[0]["Сумма операции"] == 999.99
            assert result.iloc[0]["Категория"] == "Супермаркет"