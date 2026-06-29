import pandas as pd
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Вычисляем путь к папке data относительно расположения этого файла.
# Если utils.py лежит в src, то parent.parent ведет в корень проекта.
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


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
        # Читаем первый лист Excel
        df = pd.read_excel(path, sheet_name=0)

        if df.empty:
            logger.warning("Файл найден, но он пустой.")
            return df

        # --- 1. Обработка дат ---
        col_date = "Дата операции"

        if col_date not in df.columns:
            logger.error(f"В файле отсутствует колонка '{col_date}'. Проверьте заголовки в Excel.")
            return pd.DataFrame()

        # Попытка 1: Строгий формат (как в твоем примере: 31.12.2021 16:44:00)
        df[col_date] = pd.to_datetime(
            df[col_date],
            format="%d.%m.%Y %H:%M:%S",
            errors="coerce"
        )

        # Попытка 2: Если остались пустые значения (NaT), пробуем угадать формат
        mask_null = df[col_date].isna()
        if mask_null.any():
            logger.warning(
                f"Найдено {mask_null.sum()} дат, не подходящих под формат ДД.ММ.ГГГГ ЧЧ:ММ:СС. "
                f"Пытаемся распознать их автоматически (dayfirst=True)."
            )
            # Исправленная логика: перезаписываем ТОЛЬКО null-значения
            df.loc[mask_null, col_date] = pd.to_datetime(
                df.loc[mask_null, col_date],
                dayfirst=True,
                errors="coerce"
            )

        # Удаляем строки, где дата так и не распарсилась (мусорные данные)
        initial_rows = len(df)
        df = df.dropna(subset=[col_date])
        dropped_rows = initial_rows - len(df)
        if dropped_rows > 0:
            logger.warning(f"Удалено {dropped_rows} строк с некорректными датами.")

        # --- 2. Обработка сумм ---
        col_amount = "Сумма операции"
        if col_amount in df.columns:
            # Превращаем в число, ошибки (текст вместо цифр) заменяем на 0
            df[col_amount] = pd.to_numeric(df[col_amount], errors="coerce").fillna(0)
        else:
            logger.error(f"В файле отсутствует колонка '{col_amount}'.")
            return pd.DataFrame()

        # --- 3. Нормализация категорий ---
        col_category = "Категория"
        if col_category in df.columns:
            # Убираем лишние пробелы по краям и приводим к строке
            df[col_category] = df[col_category].astype(str).str.strip()

        # --- 4. Проверка обязательных колонок для агрегации ---
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