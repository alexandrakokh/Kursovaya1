from unittest.mock import patch
import pandas as pd
from src import main


@patch("src.main.load_transactions")
@patch("src.main.get_cbr_rates_json")
@patch("src.main.build_main_page_response")
def test_main_happy_path(mock_build, mock_rates, mock_load):
    # Подготавливаем данные
    mock_df = pd.DataFrame({
        "Номер карты": ["1112", "4556", "5091"],
        "Дата операции": pd.to_datetime(["2026-06-30 10:00", "2026-06-30 11:00", "2026-06-30 12:00"]),
        "Сумма операции": [-100, -200, 300],
        "Категория": ["Еда", "Такси", "Доход"],
        "Описание": ["Молоко", "Поездка", "Перевод"]
    })
    mock_load.return_value = mock_df
    mock_rates.return_value = {"Valute": {"USD": {"Value": 90.0}, "EUR": {"Value": 98.0}}}

    # Любой валидный ответ, главное — чтобы функция была вызвана
    mock_build.return_value = {"greeting": "Добрый день"}

    main.main()

    mock_load.assert_called_once()
    mock_rates.assert_called_once()
    mock_build.assert_called_once()


@patch("pathlib.Path.exists", return_value=False)
@patch("src.main.get_cbr_rates_json")
@patch("src.main.build_main_page_response")
def test_main_no_data_file(mock_build, mock_rates, mock_exists):
    mock_rates.return_value = {"Valute": {"USD": {"Value": 90.0}}}
    mock_build.return_value = {"greeting": "Добрый день"}

    main.main()

    # Файл не существует -> блок try/except в main создаст пустой DataFrame,
    # но функции всё равно должны быть вызваны
    assert mock_rates.called
    assert mock_build.called


@patch("pathlib.Path.exists", return_value=True)
@patch("src.main.load_transactions", side_effect=ValueError("Битый Excel"))
@patch("src.main.get_cbr_rates_json")
@patch("src.main.build_main_page_response")
def test_main_excel_read_error(mock_build, mock_rates, mock_load, mock_exists):
    mock_rates.return_value = {"Valute": {"USD": {"Value": 90.0}}}
    mock_build.return_value = {"greeting": "Добрый день"}

    main.main()

    # load_transactions должен быть вызван ровно один раз (и выбросить ошибку)
    mock_load.assert_called_once()
    assert mock_rates.called
    assert mock_build.called


@patch("pathlib.Path.exists", return_value=True)
@patch("src.main.load_transactions", return_value=pd.DataFrame())
@patch("src.main.get_cbr_rates_json", return_value=None)
@patch("src.main.build_main_page_response")
def test_main_cbr_fallback(mock_build, mock_rates, mock_load, mock_exists):
    mock_build.return_value = {"greeting": "Добрый день"}

    main.main()

    mock_load.assert_called_once()
    mock_rates.assert_called_once()
    assert mock_build.called
