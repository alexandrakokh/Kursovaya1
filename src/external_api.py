import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def fetch_currency_rates() -> List[Dict[str, Any]]:
    try:
        # Сюда вставь свой реальный запрос к API (requests.get и т.д.)
        # response = requests.get("...")
        # return response.json()
        raise Exception("API недоступно (для теста)")  # закомментируй, когда будет реальный API
    except Exception as e:
        logger.warning("API курсов валют недоступно. Используем дефолтные значения. Ошибка: %s", e)
        return [
            {"currency": "USD", "rate": 90.0},
            {"currency": "EUR", "rate": 98.0},
        ]

def fetch_stock_prices() -> List[Dict[str, Any]]:
    try:
        # Сюда вставь реальный запрос к API акций
        # ...
        raise Exception("API акций недоступно (для теста)")
    except Exception as e:
        logger.warning("API акций недоступно. Используем дефолтные значения. Ошибка: %s", e)
        return [
            {"stock": "AAPL", "price": 180.0},
            {"stock": "AMZN", "price": 3200.0},
            {"stock": "GOOGL", "price": 140.0},
            {"stock": "MSFT", "price": 380.0},
            {"stock": "TSLA", "price": 250.0},
        ]