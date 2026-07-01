from unittest.mock import patch, MagicMock
from src.cbr_client import get_cbr_rates_json, build_currency_rates


class TestGetCbrRatesJson:
    """Тесты для функции, которая делает HTTP-запрос (изолируем сеть через patch)."""

    @patch("src.cbr_client.requests.get")
    def test_success_response(self, mock_get):
        # 1. Настраиваем мок: успешный ответ
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None  # Ошибок нет
        mock_response.json.return_value = {"Valute": {"R01235": {"Value": 90.5}}}
        mock_get.return_value = mock_response

        # 2. Вызываем функцию
        result = get_cbr_rates_json()

        # 3. Проверяем результат
        assert result is not None
        assert "Valute" in result

        mock_get.assert_called_once_with("https://www.cbr-xml-daily.ru/daily_json.js", timeout=10)

    @patch("src.cbr_client.requests.get")
    def test_network_error_returns_none(self, mock_get):
        # 1. Настраиваем мок: выбрасываем ошибку сети
        from requests.exceptions import RequestException

        mock_get.side_effect = RequestException("Connection failed")

        # 2. Вызываем
        result = get_cbr_rates_json()

        # 3. Проверяем, что вернули None, а не упали с ошибкой
        assert result is None


class TestBuildCurrencyRates:

    def test_all_currencies_found(self):
        data = {
            "Valute": {
                "USD": {"Value": 91.0},
                "EUR": {"Value": 99.5},
            }
        }
        result = build_currency_rates(data)

        assert len(result) == 2
        usd_rate = next((r["rate"] for r in result if r["currency"] == "USD"), None)
        eur_rate = next((r["rate"] for r in result if r["currency"] == "EUR"), None)

        assert usd_rate == 91.0
        assert eur_rate == 99.5

    def test_missing_usd_uses_default(self):
        """USD нет в ответе ЦБ -> берём дефолт 90.0"""
        data = {
            "Valute": {
                "EUR": {"Value": 100.0},  # EUR есть
                # USD отсутствует
            }
        }
        result = build_currency_rates(data)

        usd_rate = next((r["rate"] for r in result if r["currency"] == "USD"), None)
        eur_rate = next((r["rate"] for r in result if r["currency"] == "EUR"), None)

        assert usd_rate == 90.0  # дефолт
        assert eur_rate == 100.0  # реальный курс

    def test_missing_eur_uses_default(self):
        """EUR нет в ответе ЦБ -> берём дефолт 98.0"""
        data = {
            "Valute": {
                "USD": {"Value": 92.0},  # USD есть
                # EUR отсутствует
            }
        }
        result = build_currency_rates(data)

        usd_rate = next((r["rate"] for r in result if r["currency"] == "USD"), None)
        eur_rate = next((r["rate"] for r in result if r["currency"] == "EUR"), None)

        assert usd_rate == 92.0  # реальный курс
        assert eur_rate == 98.0  # дефолт

    def test_invalid_rate_type_uses_default(self):
        data = {
            "Valute": {
                "USD": {"Value": "не_число"},
                "EUR": {"Value": 88.0},
            }
        }
        result = build_currency_rates(data)

        usd_rate = next((r["rate"] for r in result if r["currency"] == "USD"), None)
        eur_rate = next((r["rate"] for r in result if r["currency"] == "EUR"), None)

        assert usd_rate == 90.0  # дефолт из-за неверного типа
        assert eur_rate == 88.0

    def test_none_input_returns_defaults(self):
        result = build_currency_rates(None)
        assert len(result) == 2

        usd_rate = next((r["rate"] for r in result if r["currency"] == "USD"), None)
        eur_rate = next((r["rate"] for r in result if r["currency"] == "EUR"), None)

        assert usd_rate == 90.0
        assert eur_rate == 98.0
