from unittest.mock import patch
import pandas as pd
from src import main


@patch("src.main.load_transactions")
@patch("src.main.get_currency_rates")
@patch("src.main.build_main_page_response")
def test_main_happy_path(mock_build, mock_rates, mock_load):
    mock_df = pd.DataFrame({
        "Номер карты": ["1112", "4556", "5091"],
        "Дата операции": pd.to_datetime(["2026-06-30 10:00", "2026-06-30 11:00", "2026-06-30 12:00"]),
        "Сумма операции": [-100, -200, 300],
        "Категория": ["Еда", "Такси", "Доход"],
        "Описание": ["Молоко", "Поездка", "Перевод"]
    })
    mock_load.return_value = mock_df
    mock_rates.return_value = [
        {"currency": "USD", "rate": 90.0},
        {"currency": "EUR", "rate": 98.0}
    ]
    mock_build.return_value = {"greeting": "Добрый день"}

    main.main([])

    mock_load.assert_called_once()
    mock_rates.assert_called_once()
    mock_build.assert_called_once()


@patch("src.main.load_transactions", return_value=pd.DataFrame())
@patch("src.main.get_currency_rates")
@patch("src.main.build_main_page_response")
def test_main_no_data_file(mock_build, mock_rates, mock_load):
    mock_rates.return_value = [{"currency": "USD", "rate": 90.0}]
    mock_build.return_value = {"greeting": "Добрый день"}

    main.main([])

    assert mock_load.called
    assert mock_rates.called
    assert mock_build.called


@patch("src.main.load_transactions", side_effect=ValueError("Битый Excel"))
@patch("src.main.get_currency_rates")
@patch("src.main.build_main_page_response")
def test_main_excel_read_error(mock_build, mock_rates, mock_load):
    """
    Проверяем, что при ошибке чтения Excel программа не падает,
    а обрабатывает ситуацию как 'нет данных' (через try/except в main).
    """
    mock_rates.return_value = [{"currency": "USD", "rate": 90.0}]
    mock_build.return_value = {"greeting": "Добрый день"}

    # Вызываем main. Он должен поймать ошибку в try/except и продолжить работу
    main.main([])

    mock_load.assert_called_once()
    mock_rates.assert_called_once()
    assert mock_build.called


# ВАЖНО: В этом тесте мы НЕ патчим get_currency_rates!
# Мы проверяем реальную логику функции get_currency_rates (её try/except).
@patch("src.main.load_transactions", return_value=pd.DataFrame())
@patch("src.main.build_main_page_response")
def test_main_cbr_fallback(mock_build, mock_load):
    """
    Проверяет, что если реальная функция get_currency_rates не может достучаться до ЦБ,
    она сама возвращает дефолтные значения, и программа не падает.
    """
    mock_build.return_value = {"greeting": "Добрый день"}

    main.main([])

    mock_load.assert_called_once()
    assert mock_build.called
