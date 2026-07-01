import argparse
import json
import logging
import os
from datetime import datetime
from typing import List, Dict, Any

import pandas as pd
import requests

from src.views import build_main_page_response

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s,%(msecs)03d [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def get_project_root() -> str:
    """
    Возвращает абсолютный путь к корню проекта (папка Курсовая1).
    __file__ — это путь к текущему файлу (src/main.py).
    dirname дважды поднимается на уровень выше: src -> Курсовая1.
    """
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_transactions() -> pd.DataFrame:
    """Загружает operations.xlsx из папки data в корне проекта."""
    project_root = get_project_root()
    file_path = os.path.join(project_root, "data", "operations.xlsx")

    logger.info("Попытка загрузки файла операций: %s", file_path)

    if not os.path.exists(file_path):
        logger.error("Файл не найден! Проверьте, лежит ли operations.xlsx в папке data внутри корня проекта.")
        logger.error("Ожидаемый путь: %s", file_path)
        return pd.DataFrame()

    try:
        df = pd.read_excel(file_path)
        logger.info("Успешно загружено %d операций из Excel.", len(df))
        return df
    except Exception as e:
        logger.exception("Ошибка при чтении Excel: %s", e)
        # Важно: не выбрасываем ошибку дальше, а возвращаем пустой DataFrame.
        # Обработка ошибки на уровне main() решит, что делать дальше.
        return pd.DataFrame()


def load_settings(settings_path: str) -> Dict[str, Any]:
    """Загружает настройки. Если нет — возвращает пустые списки по умолчанию."""
    if not os.path.exists(settings_path):
        logger.warning("Файл настроек %s не найден. Используем значения по умолчанию.", settings_path)
        return {}

    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.exception("Ошибка чтения файла настроек: %s", e)
        return {}


def get_currency_rates(currencies: List[str]) -> List[Dict[str, float]]:
    """Получает курсы валют от ЦБ РФ."""
    logger.info("Запрос курсов валют у ЦБ РФ...")
    url = "https://www.cbr-xml-daily.ru/daily_json.js"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.exception("Не удалось получить курсы валют: %s", e)
        # Fallback логика: возвращаем дефолтные курсы, чтобы приложение не падало
        return [{"currency": c, "rate": 75.0} for c in currencies]

    rates = []
    mapping = {"USD": "USD", "EUR": "EUR"}
    for c in currencies:
        key = mapping.get(c)
        if not key:
            continue
        item = data["Valute"].get(key)
        if item:
            rates.append({"currency": c, "rate": float(item["Value"])})

    logger.info("Курсы валют получены: %s", rates)
    return rates


def generate_stock_prices(stocks: List[str]) -> List[Dict[str, float]]:
    """Генерирует фейковые цены акций для демонстрации."""
    import random

    prices = []
    for s in stocks:
        price = round(random.uniform(100, 3000), 2)
        prices.append({"stock": s, "price": price})
    return prices


def main(cli_args=None):
    """
    Точка входа приложения.

    Args:
        cli_args (list, optional): Список аргументов командной строки для тестирования.
                                   Если None, используются реальные аргументы из sys.argv.
    """
    parser = argparse.ArgumentParser(description="Финансовый отчёт (Курсовая работа)")
    parser.add_argument(
        "--date",
        type=str,
        default=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        help="Дата для фильтрации в формате YYYY-MM-DD HH:MM:SS",
    )

    # Ключевое исправление для тестов:
    if cli_args is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(cli_args)

    logger.info("Запуск приложения...")
    report_date_str = args.date
    logger.info("Дата для фильтрации: %s", report_date_str)

    project_root = get_project_root()
    settings_file_path = os.path.join(project_root, "user_settings.json")

    # --- ИСПРАВЛЕНИЕ: обработка ошибки загрузки транзакций ---
    try:
        transactions = load_transactions()
    except Exception as e:
        # Этот блок нужен на случай, если load_transactions вдруг выбросит исключение,
        # хотя внутри неё уже есть try/except. Это дополнительный уровень защиты.
        logger.exception("Критическая ошибка при загрузке транзакций: %s. Возвращаем пустой DataFrame.", e)
        transactions = pd.DataFrame()
    # ---------------------------------------------------------

    if transactions.empty:
        logger.warning("Нет данных транзакций. Отчёт будет содержать только курсы и акции.")

        settings = load_settings(settings_file_path)
        currencies = settings.get("currencies", ["USD", "EUR"])
        stocks = settings.get("stocks", ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA"])

        # get_currency_rates уже имеет свой try/except внутри, поэтому можно вызывать смело
        currency_rates = get_currency_rates(currencies)
        stock_prices = generate_stock_prices(stocks)

        now = datetime.now()
        response = build_main_page_response(
            transactions=transactions,
            report_date_str=report_date_str,
            now=now,
            stock_prices=stock_prices,
            currency_rates=currency_rates,
        )
        print(json.dumps(response, ensure_ascii=False, indent=2))
        return

    settings = load_settings(settings_file_path)
    currencies = settings.get("currencies", ["USD", "EUR"])
    stocks = settings.get("stocks", ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA"])

    currency_rates = get_currency_rates(currencies)
    stock_prices = generate_stock_prices(stocks)

    now = datetime.now()

    response = build_main_page_response(
        transactions=transactions,
        report_date_str=report_date_str,
        now=now,
        stock_prices=stock_prices,
        currency_rates=currency_rates,
    )

    print("\n--- Главная страница (JSON) ---")
    print(json.dumps(response, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
