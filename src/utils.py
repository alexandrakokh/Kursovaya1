import pandas as pd
import logging
from pathlib import Path
import time
import functools

logger = logging.getLogger(__name__)

# Вычисляем путь к папке data относительно расположения этого файла.
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def log_execution_time(func):
    """Декоратор для замера времени выполнения функции."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        duration = end - start
        logger.info("Функция %s выполнена за %.4f сек.", func.__name__, duration)
        return result

    return wrapper


def load_transactions(file_path: str | None = None) -> pd.DataFrame:
    """
    Загружает транзакции из Excel с валидацией типов данных.

    Логика:
    1. Читает Excel.
    2. Парсит даты (приоритет: строгий формат, затем авто-определение).
    3. Удаляет строки с битыми датами.
    4. Приводит суммы к числам, категории — к строкам без пробелов.

    Возвращает: pd.DataFrame или пустой DataFrame при ошибке.
    """
    if file_path is None:
        file_path = DATA_DIR / "operations.xlsx"

    path = Path(file_path)

    if not path.exists():
        logger.error(f"Файл не найден: {path}")
        return pd.DataFrame()

    try:
        df = pd.read_excel(path, sheet_name=0)

        if df.empty:
            logger.warning("Файл найден, но он пустой.")
            return df

        col_date = "Дата операции"
        if col_date not in df.columns:
            logger.error(f"В файле отсутствует колонка '{col_date}'. Проверьте заголовки в Excel.")
            return pd.DataFrame()

        # Строгий формат
        df[col_date] = pd.to_datetime(df[col_date], format="%d.%m.%Y %H:%M:%S", errors="coerce")

        # Авто-определение для оставшихся
        mask_null = df[col_date].isna()
        if mask_null.any():
            logger.warning(
                f"Найдено {mask_null.sum()} дат, не подходящих под формат ДД.ММ.ГГГГ ЧЧ:ММ:СС. "
                f"Пытаемся распознать их автоматически (dayfirst=True)."
            )
            df.loc[mask_null, col_date] = pd.to_datetime(df.loc[mask_null, col_date], dayfirst=True, errors="coerce")

        initial_rows = len(df)
        df = df.dropna(subset=[col_date])
        dropped_rows = initial_rows - len(df)
        if dropped_rows > 0:
            logger.warning(f"Удалено {dropped_rows} строк с некорректными датами.")

        col_amount = "Сумма операции"
        if col_amount in df.columns:
            df[col_amount] = pd.to_numeric(df[col_amount], errors="coerce").fillna(0)
        else:
            logger.error(f"В файле отсутствует колонка '{col_amount}'.")
            return pd.DataFrame()

        col_category = "Категория"
        if col_category in df.columns:
            df[col_category] = df[col_category].astype(str).str.strip()

        required_cols = ["Номер карты", col_date, col_amount, col_category]
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            logger.error(f"Отсутствуют обязательные колонки для работы отчета: {missing_cols}")
            return pd.DataFrame()

        logger.info(f"Успешно загружено и обработано {len(df)} операций.")
        return df

    except Exception as e:
        logger.error(f"Критическая ошибка при чтении файла: {e}")
        return pd.DataFrame()
