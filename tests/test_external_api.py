from unittest.mock import patch
from src.external_api import fetch_currency_rates, fetch_stock_prices


class TestFetchCurrencyRates:
    """Тесты для курсов валют."""

    def test_returns_defaults_when_exception_raised(self):
        """
        Проверяем, что при ошибке (Exception) функция возвращает дефолтные значения.
        Так как внутри функции просто raise Exception, мок нужен только для того,
        чтобы убедиться, что логика не падает, а перехватывает ошибку.
        Но в данном коде мы можем просто вызвать функцию и проверить результат.
        """
        result = fetch_currency_rates()

        assert isinstance(result, list)
        assert len(result) == 2

        # Ищем USD и EUR в списке
        usd = next((item for item in result if item["currency"] == "USD"), None)
        eur = next((item for item in result if item["currency"] == "EUR"), None)

        assert usd is not None
        assert eur is not None
        assert usd["rate"] == 90.0
        assert eur["rate"] == 98.0

    @patch("src.external_api.logger")
    def test_logs_warning_on_error(self, mock_logger):
        """Проверяем, что при ошибке пишется предупреждение в лог."""
        fetch_currency_rates()

        # Проверяем, что logger.warning был вызван хотя бы один раз
        assert mock_logger.warning.called is True
        # Можно проверить, что в сообщении есть слово "API"
        call_args = mock_logger.warning.call_args[0][0]  # Текст сообщения
        assert "API курсов валют недоступно" in call_args


class TestFetchStockPrices:
    """Тесты для акций."""

    def test_returns_defaults_when_exception_raised(self):
        """Проверяем возврат дефолтных акций при ошибке."""
        result = fetch_stock_prices()

        assert isinstance(result, list)
        assert len(result) == 5

        stocks = {item["stock"]: item["price"] for item in result}

        assert stocks["AAPL"] == 180.0
        assert stocks["AMZN"] == 3200.0
        assert stocks["TSLA"] == 250.0

    @patch("src.external_api.logger")
    def test_logs_warning_on_stock_error(self, mock_logger):
        """Проверяем лог для акций."""
        fetch_stock_prices()

        assert mock_logger.warning.called is True
        call_args = mock_logger.warning.call_args[0][0]
        assert "API акций недоступно" in call_args
