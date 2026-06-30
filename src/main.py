import logging
from datetime import datetime
from pathlib import Path
import json

import pandas as pd

from src.utils import load_transactions
from src.views import build_main_page_response
from src.cbr_client import get_cbr_rates_json, build_currency_rates

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    logger.info("Starting application...")

    # Определяем путь к файлу данных относительно этого скрипта
    base_dir = Path(__file__).resolve().parent.parent
    data_path = base_dir / "data" / "operations.xlsx"

    logger.debug("Ожидаемый путь к данным: %s", data_path)

    # 1. Загрузка транзакций из Excel
    if not data_path.exists():
        logger.error("Файл операций не найден: %s", data_path)
        # Создаем пустой DataFrame с нужными колонками, чтобы код не упал дальше
        transactions = pd.DataFrame(columns=["Номер карты", "Дата операции", "Сумма операции", "Категория", "Описание"])
    else:
        try:
            transactions = load_transactions(str(data_path))
            if transactions.empty:
                logger.warning("Файл найден, но он пустой или не содержит валидных данных.")
            else:
                logger.info("Успешно загружено %d операций.", len(transactions))
        except Exception as e:
            logger.critical("Критическая ошибка при чтении Excel файла: %s", e, exc_info=True)
            # Если файл битый, всё равно продолжаем с пустым DF, чтобы увидеть структуру JSON без данных
            transactions = pd.DataFrame(
                columns=["Номер карты", "Дата операции", "Сумма операции", "Категория", "Описание"])

    # 2. Получение курсов валют от ЦБ РФ
    logger.info("Запрос курсов валют у ЦБ РФ...")
    raw_rates = get_cbr_rates_json()
    currency_rates = build_currency_rates(raw_rates)

    # Логируем, что именно получили (дефолт или реальные курсы)
    if raw_rates is None:
        logger.warning("Не удалось получить курсы от ЦБ, используются значения по умолчанию.")
    else:
        logger.info("Курсы валют успешно получены: %s", currency_rates)

    # 3. Дата для отчета
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 4. Акции (заглушка)
    stock_prices = [
        {"stock": "AAPL", "price": 180.0},
        {"stock": "AMZN", "price": 3200.0},
        {"stock": "GOOGL", "price": 140.0},
        {"stock": "MSFT", "price": 380.0},
        {"stock": "TSLA", "price": 250.0},
    ]


    response = build_main_page_response(
        transactions=transactions,
        date_str=date_str,
        stock_prices=stock_prices,
        currency_rates=currency_rates,
    )

    print("\n--- Главная страница (JSON) ---")
    print(json.dumps(response, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
