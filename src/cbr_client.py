import logging
import requests
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


def get_cbr_rates_json() -> Optional[Dict[str, Any]]:
    url = "https://www.cbr-xml-daily.ru/daily_json.js"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        logger.info("Курсы валют успешно получены от ЦБ")
        return data
    except requests.exceptions.RequestException as e:
        logger.error("Не удалось получить курсы валют от ЦБ: %s", e)
        return None


def build_currency_rates(rates_data: Optional[Dict[str, Any]]) -> List[Dict[str, float]]:
    """
    Преобразует сырые данные ЦБ в формат, нужный для main_page_response.
    Если rates_data == None, возвращает дефолтные значения.
    """
    if rates_data is None:
        return [
            {"currency": "USD", "rate": 90.0},
            {"currency": "EUR", "rate": 98.0},
        ]

    valute_map = rates_data.get("Valute", {})
    result = []

    for cur in ("USD", "EUR"):
        val = valute_map.get(cur)
        if val:
            rate = val.get("Value")
            if isinstance(rate, (int, float)):
                result.append({"currency": cur, "rate": float(rate)})
            else:
                logger.warning("Некорректный курс для %s: %s, используем дефолт", cur, rate)
                result.append({"currency": cur, "rate": 90.0 if cur == "USD" else 98.0})
        else:
            logger.warning("Курс для %s не найден в ответе ЦБ, используем дефолт", cur)
            result.append({"currency": cur, "rate": 90.0 if cur == "USD" else 98.0})

    return result
