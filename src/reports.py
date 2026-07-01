import pandas as pd
from datetime import datetime
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def _get_spending_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Возвращает DataFrame только с тратами (сумма < 0).
    Это главное исправление, чтобы убрать зарплаты и переводы из отчётов.
    """
    if df.empty:
        return df

    amount_col = "Сумма операции"
    if amount_col not in df.columns:
        # Фолбэк, если колонка называется иначе
        if "Сумма платежа" in df.columns:
            amount_col = "Сумма платежа"
        else:
            logger.error("Не найдена колонка с суммой.")
            return pd.DataFrame()

    # Оставляем только отрицательные суммы (траты)
    spending_df = df[df[amount_col] < 0].copy()
    return spending_df


def spending_by_category(df: pd.DataFrame, category: str) -> dict:
    """
    Считает траты по одной категории.
    """
    spending_df = _get_spending_df(df)

    if spending_df.empty:
        logger.warning("Нет трат для расчёта.")
        return {"category": category, "total_amount": 0.0, "rows": 0}

    # Нормализуем категории: убираем пробелы, приводим к одному регистру для надёжности
    spending_df["Категория_norm"] = spending_df["Категория"].astype(str).str.strip()
    target_category = category.strip()

    filtered = spending_df[spending_df["Категория_norm"] == target_category]

    total = filtered["Сумма операции"].sum()
    rows = len(filtered)

    logger.info(f"spending_by_category: category={category}, rows={rows}")

    result = {"category": target_category, "total_amount": float(total), "rows": rows}

    # Сохраняем отчёт
    _save_report(result, f"spending_by_category_{target_category.replace(' ', '_')}")
    return result


def spending_by_weekday(df: pd.DataFrame) -> dict:
    """
    Траты по дням недели (понедельник=0 ... воскресенье=6).
    """
    spending_df = _get_spending_df(df)

    if spending_df.empty:
        result = {str(i): 0.0 for i in range(7)}
        _save_report(result, "spending_by_weekday")
        return result

    spending_df["day_of_week"] = spending_df["Дата операции"].dt.dayofweek
    grouped = spending_df.groupby("day_of_week")["Сумма операции"].sum().to_dict()

    # Гарантируем наличие всех дней недели (даже если по какому-то дню трат не было)
    full_result = {str(i): float(grouped.get(i, 0.0)) for i in range(7)}

    _save_report(full_result, "spending_by_weekday")
    return full_result


def spending_by_workday(df: pd.DataFrame) -> dict:
    """
    Разделение трат на будни и выходные.
    Будни: пн–пт (0–4), Выходные: сб–вс (5–6).
    """
    spending_df = _get_spending_df(df)

    if spending_df.empty:
        result = {"work": 0.0, "weekend": 0.0}
        _save_report(result, "spending_by_workday")
        return result

    spending_df["day_of_week"] = spending_df["Дата операции"].dt.dayofweek

    work_days = spending_df[spending_df["day_of_week"].between(0, 4)]
    weekend_days = spending_df[spending_df["day_of_week"].between(5, 6)]

    result = {"work": float(work_days["Сумма операции"].sum()), "weekend": float(weekend_days["Сумма операции"].sum())}

    _save_report(result, "spending_by_workday")
    return result


def _save_report(data: dict, filename_prefix: str):
    """
    Вспомогательная функция для сохранения JSON-отчётов.
    """
    reports_dir = Path(__file__).resolve().parent.parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = reports_dir / f"{filename_prefix}_{timestamp}.json"

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info(f"report_logger: saved to {filepath}")
